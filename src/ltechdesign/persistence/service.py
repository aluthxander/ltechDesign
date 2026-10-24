"""Serialized side-effect service suitable for a worker/IO actor, never a GUI callback.

Callers publish a returned admission only after success. Save consumes an immutable
snapshot; the owner applies its returned checkpoint, never substitutes the live model.
"""

import os
import tempfile
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from ltechdesign.commands.dispatcher import SaveCheckpoint, fingerprint
from ltechdesign.domain.errors import ModelError, fail
from ltechdesign.domain.models import DocumentSession, Project, Writer

from .archive import (
    DEFAULT_LIMITS,
    ArchiveLimits,
    LoadedProject,
    check_cancel,
    read_archive,
    write_archive,
)
from .paths import Fingerprint, WriterLock, canonical_path, fingerprint_path, fingerprint_stream


@dataclass(slots=True)
class FileHandle:
    admission: DocumentSession
    loaded: LoadedProject
    path: Path | None = None
    baseline: Fingerprint | None = None
    read_only: bool = False
    _requested: Path | None = None
    _lock: WriterLock | None = None
    _closed: bool = False


@dataclass(frozen=True, slots=True)
class SaveResult:
    path: Path
    checkpoint: SaveCheckpoint
    baseline: Fingerprint
    backup: Path | None = None


class PersistenceService:
    def __init__(self, *, limits: ArchiveLimits = DEFAULT_LIMITS) -> None:
        self.limits = limits
        self._guard = threading.RLock()
        self._handles: list[FileHandle] = []

    def new(self, project: Project, blobs: Mapping[str, bytes]) -> FileHandle:
        """New unsaved lifecycle admission; caller supplies an already valid aggregate."""
        with self._guard:
            handle = FileHandle(DocumentSession(project=project), LoadedProject(project, blobs))
            self._handles.append(handle)
            return handle

    def open(
        self,
        path: str | Path,
        *,
        read_only: bool = False,
        cancelled: Callable[[], bool] | None = None,
    ) -> FileHandle:
        with self._guard:
            requested = Path(path).absolute()
            canonical = canonical_path(requested, writer=not read_only)
            for existing in self._handles:
                if not existing._closed and existing.path == canonical:
                    return existing
            lock = None if read_only else WriterLock(canonical)
            try:
                with canonical.open("rb") as stream:
                    baseline = fingerprint_stream(stream, maximum=self.limits.archive_bytes)
                    loaded = read_archive(stream, limits=self.limits, cancelled=cancelled)
                    if fingerprint_stream(stream, maximum=self.limits.archive_bytes) != baseline:
                        fail("changed_during_load", code="external_change_conflict")
                if (
                    canonical_path(requested, writer=not read_only) != canonical
                    or fingerprint_path(canonical, maximum=self.limits.archive_bytes) != baseline
                ):
                    fail("changed_during_load", code="external_change_conflict")
                check_cancel(cancelled)
                handle = FileHandle(
                    DocumentSession(project=loaded.project),
                    loaded,
                    canonical,
                    baseline,
                    read_only,
                    requested,
                    lock,
                )
                self._handles.append(handle)
                return handle
            except BaseException as error:
                if lock is not None:
                    lock.close()
                if isinstance(error, OSError):
                    raise ModelError("open_failed", code="io_error") from error
                raise

    def _active(self, handle: FileHandle) -> None:
        if handle._closed or not any(h is handle for h in self._handles):
            fail("session_closed", code="session_closed")

    def _unchanged(self, requested: Path, path: Path, baseline: Fingerprint | None) -> None:
        if canonical_path(requested, writer=True) != path:
            fail("path_retargeted", code="external_change_conflict")
        if fingerprint_path(path, maximum=self.limits.archive_bytes) != baseline:
            fail("external_file_changed", code="external_change_conflict")

    def _backup(self, path: Path, baseline: Fingerprint) -> Path:
        """Exclusive, durable old-byte backup; never overwrite a previous migration backup."""
        backup = path.with_name(path.name + ".pre-migration-" + baseline.digest[:16] + ".bak")
        created = False
        try:
            with backup.open("xb") as target:
                created = True
                with path.open("rb") as source:
                    size = 0
                    while chunk := source.read(65536):
                        size += len(chunk)
                        if size > self.limits.archive_bytes:
                            fail("backup_source_grew", code="external_change_conflict")
                        target.write(chunk)
                target.flush()
                os.fsync(target.fileno())
            saved = fingerprint_path(backup, maximum=self.limits.archive_bytes)
            if saved is None or saved.digest != baseline.digest or saved.size != baseline.size:
                fail("backup_source_changed", code="external_change_conflict")
            return backup
        except FileExistsError:
            existing = fingerprint_path(backup, maximum=self.limits.archive_bytes)
            if (
                backup.is_symlink()
                or existing is None
                or existing.digest != baseline.digest
                or existing.size != baseline.size
            ):
                fail("backup_collision", code="io_error")
            return backup
        except BaseException:
            if created:
                backup.unlink(missing_ok=True)
            raise

    def save(
        self,
        handle: FileHandle,
        snapshot: DocumentSession,
        blobs: Mapping[str, bytes],
        *,
        target: str | Path | None = None,
        overwrite: bool = False,
        migration_backup: bool = False,
        cancelled: Callable[[], bool] | None = None,
    ) -> SaveResult:
        """Atomic save/Save As. Explicit overwrite intent only applies to a different target.

        A future migrator must set migration_backup before writing migrated data to
        its original source. There are no supported historical migration edges yet.
        Cancellation is checked before replacement only; success is final afterwards.
        """
        with self._guard:
            self._active(handle)
            if (
                snapshot.session_id != handle.admission.session_id
                or snapshot.project.document.document_id
                != handle.admission.project.document.document_id
            ):
                fail("snapshot_session_mismatch", code="session_closed")
            requested = Path(target).absolute() if target is not None else handle._requested
            if requested is None:
                fail("save_target_required", code="path_not_allowed")
            path = canonical_path(requested, writer=True)
            if target is None and path != handle.path:
                fail("source_path_retargeted", code="external_change_conflict")
            same = path == handle.path
            if same and handle.read_only:
                fail("read_only_source", code="read_only")
            new_lock: WriterLock | None = None
            temporary: Path | None = None
            backup: Path | None = None
            try:
                if same:
                    baseline = handle.baseline
                else:
                    if any(
                        h is not handle and not h._closed and h.path == path for h in self._handles
                    ):
                        fail("target_in_use", code="target_in_use")
                    new_lock = WriterLock(path)
                    baseline = fingerprint_path(path, maximum=self.limits.archive_bytes)
                    if baseline is not None and (not overwrite or handle.read_only):
                        fail("target_exists", code="target_in_use")
                self._unchanged(requested, path, baseline)
                if same and handle._requested is not None:
                    self._unchanged(handle._requested, path, baseline)
                checkpoint = SaveCheckpoint(
                    snapshot.session_id, snapshot.revision, fingerprint(snapshot.project)
                )
                project = replace(
                    snapshot.project,
                    manifest=replace(
                        snapshot.project.manifest,
                        saved_revision=snapshot.revision,
                        saved_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        writer=Writer(name="ltechDesign Studio", version="0.1.0"),
                    ),
                )
                # Until a renderer can generate a thumbnail for this exact snapshot,
                # do not label an admission's old preview as the newly saved revision.
                if checkpoint.digest != fingerprint(handle.loaded.project):
                    previews = {p for p in project.opaque_files if p.startswith("thumbnails/")}
                    if previews:
                        project = replace(
                            project,
                            manifest=replace(
                                project.manifest,
                                files=tuple(
                                    e for e in project.manifest.files if e.path not in previews
                                ),
                                optional_capabilities=tuple(
                                    c
                                    for c in project.manifest.optional_capabilities
                                    if c != "preview.thumbnail/1"
                                ),
                            ),
                            opaque_files={
                                p: b for p, b in project.opaque_files.items() if p not in previews
                            },
                        )
                # Defensive copy pins byte references even if a caller later releases its lease.
                pinned = dict(blobs)
                fd, name = tempfile.mkstemp(prefix=".ltechdesign-", suffix=".tmp", dir=path.parent)
                temporary = Path(name)
                with os.fdopen(fd, "w+b") as stream:
                    write_archive(stream, project, pinned, limits=self.limits, cancelled=cancelled)
                    stream.flush()
                    os.fsync(stream.fileno())
                    stream.seek(0)
                    read_archive(stream, limits=self.limits, cancelled=cancelled)
                    saved = fingerprint_stream(stream, maximum=self.limits.archive_bytes)
                self._unchanged(requested, path, baseline)
                if migration_backup and same and baseline is not None:
                    backup = self._backup(path, baseline)
                # Last cancellation hook precedes final baseline check and commit barrier.
                check_cancel(cancelled)
                self._unchanged(requested, path, baseline)
                if same and handle._requested is not None:
                    self._unchanged(handle._requested, path, baseline)
                result = SaveResult(path, checkpoint, saved, backup)
                os.replace(temporary, path)
                # No fallible filesystem work or cancellation after publication.
                temporary = None
                old_lock = handle._lock
                handle.path, handle.baseline, handle._requested = path, saved, requested
                handle.read_only = False
                if not same:
                    handle._lock, new_lock = new_lock, None
                    if old_lock is not None:
                        old_lock.close()
                return result
            except OSError as error:
                raise ModelError("save_failed", code="io_error") from error
            finally:
                try:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
                finally:
                    if new_lock is not None:
                        new_lock.close()

    def reload(self, handle: FileHandle) -> FileHandle:
        """Validate replacement admission before updating any existing handle state."""
        with self._guard:
            self._active(handle)
            if handle.path is None:
                fail("reload_requires_path", code="path_not_allowed")
            staging = PersistenceService(limits=self.limits)
            candidate = staging.open(handle._requested or handle.path, read_only=True)
            try:
                if candidate.path != handle.path:
                    fail("path_retargeted", code="external_change_conflict")
                handle.admission = candidate.admission
                handle.loaded = candidate.loaded
                handle.baseline = candidate.baseline
            finally:
                staging.close(candidate)
            return handle

    def close(self, handle: FileHandle) -> None:
        with self._guard:
            self._active(handle)
            if handle._lock is not None:
                handle._lock.close()
            handle._closed = True
            self._handles = [h for h in self._handles if h is not handle]
