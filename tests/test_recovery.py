import os
from dataclasses import replace
from pathlib import Path

import pytest
from test_commands import ok

from ltechdesign.assets import BlobStore
from ltechdesign.commands import Delete, Dispatcher, Move, RemoveAsset
from ltechdesign.domain import ModelError, create_project, semantic_content
from ltechdesign.domain.models import DocumentSession, MediaData
from ltechdesign.persistence import PersistenceService, read_archive
from ltechdesign.persistence.preferences import Preferences
from ltechdesign.persistence.recovery import RecoveryStore

pytestmark = pytest.mark.core
FIXTURE = Path(__file__).resolve().parents[1] / "examples/proyek-contoh.ltechdesign"


def test_unnamed_generations_restore_new_session_and_normal_save(tmp_path: Path) -> None:
    recovery = RecoveryStore(tmp_path / "recovery")
    snapshot = DocumentSession(project=create_project("Belum bernama"))
    for revision in range(3):
        entry = recovery.write(replace(snapshot, revision=revision), {})
    assert entry.revision == 2 and entry.timestamp.endswith("Z") and entry.source is None
    assert RecoveryStore(recovery.root).scan() == ()  # live writer cannot be offered
    recovery.release()
    reader = RecoveryStore(recovery.root)
    (offer,) = reader.scan()
    assert [e.revision for e in offer.entries] == [2, 1]
    loaded = reader.load(offer, offer.entries[0])
    service = PersistenceService()
    handle = service.new(loaded.project, loaded.blobs)
    assert handle.admission.session_id != snapshot.session_id
    assert handle.admission.revision == 0 and handle.path is None
    engine = Dispatcher(handle.admission)
    assert engine.dirty and not engine.undo_history
    path = tmp_path / "restored.ltechdesign"
    saved = service.save(handle, engine.snapshot, {}, target=path)
    engine.mark_saved(saved.checkpoint)
    assert not engine.dirty
    service.close(handle)
    reader.discard(offer)
    assert not reader.scan()
    reopened = service.open(path)
    assert reopened.admission.session_id != handle.admission.session_id
    assert semantic_content(reopened.loaded.project) == semantic_content(snapshot.project)
    service.close(reopened)


@pytest.mark.parametrize("failure", ["write", "record", "publish"])
def test_io_failure_keeps_last_successful_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    from ltechdesign.persistence import recovery as module

    recovery = RecoveryStore(tmp_path)
    snapshot = DocumentSession(project=create_project())
    first = recovery.write(snapshot, {})

    def reject(*args: object, **kwargs: object) -> None:
        raise PermissionError("Injected disk failure")

    with monkeypatch.context() as patch:
        if failure == "write":
            patch.setattr(module, "write_archive", reject)
        elif failure == "record":
            patch.setattr(module, "atomic_json", reject)
        else:
            real_replace = os.replace

            def publish(source: str | Path, target: str | Path) -> None:
                if Path(source).is_dir():
                    reject()
                real_replace(source, target)

            patch.setattr(os, "replace", publish)
        with pytest.raises(ModelError, match="recovery_write_failed"):
            recovery.write(replace(snapshot, revision=1), {})
    assert (first.directory / "snapshot.ltechdesign").exists()
    assert not list(first.directory.parent.glob(".staging-*"))
    recovery.release()
    (offer,) = recovery.scan()
    assert len(offer.entries) == 1 and offer.entries[0].revision == 0
    assert recovery.load(offer, offer.entries[0]).project.document.name == "Untitled"
    offer.release()


@pytest.mark.parametrize("damage", ["archive", "metadata", "missing"])
def test_corrupt_autosave_is_retained_and_previous_snapshot_available(
    tmp_path: Path, damage: str
) -> None:
    recovery = RecoveryStore(tmp_path)
    snapshot = DocumentSession(project=create_project())
    recovery.write(snapshot, {})
    last = recovery.write(replace(snapshot, revision=1), {})
    if damage == "metadata":
        (last.directory / "record.json").write_bytes(b"{broken")
    elif damage == "missing":
        (last.directory / "snapshot.ltechdesign").unlink()
    else:
        (last.directory / "snapshot.ltechdesign").write_bytes(b"corrupt archive")
    recovery.release()
    (offer,) = recovery.scan()
    assert offer.entries[0].error and not offer.entries[1].error
    with pytest.raises(ModelError):
        recovery.load(offer, offer.entries[0])
    assert recovery.load(offer, offer.entries[1]).project.document == snapshot.project.document
    offer.release()  # Later preserves damaged files too, never silently delete evidence
    assert last.directory.exists()
    (offer,) = recovery.scan()
    recovery.discard(offer)
    assert not recovery.scan()


def test_recovery_retire_covers_only_saved_revision_and_rejects_old_write(tmp_path: Path) -> None:
    recovery = RecoveryStore(tmp_path)
    snapshot = DocumentSession(project=create_project())
    recovery.write(replace(snapshot, revision=1), {})
    latest = recovery.write(replace(snapshot, revision=2), {})
    recovery.retire(snapshot.session_id, 1)
    assert latest.directory.exists()
    with pytest.raises(ModelError) as error:
        recovery.write(replace(snapshot, revision=1), {})
    assert error.value.code == "revision_conflict"
    recovery.close_session(snapshot.session_id, discard=True)
    assert not recovery.scan()


def test_persisted_recovery_survives_real_gc_history_and_external_change(tmp_path: Path) -> None:
    with FIXTURE.open("rb") as stream:
        loaded = read_archive(stream)
    source = tmp_path / "source.ltechdesign"
    source.write_bytes(FIXTURE.read_bytes())
    service = PersistenceService()
    handle = service.open(source)
    store = BlobStore()
    lease = store.admit(loaded.project.assets.assets, loaded.blobs)
    engine = Dispatcher(handle.admission, initially_saved=True, assets=store.retention())
    lease.release()
    recovery = RecoveryStore(tmp_path / "recovery")
    with store.pin(engine.snapshot.project.assets.assets) as pin:
        recovery.write(
            engine.snapshot,
            pin.blobs,
            source=handle.path,
            source_digest=handle.baseline.digest if handle.baseline else None,
        )
    image = next(n for n in loaded.project.document.nodes.values() if isinstance(n.data, MediaData))
    assert isinstance(image.data, MediaData)
    asset = next(a for a in loaded.project.assets.assets if a.id == image.data.asset_id)
    ok(engine, Delete(node_id=image.id), RemoveAsset(asset_id=asset.id))
    assert not store.collect()  # undo still owns the actual bytes
    ok(engine, action="undo")
    ok(engine, action="redo")
    engine.close()
    assert asset.path in store.collect()  # persisted recovery is self-contained
    source.write_bytes(b"EXTERNAL EDIT")
    service.close(handle)
    recovery.release()
    (offer,) = recovery.scan()
    restored = recovery.load(offer, offer.entries[0])
    assert restored.blobs == loaded.blobs
    assert source.read_bytes() == b"EXTERNAL EDIT"
    rescued = service.new(restored.project, restored.blobs)
    service.save(
        rescued, rescued.admission, restored.blobs, target=tmp_path / "rescued.ltechdesign"
    )
    assert source.read_bytes() == b"EXTERNAL EDIT"
    service.close(rescued)
    recovery.discard(offer)


def test_stale_manual_save_does_not_overwrite_newer_snapshot(tmp_path: Path) -> None:
    with FIXTURE.open("rb") as stream:
        loaded = read_archive(stream)
    service = PersistenceService()
    handle = service.new(loaded.project, loaded.blobs)
    engine = Dispatcher(handle.admission)
    old = engine.snapshot
    node = next(n for n in old.project.document.nodes.values() if n.parent_id is None)
    ok(engine, Move(node_id=node.id, dx=1, dy=0))
    path = tmp_path / "newer.ltechdesign"
    service.save(handle, engine.snapshot, loaded.blobs, target=path)
    actual = path.read_bytes()
    with pytest.raises(ModelError) as error:
        service.save(handle, old, loaded.blobs)
    assert error.value.code == "revision_conflict" and path.read_bytes() == actual
    service.close(handle)


def test_preferences_recent_bounds_validation_and_corrupt_defaults(tmp_path: Path) -> None:
    prefs = Preferences(tmp_path)
    assert prefs.autosave_seconds == 120 and not prefs.recent
    prefs.set_autosave(0)
    assert Preferences(tmp_path).autosave_seconds == 0
    prefs.set_autosave(30)
    for n in range(15):
        prefs.remember(tmp_path / f"{n}.ltechdesign")
    prefs.remember(tmp_path / "14.ltechdesign")
    assert len(prefs.recent) == 12
    with pytest.raises(ValueError):
        prefs.set_autosave(1)
    prefs.path.write_bytes(b"invalid")
    assert prefs.autosave_seconds == 120 and prefs.recent == ()
