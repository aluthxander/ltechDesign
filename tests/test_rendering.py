from dataclasses import replace

import pytest
from PySide6.QtCore import QPoint, QRectF
from PySide6.QtGui import QImage, QPainter
from pytestqt.qtbot import QtBot
from test_commands import engine, node, ok

from ltechdesign.commands import Create, Group, Move, Reorder, Update
from ltechdesign.commands.dispatcher import Dispatcher
from ltechdesign.domain import ModelError
from ltechdesign.domain.geometry import world_matrix
from ltechdesign.domain.models import Fill, NodeId, Point, Style
from ltechdesign.rendering.canvas import CanvasView
from ltechdesign.rendering.drawing import render_image

pytestmark = pytest.mark.desktop


def drawing_fixture() -> Dispatcher:
    d = engine()
    first = node(
        d,
        "red",
        x=20,
        y=20,
        width=60,
        height=60,
        pivot=Point(x=30, y=30),
        style=Style(fill=Fill(color="#FF0000FF")),
    )
    second = replace(first, id=NodeId("blue"), x=50, style=Style(fill=Fill(color="#0000FFFF")))
    ok(d, Create(node=first), Create(node=second))
    ok(d, Group(node_ids=(first.id, second.id), group_id=NodeId("group")))
    group = d.snapshot.project.document.nodes[NodeId("group")]
    ok(d, Update(node=replace(group, opacity=0.5)))
    return d


def test_isolated_overlap_and_z_order(qtbot: QtBot) -> None:
    d = drawing_fixture()
    doc = d.snapshot.project.document
    image = render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 150, 100))
    assert image.pixelColor(30, 30).alpha() == pytest.approx(128, abs=1)
    assert image.pixelColor(60, 30).alpha() == pytest.approx(128, abs=1)
    assert image.pixelColor(60, 30).blue() == 255
    ok(d, Reorder(node_id=NodeId("red"), index=1))
    doc = d.snapshot.project.document
    image = render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 150, 100))
    assert image.pixelColor(60, 30).red() == 255


def test_nested_world_transform_incremental_and_navigation(qtbot: QtBot) -> None:
    d = drawing_fixture()
    view = CanvasView()
    qtbot.addWidget(view)
    view.resize(700, 500)
    view.show()
    doc = d.snapshot.project.document
    group = doc.nodes[NodeId("group")]
    ok(d, Update(node=replace(group, rotation=31, scale=1.3)))
    doc = d.snapshot.project.document
    view.adapter.sync(doc)
    identities = dict(view.adapter.items)
    actual = identities[NodeId("red")].mapToScene(10, 15)
    expected = world_matrix(doc, NodeId("red")).point(Point(x=10, y=15))
    assert actual.x() == pytest.approx(expected.x)
    assert actual.y() == pytest.approx(expected.y)
    ok(d, Move(node_id=NodeId("blue"), dx=5, dy=3))
    view.adapter.sync(d.snapshot.project.document)
    assert all(view.adapter.items[k] is item for k, item in identities.items())
    snapshot, history = d.snapshot, d.undo_history
    cursor = QPoint(220, 190)
    before = view.mapToScene(cursor)
    view.set_zoom(2.0, cursor)
    after = view.mapToScene(cursor)
    assert abs(before.x() - after.x()) < 1
    assert abs(before.y() - after.y()) < 1
    view.set_zoom(100000)
    assert view.zoom == view.MAX_ZOOM
    view.set_zoom(0)
    assert view.zoom == pytest.approx(view.MIN_ZOOM)
    view.selection = (NodeId("red"),)
    view.zoom_selection()
    assert d.snapshot is snapshot and d.undo_history == history


def test_rounded_clip_visibility_and_leaf_alpha(qtbot: QtBot) -> None:
    d = engine()
    frame = node(
        d,
        "frame",
        "frame",
        width=100,
        height=100,
        clip_content=True,
        style=Style(fill=Fill(color="#FF0000FF"), radius=(30, 30, 30, 30)),
    )
    child = node(
        d,
        "child",
        parent_id=frame.id,
        width=100,
        height=100,
        style=Style(fill=Fill(color="#0000FFFF")),
    )
    ok(d, Create(node=frame), Create(node=child))
    doc = d.snapshot.project.document
    image = render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 100, 100))
    assert image.pixelColor(1, 1).alpha() == 0
    assert image.pixelColor(50, 50).blue() == 255
    ok(d, Update(node=replace(child, visible=False)))
    doc = d.snapshot.project.document
    image = render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 100, 100))
    assert image.pixelColor(50, 50).red() == 255
    # Isolation resets the device transform for composition; the ancestor's
    # rounded clip must survive that reset.
    ok(d, Update(node=child), Group(node_ids=(child.id,), group_id=NodeId("clipped-group")))
    group = d.snapshot.project.document.nodes[NodeId("clipped-group")]
    ok(d, Update(node=replace(group, opacity=0.5)))
    doc = d.snapshot.project.document
    image = render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 100, 100))
    assert image.pixelColor(1, 1).alpha() == 0
    assert image.pixelColor(50, 50).blue() == pytest.approx(127, abs=1)


def test_scene_and_shared_image_equivalent_without_overlays(qtbot: QtBot) -> None:
    d = drawing_fixture()
    doc = d.snapshot.project.document
    view = CanvasView()
    qtbot.addWidget(view)
    view.adapter.sync(doc)
    view.selection = (NodeId("group"),)
    image = QImage(150, 100, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    view.scene().render(painter, QRectF(0, 0, 150, 100), QRectF(0, 0, 150, 100))
    painter.end()
    expected = render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 150, 100))
    assert image.pixelColor(60, 30) == expected.pixelColor(60, 30)
    assert image.pixelColor(10, 10).alpha() == 0


def test_nested_isolation_pixel_budget_and_style(qtbot: QtBot) -> None:
    d = drawing_fixture()
    ok(d, Group(node_ids=(NodeId("group"),), group_id=NodeId("outer")))
    outer = d.snapshot.project.document.nodes[NodeId("outer")]
    ok(d, Update(node=replace(outer, opacity=0.5)))
    doc = d.snapshot.project.document
    image = render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 150, 100))
    assert image.pixelColor(60, 30).alpha() == pytest.approx(64, abs=1)
    with pytest.raises(ModelError, match="render_pixels"):
        render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 1000000, 1000000))
    with pytest.raises(ModelError, match="isolation_pixels"):
        render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 1, 1), scale=1000)


def test_ctrl_wheel_pan_and_hidden_root(qtbot: QtBot) -> None:
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent, QWheelEvent

    d = drawing_fixture()
    view = CanvasView()
    qtbot.addWidget(view)
    view.resize(600, 400)
    view.show()
    view.adapter.sync(d.snapshot.project.document)
    snapshot = d.snapshot
    event = QWheelEvent(
        QPointF(100, 100),
        QPointF(100, 100),
        QPoint(),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.ControlModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    view.wheelEvent(event)
    assert view.zoom > 1
    before = view.horizontalScrollBar().value()
    view.mousePressEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(100, 100),
            QPointF(100, 100),
            Qt.MouseButton.MiddleButton,
            Qt.MouseButton.MiddleButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    view.mouseMoveEvent(
        QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(120, 100),
            QPointF(120, 100),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.MiddleButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )
    assert view.horizontalScrollBar().value() == before - 20
    assert d.snapshot is snapshot
    group = d.snapshot.project.document.nodes[NodeId("group")]
    ok(d, Update(node=replace(group, visible=False)))
    doc = d.snapshot.project.document
    view.adapter.sync(doc)
    image = render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 150, 100))
    assert image.pixelColor(60, 30).alpha() == 0


def test_line_polygon_stroke_and_overflow(qtbot: QtBot) -> None:
    from ltechdesign.domain.models import Stroke

    d = engine()
    line = node(d, "line", "line", style=Style(stroke=Stroke(color="#112233FF", width=4)))
    polygon = node(d, "polygon", "polygon", x=120, style=Style(fill=Fill(color="#00FF00FF")))
    ok(d, Create(node=line), Create(node=polygon))
    doc = d.snapshot.project.document
    image = render_image(doc, doc.pages[0].root_ids, QRectF(-5, -5, 250, 120))
    assert image.pixelColor(55, 55).alpha() == 255
    assert image.pixelColor(175, 30).green() == 255
