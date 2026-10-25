from dataclasses import replace
from pathlib import Path

import pytest
import test_drawing_tools as drawing_tools
from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QColorDialog, QDialog, QFileDialog
from pytestqt.qtbot import QtBot
from test_hierarchy_panel import external

from ltechdesign.commands import Group, SetProperties, Update
from ltechdesign.domain.geometry import local_matrix, world_matrix
from ltechdesign.domain.models import Fill, NodeId, Point, Style
from ltechdesign.rendering.drawing import render_image
from ltechdesign.ui.canvas import EditorCanvas
from ltechdesign.ui.inspector import InspectorPanel
from ltechdesign.ui.window import StudioWindow, Tab

pytestmark = pytest.mark.desktop
editor = drawing_tools.editor
add = drawing_tools.add


def enter(panel: InspectorPanel, key: str, text: str) -> None:
    panel.begin(key)
    panel.fields[key].setText(text)
    panel.finish(key)


def test_nested_geometry_inspector_scene_and_undo(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, view = editor
    parent = add(window, tab, "frame", x=80, y=60, rotation=37, scale=1.4)
    shape = add(window, tab, "rectangle", parent_id=parent.id, x=12, y=18, rotation=-21)
    view.set_selection((shape.id,))
    panel = window.inspector
    assert panel.fields["x"].text() == "12" and panel.fields["y"].text() == "18"
    before = tab.dispatcher.snapshot.project
    enter(panel, "x", "53")
    enter(panel, "y", "24")
    pre_resize = tab.dispatcher.snapshot.project.document.nodes[shape.id]
    anchor = local_matrix(pre_resize).point(Point())
    enter(panel, "width", "160")
    changed = tab.dispatcher.snapshot.project.document.nodes[shape.id]
    assert local_matrix(changed).point(Point()).x == pytest.approx(anchor.x)
    assert local_matrix(changed).point(Point()).y == pytest.approx(anchor.y)
    enter(panel, "rotation", "42")
    doc = tab.dispatcher.snapshot.project.document
    actual = view.adapter.items[shape.id].mapToScene(19, 27)
    expected = world_matrix(doc, shape.id).point(Point(x=19, y=27))
    assert actual.x() == pytest.approx(expected.x) and actual.y() == pytest.approx(expected.y)
    for _ in range(4):
        window.history("undo")
    assert tab.dispatcher.snapshot.project == before
    assert panel.fields["x"].text() == "12" and panel.fields["width"].text() == "100"


def test_mixed_values_atomic_style_and_invalid_input(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, view = editor
    a = add(window, tab, "rectangle", x=10, opacity=0.5, style=Style(fill=Fill(color="#FF0000FF")))
    b = add(window, tab, "rectangle", x=120, style=Style(fill=Fill(color="#0000FFFF")))
    view.set_selection((a.id, b.id))
    panel = window.inspector
    for key in ("x", "opacity", "fill"):
        assert panel.fields[key].text() == "" and panel.fields[key].placeholderText() == "Mixed"
    assert not panel.opacity.isEnabled()
    depth = len(tab.dispatcher.undo_history)
    enter(panel, "fill", "#12AB34")
    assert len(tab.dispatcher.undo_history) == depth + 1
    assert panel.fields["fill"].text() == "#12AB34FF"
    doc = tab.dispatcher.snapshot.project.document
    assert doc.nodes[a.id].style.fill == doc.nodes[b.id].style.fill
    image = render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 240, 120))
    assert image.pixelColor(140, 20).green() == 171
    window.history("undo")
    assert panel.fields["fill"].placeholderText() == "Mixed"
    before = tab.dispatcher.snapshot
    for key, text in (
        ("width", "-1"),
        ("opacity", "1.5"),
        ("x", "NaN"),
        ("radius", "oops"),
        ("fill", "#GG0000"),
    ):
        enter(panel, key, text)
        assert tab.dispatcher.snapshot is before and "tidak valid" in panel.feedback.text()
    enter(panel, "opacity", "0.25")
    assert panel.opacity.isEnabled() and panel.opacity.value() == 25


def test_keyboard_and_slider_merge_without_merging_distinct_edits(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, view = editor
    shape = add(window, tab, "rectangle")
    view.set_selection((shape.id,))
    panel = window.inspector
    field = panel.fields["x"]
    panel.ensureWidgetVisible(field)
    field.setFocus()
    depth = len(tab.dispatcher.undo_history)
    for _ in range(4):
        QTest.keyClick(field, Qt.Key.Key_Up)
    assert field.text() == "4" and len(tab.dispatcher.undo_history) == depth + 1
    QTest.keyClick(field, Qt.Key.Key_Return)
    QTest.keyClick(field, Qt.Key.Key_Up)
    assert len(tab.dispatcher.undo_history) == depth + 2
    panel.fields["y"].setFocus()
    window.history("undo")
    assert field.text() == "4"
    window.history("undo")
    assert field.text() == "0"
    panel.opacity.setSliderDown(True)
    for number in (80, 60, 40):
        panel.opacity.setValue(number)
    panel.opacity.setSliderDown(False)
    assert tab.dispatcher.snapshot.project.document.nodes[shape.id].opacity == 0.4
    window.history("undo")
    assert tab.dispatcher.snapshot.project.document.nodes[shape.id].opacity == 1


def test_stale_edit_selection_change_and_color_picker_cancel(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, tab, view = editor
    a, b = add(window, tab, "rectangle"), add(window, tab, "rectangle", x=130)
    view.set_selection((a.id,))
    panel = window.inspector
    panel.begin("x")
    panel.fields["x"].setText("999")
    external(tab, SetProperties(node_ids=(a.id,), property="x", value=75))
    revision = tab.dispatcher.snapshot.revision
    panel.finish("x")
    assert tab.dispatcher.snapshot.revision == revision and panel.fields["x"].text() == "75"
    panel.begin("y")
    panel.fields["y"].setText("999")
    view.set_selection((b.id,))
    panel.finish("y")
    assert tab.dispatcher.snapshot.revision == revision and panel.fields["y"].text() == "0"
    monkeypatch.setattr(QColorDialog, "getColor", lambda *a, **k: QColor())
    panel.pick("fill")
    assert tab.dispatcher.snapshot.revision == revision
    monkeypatch.setattr(QColorDialog, "getColor", lambda *a, **k: QColor(12, 34, 56, 78))
    panel.pick("fill")
    assert panel.fields["fill"].text() == "#0C22384E"

    def change_during_picker(*args: object, **kwargs: object) -> QColor:
        external(tab, SetProperties(node_ids=(b.id,), property="fill", value="#ABCDEF80"))
        return QColor("red")

    monkeypatch.setattr(QColorDialog, "getColor", change_during_picker)
    panel.pick("fill")
    assert panel.fields["fill"].text() == "#ABCDEF80"


def test_group_uniform_resize_and_opacity_undo(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, view = editor
    a = add(window, tab, "rectangle", x=20, y=20, style=Style(fill=Fill(color="#FF0000FF")))
    b = add(window, tab, "rectangle", x=60, y=20, style=Style(fill=Fill(color="#0000FFFF")))
    assert window.execute(tab, (Group(node_ids=(a.id, b.id), group_id=NodeId("group")),))
    view.set_selection((NodeId("group"),))
    panel = window.inspector
    group = tab.dispatcher.snapshot.project.document.nodes[NodeId("group")]
    assert not panel.fields["fill"].isEnabled()
    enter(panel, "width", str(group.width * 2))
    assert float(panel.fields["height"].text()) == group.height * 2
    window.history("undo")
    enter(panel, "opacity", "0.5")
    doc = tab.dispatcher.snapshot.project.document
    image = render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 200, 150))
    assert image.pixelColor(30, 30).alpha() == pytest.approx(128, abs=1)
    assert image.pixelColor(80, 30).alpha() == pytest.approx(128, abs=1)
    assert image.pixelColor(80, 30).blue() == 255
    window.history("undo")
    assert panel.fields["opacity"].text() == "1"


def test_palette_defaults_and_style_native_save_open_evidence(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, tab, view = editor
    panel = window.inspector
    original_revision = tab.dispatcher.snapshot.revision
    monkeypatch.setattr(QColorDialog, "getColor", lambda *a, **k: QColor(40, 130, 210, 255))
    panel.pick_palette("foreground")
    monkeypatch.setattr(QColorDialog, "getColor", lambda *a, **k: QColor(248, 244, 238, 255))
    panel.pick_palette("background")
    assert tab.dispatcher.snapshot.revision == original_revision
    assert view.foreground == "#2882D2FF" and view.background == "#F8F4EEFF"
    view.set_tool("rectangle")
    drawing_tools.drag(qtbot, view, Point(x=50, y=50), Point(x=210, y=170))
    assert len(tab.selection) == 1
    key = tab.selection[0]
    for field, supplied in (
        ("stroke", "#123456"),
        ("stroke_width", "6"),
        ("radius", "20"),
        ("shadow_enabled", "1"),
        ("shadow_x", "12"),
        ("shadow_y", "10"),
        ("shadow_blur", "5"),
        ("shadow_spread", "2"),
        ("opacity", "0.85"),
    ):
        enter(panel, field, supplied)
    window.tool_actions[None].trigger()
    view.fit_bounds(QRectF(10, 10, 260, 210))
    bounds = QRectF(0, 0, 280, 230)
    doc = tab.dispatcher.snapshot.project.document
    image = render_image(doc, doc.pages[0].root_ids, bounds)
    assert image.save(str(tmp_path / "inspector-style.png"))
    qtbot.wait(30)
    assert window.grab().save(str(tmp_path / "inspector-native.png"))
    target = tmp_path / "editable-style.ltechdesign"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    window.save_document(as_new=True)
    qtbot.waitUntil(lambda: not window.busy)
    assert not tab.dispatcher.dirty
    window.close_tab(window.tabs.currentIndex())
    qtbot.waitUntil(lambda: not window.busy)
    window.open_path(str(target))
    qtbot.waitUntil(lambda: not window.busy)
    reopened = window.current
    assert reopened and reopened.view
    reloaded = reopened.dispatcher.snapshot.project.document
    assert reloaded == doc and key in reloaded.nodes
    assert render_image(reloaded, reloaded.pages[0].root_ids, bounds) == image
    reopened.view.set_selection((key,))
    assert panel.fields["stroke_width"].text() == "6" and panel.fields["shadow_blur"].text() == "5"
    # Document read-only status disables content controls; session palette remains available.
    reopened.handle.read_only = True
    window.refresh()
    assert not panel.fields["x"].isEnabled() and panel.foreground_button.isEnabled()
    reopened.handle.read_only = False
    window.refresh()


def test_unequal_corner_radii_are_mixed_until_explicitly_edited(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, view = editor
    a = add(window, tab, "rectangle", style=Style(radius=(1, 2, 3, 4)))
    view.set_selection((a.id,))
    assert window.inspector.fields["radius"].placeholderText() == "Mixed"
    enter(window.inspector, "radius", "1000")
    changed = tab.dispatcher.snapshot.project.document.nodes[a.id]
    assert changed.style.radius == (1000, 1000, 1000, 1000)
    # Authored radius stays editable; drawing clamps all corners to legal geometry.
    from ltechdesign.rendering.drawing import path

    assert path(changed).boundingRect() == QRectF(0, 0, 100, 100)
    assert window.execute(tab, (Update(node=replace(changed, locked=True)),))
    assert not tab.selection and not window.inspector.fields["radius"].isEnabled()


def test_real_alpha_color_dialog_and_palette_frame_artboard_defaults(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, tab, view = editor
    a = add(window, tab, "rectangle", x=20, style=Style(fill=Fill(color="#FF0000FF")))
    b = add(window, tab, "rectangle", x=150, style=Style(fill=Fill(color="#0000FFFF")))
    view.set_selection((a.id, b.id))
    panel = window.inspector
    qtbot.wait(20)
    assert window.grab().save(str(tmp_path / "inspector-mixed-native.png"))
    dialogs: list[QColorDialog] = []

    def accept_picker() -> None:
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QColorDialog) and widget.isVisible():
                dialogs.append(widget)
                assert widget.testOption(QColorDialog.ColorDialogOption.ShowAlphaChannel)
                widget.setCurrentColor(QColor(80, 120, 160, 100))
                assert widget.grab().save(str(tmp_path / "color-picker-native.png"))
                widget.accept()

    QTimer.singleShot(100, accept_picker)
    QTest.mouseClick(panel.pickers["fill"], Qt.MouseButton.LeftButton)
    assert dialogs and panel.fields["fill"].text() == "#5078A064"
    panel.background = "#F0E0D080"
    panel.foreground = "#204060A0"
    panel.sync_palette()
    view.set_selection(())
    view.centerOn(150, 150)
    view.set_tool("frame")
    drawing_tools.drag(qtbot, view, Point(x=40, y=180), Point(x=180, y=250))
    frame = tab.dispatcher.snapshot.project.document.nodes[tab.selection[0]]
    assert frame.type == "frame" and frame.style.fill == Fill(color=panel.foreground)
    from ltechdesign.domain.models import FrameData

    assert isinstance(frame.data, FrameData) and frame.data.background == panel.background
    from ltechdesign.ui.artboard import ArtboardDialog

    monkeypatch.setattr(ArtboardDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    window.create_artboard()
    board = tab.dispatcher.snapshot.project.document.nodes[tab.selection[0]]
    assert board.type == "artboard" and isinstance(board.data, FrameData)
    assert board.data.background == panel.background
