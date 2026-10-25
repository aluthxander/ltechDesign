import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import test_drawing_tools as drawing_tools
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QImage, QMouseEvent, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog
from pytestqt.qtbot import QtBot
from test_hierarchy_panel import external

from ltechdesign.commands import Group, SetProperties, Update
from ltechdesign.domain.arrangement import ArrangeMode
from ltechdesign.domain.geometry import world_matrix
from ltechdesign.domain.models import Fill, NodeId, Point, Style
from ltechdesign.domain.snapping import AXES, geometry
from ltechdesign.rendering.drawing import render_image
from ltechdesign.rendering.pdf import render_pdf
from ltechdesign.ui.canvas import EditorCanvas
from ltechdesign.ui.canvas_aids import CanvasAidControls
from ltechdesign.ui.window import StudioWindow, Tab

pytestmark = pytest.mark.desktop
editor = drawing_tools.editor
add = drawing_tools.add


def configure(window: StudioWindow, *, grid: bool = False) -> CanvasAidControls:
    assert window.current is not None
    control = window.current.widget.findChild(CanvasAidControls)
    assert control is not None
    control.checks["snap"].setChecked(True)
    control.checks["grid_snap"].setChecked(grid)
    control.checks["object_snap"].setChecked(not grid)
    return control


def move_preview(
    view: EditorCanvas,
    start: QPointF,
    end: QPointF,
    modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
) -> QPoint:
    a, b = view.mapFromScene(start), view.mapFromScene(end)
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=a)
    QApplication.sendEvent(
        view.viewport(),
        QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(b),
            QPointF(b),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            modifiers,
        ),
    )
    return b


@pytest.mark.parametrize("zoom", [0.5, 1, 2])
def test_object_snap_nested_rotation_preview_then_one_undo_and_inspector(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    zoom: float,
    tmp_path: Path,
) -> None:
    window, tab, view = editor
    window.resize(1500, 900)
    parent = add(window, tab, "frame", x=50, y=70, width=500, height=400, rotation=31, scale=1.2)
    a = add(
        window,
        tab,
        "rectangle",
        parent_id=parent.id,
        x=80,
        y=90,
        width=100,
        height=70,
        rotation=-17,
        style=Style(fill=Fill(color="#2080C0FF")),
    )
    before_doc = tab.dispatcher.snapshot.project.document
    bound = geometry(before_doc, a.id)
    target = add(
        window,
        tab,
        "rectangle",
        x=bound.max_x + 50,
        y=bound.max_y + 140,
        width=50,
        height=60,
        style=Style(fill=Fill(color="#E08030FF")),
    )
    control = configure(window)
    control.checks["grid"].setChecked(True)
    view.set_selection((a.id,))
    view.set_zoom(zoom)
    matrix = world_matrix(tab.dispatcher.snapshot.project.document, a.id)
    center = matrix.point(a.pivot)
    start = QPointF(center.x, center.y)
    end = start + QPointF(50 - 3 / zoom / view.devicePixelRatioF(), 15)
    view.centerOn((start.x() + end.x()) / 2, (start.y() + end.y()) / 2)
    before, depth = tab.dispatcher.snapshot, len(tab.dispatcher.undo_history)
    b = move_preview(view, start, end)
    assert view.transforms.active is not None and view.aids.guides
    assert any(g.axis == "x" and g.coordinate == pytest.approx(target.x) for g in view.aids.guides)
    assert tab.dispatcher.snapshot is before
    qtbot.wait(20)
    assert window.grab().save(str(tmp_path / "smart-guides-native.png"))
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=b)
    doc = tab.dispatcher.snapshot.project.document
    assert geometry(doc, a.id).max_x == pytest.approx(target.x, abs=1e-8)
    assert not view.aids.guides and len(tab.dispatcher.undo_history) == depth + 1
    assert float(window.inspector.fields["x"].text()) == pytest.approx(doc.nodes[a.id].x)
    actual = view.adapter.items[a.id].mapToScene(0, 0)
    expected = world_matrix(doc, a.id).point(Point())
    assert (actual.x(), actual.y()) == pytest.approx((expected.x, expected.y))
    window.history("undo")
    assert tab.dispatcher.snapshot.project == before.project


def test_grid_snap_drawing_and_rotated_parent_drawing_endpoints(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, view = editor
    configure(window, grid=True)
    view.centerOn(120, 120)
    view.set_tool("rectangle")
    before = tab.dispatcher.snapshot.revision
    drawing_tools.drag(qtbot, view, Point(x=42, y=58), Point(x=122, y=138))
    a = tab.dispatcher.snapshot.project.document.nodes[tab.selection[0]]
    assert (a.x, a.y, a.width, a.height) == pytest.approx((40, 60, 80, 80))
    assert tab.dispatcher.snapshot.revision == before + 1
    parent = add(window, tab, "frame", x=200, y=50, width=300, height=300, rotation=25)
    view.set_tool("line")
    view.centerOn(300, 200)
    drawing_tools.drag(qtbot, view, Point(x=282, y=138), Point(x=362, y=218))
    doc = tab.dispatcher.snapshot.project.document
    line = doc.nodes[tab.selection[0]]
    assert line.parent_id == parent.id
    from ltechdesign.domain.models import LineData

    assert isinstance(line.data, LineData)
    world = world_matrix(doc, line.id)
    p, q = world.point(line.data.start), world.point(line.data.end)
    assert (p.x, p.y, q.x, q.y) == pytest.approx((280, 140, 360, 220))


@pytest.mark.parametrize("mode", ["corner", "side", "uniform", "group", "multi"])
def test_resize_snap_preserves_anchor_and_uniform_constraints(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    mode: str,
) -> None:
    window, tab, view = editor
    window.resize(1500, 900)
    parent = None
    if mode in ("corner", "side", "uniform"):
        parent = add(
            window, tab, "frame", x=50, y=50, width=500, height=400, rotation=-11, scale=1.2
        ).id
    a = add(
        window, tab, "rectangle", parent_id=parent, x=50, y=60, width=100, height=70, rotation=23
    )
    keys: tuple[NodeId, ...] = (a.id,)
    if mode in ("multi", "group"):
        a = replace(a, rotation=0)
        assert window.execute(tab, (Update(node=a),))
        b = add(window, tab, "rectangle", x=170, y=90, width=70, height=50)
        keys = (a.id, b.id)
        if mode == "group":
            assert window.execute(tab, (Group(node_ids=keys, group_id=NodeId("g")),))
            keys = (NodeId("g"),)
    configure(window)
    view.set_selection(keys)
    original = view.transforms.geometry()
    assert original is not None
    basis, rect, _ = original
    side = mode == "side"
    anchor = basis.point(Point(x=rect.left(), y=rect.center().y() if side else rect.top()))
    handle = view.transforms.handles()["e" if side else "se"]
    end = QPointF(anchor.x, anchor.y) + (handle - QPointF(anchor.x, anchor.y)) * 1.4
    target = add(
        window,
        tab,
        "rectangle",
        x=end.x() + 3 / view.devicePixelRatioF(),
        y=end.y() + 150,
        width=30,
        height=30,
    )
    view.set_selection(keys)
    view.centerOn((handle.x() + end.x()) / 2, (handle.y() + end.y()) / 2)
    before = tab.dispatcher.snapshot.project
    modifier = (
        Qt.KeyboardModifier.ShiftModifier if mode == "uniform" else Qt.KeyboardModifier.NoModifier
    )
    point = move_preview(view, handle, end, modifier)
    active = view.transforms.active
    assert active is not None and active.mode == "resize"
    assert any(g.axis == "x" and g.coordinate == pytest.approx(target.x) for g in view.aids.guides)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=point, stateKey=modifier)
    after_handle = view.transforms.handles()["e" if side else "se"]
    assert after_handle.x() == pytest.approx(target.x, abs=1e-8)
    current = view.transforms.geometry()
    assert current is not None
    matrix, box, _ = current
    new_anchor = matrix.point(Point(x=box.left(), y=box.center().y() if side else box.top()))
    assert (new_anchor.x, new_anchor.y) == pytest.approx((anchor.x, anchor.y))
    if mode in ("uniform", "group", "multi"):
        # Multi uses world AABB, group uses scale-inclusive world projection.
        original_ratio = (basis.similarity_scale() * rect.width()) / (
            basis.similarity_scale() * rect.height()
        )
        assert box.width() / box.height() == pytest.approx(original_ratio)
    if side:
        assert tab.dispatcher.snapshot.project.document.nodes[a.id].height == 70
    window.history("undo")
    assert tab.dispatcher.snapshot.project == before


@pytest.mark.parametrize(
    "mode", ["left", "hcenter", "right", "top", "vcenter", "bottom", "distribute_x", "distribute_y"]
)
def test_inspector_alignment_buttons_sync_canvas_and_undo(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    mode: ArrangeMode,
) -> None:
    window, tab, view = editor
    parent = add(window, tab, "frame", x=60, y=30, width=400, height=350, rotation=29)
    nodes = [
        add(window, tab, "rectangle", parent_id=parent.id, x=x, y=y, width=w, height=h, rotation=r)
        for x, y, w, h, r in ((20, 30, 50, 40, -17), (140, 150, 70, 30, 14), (270, 210, 60, 80, 0))
    ]
    view.set_selection(tuple(n.id for n in nodes))
    before, depth = tab.dispatcher.snapshot.project, len(tab.dispatcher.undo_history)
    QTest.mouseClick(window.inspector.arrangement.buttons[mode], Qt.MouseButton.LeftButton)
    doc = tab.dispatcher.snapshot.project.document
    assert doc != before.document and len(tab.dispatcher.undo_history) == depth + 1
    assert doc.nodes[parent.id].children == before.document.nodes[parent.id].children
    if mode.startswith("distribute"):
        bounds = sorted(
            [geometry(doc, n.id) for n in nodes],
            key=lambda b: b.min_x if mode == "distribute_x" else b.min_y,
        )
        first = (
            bounds[1].min_x - bounds[0].max_x
            if mode == "distribute_x"
            else bounds[1].min_y - bounds[0].max_y
        )
        second = (
            bounds[2].min_x - bounds[1].max_x
            if mode == "distribute_x"
            else bounds[2].min_y - bounds[1].max_y
        )
        assert first == pytest.approx(second)
    view.set_selection((nodes[0].id,))
    assert float(window.inspector.fields["x"].text()) == pytest.approx(doc.nodes[nodes[0].id].x)
    assert not window.inspector.arrangement.buttons["left"].isEnabled()
    window.history("undo")
    assert tab.dispatcher.snapshot.project == before


def test_overlay_toggle_no_history_export_or_native_contamination(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, tab, view = editor
    a = add(
        window,
        tab,
        "rectangle",
        x=40,
        y=60,
        width=70,
        height=60,
        style=Style(fill=Fill(color="#2080C0FF")),
    )
    b = add(
        window,
        tab,
        "rectangle",
        x=190,
        y=140,
        width=60,
        height=70,
        style=Style(fill=Fill(color="#E08030FF")),
    )
    view.set_selection((a.id, b.id))
    control = configure(window, grid=True)
    bounds = QRectF(0, 0, 320, 260)
    doc = tab.dispatcher.snapshot.project.document
    expected = render_image(doc, doc.pages[0].root_ids, bounds)
    snapshot, history = tab.dispatcher.snapshot, tab.dispatcher.undo_history
    for widget in control.checks.values():
        widget.setChecked(not widget.isChecked())
    control.spacing.setValue(25)
    assert tab.dispatcher.snapshot is snapshot and tab.dispatcher.undo_history is history
    assert render_image(doc, doc.pages[0].root_ids, bounds) == expected
    image = QImage(320, 260, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    view.scene().render(painter, bounds, bounds)
    painter.end()
    assert image == expected
    assert image.save(str(tmp_path / "overlay-free-export.png"))
    render_pdf(doc, doc.pages[0].root_ids, bounds, tmp_path / "overlay-free-export.pdf")
    QTest.mouseClick(window.inspector.arrangement.buttons["left"], Qt.MouseButton.LeftButton)
    assert expected != render_image(
        tab.dispatcher.snapshot.project.document, doc.pages[0].root_ids, bounds
    )
    final = tab.dispatcher.snapshot.project.document
    arranged = render_image(final, final.pages[0].root_ids, bounds)
    assert arranged.save(str(tmp_path / "arranged-shared.png"))
    assert render_pdf(final, final.pages[0].root_ids, bounds, tmp_path / "arranged.pdf") == ()
    from PySide6.QtCore import QSize
    from PySide6.QtPdf import QPdfDocument

    pdf = QPdfDocument()
    assert pdf.load(str(tmp_path / "arranged.pdf")) == QPdfDocument.Error.None_
    raster = pdf.render(0, QSize(320, 260))
    assert raster.pixelColor(50, 150).red() == 224  # second object now at aligned x=40
    assert raster.pixelColor(200, 150).alpha() == 0  # previous location is empty
    assert raster.save(str(tmp_path / "arranged-pdf-raster.png"))
    target = tmp_path / "arranged-editable.ltechdesign"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    window.save_document(as_new=True)
    qtbot.waitUntil(lambda: not window.busy)
    window.close_tab(window.tabs.currentIndex())
    qtbot.waitUntil(lambda: not window.busy)
    window.open_path(str(target))
    qtbot.waitUntil(lambda: not window.busy)
    reopened = window.current
    assert reopened and reopened.view and reopened.dispatcher.snapshot.project.document == final
    assert reopened.view.grid_spacing == 20 and not reopened.view.aids.settings.snap


def test_multiselect_snap_preserves_relative_world_pose_excludes_locked_and_stale_revision(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, view = editor
    a = add(window, tab, "rectangle", x=40, y=60, width=50, height=40)
    b = add(window, tab, "rectangle", x=120, y=80, width=50, height=40)
    target = add(window, tab, "rectangle", x=220, y=200, width=60, height=50)
    hidden = add(window, tab, "rectangle", x=216, y=200, visible=False)
    locked = add(window, tab, "rectangle", x=217, y=200, locked=True)
    configure(window)
    view.set_selection((a.id, b.id))
    view.centerOn(150, 120)
    before = tab.dispatcher.snapshot
    p = move_preview(view, QPointF(65, 80), QPointF(112, 80))
    assert {t.key for t in view.aids.index.x}.isdisjoint({a.id, b.id, hidden.id, locked.id})
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=p)
    doc = tab.dispatcher.snapshot.project.document
    assert geometry(doc, b.id).max_x == pytest.approx(target.x)
    assert doc.nodes[b.id].x - doc.nodes[a.id].x == 80
    assert doc.nodes[b.id].y - doc.nodes[a.id].y == 20
    window.history("undo")
    assert tab.dispatcher.snapshot.project == before.project
    p = move_preview(view, QPointF(65, 80), QPointF(112, 80))
    external(tab, SetProperties(node_ids=(target.id,), property="x", value=260))
    revision = tab.dispatcher.snapshot.revision
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=p)
    assert tab.dispatcher.snapshot.revision == revision and not view.aids.guides
    assert tab.dispatcher.snapshot.project.document.nodes[a.id].x == 40


@pytest.mark.parametrize("zoom", [0.1, 0.5, 1, 3])
def test_ruler_ticks_track_pan_zoom_in_logical_pixels(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    zoom: float,
) -> None:
    _, tab, view = editor
    view.set_zoom(zoom)
    view.centerOn(-120, 75)
    snapshot = tab.dispatcher.snapshot
    assert view.aids.top_bar.isVisible() and view.aids.left_bar.isVisible()
    assert not view.aids.top_bar.geometry().intersects(view.viewport().geometry())
    assert not view.aids.left_bar.geometry().intersects(view.viewport().geometry())
    for axis in AXES:
        ticks = view.aids.ticks(axis)
        assert ticks and any(major for _, _, major in ticks)
        for coordinate, position, _ in ticks:
            expected = (
                view.viewportTransform().map(QPointF(coordinate, 0)).x()
                if axis == "x"
                else view.viewportTransform().map(QPointF(0, coordinate)).y()
            )
            assert position == pytest.approx(expected)
    assert tab.dispatcher.snapshot is snapshot


@pytest.mark.parametrize("scale", [1, 1.5, 2])
def test_actual_qt_screen_scale_subprocess(scale: float, tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    environment = {
        k: v
        for k, v in os.environ.items()
        if k not in ("QT_SCALE_FACTOR", "QT_SCREEN_SCALE_FACTORS")
    }
    environment["QT_QPA_PLATFORM"] = "windows" if os.name == "nt" else "offscreen"
    native = subprocess.run(
        [
            sys.executable,
            "-c",
            "from PySide6.QtGui import QGuiApplication; "
            "a=QGuiApplication([]); print(a.primaryScreen().devicePixelRatio())",
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    environment["QT_SCALE_FACTOR"] = str(scale / float(native.stdout.strip()))
    result = subprocess.run(
        [sys.executable, str(root / "scripts/check_canvas_aids.py"), str(tmp_path)],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["dpr"] == pytest.approx(scale)
    assert len(report["zooms"]) == 4
    assert all(z["near_snap"] and not z["far_snap"] and z["one_undo"] for z in report["zooms"])


def test_snap_off_and_explicit_inspector_nudge_remain_exact_logical_values(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, view = editor
    a = add(window, tab, "rectangle", x=40, y=60, width=50, height=40)
    add(window, tab, "rectangle", x=140, y=200, width=60, height=50)
    control = configure(window)
    control.checks["snap"].setChecked(False)
    view.set_selection((a.id,))
    view.centerOn(100, 120)
    start, end = QPointF(65, 80), QPointF(112, 80)
    actual_delta = view.mapToScene(view.mapFromScene(end)) - view.mapToScene(
        view.mapFromScene(start)
    )
    b = move_preview(view, start, end)
    assert not view.aids.guides
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=b)
    assert tab.dispatcher.snapshot.project.document.nodes[a.id].x == pytest.approx(
        40 + actual_delta.x()
    )
    window.history("undo")
    control.checks["snap"].setChecked(True)
    control.checks["grid_snap"].setChecked(True)
    QTest.keyClick(view, Qt.Key.Key_Right)
    assert tab.dispatcher.snapshot.project.document.nodes[a.id].x == 41
    panel = window.inspector
    panel.begin("x")
    panel.fields["x"].setText("43.5")
    panel.finish("x")
    assert tab.dispatcher.snapshot.project.document.nodes[a.id].x == 43.5
    assert panel.fields["x"].text() == "43.5"


def test_toggle_or_ruler_click_cancels_preview_without_creating_manual_guides(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, view = editor
    a = add(window, tab, "rectangle", x=40, y=60, width=50, height=40)
    add(window, tab, "rectangle", x=140, y=200, width=60, height=50)
    control = configure(window)
    view.set_selection((a.id,))
    view.centerOn(100, 120)
    before = tab.dispatcher.snapshot
    b = move_preview(view, QPointF(65, 80), QPointF(112, 80))
    assert view.aids.guides
    control.checks["smart_guides"].setChecked(False)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=b)
    assert tab.dispatcher.snapshot is before and not view.aids.guides
    QTest.mouseClick(view.aids.left_bar, Qt.MouseButton.LeftButton, pos=QPoint(10, 80))
    assert tab.dispatcher.snapshot is before and tab.selection == (a.id,)
    control.checks["smart_guides"].setChecked(True)
    cursor = move_preview(view, QPointF(65, 80), QPointF(112, 80))
    assert view.transforms.active is not None
    window.layers.clearSelection()  # programmatic session update, no focus-out event
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=cursor)
    assert tab.dispatcher.snapshot is before and not view.aids.guides
    assert view.transforms.active is None and not tab.selection


def test_multiselect_across_rotated_parents_snaps_as_one_rigid_selection(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, view = editor
    p = add(window, tab, "frame", x=20, y=30, width=250, height=250, rotation=20)
    q = add(window, tab, "frame", x=400, y=250, width=250, height=250, rotation=-15)
    a = add(window, tab, "rectangle", parent_id=p.id, x=40, y=50, width=60, height=50)
    b = add(window, tab, "rectangle", parent_id=q.id, x=40, y=50, width=60, height=50)
    doc = tab.dispatcher.snapshot.project.document
    union = geometry(doc, a.id).union(geometry(doc, b.id))
    target = add(
        window, tab, "rectangle", x=union.max_x + 50, y=union.max_y + 140, width=40, height=40
    )
    configure(window)
    view.set_selection((a.id, b.id))
    source = tab.dispatcher.snapshot.project
    old_a, old_b = world_matrix(source.document, a.id), world_matrix(source.document, b.id)
    center = old_a.point(a.pivot)
    start = QPointF(center.x, center.y)
    end = start + QPointF(50 - 3 / view.devicePixelRatioF(), 0)
    view.centerOn((start.x() + end.x()) / 2, (start.y() + end.y()) / 2)
    cursor = move_preview(view, start, end)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=cursor)
    final = tab.dispatcher.snapshot.project.document
    assert geometry(final, a.id).union(geometry(final, b.id)).max_x == pytest.approx(target.x)
    new_a, new_b = world_matrix(final, a.id), world_matrix(final, b.id)
    assert (new_a.tx - old_a.tx, new_a.ty - old_a.ty) == pytest.approx(
        (new_b.tx - old_b.tx, new_b.ty - old_b.ty)
    )
    assert (new_a.a, new_a.b, new_b.a, new_b.b) == pytest.approx(
        (old_a.a, old_a.b, old_b.a, old_b.b)
    )
    window.history("undo")
    assert tab.dispatcher.snapshot.project == source
