from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from threading import Event, get_ident
from typing import Literal

import pytest
import test_drawing_tools as drawing_tools
from PySide6.QtCore import (
    QMimeData,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QUrl,
)
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QImage, QPainter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from pytestqt.qtbot import QtBot

from ltechdesign.commands import Delete, RemoveAsset, Update
from ltechdesign.domain.errors import ModelError
from ltechdesign.domain.models import Crop, MediaData, NodeId, PageId, Style
from ltechdesign.rendering.drawing import render_image
from ltechdesign.rendering.media import prepare_source
from ltechdesign.rendering.pdf import render_pdf
from ltechdesign.ui.canvas import EditorCanvas
from ltechdesign.ui.window import StudioWindow, Tab

pytestmark = pytest.mark.desktop
editor = drawing_tools.editor


@pytest.fixture(autouse=True)
def clear_node_clipboard(qapp: QApplication) -> Iterator[None]:
    yield
    # Release Python-owned QMimeData before QApplication is destroyed (Qt offscreen).
    qapp.clipboard().clear()


SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="80" height="40" viewBox="0 0 80 40">'
    b'<rect width="40" height="40" fill="#ff0000"/>'
    b'<path d="M40 0 H80 V40 H40 Z" fill="#0000ff"/></svg>'
)


def image_file(tmp_path: Path, format_name: str = "PNG") -> Path:
    image = QImage(80, 40, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.red)
    p = QPainter(image)
    p.fillRect(40, 0, 40, 40, Qt.GlobalColor.blue)
    p.end()
    target = tmp_path / ("source." + format_name.lower())
    assert image.save(str(target), format_name)  # type: ignore[call-overload]
    return target


def import_image(
    qtbot: QtBot, window: StudioWindow, tab: Tab, path: Path, target: NodeId | None = None
) -> NodeId:
    node = tab.dispatcher.snapshot.project.document.nodes[target] if target else None
    owner = get_ident()
    publications: list[int] = []
    unsubscribe = tab.dispatcher.subscribe(lambda _: publications.append(get_ident()))
    job = window.images.start(tab, [str(path)], QPointF(0, 0), node)
    assert job
    qtbot.waitUntil(lambda: window.images.active is None, timeout=10000)
    status = window.images.status(job)
    unsubscribe()
    assert status["state"] == "succeeded", status
    assert publications == [owner]  # Worker result commits/widgets only on GUI owner thread.
    return tab.selection[0]


@pytest.mark.parametrize("format_name", ["PNG", "JPEG", "WEBP", "SVG"])
def test_dialog_import_portable_after_source_move_and_editable_reopen(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    format_name: str,
) -> None:
    window, tab, view = editor
    if format_name == "SVG":
        source = tmp_path / "source.svg"
        source.write_bytes(SVG)
    else:
        source = image_file(tmp_path, format_name)
    original = source.read_bytes()
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *a, **k: ([str(source)], ""))
    window.menu_actions["import_images"].trigger()
    qtbot.waitUntil(lambda: window.images.active is None)
    assert len(tab.selection) == 1
    key = tab.selection[0]
    assert window.inspector.images.gallery.count() == 1
    assert len(tab.dispatcher.undo_history) == 1 and tab.dispatcher.snapshot.revision == 1
    node = tab.dispatcher.snapshot.project.document.nodes[key]
    assert isinstance(node.data, MediaData)
    assert node.type == ("svg" if format_name == "SVG" else "image")
    source.rename(source.with_name("moved-away"))
    project = tab.dispatcher.snapshot.project
    assets = project.assets.assets
    with tab.store.pin(assets) as pinned:
        assert list(pinned.blobs.values()) == [original]
    native = tmp_path / "portable.ltechdesign"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(native), ""))
    window.save_document(as_new=True)
    qtbot.waitUntil(lambda: not window.busy)
    before = render_image(
        project.document,
        project.document.pages[0].root_ids,
        QRectF(node.x, node.y, node.width, node.height),
        resources=view.adapter.resources,
    )
    portable = tmp_path / "copy.ltechdesign"
    portable.write_bytes(native.read_bytes())
    window.open_path(str(portable), read_only=True)
    qtbot.waitUntil(lambda: not window.busy)
    reopened = window.current
    assert reopened and reopened is not tab and reopened.view
    loaded = reopened.dispatcher.snapshot.project
    assert loaded.document == project.document
    with reopened.store.pin(loaded.assets.assets) as pinned:
        assert list(pinned.blobs.values()) == [original]
    after = render_image(
        loaded.document,
        loaded.document.pages[0].root_ids,
        QRectF(node.x, node.y, node.width, node.height),
        resources=reopened.view.adapter.resources,
    )
    assert after == before


def test_crop_fit_replace_keep_container_and_real_gc_history_leases(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, tab, view = editor
    key = import_image(qtbot, window, tab, image_file(tmp_path))
    original = tab.dispatcher.snapshot.project.document.nodes[key]
    node = replace(original, rotation=27, opacity=0.6, style=Style(radius=(8, 12, 4, 16)))
    assert window.execute(tab, (Update(node=node),))
    panel = window.inspector.images
    panel.crop["x"].setText("0.5")
    panel.crop["width"].setText("0.5")
    panel.fit.setCurrentText("fill")
    panel.apply_button.click()
    cropped = tab.dispatcher.snapshot.project.document.nodes[key]
    assert isinstance(cropped.data, MediaData) and cropped.data.crop == Crop(x=0.5, width=0.5)
    assert replace(cropped, data=node.data) == node
    window.history("undo")
    assert tab.dispatcher.snapshot.project.document.nodes[key] == node
    window.history("redo")
    svg = tmp_path / "replace.svg"
    svg.write_bytes(SVG)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(svg), ""))
    panel.replace_button.click()
    qtbot.waitUntil(lambda: window.images.active is None)
    replaced = tab.dispatcher.snapshot.project.document.nodes[key]
    assert isinstance(replaced.data, MediaData) and isinstance(cropped.data, MediaData)
    assert replaced.data.asset_id != cropped.data.asset_id and replaced.type == "svg"
    assert replace(replaced, data=cropped.data, type=cropped.type) == cropped
    from io import BytesIO

    from ltechdesign.persistence.archive import read_archive, write_archive

    snapshot = tab.dispatcher.snapshot
    archive = BytesIO()
    with tab.store.pin(snapshot.project.assets.assets) as pinned:
        write_archive(archive, snapshot.project, pinned.blobs)
    svg.unlink()
    archive.seek(0)
    restored = read_archive(archive)
    assert restored.project.document == snapshot.project.document
    assert restored.project.document.nodes[key].data == replaced.data
    assert window.execute(tab, (RemoveAsset(asset_id=cropped.data.asset_id),))
    assert window.execute(tab, (Delete(node_id=key), RemoveAsset(asset_id=replaced.data.asset_id)))
    # No live assets, yet cleanup cannot collect bytes referenced by undo/redo.
    assert not tab.dispatcher.snapshot.project.assets.assets
    assert tab.store.collect() == ()
    window.history("undo")
    assert tab.dispatcher.snapshot.project.document.nodes[key] == replaced
    window.history("undo")
    window.history("undo")
    assert tab.dispatcher.snapshot.project.document.nodes[key] == cropped
    assert tab.store.collect() == ()
    window.history("redo")
    assert tab.dispatcher.snapshot.project.document.nodes[key] == replaced
    project_snapshot = tab.dispatcher.snapshot.project
    lease = tab.store.pin(project_snapshot.assets.assets)  # independent recovery/job/snapshot root
    tab.dispatcher.close()
    assert tab.store.collect() == ()
    lease.release()
    assert len(tab.store.collect()) == 2


@pytest.mark.parametrize("fit", ["fit", "fill", "stretch"])
@pytest.mark.parametrize("vector", [False, True])
def test_source_crop_then_mapping_pixels_rounded_clip(
    qapp: QApplication, tmp_path: Path, fit: Literal["fit", "fill", "stretch"], vector: bool
) -> None:
    from ltechdesign.domain import create_node
    from ltechdesign.domain.models import AssetId
    from ltechdesign.rendering.media import draw_media

    source = prepare_source(
        SVG if vector else image_file(tmp_path).read_bytes(),
        "image/svg+xml" if vector else "image/png",
    )
    node = create_node(
        "svg" if vector else "image",
        PageId("page"),
        width=80,
        height=80,
        data=MediaData(asset_id=AssetId("a"), fit=fit, crop=Crop(x=0.5, width=0.5)),
        node_id=NodeId("n"),
    )
    image = QImage(80, 80, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    draw_media(p, node, source)
    p.end()
    assert image.pixelColor(40, 40).blue() > 250 and image.pixelColor(40, 40).red() < 5
    # Square source crop => all three modes cover the square container exactly.
    assert image.pixelColor(10, 10).alpha() == 255
    rounded = replace(node, style=Style(radius=(30, 30, 30, 30)))
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw_media(p, rounded, source)
    p.end()
    assert image.pixelColor(0, 0).alpha() == 0 and image.pixelColor(40, 40).blue() > 250


def test_shared_canvas_png_pdf_nested_transform_clip_and_vector_pdf(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas], tmp_path: Path
) -> None:
    from ltechdesign.commands import Create, Reparent
    from ltechdesign.domain import create_node
    from ltechdesign.domain.models import FrameData

    window, tab, view = editor
    raster = import_image(qtbot, window, tab, image_file(tmp_path))
    svg = tmp_path / "vector.svg"
    svg.write_bytes(SVG)
    vector = import_image(qtbot, window, tab, svg)
    doc = tab.dispatcher.snapshot.project.document
    frame = replace(
        create_node("frame", doc.pages[0].id, width=125, height=95, data=FrameData()),
        x=30,
        y=35,
        rotation=15,
        clip_content=True,
        style=Style(radius=(16, 16, 16, 16)),
    )
    assert window.execute(
        tab,
        (
            Create(node=frame),
            Reparent(
                node_id=raster, page_id=frame.page_id, parent_id=frame.id, preserve_appearance=False
            ),
            Reparent(
                node_id=vector, page_id=frame.page_id, parent_id=frame.id, preserve_appearance=False
            ),
        ),
    )
    doc = tab.dispatcher.snapshot.project.document
    assert window.execute(
        tab,
        tuple(
            Update(
                node=replace(
                    doc.nodes[k],
                    x=offset,
                    y=10,
                    width=100,
                    height=70,
                    rotation=19,
                    opacity=opacity,
                    style=Style(radius=(20, 8, 16, 2)),
                    data=MediaData(
                        asset_id=doc.nodes[k].data.asset_id,  # type: ignore[union-attr]
                        fit="fill",
                        crop=Crop(x=0.25, width=0.7),
                    ),
                )
            )
            for k, offset, opacity in ((raster, -10, 0.65), (vector, 45, 1))
        ),
    )
    doc = tab.dispatcher.snapshot.project.document
    bounds = QRectF(0, 0, 220, 180)
    resources = view.adapter.resources
    assert resources
    png = render_image(doc, (frame.id,), bounds, resources=resources)
    canvas = QImage(png.size(), png.format())
    canvas.fill(Qt.GlobalColor.transparent)
    p = QPainter(canvas)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    view.scene().render(p, bounds, bounds)
    p.end()
    assert canvas == png
    pdf = tmp_path / "images.pdf"
    rasterized = render_pdf(doc, (frame.id,), bounds, pdf, resources=resources)
    assert rasterized == (raster,)
    reader = QPdfDocument()
    assert reader.load(str(pdf)) == QPdfDocument.Error.None_
    pdf_image = reader.render(0, QSize(440, 360))
    assert not pdf_image.isNull()
    reference = render_image(doc, (frame.id,), bounds, scale=2, resources=resources)
    # PDF rasterizer uses white paper: compare opaque interiors and outside clips.
    opaque = errors = 0
    for y in range(0, 360, 2):
        for x in range(0, 440, 2):
            c = reference.pixelColor(x, y)
            if c.alpha() == 255 and all(
                reference.pixelColor(x + dx, y + dy) == c
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))
                if 0 < x < 439 and 0 < y < 359
            ):
                opaque += 1
                actual = pdf_image.pixelColor(x, y)
                errors = max(errors, abs(c.red() - actual.red()), abs(c.blue() - actual.blue()))
    assert opaque > 100 and errors <= 2
    assert png.pixelColor(0, 0).alpha() == 0
    # Fully opaque SVG-only PDF contains vector drawing, no image XObject.
    v = replace(doc.nodes[vector], parent_id=None, x=0, y=0, rotation=0, style=Style())
    simple = replace(doc, nodes={v.id: v}, pages=(replace(doc.pages[0], root_ids=(v.id,)),))
    vector_pdf = tmp_path / "vector.pdf"
    assert render_pdf(simple, (v.id,), QRectF(0, 0, 100, 70), vector_pdf, resources=resources) == ()
    assert b"/Subtype /Image" not in vector_pdf.read_bytes()


def test_drop_copies_local_files_rejects_remote_and_readonly(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas], tmp_path: Path
) -> None:
    window, tab, view = editor
    source = image_file(tmp_path)
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(source))])
    point = view.mapFromScene(20, 30)
    enter = QDragEnterEvent(
        point,
        Qt.DropAction.CopyAction | Qt.DropAction.MoveAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(view.viewport(), enter)
    assert enter.isAccepted()
    drop = QDropEvent(
        QPointF(point),
        Qt.DropAction.CopyAction | Qt.DropAction.MoveAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(view.viewport(), drop)
    assert drop.isAccepted() and drop.dropAction() == Qt.DropAction.CopyAction
    qtbot.waitUntil(lambda: window.images.active is None)
    assert source.exists() and len(tab.selection) == 1
    node = tab.dispatcher.snapshot.project.document.nodes[tab.selection[0]]
    assert abs(node.x - 20) < 1 and abs(node.y - 30) < 1
    mime.setUrls([QUrl("https://remote/image.png")])
    remote = QDragEnterEvent(
        point,
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    view.dragEnterEvent(remote)
    assert not remote.isAccepted()
    view.writable = False
    mime.setUrls([QUrl.fromLocalFile(str(source))])
    locked = QDragEnterEvent(
        point,
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    view.dragEnterEvent(locked)
    assert not locked.isAccepted()


@pytest.mark.parametrize("mode", ["cancel", "stale", "malformed", "unsafe", "size"])
def test_import_failure_is_atomic_staging_clean_and_ui_responsive(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    import ltechdesign.ui.images as images

    window, tab, _ = editor
    source = image_file(tmp_path)
    other = tmp_path / "other.svg"
    other.write_bytes(SVG)
    if mode == "malformed":
        other.write_bytes(b"\x89PNG\r\n\x1a\nbroken")
    if mode == "unsafe":
        other.write_bytes(b'<svg><image href="file:///secret"/></svg>')
    if mode == "size":
        with other.open("wb") as stream:
            stream.truncate(50 * 1024 * 1024 + 1)
    before = tab.dispatcher.snapshot
    started, release = Event(), Event()
    from ltechdesign.assets.importing import stage_image

    real = stage_image

    def slow(*args, **kwargs):  # type: ignore[no-untyped-def]
        started.set()
        assert release.wait(5)
        return real(*args, **kwargs)

    monkeypatch.setattr(images, "stage_image", slow)
    job = window.images.start(tab, [str(source), str(other)], QPointF())
    assert job
    qtbot.waitUntil(started.is_set)
    heartbeats: list[int] = []
    QTimer.singleShot(0, lambda: heartbeats.append(1))
    qtbot.waitUntil(lambda: bool(heartbeats))
    assert window.images.status(job)["state"] == "running"
    assert window.images.start(tab, [str(source)], QPointF()) is None
    if mode == "cancel":
        window.inspector.images.cancel_button.click()
    if mode == "stale":
        from ltechdesign.commands import Create
        from ltechdesign.domain import create_node

        assert window.execute(
            tab, (Create(node=create_node("rectangle", before.project.document.pages[0].id)),)
        )
        before = tab.dispatcher.snapshot
    release.set()
    qtbot.waitUntil(lambda: window.images.active is None, timeout=10000)
    status = window.images.status(job)
    assert status["state"] == ("cancelled" if mode == "cancel" else "failed"), status
    assert tab.dispatcher.snapshot == before and tab.media == {}
    assert tab.store.collect() == ()
    assert not tab.store._staged and not tab.store._blobs


@pytest.mark.parametrize(
    "svg",
    [
        b'<svg width="20" height="20" opacity="0.5"><rect width="20" height="20"/></svg>',
        b'<svg width="20" height="20"><g opacity="0.5"><rect width="20" height="20"/></g></svg>',
        b'<svg width="1e99" height="2"/>',
        b'<svg width="20" height="20"><path d="M nan 2"/></svg>',
        b'<svg><g onload="x"/></svg>',
        b'<svg><use href="#a"/></svg>',
    ],
)
def test_malformed_svg_rejected_before_drawing(qapp: QApplication, svg: bytes) -> None:
    with pytest.raises(ModelError):
        prepare_source(svg, "image/svg+xml")


@pytest.mark.parametrize("fit", ["fit", "fill", "stretch"])
@pytest.mark.parametrize("vector", [False, True])
def test_fit_fill_stretch_distinguish_non_square_source(
    qapp: QApplication, tmp_path: Path, fit: Literal["fit", "fill", "stretch"], vector: bool
) -> None:
    from ltechdesign.domain import create_node
    from ltechdesign.domain.models import AssetId
    from ltechdesign.rendering.media import draw_media

    source = prepare_source(
        SVG if vector else image_file(tmp_path).read_bytes(),
        "image/svg+xml" if vector else "image/png",
    )
    node = create_node(
        "svg" if vector else "image",
        PageId("page"),
        width=80,
        height=80,
        data=MediaData(asset_id=AssetId("a"), fit=fit),
    )
    image = QImage(80, 80, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    draw_media(painter, node, source)
    painter.end()
    assert image.pixelColor(10, 5).alpha() == (0 if fit == "fit" else 255)
    assert image.pixelColor(10, 40).red() == 255 and image.pixelColor(70, 40).blue() == 255
    from ltechdesign.rendering.media import media_rects

    _, dst = media_rects(node, source)
    assert (dst.x(), dst.y(), dst.width(), dst.height()) == {
        "fit": (0, 20, 80, 40),
        "fill": (-40, 0, 160, 80),
        "stretch": (0, 0, 80, 80),
    }[fit]


def test_cancel_after_staging_and_after_commit(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ltechdesign.ui.images as images
    from ltechdesign.assets.importing import stage_image

    window, tab, _ = editor
    source = image_file(tmp_path)
    ready, release = Event(), Event()

    def staged(*args, **kwargs):  # type: ignore[no-untyped-def]
        result = stage_image(*args, **kwargs)
        ready.set()
        assert release.wait(5)
        return result

    monkeypatch.setattr(images, "stage_image", staged)
    before = tab.dispatcher.snapshot
    job = window.images.start(tab, [str(source)], QPointF())
    assert job
    qtbot.waitUntil(ready.is_set)
    assert tab.store._staged
    window.images.cancel(job)
    release.set()
    qtbot.waitUntil(lambda: window.images.active is None)
    assert window.images.status(job)["state"] == "cancelled"
    assert tab.dispatcher.snapshot == before and not tab.store._blobs and not tab.store._staged
    monkeypatch.setattr(images, "stage_image", stage_image)
    key = import_image(qtbot, window, tab, source)
    success_id = next(reversed(window.images.jobs))
    revision = tab.dispatcher.snapshot.revision
    window.images.cancel(success_id)
    assert window.images.status(success_id)["state"] == "succeeded"
    assert (
        key in tab.dispatcher.snapshot.project.document.nodes
        and tab.dispatcher.snapshot.revision == revision
    )


def test_decoder_does_not_hold_store_lock_and_preflight_budget(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from concurrent.futures import ThreadPoolExecutor

    import ltechdesign.assets.store as storage
    from ltechdesign.assets import BlobStore
    from ltechdesign.assets.importing import stage_image
    from ltechdesign.assets.validation import validate_asset

    source = image_file(tmp_path)
    store = BlobStore()
    started, release = Event(), Event()

    def slow(*args, **kwargs):  # type: ignore[no-untyped-def]
        started.set()
        assert release.wait(5)
        validate_asset(*args, **kwargs)

    monkeypatch.setattr(storage, "validate_asset", slow)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(stage_image, source, store, lambda: False)
        qtbot.waitUntil(started.is_set)
        # A validation holding the lock would deadlock this GUI-thread pin.
        with store.pin(()) as pinned:
            assert not pinned.blobs
        release.set()
        result = future.result(timeout=5)
    store.discard_staging((result.staging_id,))
    assert store.collect()
    with pytest.raises(ModelError, match="raster_pixels"):
        prepare_source(source.read_bytes(), "image/png", byte_budget=96 * 72 * 4 + 100)


def test_jpeg_exif_orientation_animation_and_svg_declaration(
    qapp: QApplication, tmp_path: Path
) -> None:
    from io import BytesIO

    from PIL import Image

    image = Image.new("RGB", (80, 40), "red")
    encoded = BytesIO()
    metadata = Image.Exif()
    metadata[274] = 6
    image.save(encoded, format="JPEG", exif=metadata)
    oriented = prepare_source(encoded.getvalue(), "image/jpeg")
    assert (oriented.width, oriented.height) == (40, 80)
    encoded = BytesIO()
    image.save(
        encoded,
        format="PNG",
        save_all=True,
        append_images=[Image.new("RGB", (80, 40), "blue")],
        duration=100,
    )
    with pytest.raises(ModelError, match="animated_image_unsupported"):
        prepare_source(encoded.getvalue(), "image/png")
    declared = b'<?xml version="1.0" encoding="UTF-8"?>\n' + SVG
    assert prepare_source(declared, "image/svg+xml").picture is not None


def test_existing_internal_node_clipboard_prepares_embedded_media(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas], tmp_path: Path
) -> None:
    from ltechdesign.domain import create_project

    window, tab, _ = editor
    source = image_file(tmp_path)
    key = import_image(qtbot, window, tab, source)
    original = tab.dispatcher.snapshot.project.document.nodes[key]
    assert isinstance(original.data, MediaData)
    original_source = tab.media[original.data.asset_id]
    window.editing.copy(tab, cut=False)
    qtbot.waitUntil(lambda: not window.busy)
    source.unlink()
    window.admit(
        window.prepare_admission(window.service.new(create_project("Clipboard media"), {}))
    )
    target = window.current
    assert target and target.view and target is not tab
    window.editing.paste(target)
    qtbot.waitUntil(lambda: not window.busy)
    node = target.dispatcher.snapshot.project.document.nodes[target.selection[0]]
    assert isinstance(node.data, MediaData)
    assert node.data.asset_id != original.data.asset_id
    assert target.media[node.data.asset_id].image == original_source.image
    assert (
        target.view.adapter.resources and node.data.asset_id in target.view.adapter.resources.media
    )
    doc = target.dispatcher.snapshot.project.document
    assert not render_image(
        doc,
        doc.pages[0].root_ids,
        QRectF(node.x, node.y, node.width, node.height),
        resources=target.view.adapter.resources,
    ).isNull()
    window.history("undo")
    assert not target.dispatcher.snapshot.project.document.nodes
    window.history("redo")
    assert node.id in target.dispatcher.snapshot.project.document.nodes


def test_closed_session_cannot_receive_import_completion(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ltechdesign.ui.images as images
    from ltechdesign.assets.importing import stage_image

    window, tab, _ = editor
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Discard)
    started, release = Event(), Event()

    def slow(*args, **kwargs):  # type: ignore[no-untyped-def]
        started.set()
        assert release.wait(5)
        return stage_image(*args, **kwargs)

    monkeypatch.setattr(images, "stage_image", slow)
    job = window.images.start(tab, [str(image_file(tmp_path))], QPointF())
    assert job
    qtbot.waitUntil(started.is_set)
    window.close_tab(0)  # Import is still staging; document has no authored edit to save.
    qtbot.waitUntil(lambda: not window.busy and not window.documents)
    release.set()
    qtbot.waitUntil(lambda: window.images.active is None)
    result = window.images.status(job)
    assert result["state"] == "failed" and result["error"]
    assert not window.documents and not tab.store._staged and not tab.store._blobs


def test_overlapping_images_use_isolated_group_opacity(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas], tmp_path: Path
) -> None:
    from ltechdesign.commands import Group

    window, tab, view = editor
    raster = import_image(qtbot, window, tab, image_file(tmp_path))
    svg = tmp_path / "blue.svg"
    svg.write_bytes(b'<svg width="80" height="40"><rect width="80" height="40" fill="blue"/></svg>')
    vector = import_image(qtbot, window, tab, svg)
    group = NodeId("image-group")
    assert window.execute(tab, (Group(node_ids=(raster, vector), group_id=group),))
    node = tab.dispatcher.snapshot.project.document.nodes[group]
    assert window.execute(tab, (Update(node=replace(node, opacity=0.5)),))
    doc = tab.dispatcher.snapshot.project.document
    image = render_image(
        doc, doc.pages[0].root_ids, QRectF(0, 0, 80, 40), resources=view.adapter.resources
    )
    pixel = image.pixelColor(20, 20)
    assert pixel.alpha() in (127, 128) and pixel.blue() == 255 and pixel.red() == 0
    assert render_pdf(
        doc,
        (group,),
        QRectF(0, 0, 80, 40),
        tmp_path / "group.pdf",
        resources=view.adapter.resources,
    ) == (group,)
