import io
import json
import os
import shutil
import stat
import struct
import zipfile
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from test_commands import ok, request
from test_domain import fixture, payloads

from ltechdesign.assets import BlobStore
from ltechdesign.commands import Dispatcher, Move, RegisterAsset, RemoveAsset
from ltechdesign.domain import ModelError, create_project, semantic_content
from ltechdesign.domain.codec import json_bytes
from ltechdesign.domain.models import DocumentSession, MediaData, NodeId, TextData
from ltechdesign.persistence import (
    ArchiveLimits,
    FileHandle,
    LoadedProject,
    PersistenceService,
    duplicate_project,
    read_archive,
    write_archive,
)
from ltechdesign.persistence import service as service_module
from ltechdesign.persistence.paths import WriterLock, canonical_path

pytestmark = pytest.mark.core
ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "examples/proyek-contoh.ltechdesign"


@pytest.fixture
def native() -> LoadedProject:
    with NATIVE.open("rb") as stream:
        return read_archive(stream)


@pytest.fixture
def service() -> Iterator[PersistenceService]:
    instance = PersistenceService()
    yield instance
    for handle in tuple(instance._handles):
        if not handle._closed:
            instance.close(handle)


def zip_bytes(members: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, data in members.items():
            archive.writestr(path, data)
    return stream.getvalue()


def members() -> dict[str, bytes]:
    with zipfile.ZipFile(NATIVE) as archive:
        return {info.filename: archive.read(info) for info in archive.infolist()}


def rehash(data: dict[str, bytes]) -> dict[str, bytes]:
    import hashlib

    manifest = json.loads(data["manifest.json"])
    for entry in manifest["files"]:
        if entry["path"] in data:
            value = data[entry["path"]]
            entry.update(byte_length=len(value), sha256=hashlib.sha256(value).hexdigest())
    data["manifest.json"] = json_bytes(manifest)
    return data


def saved(service: PersistenceService, path: Path, native: LoadedProject) -> FileHandle:
    handle = service.new(native.project, native.blobs)
    service.save(handle, handle.admission, native.blobs, target=path)
    return handle


def test_roundtrip_portable_editable_and_runtime_exclusion(
    service: PersistenceService,
    native: LoadedProject,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources = tmp_path / "import-sources"
    sources.mkdir()
    for path, data in native.blobs.items():
        (sources / Path(path).name).write_bytes(data)
    original = tmp_path / "original.ltechdesign"
    handle = saved(service, original, native)
    store = BlobStore()
    lease = store.admit(native.project.assets.assets, native.blobs)
    engine = Dispatcher(handle.admission, initially_saved=True, assets=store.retention())
    lease.release()
    candidate = next(
        n for n in engine.snapshot.project.document.nodes.values() if n.type == "ellipse"
    )
    ok(engine, Move(node_id=candidate.id, dx=7, dy=9))
    with store.pin(engine.snapshot.project.assets.assets) as job:
        result = service.save(handle, engine.snapshot, job.blobs)
    engine.mark_saved(result.checkpoint)
    assert not engine.dirty
    service.close(handle)
    destination = tmp_path / "moved"
    destination.mkdir()
    moved = destination / original.name
    shutil.move(original, moved)
    for source in sources.iterdir():
        source.unlink()
    sources.rmdir()
    monkeypatch.chdir(destination)
    restored = service.open(moved)
    assert restored.admission.session_id != engine.snapshot.session_id
    assert restored.admission.revision == 0
    assert restored.loaded.project.manifest.saved_revision == 1
    assert semantic_content(restored.loaded.project) == semantic_content(engine.snapshot.project)
    assert dict(restored.loaded.blobs) == dict(native.blobs)
    assert len(restored.loaded.project.document.pages) == 2
    assert restored.loaded.project.tokens.bindings
    assert any(n.parent_id for n in restored.loaded.project.document.nodes.values())
    with zipfile.ZipFile(moved) as archive:
        for filename in ("document.json", "manifest.json", "workspace.json"):
            text = archive.read(filename).decode()
            assert not any(term in text for term in ("session_id", "job_id", "request_id", "undo"))
    ok(engine, action="undo")
    assert semantic_content(engine.snapshot.project) == semantic_content(native.project)
    engine.close()


def test_repeat_native_roundtrip_and_optional_members(native: LoadedProject) -> None:
    current = native
    for _ in range(3):
        stream = io.BytesIO()
        write_archive(stream, current.project, current.blobs)
        current = read_archive(stream)
        assert semantic_content(current.project) == semantic_content(native.project)
        assert current.project.workspace == native.project.workspace
        assert current.blobs == native.blobs
    project = create_project()
    stream = io.BytesIO()
    write_archive(stream, project, {})
    assert read_archive(stream).project.workspace is None


def test_old_fixture_bad_png_is_not_silently_accepted() -> None:
    with pytest.raises(ModelError, match="invalid_image"):
        read_archive(io.BytesIO(zip_bytes(payloads(fixture()))))


@pytest.mark.parametrize(
    "kind",
    [
        "hash",
        "size",
        "missing",
        "extra",
        "format",
        "version",
        "capability",
        "json",
        "unknown",
        "binding",
        "font",
        "workspace",
    ],
)
def test_malformed_members_rejected(kind: str) -> None:
    data = members()
    manifest = json.loads(data["manifest.json"])
    if kind == "hash":
        manifest["files"][0]["sha256"] = "0" * 64
    elif kind == "size":
        manifest["files"][0]["byte_length"] += 1
    elif kind == "missing":
        del data[next(p for p in data if p.startswith("assets/data/"))]
    elif kind == "extra":
        data["extra.txt"] = b"undeclared"
    elif kind == "format":
        manifest["format_id"] = "other.project"
    elif kind == "version":
        manifest["format_version"] = "1.1"
    elif kind == "capability":
        manifest["required_capabilities"].append("future.render/9")
    elif kind == "json":
        data["document.json"] = b'{"schema_version":"1.0","schema_version":"1.0"}'
    elif kind == "unknown":
        document = json.loads(data["document.json"])
        document["session_id"] = "not-portable"
        data["document.json"] = json_bytes(document)
    elif kind == "binding":
        tokens = json.loads(data["tokens.json"])
        tokens["bindings"][0]["node_id"] = "absent"
        data["tokens.json"] = json_bytes(tokens)
    elif kind == "font":
        fonts = json.loads(data["fonts.json"])
        fonts["fonts"][0]["asset_id"] = "absent"
        data["fonts.json"] = json_bytes(fonts)
    else:
        workspace = json.loads(data["workspace.json"])
        workspace["active_page_id"] = "absent"
        data["workspace.json"] = json_bytes(workspace)
    data["manifest.json"] = json_bytes(manifest)
    if kind in ("json", "unknown", "binding", "font", "workspace"):
        rehash(data)
    with pytest.raises(ModelError):
        read_archive(io.BytesIO(zip_bytes(data)))


@pytest.mark.parametrize(
    "name",
    [
        "../x",
        "/absolute",
        "a\\b",
        "a//b",
        "a/./b",
        "C:/x",
        "NUL.txt",
        "a:stream",
        "trailing.",
        "e\u0301.txt",
        "x\x00z",
    ],
)
def test_unsafe_zip_paths(name: str) -> None:
    stream = io.BytesIO(zip_bytes({name: b"x"}))
    with pytest.raises(ModelError):
        read_archive(stream)


@pytest.mark.parametrize(
    "variant",
    [
        "duplicate",
        "case_alias",
        "symlink",
        "directory",
        "bzip2",
        "truncated",
        "garbage",
        "fake_count",
        "encrypted",
    ],
)
def test_archive_structure_rejection(variant: str) -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        if variant in ("duplicate", "case_alias"):
            archive.writestr("manifest.json", b"{}")
            if variant == "duplicate":
                with pytest.warns(UserWarning):
                    archive.writestr("manifest.json", b"{}")
            else:
                archive.writestr("MANIFEST.JSON", b"{}")
        elif variant == "symlink":
            info = zipfile.ZipInfo("manifest.json")
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, b"elsewhere")
        elif variant == "directory":
            for path, data in members().items():
                archive.writestr(path, data)
            archive.writestr("not-in-inventory/", b"")
        elif variant == "bzip2":
            archive.writestr("manifest.json", b"{}", compress_type=zipfile.ZIP_BZIP2)
        else:
            archive.writestr("manifest.json", b"{}")
    raw = stream.getvalue()
    if variant == "truncated":
        raw = raw[:-5]
    elif variant == "garbage":
        raw = b"not a ZIP"
    elif variant == "fake_count":
        raw = raw[:-12] + b"\x00\x00" + raw[-10:]
    elif variant == "encrypted":
        blob = bytearray(raw)
        struct.pack_into("<H", blob, blob.index(b"PK\x01\x02") + 8, 1)
        raw = bytes(blob)
    with pytest.raises(ModelError):
        read_archive(io.BytesIO(raw))


def test_valid_directories_and_zip64_local_headers() -> None:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("assets/", b"")
        archive.writestr("assets/data/", b"")
        for path, payload in members().items():
            with archive.open(path, "w", force_zip64=True) as member:
                member.write(payload)
    assert read_archive(stream).project.document.nodes


@pytest.mark.parametrize(
    "limits",
    [
        ArchiveLimits(entries=2),
        ArchiveLimits(expanded_bytes=100),
        ArchiveLimits(archive_bytes=100),
        ArchiveLimits(asset_bytes=10),
        ArchiveLimits(directory_bytes=20),
    ],
)
def test_bounded_archive(limits: ArchiveLimits) -> None:
    with NATIVE.open("rb") as stream, pytest.raises(ModelError) as error:
        read_archive(stream, limits=limits)
    assert error.value.code == "limit_exceeded"


def test_failure_to_open_does_not_replace_existing_model_or_lock(
    service: PersistenceService, native: LoadedProject, tmp_path: Path
) -> None:
    old = saved(service, tmp_path / "old.ltechdesign", native)
    engine = Dispatcher(old.admission, initially_saved=True)
    before = engine.snapshot
    damaged = tmp_path / "damaged.ltechdesign"
    data = members()
    data["document.json"] += b"tampered"
    damaged.write_bytes(zip_bytes(data))
    with pytest.raises(ModelError):
        service.open(damaged)
    assert engine.snapshot is before and not engine.dirty
    assert len(service._handles) == 1
    assert not Path(str(damaged) + ".lock").exists()
    assert Path(str(old.path) + ".lock").exists()


@pytest.mark.parametrize("failure", ["replace", "validation", "cancel", "missing_blob"])
def test_failed_save_preserves_file_checkpoint_and_cleans_temp(
    service: PersistenceService,
    native: LoadedProject,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    path = tmp_path / "save.ltechdesign"
    handle = saved(service, path, native)
    old_bytes, baseline = path.read_bytes(), handle.baseline
    if failure == "replace":

        def reject(*args: object) -> None:
            raise PermissionError("fault injection")

        monkeypatch.setattr(os, "replace", reject)
    elif failure == "validation":

        def invalid(*args: object, **kwargs: object) -> None:
            raise ModelError("injected_validation_failure")

        monkeypatch.setattr(service_module, "read_archive", invalid)
    with pytest.raises(ModelError):
        service.save(
            handle,
            handle.admission,
            {} if failure == "missing_blob" else native.blobs,
            cancelled=(lambda: True) if failure == "cancel" else None,
        )
    assert path.read_bytes() == old_bytes and handle.baseline == baseline
    assert not list(tmp_path.glob(".ltechdesign-*.tmp"))
    assert Path(str(path) + ".lock").exists()


def test_save_as_holds_source_until_target_success_and_preserves_identity(
    service: PersistenceService,
    native: LoadedProject,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, target = tmp_path / "source.ltechdesign", tmp_path / "target.ltechdesign"
    handle = saved(service, source, native)
    original = source.read_bytes()
    real_replace = os.replace
    calls = []

    def observe(src: str | Path, dst: str | Path) -> None:
        assert Path(str(source) + ".lock").exists()
        assert Path(str(target) + ".lock").exists()
        assert handle.path == canonical_path(source)
        calls.append(dst)
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", observe)
    session_id = handle.admission.session_id
    service.save(handle, handle.admission, native.blobs, target=target)
    assert calls and handle.path == canonical_path(target)
    assert handle.admission.session_id == session_id
    assert source.read_bytes() == original
    assert not Path(str(source) + ".lock").exists()
    service.close(handle)
    restored = service.open(target)
    assert restored.loaded.project.document.document_id == native.project.document.document_id


def test_failed_save_as_retains_source_and_releases_target(
    service: PersistenceService,
    native: LoadedProject,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, target = tmp_path / "source.ltechdesign", tmp_path / "target.ltechdesign"
    handle = saved(service, source, native)

    def deny(*args: object) -> None:
        raise OSError("target replace failed")

    monkeypatch.setattr(os, "replace", deny)
    with pytest.raises(ModelError):
        service.save(handle, handle.admission, native.blobs, target=target)
    assert handle.path == canonical_path(source)
    assert Path(str(source) + ".lock").exists()
    assert not Path(str(target) + ".lock").exists() and not target.exists()


def test_single_writer_readonly_save_as_and_canonical_alias(
    service: PersistenceService, native: LoadedProject, tmp_path: Path
) -> None:
    source = tmp_path / "project.ltechdesign"
    handle = saved(service, source, native)
    alias = tmp_path / "." / source.name
    assert service.open(alias) is handle
    second = PersistenceService()
    with pytest.raises(ModelError, match="target_in_use"):
        second.open(alias)
    reader = second.open(alias, read_only=True)
    try:
        assert reader.admission.session_id != handle.admission.session_id
        with pytest.raises(ModelError, match="read_only"):
            second.save(reader, reader.admission, reader.loaded.blobs)
        second.save(
            reader, reader.admission, reader.loaded.blobs, target=tmp_path / "copy.ltechdesign"
        )
        assert not reader.read_only
    finally:
        second.close(reader)


@pytest.mark.parametrize("change", ["bytes_same_mtime", "replace_same_bytes", "delete"])
def test_external_change_conflict(
    service: PersistenceService, native: LoadedProject, tmp_path: Path, change: str
) -> None:
    path = tmp_path / "source.ltechdesign"
    handle = saved(service, path, native)
    before = path.stat()
    original = path.read_bytes()
    if change == "bytes_same_mtime":
        path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    elif change == "replace_same_bytes":
        other = tmp_path / "external.tmp"
        other.write_bytes(original)
        os.replace(other, path)
    else:
        path.unlink()
    external = path.read_bytes() if path.exists() else None
    with pytest.raises(ModelError, match="external_change_conflict"):
        service.save(handle, handle.admission, native.blobs)
    assert (path.read_bytes() if path.exists() else None) == external


def test_external_change_between_staging_and_replace(
    service: PersistenceService,
    native: LoadedProject,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "source.ltechdesign"
    handle = saved(service, path, native)
    real_read = read_archive

    def race(*args: Any, **kwargs: Any) -> LoadedProject:
        result = real_read(*args, **kwargs)
        path.write_bytes(b"external edit during save")
        return result

    monkeypatch.setattr(service_module, "read_archive", race)
    with pytest.raises(ModelError, match="external_change_conflict"):
        service.save(handle, handle.admission, native.blobs)
    assert path.read_bytes() == b"external edit during save"


def test_migration_backup_is_exact_and_precedes_replace(
    service: PersistenceService,
    native: LoadedProject,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "source.ltechdesign"
    handle = saved(service, path, native)
    original = path.read_bytes()
    real_replace = os.replace

    def verify(src: str | Path, dst: str | Path) -> None:
        backups = list(tmp_path.glob("*.bak"))
        assert len(backups) == 1 and backups[0].read_bytes() == original
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", verify)
    result = service.save(handle, handle.admission, native.blobs, migration_backup=True)
    assert result.backup is not None and result.backup.read_bytes() == original


def test_duplicate_remaps_all_known_references_and_roundtrips(native: LoadedProject) -> None:
    clone = duplicate_project(native.project)
    assert clone.document.document_id != native.project.document.document_id
    assert not clone.document.nodes.keys() & native.project.document.nodes.keys()
    assert not {p.id for p in clone.document.pages} & {p.id for p in native.project.document.pages}
    for old, new in zip(
        native.project.document.nodes.values(), clone.document.nodes.values(), strict=True
    ):
        assert old.x == new.x and old.y == new.y and old.type == new.type
        if isinstance(new.data, MediaData):
            assert new.data.asset_id in {a.id for a in clone.assets.assets}
        if isinstance(new.data, TextData):
            assert new.data.typography.font_id in {f.id for f in clone.fonts.fonts}
    stream = io.BytesIO()
    write_archive(stream, clone, native.blobs)
    assert semantic_content(read_archive(stream).project) == semantic_content(clone)


def test_unknown_optional_extension_preserved_and_duplicate_rejected(native: LoadedProject) -> None:
    import hashlib

    from ltechdesign.domain.models import Extension, InventoryEntry

    data = b"opaque metadata: { not JSON }\x00"
    path = "extensions/vendor.meta/data.bin"
    manifest = replace(
        native.project.manifest,
        optional_capabilities=native.project.manifest.optional_capabilities + ("vendor.meta/1",),
        extensions=(
            Extension(
                id="vendor.meta",
                version="1",
                capability="vendor.meta/1",
                paths=(path,),
                edit_policy="preserve_opaque",
                asset_ids=(native.project.assets.assets[0].id,),
            ),
        ),
        files=native.project.manifest.files
        + (
            InventoryEntry(
                path=path,
                media_type="application/octet-stream",
                byte_length=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
            ),
        ),
    )
    project = replace(native.project, manifest=manifest, opaque_files={path: data})
    stream = io.BytesIO()
    write_archive(stream, project, native.blobs)
    restored = read_archive(stream)
    assert restored.project.opaque_files[path] == data
    assert semantic_content(restored.project) == semantic_content(project)
    with pytest.raises(ModelError, match="extension_remapper_unavailable"):
        duplicate_project(restored.project)


def test_store_transactions_undo_redo_jobs_recovery_and_gc(native: LoadedProject) -> None:
    asset = next(a for a in native.project.assets.assets if a.media_type == "image/png")
    store = BlobStore()
    engine = Dispatcher(DocumentSession(project=create_project()), assets=store.retention())
    staging_id = store.stage(asset, native.blobs[asset.path])
    ok(engine, RegisterAsset(asset=asset, staging_id=staging_id))
    job = store.pin((asset,))
    recovery = store.pin((asset,))
    ok(engine, RemoveAsset(asset_id=asset.id))
    assert not store.collect()  # history owns removed asset
    ok(engine, action="undo")
    assert engine.snapshot.project.assets.assets == (asset,)
    ok(engine, action="redo")
    engine.clear_history()
    engine.close()
    assert not store.collect()  # job and recovery survive dispatcher close
    job.release()
    assert not store.collect()
    recovery.release()
    assert store.collect() == (asset.path,)


def test_store_rollback_and_prepare_blocks_gc(native: LoadedProject) -> None:
    asset = next(a for a in native.project.assets.assets if a.media_type == "image/png")
    store = BlobStore()
    adapter = store.retention()
    engine = Dispatcher(DocumentSession(project=create_project()), assets=adapter)
    stage = store.stage(asset, native.blobs[asset.path])
    invalid = request(
        engine,
        RegisterAsset(asset=asset, staging_id=stage),
        Move(
            node_id=NodeId("absent"),
            dx=1,
            dy=0,
        ),
    )
    assert not engine.dispatch(invalid, client_id="local").ok
    assert not engine.snapshot.project.assets.assets
    assert store.collect() == (asset.path,)
    stage = store.stage(asset, native.blobs[asset.path])
    prepared = adapter.prepare({asset.id: asset}, {stage: asset})
    with pytest.raises(ModelError, match="asset_transaction_active"):
        store.collect()
    prepared.abort()
    assert store.collect() == (asset.path,)


def test_asset_integrity_must_pass_before_store_publication(native: LoadedProject) -> None:
    asset = native.project.assets.assets[0]
    store = BlobStore()
    with pytest.raises(ModelError, match="integrity_mismatch"):
        store.stage(asset, b"bad")
    assert not store.collect()


def test_lock_unknown_owner_and_hardlink_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "project.ltechdesign"
    path.write_bytes(b"x")
    sidecar = Path(str(path) + ".lock")
    sidecar.write_text("ambiguous", encoding="utf-8")
    with pytest.raises(ModelError, match="file_owned"):
        WriterLock(canonical_path(path))
    assert sidecar.read_text() == "ambiguous"
    other = tmp_path / "hardlink.ltechdesign"
    os.link(path, other)
    with pytest.raises(ModelError, match="hardlink_writer"):
        canonical_path(path, writer=True)


def test_dead_owner_checked_and_ambiguous_alive_owner_kept(tmp_path: Path) -> None:
    from PySide6.QtCore import QLockFile, QSysInfo

    path = canonical_path(tmp_path / "lock.ltechdesign", writer=True)
    sidecar = Path(str(path) + ".lock")
    # Synthetic stale metadata exercises the adapter. Real crash/PID reuse is 04A.
    sidecar.write_text(f"2147483647\npython\n{QSysInfo.machineHostName()}\n", encoding="utf-8")
    lock = WriterLock(path)
    try:
        assert QLockFile(str(sidecar)).getLockInfo()[0] == os.getpid()
        assert lock._lock.staleLockTime() == 0
    finally:
        lock.close()
    sidecar.write_text(
        f"{os.getpid()}\nwrong-name\n{QSysInfo.machineHostName()}\n", encoding="utf-8"
    )
    original = sidecar.read_bytes()
    with pytest.raises(ModelError, match="owner_alive_or_ambiguous"):
        WriterLock(path)
    assert sidecar.read_bytes() == original


def test_save_checkpoint_for_old_snapshot_does_not_clean_new_edits(
    service: PersistenceService,
    native: LoadedProject,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handle = saved(service, tmp_path / "snapshot.ltechdesign", native)
    engine = Dispatcher(handle.admission, initially_saved=True)
    target = next(n for n in native.project.document.nodes.values() if n.type == "ellipse")
    ok(engine, Move(node_id=target.id, dx=1, dy=0))
    snapshot = engine.snapshot
    real_write = write_archive

    def concurrent_edit(*args: Any, **kwargs: Any) -> None:
        ok(engine, Move(node_id=target.id, dx=2, dy=0))
        real_write(*args, **kwargs)

    monkeypatch.setattr(service_module, "write_archive", concurrent_edit)
    result = service.save(handle, snapshot, native.blobs)
    engine.mark_saved(result.checkpoint)
    assert engine.dirty and engine.snapshot.revision == 2
    assert handle.path is not None
    with handle.path.open("rb") as stream:
        restored = read_archive(stream)
    assert restored.project.document.nodes[target.id].x == target.x + 1
    assert restored.project.manifest.saved_revision == 1


def test_cancel_after_barrier_reports_committed_success(
    service: PersistenceService,
    native: LoadedProject,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handle = saved(service, tmp_path / "cancel.ltechdesign", native)
    cancelled = False
    real_replace = os.replace

    def commit(src: str | Path, dst: str | Path) -> None:
        nonlocal cancelled
        real_replace(src, dst)
        cancelled = True

    monkeypatch.setattr(os, "replace", commit)
    result = service.save(handle, handle.admission, native.blobs, cancelled=lambda: cancelled)
    assert result.path.exists() and cancelled


def test_external_write_during_load_has_no_admission(
    service: PersistenceService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.ltechdesign"
    source.write_bytes(NATIVE.read_bytes())
    real_read = read_archive

    def replace_during_load(*args: Any, **kwargs: Any) -> LoadedProject:
        result = real_read(*args, **kwargs)
        # Windows denies rename while Python holds a read handle; an in-place
        # writer can still alter it. Exercise the actual competing write.
        with source.open("r+b") as changed:
            changed.seek(-1, os.SEEK_END)
            changed.write(b"!")
        return result

    monkeypatch.setattr(service_module, "read_archive", replace_during_load)
    with pytest.raises(ModelError, match="external_change_conflict"):
        service.open(source)
    assert not service._handles and not Path(str(source) + ".lock").exists()


def test_target_appearing_during_save_as_is_preserved(
    service: PersistenceService,
    native: LoadedProject,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, target = tmp_path / "source.ltechdesign", tmp_path / "target.ltechdesign"
    handle = saved(service, source, native)
    real_read = read_archive

    def appear(*args: Any, **kwargs: Any) -> LoadedProject:
        result = real_read(*args, **kwargs)
        target.write_bytes(b"external target")
        return result

    monkeypatch.setattr(service_module, "read_archive", appear)
    with pytest.raises(ModelError, match="external_change_conflict"):
        service.save(handle, handle.admission, native.blobs, target=target)
    assert target.read_bytes() == b"external target"
    assert handle.path == canonical_path(source)


def test_overwrite_requires_intent_and_target_session_rejected(
    service: PersistenceService, native: LoadedProject, tmp_path: Path
) -> None:
    source, target = tmp_path / "source.ltechdesign", tmp_path / "target.ltechdesign"
    handle = saved(service, source, native)
    target.write_bytes(b"existing file")
    with pytest.raises(ModelError, match="target_exists"):
        service.save(handle, handle.admission, native.blobs, target=target)
    assert target.read_bytes() == b"existing file"
    service.save(handle, handle.admission, native.blobs, target=target, overwrite=True)
    source_handle = service.open(source)
    with pytest.raises(ModelError, match="target_in_use"):
        service.save(
            source_handle, source_handle.admission, native.blobs, target=target, overwrite=True
        )


def test_backup_failure_preserves_source(
    service: PersistenceService,
    native: LoadedProject,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "source.ltechdesign"
    handle = saved(service, path, native)
    before = path.read_bytes()

    def fail_backup(*args: object) -> Path:
        raise PermissionError("backup unavailable")

    monkeypatch.setattr(service, "_backup", fail_backup)
    with pytest.raises(ModelError, match="io_error"):
        service.save(handle, handle.admission, native.blobs, migration_backup=True)
    assert path.read_bytes() == before


def test_source_alias_retarget_does_not_turn_save_into_save_as(
    service: PersistenceService,
    native: LoadedProject,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, other = tmp_path / "source.ltechdesign", tmp_path / "new.ltechdesign"
    handle = saved(service, source, native)
    real_canonical = canonical_path

    def retarget(path: str | Path, *, writer: bool = False) -> Path:
        return real_canonical(other, writer=writer)

    monkeypatch.setattr(service_module, "canonical_path", retarget)
    with pytest.raises(ModelError, match="source_path_retargeted"):
        service.save(handle, handle.admission, native.blobs)
    assert not other.exists() and source.exists()


def test_writer_limits_and_invalid_limit_configuration(native: LoadedProject) -> None:
    with pytest.raises(ModelError, match="limit_exceeded"):
        write_archive(io.BytesIO(), native.project, native.blobs, limits=ArchiveLimits(entries=2))
    with pytest.raises(ValueError):
        ArchiveLimits(asset_bytes=51 * 1024 * 1024)
    with pytest.raises(ValueError):
        ArchiveLimits(entries=0)


def test_thumbnail_validation_and_preservation(
    native: LoadedProject, service: PersistenceService, tmp_path: Path
) -> None:
    import hashlib

    from ltechdesign.domain.models import InventoryEntry

    png = next(
        native.blobs[a.path] for a in native.project.assets.assets if a.media_type == "image/png"
    )
    path = "thumbnails/page.png"
    entry = InventoryEntry(
        path=path,
        media_type="image/png",
        byte_length=len(png),
        sha256=hashlib.sha256(png).hexdigest(),
    )
    manifest = replace(
        native.project.manifest,
        files=native.project.manifest.files + (entry,),
        optional_capabilities=native.project.manifest.optional_capabilities
        + ("preview.thumbnail/1",),
    )
    project = replace(native.project, manifest=manifest, opaque_files={path: png})
    stream = io.BytesIO()
    write_archive(stream, project, native.blobs)
    assert read_archive(stream).project.opaque_files[path] == png
    handle = service.new(project, native.blobs)
    saved_path = tmp_path / "thumbnail.ltechdesign"
    service.save(handle, handle.admission, native.blobs, target=saved_path)
    with saved_path.open("rb") as source:
        assert read_archive(source).project.opaque_files[path] == png
    engine = Dispatcher(handle.admission)
    target = next(n for n in project.document.nodes.values() if n.type == "ellipse")
    ok(engine, Move(node_id=target.id, dx=1, dy=0))
    service.save(handle, engine.snapshot, native.blobs)
    with saved_path.open("rb") as source:
        restored = read_archive(source)
    assert path not in restored.project.opaque_files
    assert semantic_content(restored.project) == semantic_content(engine.snapshot.project)
    assert project.opaque_files[path] == png  # only the saved side-effect snapshot changed
