import os
import threading
import time
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal

import pytest
from PIL import Image
from test_commands import ok

from ltechdesign.assets import BlobStore
from ltechdesign.commands import Create, Dispatcher, Move
from ltechdesign.domain import ModelError, create_node, create_project
from ltechdesign.domain.models import Fill, NodeId, Style
from ltechdesign.exports import ExportOptions, ExportService, ExportTarget, JobStatus
from ltechdesign.exports.contracts import TERMINAL
from ltechdesign.persistence import read_archive
from ltechdesign.persistence.paths import fingerprint_path

pytestmark = pytest.mark.core
ROOT = Path(__file__).resolve().parents[1]


def crash_worker(*args: Any) -> None:
    os._exit(7)


def wait(service: ExportService, job: JobStatus, timeout: float = 25) -> JobStatus:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = service.get_job_status(job.id)
        if status.state in TERMINAL:
            return status
        threading.Event().wait(0.01)
    raise AssertionError(f"Export timed out: {service.get_job_status(job.id)}")


@pytest.fixture
def drawing() -> Iterator[tuple[Dispatcher, BlobStore, NodeId]]:
    from ltechdesign.domain.models import DocumentSession

    store = BlobStore()
    engine = Dispatcher(
        DocumentSession(project=create_project("Raster test")), assets=store.retention()
    )
    page = engine.snapshot.project.document.pages[0].id
    board = create_node("artboard", page, node_id=NodeId("board"), width=120, height=80)
    leaf = replace(
        create_node("rectangle", page, node_id=NodeId("leaf"), width=40, height=30),
        x=20,
        y=10,
        parent_id=board.id,
        style=Style(fill=Fill(color="#FF000080")),
    )
    ok(engine, Create(node=board), Create(node=leaf))
    yield engine, store, board.id
    engine.close()


def submit(
    service: ExportService,
    engine: Dispatcher,
    store: BlobStore,
    options: ExportOptions,
    request_id: str = "export",
) -> JobStatus:
    return service.submit(
        engine.snapshot,
        store,
        options,
        expected_revision=engine.snapshot.revision,
        request_id=request_id,
    )


@pytest.mark.parametrize("format", ["png", "jpg", "webp"])
def test_real_encoded_dimensions_alpha_dpi_and_flatten(
    drawing: tuple[Dispatcher, BlobStore, NodeId],
    tmp_path: Path,
    format: Literal["png", "jpg", "webp"],
) -> None:
    engine, store, board = drawing
    service = ExportService(allowed_roots=(tmp_path,))
    try:
        options = ExportOptions(
            str(tmp_path),
            ExportTarget(artboard_id=board),
            format=format,
            scale=2,
            dpi=300,
            quality=100,
            background="#204060" if format == "jpg" else None,
        )
        result = wait(service, submit(service, engine, store, options))
        assert result.state == "succeeded", result
        assert result.source_revision == engine.snapshot.revision
        assert result.progress == 1 and len(result.committed) == 1
        with Image.open(result.committed[0]) as image:
            image.load()
            assert image.size == (240, 160)
            if format == "jpg":
                assert image.mode == "RGB" and "A" not in image.getbands()
                assert image.getpixel((220, 140)) == pytest.approx((32, 64, 96), abs=2)
                assert image.getpixel((60, 40)) == pytest.approx((144, 32, 48), abs=3)
            else:
                rgba = image.convert("RGBA")
                assert rgba.getchannel("A").getpixel((220, 140)) == 0
                assert rgba.getchannel("A").getpixel((60, 40)) == 128
            if format != "webp":
                assert image.info["dpi"] == pytest.approx((300, 300), abs=1)
        assert not list(tmp_path.glob("*.lock")) and not list(tmp_path.glob("*.tmp"))
    finally:
        service.shutdown()


def test_custom_size_letterbox_and_pillow_webp_lossless(
    drawing: tuple[Dispatcher, BlobStore, NodeId], tmp_path: Path
) -> None:
    engine, store, board = drawing
    service = ExportService(allowed_roots=(tmp_path,), prefer_pillow_webp=True)
    try:
        options = ExportOptions(
            str(tmp_path),
            ExportTarget(artboard_id=board),
            format="webp",
            width=200,
            height=200,
            lossless=True,
        )
        result = wait(service, submit(service, engine, store, options))
        assert result.state == "succeeded", result
        assert result.outputs[0].encoder == "pillow"
        with Image.open(result.committed[0]) as image:
            image.load()
            assert image.size == (200, 200)
            assert image.getchannel("A").getpixel((1, 1)) == 0
            assert image.getchannel("A").getpixel((60, 60)) == 128
    finally:
        service.shutdown()


def test_all_artboards_order_naming_and_per_output_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with (ROOT / "examples/proyek-contoh.ltechdesign").open("rb") as stream:
        native = read_archive(stream)
    store = BlobStore()
    lease = store.admit(native.project.assets.assets, native.blobs)
    from ltechdesign.domain.models import DocumentSession

    snapshot = DocumentSession(project=native.project)
    service = ExportService(allowed_roots=(tmp_path,))
    real_replace = os.replace
    seen: list[str] = []

    def controlled(src: str | Path, dst: str | Path) -> None:
        seen.append(str(dst))
        if len(seen) == 2:
            raise PermissionError("Controlled write failure")
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", controlled)
    try:
        options = ExportOptions(
            str(tmp_path), ExportTarget("all_artboards"), pattern="{index:03d}-{page}-{artboard}"
        )
        job = service.submit(snapshot, store, options, expected_revision=0, request_id="all")
        lease.release()
        store.collect()  # the actual queued/running export lease retains embedded bytes
        result = wait(service, job)
        assert result.state == "failed" and result.error == "io_error", result
        assert len(result.committed) == 1
        assert result.outputs[0].name.startswith("001-Poster-")
        assert result.outputs[1].name.startswith("002-Web-")
        assert result.outputs[1].state == "failed"
        assert set(store.collect()) == set(native.blobs)
        assert not list(tmp_path.glob("*.tmp"))
    finally:
        lease.release()
        service.shutdown()


def test_job_snapshot_is_immutable_dedup_precedes_revision_and_request_conflict(
    drawing: tuple[Dispatcher, BlobStore, NodeId], tmp_path: Path
) -> None:
    engine, store, board = drawing
    service = ExportService(allowed_roots=(tmp_path,), ledger_capacity=1)
    try:
        options = ExportOptions(str(tmp_path), ExportTarget(artboard_id=board))
        before = engine.snapshot
        job = submit(service, engine, store, options)
        ok(engine, Move(node_id=NodeId("leaf"), dx=50, dy=0))
        assert (
            service.submit(
                engine.snapshot,
                store,
                options,
                expected_revision=before.revision,
                request_id="export",
            ).id
            == job.id
        )
        with pytest.raises(ModelError) as changed:
            submit(service, engine, store, replace(options, scale=2))
        assert changed.value.code == "request_id_conflict"
        with pytest.raises(ModelError) as capacity:
            submit(service, engine, store, options, request_id="new")
        assert capacity.value.code == "dedup_capacity_exceeded"
        result = wait(service, job)
        assert result.state == "succeeded" and result.source_revision == before.revision
        with Image.open(result.committed[0]) as image:
            assert image.getchannel("A").getpixel((25, 15)) == 128
            assert image.getchannel("A").getpixel((95, 15)) == 0
        assert engine.snapshot.revision == before.revision + 1
        assert len(engine.undo_history) == 2  # export made no content/history entry
    finally:
        service.shutdown()


@pytest.mark.parametrize("when", ["queued", "before_commit", "after_commit"])
def test_cancel_truthful_commit_barrier(
    drawing: tuple[Dispatcher, BlobStore, NodeId],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    when: str,
) -> None:
    from ltechdesign.exports import service as module

    engine, store, board = drawing
    service = ExportService(allowed_roots=(tmp_path,))
    entered, release = threading.Event(), threading.Event()
    real_fingerprint = fingerprint_path
    real_replace = os.replace
    calls = [0]

    def fingerprint(*args: Any, **kwargs: Any) -> Any:
        result = real_fingerprint(*args, **kwargs)
        calls[0] += 1
        if when == "before_commit" and calls[0] == 2:
            entered.set()
            assert release.wait(10)
        return result

    def replace_output(src: str | Path, dst: str | Path) -> None:
        real_replace(src, dst)
        if when == "after_commit":
            entered.set()
            assert release.wait(10)

    monkeypatch.setattr(module, "fingerprint_path", fingerprint)
    monkeypatch.setattr(os, "replace", replace_output)
    # Queue admission stays deterministic while a real coordinator slot is occupied.
    blocker = service._executor.submit(lambda: release.wait(10)) if when == "queued" else None
    try:
        options = ExportOptions(str(tmp_path), ExportTarget(artboard_id=board))
        job = submit(service, engine, store, options)
        if when == "queued":
            service.cancel_job(job.id)
            release.set()
        else:
            assert entered.wait(15)
            if when == "after_commit":
                # cancel waits behind the shared commit lock, then observes the actual output.
                cancellation = threading.Thread(target=service.cancel_job, args=(job.id,))
                cancellation.start()
                release.set()
                cancellation.join(5)
                assert not cancellation.is_alive()
            else:
                service.cancel_job(job.id)
                release.set()
        result = wait(service, job)
        assert result.state == ("succeeded" if when == "after_commit" else "cancelled"), result
        assert bool(result.committed) == (when == "after_commit")
        assert service.cancel_job(job.id) == result  # final cancel is idempotent
        assert not list(tmp_path.glob("*.tmp")) and not list(tmp_path.glob("*.lock"))
    finally:
        release.set()
        if blocker:
            blocker.result(timeout=5)
        service.shutdown()


def test_limit_rejection_and_permission_scope(
    drawing: tuple[Dispatcher, BlobStore, NodeId], tmp_path: Path
) -> None:
    engine, store, board = drawing
    service = ExportService(max_pixels=100)
    options = ExportOptions(str(tmp_path), ExportTarget(artboard_id=board))
    try:
        with pytest.raises(ModelError) as outside:
            submit(service, engine, store, options)
        assert outside.value.code == "path_not_allowed"
        service.grant_directory(tmp_path)
        result = wait(service, submit(service, engine, store, options))
        assert result.state == "failed" and result.error == "limit_exceeded"
        assert not list(tmp_path.glob("*.png"))
    finally:
        service.shutdown()


@pytest.mark.parametrize(
    "pattern", ["../escape", "{project.__class__}", "{unknown}", "{index:100000d}", "a/b"]
)
def test_naming_rejects_paths_and_unbounded_formats(tmp_path: Path, pattern: str) -> None:
    with pytest.raises(ModelError):
        ExportOptions(str(tmp_path), ExportTarget("all_artboards"), pattern=pattern).validate()


def test_collision_and_external_change_preserve_existing_file(
    drawing: tuple[Dispatcher, BlobStore, NodeId], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ltechdesign.exports import service as module

    engine, store, board = drawing
    service = ExportService(allowed_roots=(tmp_path,))
    path = tmp_path / "fixed.png"
    path.write_bytes(b"existing user file")
    options = ExportOptions(str(tmp_path), ExportTarget(artboard_id=board), pattern="fixed")
    try:
        result = wait(service, submit(service, engine, store, options))
        assert result.state == "failed" and result.error == "target_in_use"
        assert path.read_bytes() == b"existing user file"
        real_fingerprint = fingerprint_path
        calls = [0]

        def foreign_write(*args: Any, **kwargs: Any) -> Any:
            calls[0] += 1
            if calls[0] == 2:
                path.write_bytes(b"foreign change during render")
            return real_fingerprint(*args, **kwargs)

        monkeypatch.setattr(module, "fingerprint_path", foreign_write)
        result = wait(
            service, submit(service, engine, store, replace(options, overwrite=True), "replace")
        )
        assert result.state == "failed" and result.outputs[0].error == "external_change_conflict"
        assert path.read_bytes() == b"foreign change during render"
    finally:
        service.shutdown()


def test_cancel_after_first_of_all_artboards_retains_published_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ltechdesign.domain.models import DocumentSession

    with (ROOT / "examples/proyek-contoh.ltechdesign").open("rb") as stream:
        native = read_archive(stream)
    store = BlobStore()
    lease = store.admit(native.project.assets.assets, native.blobs)
    service = ExportService(allowed_roots=(tmp_path,))
    identifier: list[str] = []
    real_replace = os.replace

    def cancel_after_replace(src: str | Path, dst: str | Path) -> None:
        real_replace(src, dst)
        service.cancel_job(identifier[0])  # cancellation after the actual filesystem barrier

    monkeypatch.setattr(os, "replace", cancel_after_replace)
    try:
        snapshot = DocumentSession(project=native.project)
        job = service.submit(
            snapshot,
            store,
            ExportOptions(str(tmp_path), ExportTarget("all_artboards")),
            expected_revision=0,
            request_id="all-cancel",
        )
        identifier.append(job.id)
        result = wait(service, job)
        assert result.state == "succeeded" and result.cancel_requested
        assert len(result.committed) == 1 and result.committed[0].exists()
        assert [o.state for o in result.outputs] == ["succeeded", "cancelled"]
        assert not list(tmp_path.glob("*.tmp"))
    finally:
        lease.release()
        service.shutdown()


def test_queue_backpressure_dedup_expiry_and_export_files_not_ttl(
    drawing: tuple[Dispatcher, BlobStore, NodeId], tmp_path: Path
) -> None:
    engine, store, board = drawing
    service = ExportService(allowed_roots=(tmp_path,), max_queued=1)
    release = threading.Event()
    blocker = service._executor.submit(lambda: release.wait(10))
    try:
        options = ExportOptions(str(tmp_path), ExportTarget(artboard_id=board))
        a = submit(service, engine, store, replace(options, pattern="a"), "a")
        b = submit(service, engine, store, replace(options, pattern="b"), "b")
        with pytest.raises(ModelError) as error:
            submit(service, engine, store, replace(options, pattern="c"), "c")
        assert error.value.code == "queue_full"
        service.cancel_job(b.id)
        release.set()
        finished = wait(service, a)
        assert finished.state == "succeeded"
        assert wait(service, b).state == "cancelled"
        service._jobs[a.id].finished = time.monotonic() - 1799
        assert service.get_job_status(a.id).state == "succeeded"
        service._jobs[a.id].finished = time.monotonic() - 1801
        with pytest.raises(ModelError) as expired:
            service.get_job_status(a.id)
        assert expired.value.code == "job_not_found"
        assert finished.committed[0].exists()
    finally:
        release.set()
        blocker.result(timeout=5)
        service.shutdown()


@pytest.mark.parametrize("dimensions", [(8192, 8192), (32768, 32768)])
def test_default_64mp_limit_rejects_before_rendering(
    drawing: tuple[Dispatcher, BlobStore, NodeId], tmp_path: Path, dimensions: tuple[int, int]
) -> None:
    engine, store, board = drawing
    service = ExportService(allowed_roots=(tmp_path,))
    try:
        options = ExportOptions(
            str(tmp_path),
            ExportTarget(artboard_id=board),
            width=dimensions[0],
            height=dimensions[1],
        )
        result = wait(service, submit(service, engine, store, options))
        assert result.state == "failed" and result.error == "limit_exceeded"
        assert not list(tmp_path.glob("*.png"))
    finally:
        service.shutdown()


def test_render_process_failure_is_reported_and_staging_released(
    drawing: tuple[Dispatcher, BlobStore, NodeId], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ltechdesign.exports import service as module

    engine, store, board = drawing
    service = ExportService(allowed_roots=(tmp_path,))
    monkeypatch.setattr(module, "render_worker", crash_worker)
    try:
        result = wait(
            service,
            submit(
                service,
                engine,
                store,
                ExportOptions(str(tmp_path), ExportTarget(artboard_id=board)),
            ),
        )
        assert result.state == "failed" and result.error == "render_failed"
        assert not service.active_for() and not list(tmp_path.iterdir())
    finally:
        service.shutdown()


def test_write_failure_then_late_cancel_keeps_failed_state_and_committed_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ltechdesign.domain.models import DocumentSession

    with (ROOT / "examples/proyek-contoh.ltechdesign").open("rb") as stream:
        native = read_archive(stream)
    store = BlobStore()
    lease = store.admit(native.project.assets.assets, native.blobs)
    service = ExportService(allowed_roots=(tmp_path,))
    identifier: list[str] = []
    calls = [0]
    original = os.replace

    def publish(src: str | Path, dst: str | Path) -> None:
        calls[0] += 1
        if calls[0] == 1:
            raise PermissionError("Controlled first-output failure")
        original(src, dst)
        service.cancel_job(identifier[0])

    monkeypatch.setattr(os, "replace", publish)
    try:
        snapshot = DocumentSession(project=native.project)
        job = service.submit(
            snapshot,
            store,
            ExportOptions(str(tmp_path), ExportTarget("all_artboards")),
            expected_revision=0,
            request_id="mixed-result",
        )
        identifier.append(job.id)
        result = wait(service, job)
        assert result.state == "failed" and result.error == "io_error", result
        assert result.cancel_requested and len(result.committed) == 1
        assert [o.state for o in result.outputs] == ["failed", "succeeded"]
        assert result.committed[0].exists()
    finally:
        lease.release()
        service.shutdown()
