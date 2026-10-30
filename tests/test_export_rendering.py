from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QImageWriter, QPainter
from PySide6.QtWidgets import QGraphicsScene
from pytestqt.qtbot import QtBot
from test_commands import ok

from ltechdesign.commands import Create, Dispatcher
from ltechdesign.domain import ModelError, create_node, create_project
from ltechdesign.domain.geometry import local_matrix, world_matrix
from ltechdesign.domain.models import (
    DocumentSession,
    Fill,
    FrameData,
    NodeId,
    Shadow,
    Stroke,
    Style,
)
from ltechdesign.exports import ExportOptions, ExportTarget
from ltechdesign.rendering import drawing
from ltechdesign.rendering.canvas import SceneAdapter
from ltechdesign.rendering.exporting import plans

pytestmark = pytest.mark.desktop


def engine() -> Dispatcher:
    return Dispatcher(DocumentSession(project=create_project()))


def test_selection_ancestor_opacity_clip_zorder_and_shared_scene(qtbot: QtBot) -> None:
    del qtbot
    d = engine()
    page = d.snapshot.project.document.pages[0].id
    parent = replace(
        create_node("frame", page, width=120, height=100),
        x=50,
        y=40,
        opacity=0.5,
        clip_content=True,
        data=FrameData(background="#00FF00FF"),
        style=Style(radius=(20, 20, 20, 20)),
    )
    a = replace(
        create_node("rectangle", page, width=80, height=50),
        parent_id=parent.id,
        x=10,
        y=10,
        style=Style(fill=Fill(color="#FF0000FF")),
    )
    b = replace(a, id=NodeId("b"), x=40, y=20, style=Style(fill=Fill(color="#0000FFFF")))
    sibling = replace(
        a, id=NodeId("unselected"), x=0, y=70, style=Style(fill=Fill(color="#00FF00FF"))
    )
    ok(d, Create(node=parent), Create(node=a), Create(node=b), Create(node=sibling))
    source = d.snapshot
    options = ExportOptions(".", ExportTarget("selection", node_ids=(b.id, a.id)))
    (plan,) = plans(source.project, options)
    assert plan.bounds.getRect() == pytest.approx((60, 50, 110, 60), rel=0, abs=1e-6)
    image = drawing.render_image(plan.document, plan.roots, plan.bounds, resources=plan.resources())
    assert image.pixelColor(45, 25).alpha() == pytest.approx(127, abs=1)
    assert image.pixelColor(45, 25).blue() == 255  # request order cannot reverse document z-order
    assert image.pixelColor(5, 5).red() == 255
    assert image.pixelColor(0, 59).alpha() == 0  # parent fill/unselected sibling excluded
    scene = QGraphicsScene()
    adapter = SceneAdapter(scene)
    adapter.resources = plan.resources()
    adapter.sync(plan.document)
    rendered = QImage(image.size(), image.format())
    rendered.fill(Qt.GlobalColor.transparent)
    painter = QPainter(rendered)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scene.render(
        painter,
        QRectF(0, 0, image.width(), image.height()),
        plan.bounds,
        Qt.AspectRatioMode.IgnoreAspectRatio,
    )
    painter.end()
    assert bytes(rendered.constBits()) == bytes(image.constBits())
    assert d.snapshot is source and len(d.undo_history) == 1


def test_rounded_ancestor_clip_rejects_truly_empty_selection(qtbot: QtBot) -> None:
    del qtbot
    d = engine()
    page = d.snapshot.project.document.pages[0].id
    parent = replace(
        create_node("frame", page),
        rotation=37,
        clip_content=True,
        style=Style(radius=(50, 50, 50, 50)),
    )
    child = replace(
        create_node("rectangle", page, width=2, height=2),
        parent_id=parent.id,
        style=Style(fill=Fill(color="#FF0000FF")),
    )
    ok(d, Create(node=parent), Create(node=child))
    with pytest.raises(ModelError, match="empty_export_bounds"):
        plans(
            d.snapshot.project, ExportOptions(".", ExportTarget("selection", node_ids=(child.id,)))
        )


def test_selection_stroke_shadow_envelope_and_redundant_descendant(qtbot: QtBot) -> None:
    del qtbot
    d = engine()
    page = d.snapshot.project.document.pages[0].id
    node = replace(
        create_node("rectangle", page, width=40, height=20),
        x=-10,
        y=20,
        style=Style(
            fill=Fill(color="#AA8040FF"),
            stroke=Stroke(color="#FFFFFFFF", width=8),
            shadows=(Shadow(blur=2, spread=3, offset_x=5, offset_y=7),),
        ),
    )
    ok(d, Create(node=node))
    (plan,) = plans(
        d.snapshot.project, ExportOptions(".", ExportTarget("selection", node_ids=(node.id,)))
    )
    expected = drawing.transform(world_matrix(d.snapshot.project.document, node.id)).mapRect(
        drawing.local_visual(d.snapshot.project.document, node.id)
    )
    assert plan.bounds == expected
    image = drawing.render_image(plan.document, plan.roots, plan.bounds, resources=plan.resources())
    assert image.width() > node.width + 8 and image.height() > node.height + 8
    assert image.pixelColor(13, 13).alpha() > 0


def test_artboard_local_axes_and_selection_world_axes(qtbot: QtBot) -> None:
    del qtbot
    d = engine()
    page = d.snapshot.project.document.pages[0].id
    board = replace(
        create_node("artboard", page, width=80, height=40),
        x=300,
        y=-200,
        rotation=30,
        scale=2,
        data=FrameData(background="#123456FF"),
    )
    child = replace(create_node("rectangle", page, width=10, height=10), parent_id=board.id)
    ok(d, Create(node=board), Create(node=child))
    project = d.snapshot.project
    (artboard,) = plans(project, ExportOptions(".", ExportTarget(artboard_id=board.id), scale=3))
    assert artboard.bounds == QRectF(0, 0, 80, 40)
    assert (artboard.width, artboard.height) == (240, 120)
    image = drawing.render_image(artboard.document, artboard.roots, artboard.bounds, 3)
    assert image.pixelColor(5, 5).name() == "#123456"
    (selection,) = plans(
        project, ExportOptions(".", ExportTarget("selection", node_ids=(child.id, board.id)))
    )
    assert selection.bounds.width() > board.width
    assert world_matrix(project.document, board.id) == local_matrix(board)


@pytest.mark.parametrize("fallback", ["missing", "failed", "no_pillow"])
def test_runtime_webp_capability_and_fallback(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fallback: str
) -> None:
    del qtbot
    from PIL import Image, features

    from ltechdesign.exports import encoding

    image = QImage(20, 10, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    image.setPixelColor(5, 5, Qt.GlobalColor.red)
    options = ExportOptions(str(tmp_path), ExportTarget("all_artboards"), format="webp")
    if fallback in ("missing", "no_pillow"):
        monkeypatch.setattr(QImageWriter, "supportedImageFormats", lambda: [])
    else:
        monkeypatch.setattr(QImageWriter, "write", lambda *a: False)
    if fallback == "no_pillow":
        monkeypatch.setattr(features, "check", lambda *a: False)
        with pytest.raises(ModelError, match="webp_encoder_unavailable"):
            encoding.encode(image, tmp_path / "image.webp", options)
    else:
        backend, notes = encoding.encode(image, tmp_path / "image.webp", options)
        assert backend == "pillow" and notes
        with Image.open(tmp_path / "image.webp") as decoded:
            decoded.load()
            assert decoded.size == (20, 10)
            assert decoded.getchannel("A").getpixel((0, 0)) == 0
