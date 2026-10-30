"""Bounded local raster jobs: pinned snapshots, worker processes and atomic per-file commit."""

import hashlib
import json
import multiprocessing
import os
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any
from uuid import uuid4

from ltechdesign.assets.store import BlobLease, BlobStore
from ltechdesign.domain.errors import ModelError, fail
from ltechdesign.domain.models import DocumentSession
from ltechdesign.persistence.archive import write_archive
from ltechdesign.persistence.paths import WriterLock, canonical_path, fingerprint_path

from .contracts import TERMINAL, ExportOptions, JobStatus, OutputResult
from .worker import render_worker


@dataclass
class _Job:
    status: JobStatus
    cancel: threading.Event
    created: float
    finished: float | None = None
    final_status: JobStatus | None = None


class ExportService:
    """GUI calls grant_directory only after explicit user destination choice.

    Local API callers must supply authorized roots. Future MCP transport must reuse
    those grants and authenticated client IDs, not silently expand its filesystem scope.
    """

    def __init__(
        self,
        *,
        allowed_roots: tuple[Path, ...] = (),
        max_pixels: int = 64_000_000,
        max_queued: int = 16,
        ledger_capacity: int = 128,
        max_outputs: int = 256,
        prefer_pillow_webp: bool = False,
    ) -> None:
        for value, maximum in (
            (max_pixels, 64_000_000),
            (max_queued, 16),
            (ledger_capacity, 1024),
            (max_outputs, 256),
        ):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError("Export limits must be positive and cannot exceed safe defaults")
        self.max_pixels, self.max_queued = max_pixels, max_queued
        self.ledger_capacity, self.max_outputs = ledger_capacity, max_outputs
        self.prefer_pillow_webp = prefer_pillow_webp
        self._guard = threading.RLock()
        self._roots: set[Path] = set()
        self._jobs: dict[str, _Job] = {}
        self._requests: dict[tuple[str, str, str], tuple[str, str]] = {}
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="raster-export")
        self._closed = False
        for root in allowed_roots:
            self.grant_directory(root)

    def grant_directory(self, path: Path) -> None:
        root = path.resolve(strict=True)
        if not root.is_dir():
            fail("output_folder_required", code="path_not_allowed")
        with self._guard:
            self._roots.add(root)

    def _allowed(self, path: Path) -> None:
        if not any(path.is_relative_to(root) for root in self._roots):
            fail("output_outside_allowed_roots", code="path_not_allowed")

    def _expire(self) -> None:
        expired = {
            key
            for key, job in self._jobs.items()
            if job.finished is not None and time.monotonic() - job.finished >= 1800
        }
        for key in expired:
            del self._jobs[key]
        self._requests = {
            scope: result for scope, result in self._requests.items() if result[1] not in expired
        }

    def submit(
        self,
        snapshot: DocumentSession,
        store: BlobStore,
        options: ExportOptions,
        *,
        expected_revision: int,
        request_id: str,
        client_id: str = "local-user",
    ) -> JobStatus:
        options.validate()
        if not request_id or len(request_id) > 256 or not client_id or len(client_id) > 256:
            fail("invalid_request_identity", code="validation_error")
        digest = hashlib.sha256(
            json.dumps(
                {"options": asdict(options), "expected_revision": expected_revision},
                sort_keys=True,
                allow_nan=False,
            ).encode()
        ).hexdigest()
        scope = (client_id, snapshot.session_id, request_id)
        with self._guard:
            if self._closed:
                fail("export_service_closed", code="session_closed")
            self._expire()
            previous = self._requests.get(scope)
            if previous is not None:
                if previous[0] != digest:
                    fail("request_payload_changed", code="request_id_conflict")
                return self._jobs[previous[1]].status
            if type(expected_revision) is not int or expected_revision != snapshot.revision:
                fail(
                    "snapshot_revision_changed",
                    code="revision_conflict",
                    current_revision=snapshot.revision,
                )
            if len(self._jobs) >= self.ledger_capacity:
                fail("export_result_retention_full", code="dedup_capacity_exceeded")
            active = sum(j.status.state not in TERMINAL for j in self._jobs.values())
            if active >= self.max_queued + 1:
                fail("export_queue_full", code="queue_full")
            folder = Path(options.folder).resolve(strict=True)
            if not folder.is_dir():
                fail("output_folder_required", code="path_not_allowed")
            self._allowed(folder)
            lease = store.pin(snapshot.project.assets.assets)
            status = JobStatus(
                str(uuid4()),
                snapshot.session_id,
                snapshot.project.document.document_id,
                snapshot.revision,
                dpi=options.dpi,
            )
            job = _Job(status, threading.Event(), time.monotonic())
            self._jobs[status.id] = job
            self._requests[scope] = digest, status.id
            try:
                self._executor.submit(self._run, job, snapshot, lease, options, folder)
            except Exception:
                lease.release()
                del self._jobs[status.id]
                del self._requests[scope]
                raise
            return status

    def get_job_status(self, job_id: str) -> JobStatus:
        with self._guard:
            self._expire()
            job = self._jobs.get(job_id)
            if job is None:
                fail("export_job_not_found", code="job_not_found")
            return job.status

    def cancel_job(self, job_id: str) -> JobStatus:
        with self._guard:
            job = self._jobs.get(job_id)
            if job is None:
                fail("export_job_not_found", code="job_not_found")
            if job.status.state not in TERMINAL:
                job.cancel.set()
                job.status = replace(job.status, cancel_requested=True)
            return job.status

    def _update(self, job: _Job, **values: Any) -> None:
        with self._guard:
            status = replace(job.status, **values)
            if status.state in TERMINAL:
                job.final_status = status
            else:
                job.status = status

    def _check_cancel(self, job: _Job) -> None:
        if job.cancel.is_set():
            fail("export_cancel_requested", code="cancelled")

    def _run(
        self,
        job: _Job,
        snapshot: DocumentSession,
        lease: BlobLease,
        options: ExportOptions,
        folder: Path,
    ) -> None:
        child = None
        parent = None
        locks: list[WriterLock] = []
        temporary: list[Path] = []
        outputs: list[OutputResult] = []
        paths: list[Path] = []
        baselines = []
        scratch = None
        try:
            self._check_cancel(job)
            self._update(job, state="running", phase="snapshot")
            scratch = tempfile.TemporaryDirectory(prefix="ltechdesign-export-")
            source = Path(scratch.name) / "snapshot.ltechdesign"
            with source.open("w+b") as stream:
                write_archive(
                    stream, snapshot.project, lease.blobs, cancelled=lambda: job.cancel.is_set()
                )
            self._check_cancel(job)
            context = multiprocessing.get_context("spawn")
            parent, remote = context.Pipe()
            child = context.Process(
                target=render_worker,
                args=(
                    str(source),
                    options,
                    remote,
                    self.max_pixels,
                    self.max_outputs,
                    self.prefer_pillow_webp,
                ),
                daemon=True,
            )
            child.start()
            remote.close()
            last_message = time.monotonic()
            while True:
                self._check_cancel(job)
                if not parent.poll(0.03):
                    if not child.is_alive():
                        fail("render_worker_exited", code="render_failed")
                    if time.monotonic() - last_message > 300:
                        fail("render_worker_timeout", code="render_failed")
                    continue
                try:
                    message = parent.recv()
                except EOFError:
                    fail("render_worker_exited", code="render_failed")
                last_message = time.monotonic()
                kind = message[0]
                if kind == "progress":
                    self._update(
                        job,
                        progress=max(job.status.progress, min(0.99, message[1])),
                        phase=message[2],
                    )
                elif kind == "plans":
                    for metadata in message[1]:
                        path = canonical_path(folder / metadata["name"], writer=True)
                        self._allowed(path)
                        locks.append(WriterLock(path))
                        baseline = fingerprint_path(path, maximum=512 * 1024 * 1024)
                        if baseline is not None and not options.overwrite:
                            fail("export_target_exists", code="target_in_use", name=path.name)
                        paths.append(path)
                        baselines.append(baseline)
                        fd, name = tempfile.mkstemp(
                            prefix=".ltechdesign-export-", suffix=".tmp", dir=folder
                        )
                        os.close(fd)
                        temporary.append(Path(name))
                        outputs.append(OutputResult(**metadata, state="not_attempted"))
                    self._update(job, outputs=tuple(outputs))
                    parent.send([str(p) for p in temporary])
                elif kind in ("ready", "output_error"):
                    index = message[1]
                    try:
                        if kind == "output_error":
                            raise ModelError(message[3], code=message[2])
                        self._check_cancel(job)
                        if (
                            Path(options.folder).resolve(strict=True) != folder
                            or canonical_path(folder / outputs[index].name, writer=True)
                            != paths[index]
                            or fingerprint_path(paths[index], maximum=512 * 1024 * 1024)
                            != baselines[index]
                        ):
                            fail("export_target_changed", code="external_change_conflict")
                        # cancel_job shares this lock: an acknowledged late cancel cannot
                        # turn a published file into a purported rollback.
                        with self._guard:
                            self._check_cancel(job)
                            os.replace(temporary[index], paths[index])
                            outputs[index] = replace(
                                outputs[index],
                                state="succeeded",
                                path=str(paths[index]),
                                encoder=message[2],
                                notes=message[3],
                            )
                            job.status = replace(
                                job.status,
                                outputs=tuple(outputs),
                                progress=(index + 1) / len(outputs),
                            )
                    except (ModelError, OSError) as error:
                        if isinstance(error, ModelError) and error.code == "cancelled":
                            raise
                        code = error.code if isinstance(error, ModelError) else "io_error"
                        outputs[index] = replace(
                            outputs[index], state="failed", error=code, message=str(error)
                        )
                        self._update(job, outputs=tuple(outputs))
                    parent.send("continue")
                elif kind == "error":
                    raise ModelError(message[2], code=message[1])
                elif kind == "done":
                    failed = next((o for o in outputs if o.state == "failed"), None)
                    self._update(
                        job,
                        state="failed" if failed else "succeeded",
                        progress=1,
                        phase="finished",
                        error=failed.error if failed else None,
                        message="Some outputs failed; see per-file report." if failed else None,
                    )
                    break
        except Exception as error:
            cancelled = isinstance(error, ModelError) and error.code == "cancelled"
            committed = any(o.state == "succeeded" for o in outputs)
            failure = next((o for o in outputs if o.state == "failed"), None)
            outputs = [
                replace(o, state="cancelled") if cancelled and o.state == "not_attempted" else o
                for o in outputs
            ]
            self._update(
                job,
                state=("failed" if failure else "succeeded" if committed else "cancelled")
                if cancelled
                else "failed",
                phase="finished",
                outputs=tuple(outputs),
                error=(failure.error if failure else None)
                if cancelled
                else error.code
                if isinstance(error, ModelError)
                else "io_error",
                message=(
                    "Cancelled remaining outputs; published files retained."
                    if cancelled and committed
                    else str(error)
                ),
            )
        finally:
            if parent is not None:
                parent.close()
            if child is not None and child.pid is not None:
                if child.is_alive():
                    child.terminate()
                child.join(5)
                if child.is_alive():
                    child.kill()
                    child.join()
                child.close()
            for path in temporary:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            for lock in reversed(locks):
                lock.close()
            if scratch is not None:
                try:
                    scratch.cleanup()
                except OSError:
                    pass
            lease.release()
            with self._guard:
                job.finished = time.monotonic()
                assert job.final_status is not None
                job.status = replace(job.final_status, cancel_requested=job.status.cancel_requested)

    def active_for(self, session_id: str | None = None) -> tuple[JobStatus, ...]:
        with self._guard:
            return tuple(
                j.status
                for j in self._jobs.values()
                if j.status.state not in TERMINAL
                and (session_id is None or j.status.session_id == session_id)
            )

    def shutdown(self) -> None:
        with self._guard:
            self._closed = True
            for job in self._jobs.values():
                if job.status.state not in TERMINAL:
                    job.cancel.set()
                    job.status = replace(job.status, cancel_requested=True)
        self._executor.shutdown(wait=False)
