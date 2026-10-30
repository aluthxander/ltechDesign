"""Basic crash recovery: immutable generations, independent of source-file ownership.

Only a renamed complete generation is published. Two generations are retained;
staging debris is never offered. An owner lock excludes live applications and is
held across startup decisions. Recovery archives contain their own asset closure,
so process-local GC and original asset folders are irrelevant after publication.
"""

import json
import os
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from ltechdesign.commands.dispatcher import fingerprint
from ltechdesign.domain.errors import ModelError, fail
from ltechdesign.domain.models import DocumentSession

from .archive import LoadedProject, read_archive, write_archive
from .paths import WriterLock
from .preferences import atomic_json


@dataclass(frozen=True)
class RecoveryEntry:
    directory: Path
    timestamp: str
    name: str
    revision: int
    source: str | None
    digest: str
    error: str | None = None


@dataclass
class RecoveryOffer:
    directory: Path
    lock: WriterLock
    entries: tuple[RecoveryEntry, ...]

    def release(self) -> None:
        self.lock.close()


def _uuid(value: str) -> bool:
    try:
        return str(UUID(value)) == value
    except ValueError:
        return False


class RecoveryStore:
    def __init__(self, root: Path) -> None:
        self.root = root.absolute()
        self._owners: dict[str, WriterLock] = {}
        self._latest: dict[str, int] = {}

    def _directory(self, session_id: str) -> Path:
        if not _uuid(session_id):
            fail("invalid_recovery_identity")
        self.root.mkdir(parents=True, exist_ok=True)
        directory = self.root / session_id
        if directory.is_symlink():
            fail("unsafe_recovery_path", code="path_not_allowed")
        directory.mkdir(exist_ok=True)
        return directory

    def write(
        self,
        snapshot: DocumentSession,
        blobs: Mapping[str, bytes],
        *,
        source: Path | None = None,
        source_digest: str | None = None,
    ) -> RecoveryEntry:
        """Serialized worker operation. Does not mark the document saved or touch its source."""
        key = snapshot.session_id
        directory = self._directory(key)
        if key not in self._owners:
            self._owners[key] = WriterLock(directory / "owner")
        if snapshot.revision <= self._latest.get(key, -1):
            fail("stale_recovery_snapshot", code="revision_conflict")
        timestamp = datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
        name = f"{snapshot.revision:020d}-{uuid4()}"
        staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=directory))
        try:
            project = replace(
                snapshot.project,
                manifest=replace(
                    snapshot.project.manifest,
                    saved_revision=snapshot.revision,
                    saved_at=timestamp,
                    files=tuple(
                        e
                        for e in snapshot.project.manifest.files
                        if not e.path.startswith("thumbnails/")
                    ),
                    optional_capabilities=tuple(
                        c
                        for c in snapshot.project.manifest.optional_capabilities
                        if c != "preview.thumbnail/1"
                    ),
                ),
                opaque_files={
                    p: b
                    for p, b in snapshot.project.opaque_files.items()
                    if not p.startswith("thumbnails/")
                },
            )
            with (staging / "snapshot.ltechdesign").open("w+b") as stream:
                write_archive(stream, project, blobs)
                stream.flush()
                os.fsync(stream.fileno())
                stream.seek(0)
                loaded = read_archive(stream)
            digest = fingerprint(loaded.project)
            atomic_json(
                staging / "record.json",
                {
                    "version": 1,
                    "timestamp": timestamp,
                    "name": project.document.name,
                    "revision": snapshot.revision,
                    "source": str(source) if source else None,
                    "source_digest": source_digest,
                    "digest": digest,
                },
            )
            final = directory / name
            os.replace(staging, final)  # publication barrier; old generations still exist
            self._latest[key] = snapshot.revision
        except OSError as error:
            raise ModelError("recovery_write_failed", code="io_error") from error
        finally:
            if staging.exists():
                shutil.rmtree(staging)
        # Maintenance failure must not misreport a committed snapshot as failed.
        try:
            for old in self._generations(directory)[2:]:
                shutil.rmtree(old)
        except OSError:
            pass
        return RecoveryEntry(
            final,
            timestamp,
            project.document.name,
            snapshot.revision,
            str(source) if source else None,
            digest,
        )

    def _generations(self, directory: Path) -> list[Path]:
        return sorted(
            (
                p
                for p in directory.iterdir()
                if p.is_dir()
                and not p.is_symlink()
                and len(p.name) == 57
                and p.name[:20].isdigit()
                and p.name[20] == "-"
                and _uuid(p.name[21:])
            ),
            reverse=True,
        )

    def _entry(self, directory: Path) -> RecoveryEntry:
        try:
            record = directory / "record.json"
            if record.is_symlink() or record.stat().st_size > 65536:
                fail("invalid_recovery_record")
            value = json.loads(record.read_text(encoding="utf-8"))
            if (
                not isinstance(value, dict)
                or value.get("version") != 1
                or type(value.get("revision")) is not int
                or value["revision"] < 0
                or value["revision"] != int(directory.name[:20])
                or not isinstance(value.get("timestamp"), str)
                or datetime.fromisoformat(value["timestamp"]).utcoffset() is None
                or not isinstance(value.get("name"), str)
                or not isinstance(value.get("digest"), str)
                or len(value["digest"]) != 64
                or (value.get("source") is not None and not isinstance(value["source"], str))
            ):
                fail("invalid_recovery_record")
            return RecoveryEntry(
                directory,
                value["timestamp"],
                value["name"],
                value["revision"],
                value.get("source"),
                value["digest"],
            )
        except (OSError, ValueError, TypeError, ModelError):
            return RecoveryEntry(
                directory, "unknown", "Recovery rusak", -1, None, "", "invalid_recovery_record"
            )

    def scan(self) -> tuple[RecoveryOffer, ...]:
        self.root.mkdir(parents=True, exist_ok=True)
        offers = []
        for directory in sorted(self.root.iterdir()):
            if not directory.is_dir() or directory.is_symlink() or not _uuid(directory.name):
                continue
            try:
                lock = WriterLock(directory / "owner")
            except ModelError as error:
                if error.code in ("file_owned", "target_in_use"):
                    continue
                raise
            entries = tuple(self._entry(p) for p in self._generations(directory))
            if entries:
                offer = RecoveryOffer(directory, lock, entries)
                validated = []
                for entry in entries:
                    try:
                        self.load(offer, entry)
                        validated.append(entry)
                    except ModelError as error:
                        validated.append(replace(entry, error=error.reason))
                offer.entries = tuple(validated)
                offers.append(offer)
            else:
                lock.close()
        return tuple(offers)

    def load(self, offer: RecoveryOffer, entry: RecoveryEntry) -> LoadedProject:
        if entry not in offer.entries or entry.directory.parent != offer.directory or entry.error:
            fail("invalid_recovery_entry")
        path = entry.directory / "snapshot.ltechdesign"
        if path.is_symlink():
            fail("unsafe_recovery_path", code="path_not_allowed")
        try:
            with path.open("rb") as stream:
                loaded = read_archive(stream)
        except OSError as error:
            raise ModelError("recovery_read_failed", code="io_error") from error
        if (
            loaded.project.manifest.saved_revision != entry.revision
            or fingerprint(loaded.project) != entry.digest
        ):
            fail("recovery_digest_mismatch")
        return loaded

    def discard(self, offer: RecoveryOffer) -> None:
        # Keep the lock until all snapshots are gone; another process cannot restore halfway.
        for generation in self._generations(offer.directory):
            shutil.rmtree(generation)
        offer.release()

    def retire(self, session_id: str, through_revision: int) -> None:
        """Manual save clears only snapshots it actually covers, never a newer generation."""
        if session_id not in self._owners:
            return
        directory = self.root / session_id
        for generation in self._generations(directory):
            if int(generation.name[:20]) <= through_revision:
                shutil.rmtree(generation)

    def close_session(self, session_id: str, *, discard: bool) -> None:
        lock = self._owners.get(session_id)
        if lock is None:
            return
        if discard:
            self.retire(session_id, 2**63 - 1)
        lock.close()
        self._owners.pop(session_id, None)
        self._latest.pop(session_id, None)

    def release(self) -> None:
        for key in tuple(self._owners):
            self.close_session(key, discard=False)
