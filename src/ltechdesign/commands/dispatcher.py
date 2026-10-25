"""One owner-thread content dispatcher; immutable publication and bounded runtime retry."""

import hashlib
import json
import logging
import sys
import threading
import time
from collections.abc import Callable, Mapping
from concurrent.futures import Future
from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import UTC, datetime
from typing import Any

from ltechdesign.domain.codec import MAX_JSON_BYTES, semantic_content
from ltechdesign.domain.errors import ModelError, fail
from ltechdesign.domain.models import (
    MAX_REVISION,
    Asset,
    AssetId,
    DocumentSession,
    NodeId,
    Project,
    SessionId,
)
from ltechdesign.domain.typing import check_record, primitive
from ltechdesign.domain.typography import require_metrics

from .contracts import Error, RegisterAsset, Request, Result
from .planning import Draft
from .retention import AssetRetention, MetadataOnlyRetention, PreparedAssets

LOG = logging.getLogger(__name__)


def canonical(value: Any) -> bytes:
    """Typed defaults are present; sorted keys, 1 == 1.0 and signed zero normalized."""

    def normalize(item: Any) -> Any:
        if isinstance(item, bytes):
            return {"$bytes": item.hex()}
        if isinstance(item, float) and item.is_integer():
            return int(item)
        if isinstance(item, dict):
            return {k: normalize(v) for k, v in item.items()}
        if isinstance(item, (list, tuple)):
            return [normalize(v) for v in item]
        return item

    return json.dumps(
        normalize(value), sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")


def fingerprint(project: Project) -> str:
    return hashlib.sha256(canonical(semantic_content(project))).hexdigest()


def retained_size(value: object, seen: set[int] | None = None) -> int:
    """Conservative Python object-graph charge, not a serialized-byte memory estimate.

    Each entry is charged independently (shared snapshots overcount safely).
    Asset bytes live in the external store; opaque extension bytes are counted here.
    """
    seen = set() if seen is None else seen
    if id(value) in seen:
        return 0
    seen.add(id(value))
    size = sys.getsizeof(value)
    if is_dataclass(value) and not isinstance(value, type):
        size += sum(retained_size(getattr(value, f.name), seen) for f in fields(value))
    elif isinstance(value, Mapping):
        # MappingProxyType's getsizeof omits its owned dictionary table.
        size += sys.getsizeof(dict(value))
        size += sum(retained_size(k, seen) + retained_size(v, seen) for k, v in value.items())
    elif isinstance(value, (tuple, list)):
        size += sum(retained_size(v, seen) for v in value)
    return size


@dataclass(frozen=True, slots=True)
class HistoryMetadata:
    action_name: str
    source: str
    timestamp: str
    request_id: str


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    before: Project
    after: Project
    metadata: HistoryMetadata
    charge: int


@dataclass(frozen=True, slots=True)
class ChangeEvent:
    snapshot: DocumentSession
    action: str
    metadata: HistoryMetadata
    dirty: bool
    history_evicted: int


@dataclass(frozen=True, slots=True)
class SaveCheckpoint:
    session_id: SessionId
    revision: int
    digest: str


@dataclass(frozen=True, slots=True)
class _State:
    snapshot: DocumentSession
    undo: tuple[HistoryEntry, ...] = ()
    redo: tuple[HistoryEntry, ...] = ()


@dataclass(slots=True)
class _Receipt:
    digest: str
    future: Future[Result]
    completed_at: float | None = None


class Dispatcher:
    def __init__(
        self,
        session: DocumentSession,
        *,
        initially_saved: bool = False,
        history_budget: int = 128 * 1024 * 1024,
        dedup_capacity: int = 4096,
        retention_seconds: float = 1800,
        clock: Callable[[], float] = time.monotonic,
        assets: AssetRetention | None = None,
        layout: Callable[[Project], Project] | None = None,
        text_layout: Callable[[Project, Project], Project] | None = None,
        read_only: bool = False,
    ) -> None:
        if (
            type(history_budget) is not int
            or type(dedup_capacity) is not int
            or history_budget < 0
            or dedup_capacity < 1
            or not 1800 <= retention_seconds < float("inf")
        ):
            raise ValueError("Invalid history/dedup budget or retention below 30 minutes")
        self._owner = threading.get_ident()
        self._state = _State(session)
        self._clean = fingerprint(session.project) if initially_saved else None
        self._fingerprint_project: Project | None = session.project if initially_saved else None
        self._fingerprint_value: str | None = self._clean
        self._history_budget = history_budget
        self._capacity = dedup_capacity
        self._retention = retention_seconds
        self._clock = clock
        self._assets = assets if assets is not None else MetadataOnlyRetention()
        self._layout = layout if layout is not None else lambda project: project
        self._text_layout = text_layout if text_layout is not None else require_metrics
        self._read_only = read_only
        self._closed = False
        self._busy = False
        self._receipts: dict[tuple[str, str], _Receipt] = {}
        self._listeners: list[Callable[[ChangeEvent], None]] = []
        self._history_group: tuple[str, str] | None = None
        lease = self._assets.prepare(self._roots(self._state), {})
        lease.commit()

    def _check_owner(self) -> None:
        if threading.get_ident() != self._owner:
            raise RuntimeError(
                "Dispatcher must run on its owner thread; enqueue through the adapter"
            )

    @property
    def snapshot(self) -> DocumentSession:
        return self._state.snapshot

    @property
    def dirty(self) -> bool:
        if self._clean is None:
            return True
        project = self.snapshot.project
        if project is not self._fingerprint_project:
            self._fingerprint_value = fingerprint(project)
            self._fingerprint_project = project
        return self._fingerprint_value != self._clean

    @property
    def undo_history(self) -> tuple[HistoryEntry, ...]:
        return self._state.undo

    @property
    def redo_history(self) -> tuple[HistoryEntry, ...]:
        return self._state.redo

    @property
    def history_bytes(self) -> int:
        return sum(e.charge for e in self._state.undo + self._state.redo)

    def subscribe(self, listener: Callable[[ChangeEvent], None]) -> Callable[[], None]:
        self._check_owner()
        self._listeners.append(listener)

        def unsubscribe() -> None:
            self._check_owner()
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    def capture_checkpoint(self) -> SaveCheckpoint:
        self._check_owner()
        self._history_group = None
        return SaveCheckpoint(
            self.snapshot.session_id, self.snapshot.revision, fingerprint(self.snapshot.project)
        )

    def end_history_group(self) -> None:
        """A side-effect snapshot is an undo boundary even before its job finishes."""
        self._check_owner()
        self._history_group = None

    def mark_saved(self, checkpoint: SaveCheckpoint) -> None:
        """Called only after the save job's successful barrier, with its captured checkpoint."""
        self._check_owner()
        if self._closed or checkpoint.session_id != self.snapshot.session_id:
            raise ValueError("Checkpoint belongs to another/closed admission")
        if not 0 <= checkpoint.revision <= self.snapshot.revision:
            raise ValueError("Invalid checkpoint revision")
        self._clean = checkpoint.digest
        self._history_group = None  # keep the saved state reachable with Undo

    def _error(self, code: str, message: str, **details: str) -> Result:
        return Result(
            self.snapshot.session_id,
            self.snapshot.project.document.document_id,
            self.snapshot.revision,
            Error(
                code,
                message,
                tuple(sorted(details.items())),
                current_revision=self.snapshot.revision,
            ),
        )

    def dispatch(
        self, request: Request, *, client_id: str, cancelled: Callable[[], bool] | None = None
    ) -> Result:
        future = self.submit(request, client_id=client_id, cancelled=cancelled)
        if not future.done():
            raise RuntimeError(
                "Reentrant caller must await submit's shared Future outside this stack"
            )
        return future.result()

    def submit(
        self, request: Request, *, client_id: str, cancelled: Callable[[], bool] | None = None
    ) -> Future[Result]:
        """Owner-thread synchronous engine, with a shared Future for in-flight retries.

        IPC must marshal to this owner. There is no thread-pool mutation of a live model.
        Nested new commands are rejected; identical in-flight retry joins the receipt.
        """
        self._check_owner()

        def done(result: Result) -> Future[Result]:
            future: Future[Result] = Future()
            future.set_result(result)
            return future

        try:
            if type(request) is not Request or type(client_id) is not str or not client_id:
                fail("invalid_request")
            check_record(request)
            if request.action != "execute" and request.operations:
                fail("history_action_has_operations")
            if request.action == "execute" and not request.operations:
                fail("empty_batch")
            if len(request.operations) > 100:
                fail("batch_limit", code="limit_exceeded")
            payload = primitive(request)
            # Dataclass operation name discriminates equal-shaped intents (Delete/Ungroup).
            payload["operations"] = [
                {"operation": type(op).__name__, "arguments": primitive(op)}
                for op in request.operations
            ]
            encoded = canonical(payload)
            if len(encoded) > MAX_JSON_BYTES:
                fail("payload_limit", code="limit_exceeded")
        except (ModelError, ValueError, TypeError) as error:
            code = (
                error.code
                if isinstance(error, ModelError) and error.code == "limit_exceeded"
                else "validation_error"
            )
            return done(self._error(code, "Invalid request envelope"))
        if self._closed or request.session_id != self.snapshot.session_id:
            return done(self._error("session_closed", "Session is not active"))
        now = self._clock()
        self._receipts = {
            key: receipt
            for key, receipt in self._receipts.items()
            if receipt.completed_at is None or now - receipt.completed_at < self._retention
        }
        key = (client_id, request.request_id)
        digest = hashlib.sha256(encoded).hexdigest()
        if key in self._receipts:
            receipt = self._receipts[key]
            if receipt.digest != digest:
                return done(
                    self._error("request_id_conflict", "Request ID has a different payload")
                )
            return receipt.future
        if len(self._receipts) >= self._capacity:
            return done(
                self._error("dedup_capacity_exceeded", "Unexpired receipts fill the ledger")
            )
        if self._busy:
            return done(self._error("queue_full", "Owner is committing; enqueue a later request"))
        receipt = _Receipt(digest, Future())
        # Consumers cannot cancel the owner operation by cancelling a returned Future.
        receipt.future.set_running_or_notify_cancel()
        self._receipts[key] = receipt
        self._busy = True
        event: ChangeEvent | None = None
        try:
            result, event = self._execute(request, cancelled, client_id)
        except Exception:
            LOG.exception("Unexpected transaction planning failure")
            result = self._error("internal_error", "Transaction could not be prepared")
        receipt.completed_at = self._clock()
        receipt.future.set_result(result)
        # Keep the reentrancy barrier through callbacks: every subscriber sees this revision.
        try:
            if event is not None:
                for listener in tuple(self._listeners):
                    try:
                        listener(event)
                    except Exception:
                        LOG.exception("Post-commit listener failed")
        finally:
            self._busy = False
        return receipt.future

    @staticmethod
    def _roots(state: _State) -> dict[AssetId, Asset]:
        projects = [state.snapshot.project]
        for entry in state.undo + state.redo:
            projects.extend((entry.before, entry.after))
        roots: dict[AssetId, Asset] = {}
        for project in projects:
            for asset in project.assets.assets:
                if asset.id in roots and roots[asset.id] != asset:
                    fail("asset_identity_reused")
                roots[asset.id] = asset
        return roots

    def _execute(
        self, request: Request, cancelled: Callable[[], bool] | None, client_id: str
    ) -> tuple[Result, ChangeEvent | None]:
        staged: dict[str, Asset] = {}
        lease: PreparedAssets | None = None
        try:
            for op in request.operations:
                if isinstance(op, RegisterAsset):
                    if op.staging_id in staged:
                        fail("duplicate_staging_id")
                    staged[op.staging_id] = op.asset
            if self._read_only:
                fail("Session is read-only", code="read_only")
            if request.expected_revision != self.snapshot.revision:
                fail("Expected revision is stale", code="revision_conflict")
            if self.snapshot.revision == MAX_REVISION:
                fail("Revision exhausted; reopen admission", code="limit_exceeded")
            if cancelled is not None and cancelled():
                fail("Cancelled before preparation", code="cancelled")
            before = self.snapshot.project
            undo, redo = self._state.undo, self._state.redo
            metadata = HistoryMetadata(
                request.action_name,
                request.source,
                datetime.now(UTC).isoformat(),
                request.request_id,
            )
            id_map: tuple[tuple[NodeId, NodeId], ...] = ()
            group = (
                (client_id, request.history_group)
                if request.action == "execute" and request.source == "GUI" and request.history_group
                else None
            )
            if request.action == "execute":
                draft = Draft(before)
                for op in request.operations:
                    draft.apply(op)
                planned = draft.finish()
                reflowed = self._text_layout(before, planned)
                after = self._layout(reflowed)
                if (
                    type(after) is not Project
                    or after.document.document_id != before.document.document_id
                ):
                    fail("invalid_layout_result")
                if after.workspace != planned.workspace:
                    fail("layout_changed_session_state")
                # Re-run the aggregate boundary even for custom layout implementations.
                after = replace(after)
                id_map = tuple(draft.id_map)
                history_before = before
                if group is not None and group == self._history_group and undo and not redo:
                    history_before, undo = undo[-1].before, undo[:-1]
                entry = HistoryEntry(
                    history_before,
                    after,
                    metadata,
                    retained_size((history_before, after, metadata)) + 128,
                )
                undo, redo = undo + (entry,), ()
            elif request.action == "undo":
                if not undo:
                    fail("No undo entry", code="history_empty")
                entry = undo[-1]
                after, undo, redo = entry.before, undo[:-1], redo + (entry,)
            else:
                if not redo:
                    fail("No redo entry", code="history_empty")
                entry = redo[-1]
                after, undo, redo = entry.after, undo + (entry,), redo[:-1]
            evicted = 0
            while sum(e.charge for e in undo + redo) > self._history_budget:
                if undo:
                    undo = undo[1:]
                else:
                    redo = redo[1:]
                evicted += 1
            snapshot = replace(self.snapshot, project=after, revision=self.snapshot.revision + 1)
            state = _State(snapshot, undo, redo)
            roots = self._roots(state)
            result = Result(
                snapshot.session_id,
                after.document.document_id,
                snapshot.revision,
                id_map=id_map,
                history_evicted=evicted,
            )
            after_fingerprint = fingerprint(after)
            event = ChangeEvent(
                snapshot, request.action, metadata, after_fingerprint != self._clean, evicted
            )
            lease = self._assets.prepare(roots, staged)
            if cancelled is not None and cancelled():
                fail("Cancelled before commit", code="cancelled")
        except ModelError as error:
            if lease is not None:
                lease.abort()
            else:
                self._assets.discard(staged)
            code = "validation_error" if error.code == "invalid_project" else error.code
            return self._error(code, error.reason, path=error.path), None
        except Exception:
            if lease is not None:
                lease.abort()
            else:
                self._assets.discard(staged)
            raise
        # Everything fallible has completed. Adapter commit is a non-throwing root swap.
        lease.commit()
        self._state = state
        self._history_group = group
        self._fingerprint_project, self._fingerprint_value = after, after_fingerprint
        return result, event

    def set_read_only(self, value: bool) -> None:
        """Lifecycle owner promotes only after successful Save As."""
        self._check_owner()
        if self._busy or self._closed:
            raise RuntimeError("Session unavailable")
        self._read_only = value

    def clear_history(self) -> None:
        """Safe explicit budget cleanup without a content revision or content success event."""
        self._check_owner()
        if self._busy:
            raise RuntimeError("Cannot clear history during a commit")
        state = _State(self.snapshot)
        lease = self._assets.prepare(self._roots(state), {})
        lease.commit()
        self._state = state
        self._history_group = None

    def close(self) -> None:
        """Lifecycle caller must drain jobs first; their independent store leases survive."""
        self._check_owner()
        if self._busy:
            raise RuntimeError("Cannot close during a commit")
        lease = self._assets.prepare({}, {})
        lease.commit()
        self._state = _State(self.snapshot)
        self._receipts.clear()
        self._listeners.clear()
        self._closed = True
