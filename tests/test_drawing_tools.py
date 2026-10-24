from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QFileDialog
from pytestqt.qtbot import QtBot

from ltechdesign.commands import Create, Update
from ltechdesign.domain import create_node, create_project
from ltechdesign.domain.geometry import world_matrix
from ltechdesign.domain.models import FrameData, Node, NodeType, Page, Point, Style
from ltechdesign.rendering.drawing import render_image
from ltechdesign.rendering.hit_testing import hit_test
from ltechdesign.rendering.pdf import render_pdf
from ltechdesign.ui.artboard import ArtboardDialog
from ltechdesign.ui.canvas import EditorCanvas
from ltechdesign.ui.window import StudioWindow, Tab

pytestmark = pytest.mark.desktop


@pytest.fixture
def editor(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[StudioWindow, Tab, EditorCanvas]]:
    window = StudioWindow()

    def fail(error: Exception) -> None:
        raise AssertionError(str(error))

    monkeypatch.setattr(window, "show_error", fail)

    def cleanup(_: object = None) -> None:
        qtbot.waitUntil(lambda: not window.busy)
        for opened in window.documents:
            opened.dispatcher.close()
            window.service.close(opened.handle)
        window.documents.clear()

    qtbot.addWidget(window, before_close_func=cleanup)
    window.admit(window.prepare_admission(window.service.new(create_project("Drawing 07"), {})))
    window.show()
    tab = window.current
    assert tab and tab.view
    view = tab.view
    view.centerOn(250, 200)
    qtbot.wait(30)
    try:
        yield window, tab, view
    finally:
        cleanup()
        window.close()


def drag(qtbot: QtBot, view: EditorCanvas, start: Point, end: Point) -> None:
    a = view.mapFromScene(QPointF(start.x, start.y))
    b = view.mapFromScene(QPointF(end.x, end.y))
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=a)
    QTest.mouseMove(view.viewport(), pos=b)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=b)


def click(qtbot: QtBot, view: EditorCanvas, x: float, y: float, *, shift: bool = False) -> None:
    QTest.mouseClick(
        view.viewport(),
        Qt.MouseButton.LeftButton,
        stateKey=Qt.KeyboardModifier.ShiftModifier if shift else Qt.KeyboardModifier.NoModifier,
        pos=view.mapFromScene(QPointF(x, y)),
    )


def add(window: StudioWindow, tab: Tab, kind: NodeType, **kwargs: object) -> Node:
    node = create_node(kind, tab.dispatcher.snapshot.project.document.pages[0].id)
    node = replace(node, **kwargs)  # type: ignore[arg-type]
    assert window.execute(tab, (Create(node=node),))
    return node


@pytest.mark.parametrize("zoom", [0.5, 1, 2, 4])
@pytest.mark.parametrize("tool", ["frame", "rectangle", "ellipse", "line", "polygon"])
def test_drawing_size_pan_zoom_and_one_undo(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas], zoom: float, tool: NodeType
) -> None:
    window, tab, view = editor
    view.set_zoom(zoom)
    view.centerOn(80, 70)  # Actual scrollbar pan, not an origin at the viewport corner.
    view.set_tool(tool)
    before = tab.dispatcher.snapshot
    drag(qtbot, view, Point(x=20, y=30), Point(x=120, y=90))
    nodes = tab.dispatcher.snapshot.project.document.nodes
    assert len(nodes) == 1
    node = next(iter(nodes.values()))
    assert (node.x, node.y, node.width, node.height) == pytest.approx(
        (20, 30, 100, 60), abs=1 / zoom
    )
    assert tab.selection == (node.id,) and len(tab.dispatcher.undo_history) == 1
    assert tab.dispatcher.snapshot.revision == before.revision + 1
    window.history("undo")
    assert not tab.dispatcher.snapshot.project.document.nodes
    window.history("redo")
    assert tab.dispatcher.snapshot.project.document.nodes[node.id] == node


def test_nested_rotated_parent_coordinates(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas]
) -> None:
    window, tab, view = editor
    art = add(window, tab, "artboard", width=600, height=500)
    outer = add(window, tab, "frame", parent_id=art.id, x=70, y=40, width=300, height=300)
    inner = add(window, tab, "frame", parent_id=outer.id, x=40, y=50, rotation=27, scale=1.4)
    matrix = world_matrix(tab.dispatcher.snapshot.project.document, inner.id)
    view.set_zoom(1.7)
    view.centerOn(210, 210)
    view.set_tool("rectangle")
    drag(qtbot, view, matrix.point(Point(x=10, y=15)), matrix.point(Point(x=60, y=55)))
    node = tab.dispatcher.snapshot.project.document.nodes[tab.selection[0]]
    assert node.parent_id == inner.id
    assert (node.x, node.y, node.width, node.height) == pytest.approx((10, 15, 50, 40), abs=1)
    assert len(tab.dispatcher.undo_history) == 4


def test_preview_escape_rightclick_focus_tool_page_and_revision_cancel(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas]
) -> None:
    window, tab, view = editor
    base = add(window, tab, "rectangle", x=300, y=200)
    view.centerOn(170, 130)
    view.set_tool("ellipse")
    before = tab.dispatcher.snapshot
    history = tab.dispatcher.undo_history
    a, b = view.mapFromScene(10, 10), view.mapFromScene(100, 80)

    def scene_image() -> QImage:
        image = QImage(500, 300, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(0)
        painter = QPainter(image)
        view.scene().render(painter, QRectF(0, 0, 500, 300), QRectF(0, 0, 500, 300))
        painter.end()
        return image

    expected_scene = scene_image()
    for cancel in ("escape", "right", "tool", "focus", "revision", "readonly"):
        view.set_tool("ellipse")
        view.writable = True
        QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=a)
        QTest.mouseMove(view.viewport(), pos=b)
        assert view.preview is not None
        assert len(view.scene().items()) == 1
        assert scene_image() == expected_scene  # Foreground preview never leaks into exports.
        assert tab.dispatcher.snapshot is before and tab.dispatcher.undo_history == history
        if cancel == "escape":
            QTest.keyClick(view, Qt.Key.Key_Escape)
        elif cancel == "right":
            QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, pos=b)
        elif cancel == "tool":
            view.set_tool(None)
        elif cancel == "focus":
            window.object_name.setEnabled(True)
            window.object_name.setFocus()
            qtbot.wait(10)
        elif cancel == "revision":
            assert window.execute(tab, (Update(node=replace(base, name="Concurrent edit")),))
            qtbot.waitUntil(lambda: "dibatalkan" in window.statusBar().currentMessage())
            before = tab.dispatcher.snapshot
            history = tab.dispatcher.undo_history
        else:
            view.sync(0, writable=False)
        QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=b)
        assert view.preview is None and view.gesture is None
        assert len(tab.dispatcher.snapshot.project.document.nodes) == 1
    view.writable = True
    view.set_tool("rectangle")
    click(qtbot, view, 10, 10)  # No area => no create, no history.
    assert tab.dispatcher.snapshot is before


def test_selection_shapes_multiselect_marquee_hidden_locked_clip(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas]
) -> None:
    window, tab, view = editor
    a = add(window, tab, "ellipse", x=30, y=30, width=80, height=80)
    b = add(window, tab, "rectangle", x=150, y=30, width=70, height=70)
    hidden = add(window, tab, "frame", x=260, y=20, visible=False)
    add(window, tab, "rectangle", parent_id=hidden.id)
    locked = add(window, tab, "frame", x=380, y=20, locked=True)
    add(window, tab, "rectangle", parent_id=locked.id)
    clip = add(
        window, tab, "frame", x=30, y=200, clip_content=True, style=Style(radius=(30, 30, 30, 30))
    )
    child = add(window, tab, "rectangle", parent_id=clip.id, x=-20, y=-20)
    view.centerOn(250, 170)
    before, history = tab.dispatcher.snapshot, tab.dispatcher.undo_history
    click(qtbot, view, 70, 70)
    assert tab.selection == (a.id,)
    click(qtbot, view, 180, 60, shift=True)
    assert tab.selection == (a.id, b.id)
    click(qtbot, view, 70, 70, shift=True)
    assert tab.selection == (b.id,)
    QTest.mouseClick(
        view.viewport(),
        Qt.MouseButton.LeftButton,
        stateKey=Qt.KeyboardModifier.ControlModifier,
        pos=view.mapFromScene(70, 70),
    )
    assert tab.selection == (b.id, a.id)
    QTest.mouseClick(
        view.viewport(),
        Qt.MouseButton.LeftButton,
        stateKey=Qt.KeyboardModifier.ControlModifier,
        pos=view.mapFromScene(70, 70),
    )
    assert tab.selection == (b.id,)
    click(qtbot, view, 31, 31)  # Ellipse corner is outside its real path.
    assert not tab.selection
    click(qtbot, view, 280, 40)
    assert not tab.selection
    click(qtbot, view, 400, 40)
    assert not tab.selection
    doc = tab.dispatcher.snapshot.project.document
    assert hit_test(doc, 0, QPointF(31, 201), 1) is None  # Rounded ancestor clip.
    assert hit_test(doc, 0, QPointF(50, 230), 1) == child.id
    drag(qtbot, view, Point(x=20, y=20), Point(x=230, y=120))
    assert set(tab.selection) == {a.id, b.id}
    view.setFocus()
    QTest.keyClick(view, Qt.Key.Key_A, modifier=Qt.KeyboardModifier.ControlModifier)
    assert set(tab.selection) == {a.id, b.id, clip.id, child.id}
    assert tab.dispatcher.snapshot is before and tab.dispatcher.undo_history == history
    assert len(window.layers.selectedItems()) == 4


def test_artboard_dialog_save_open_and_shared_targets(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, tab, view = editor

    def accept(dialog: ArtboardDialog) -> int:
        dialog.preset.setCurrentIndex(6)  # Instagram Portrait.
        return QDialog.DialogCode.Accepted.value

    monkeypatch.setattr(ArtboardDialog, "exec", accept)
    window.create_artboard()
    art = tab.dispatcher.snapshot.project.document.nodes[tab.selection[0]]
    assert (art.width, art.height) == (1080, 1350)
    view.set_tool("rectangle")
    drag(qtbot, view, Point(x=100, y=100), Point(x=400, y=300))
    assert len(tab.dispatcher.snapshot.project.document.nodes) == 2
    view.set_tool("polygon")
    drag(qtbot, view, Point(x=500, y=400), Point(x=800, y=700))
    view.set_tool("frame")
    drag(qtbot, view, Point(x=100, y=800), Point(x=400, y=1100))
    frame_id = tab.selection[0]
    view.set_tool("ellipse")
    drag(qtbot, view, Point(x=150, y=850), Point(x=300, y=1000))
    assert tab.dispatcher.snapshot.project.document.nodes[tab.selection[0]].parent_id == frame_id
    view.set_tool("line")
    drag(qtbot, view, Point(x=600, y=950), Point(x=900, y=950))
    expected = tab.dispatcher.snapshot.project.document
    target = tmp_path / "drawing.ltechdesign"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    window.save_document()
    qtbot.waitUntil(lambda: not window.busy)
    assert target.exists() and not tab.dispatcher.dirty
    window.close_tab(0)
    qtbot.waitUntil(lambda: not window.busy)
    window.open_path(str(target))
    qtbot.waitUntil(lambda: not window.busy)
    reopened = window.current
    assert reopened and reopened.view
    assert reopened.dispatcher.snapshot.project.document == expected
    bounds = QRectF(0, 0, 1080, 1350)
    image = render_image(expected, expected.pages[0].root_ids, bounds)
    assert image.pixelColor(200, 200).name() == "#80b8e8"
    assert render_pdf(expected, expected.pages[0].root_ids, bounds, tmp_path / "drawing.pdf") == ()
    assert (tmp_path / "drawing.pdf").read_bytes().startswith(b"%PDF-")
    output = Path("artifacts/drawing07")
    output.mkdir(parents=True, exist_ok=True)
    image.save(str(output / "shared.png"))
    (output / "fixture.ltechdesign").write_bytes(target.read_bytes())
    (output / "shared.pdf").write_bytes((tmp_path / "drawing.pdf").read_bytes())
    reopened.view.fit_artboard()
    reopened.view.set_tool(None)
    reopened.view.select_all()
    qtbot.wait(50)
    assert window.grab().save(str(output / f"editor-{QGuiApplication.platformName()}.png"))


def test_custom_artboard_dialog_validation_cancel_and_metadata(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from PySide6.QtWidgets import QMessageBox

    window, tab, _ = editor
    before = tab.dispatcher.snapshot
    monkeypatch.setattr(ArtboardDialog, "exec", lambda self: QDialog.DialogCode.Rejected.value)
    window.create_artboard()
    assert tab.dispatcher.snapshot is before and not tab.dispatcher.undo_history
    dialog = ArtboardDialog(window)
    dialog.preset.setCurrentIndex(10)
    assert dialog.width_input.value() == 210 and dialog.unit.currentText() == "mm"
    dialog.width_input.setValue(25.4)
    dialog.height_input.setValue(50.8)
    assert dialog.preset.currentIndex() == 0
    dialog.orientation.setCurrentIndex(2)
    dialog.dpi.setValue(300)
    dialog.background.setText("#12345680")
    node = dialog.node(before.project.document.pages[0].id)
    assert (node.width, node.height) == pytest.approx((600, 300))
    assert node.data == FrameData(unit="mm", dpi=300, background="#12345680")
    warnings: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(str(a[2])))
    dialog.background.setText("invalid")
    dialog.accept()
    assert warnings and dialog.result() != QDialog.DialogCode.Accepted
    dialog.background.setText("#12345680")
    dialog.accept()
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert tab.dispatcher.snapshot is before

    def custom(form: ArtboardDialog) -> int:
        form.width_input.setValue(25.4)
        form.height_input.setValue(50.8)
        form.unit.setCurrentText("mm")
        form.dpi.setValue(300)
        form.orientation.setCurrentIndex(2)
        form.background.setText("#12345680")
        form.show()
        qtbot.wait(30)
        output = Path("artifacts/drawing07")
        output.mkdir(parents=True, exist_ok=True)
        assert form.grab().save(str(output / f"dialog-{QGuiApplication.platformName()}.png"))
        form.hide()
        return QDialog.DialogCode.Accepted.value

    monkeypatch.setattr(ArtboardDialog, "exec", custom)
    window.create_artboard()
    key = tab.selection[0]
    target = tmp_path / "physical.ltechdesign"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    window.save_document()
    qtbot.waitUntil(lambda: not window.busy)
    window.reload_document()
    qtbot.waitUntil(lambda: not window.busy)
    reopened = window.current
    assert reopened is not None
    actual = reopened.dispatcher.snapshot.project.document.nodes[key]
    assert (actual.width, actual.height) == pytest.approx((600, 300))
    assert actual.data == node.data


def test_parent_lock_and_device_pixel_line_hit_tolerance(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas]
) -> None:
    from ltechdesign.domain.models import LineData, Stroke

    window, tab, view = editor
    parent = add(window, tab, "frame", locked=True, x=20, y=20, width=150, height=150)
    view.centerOn(120, 120)
    view.set_tool("rectangle")
    drag(qtbot, view, Point(x=30, y=30), Point(x=80, y=80))
    node = tab.dispatcher.snapshot.project.document.nodes[tab.selection[0]]
    assert node.parent_id is None
    assert not tab.dispatcher.snapshot.project.document.nodes[parent.id].children
    line = add(
        window,
        tab,
        "line",
        x=20,
        y=220,
        width=100,
        height=0,
        pivot=Point(x=50),
        data=LineData(start=Point(), end=Point(x=100)),
        style=Style(stroke=Stroke(width=2)),
    )
    doc = tab.dispatcher.snapshot.project.document
    assert hit_test(doc, 0, QPointF(50, 223), 1, 1) == line.id
    assert hit_test(doc, 0, QPointF(50, 223), 1, 4) is None
    assert hit_test(doc, 0, QPointF(50, 221), 2, 2) == line.id


def test_page_switch_cancels_and_select_all_stays_on_page(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas]
) -> None:
    window, tab, view = editor
    # Pages UI creation belongs to 09; use a valid two-page admission fixture.
    project = create_project("Pages fixture")
    project = replace(project, document=replace(project.document, pages=(Page(), Page())))
    window.admit(window.prepare_admission(window.service.new(project, {})))
    multi = window.current
    assert multi and multi.view
    multi.view.set_tool("rectangle")
    drag(qtbot, multi.view, Point(x=0, y=0), Point(x=100, y=100))
    first = multi.selection
    multi.view.set_tool("ellipse")
    QTest.mousePress(
        multi.view.viewport(), Qt.MouseButton.LeftButton, pos=multi.view.mapFromScene(5, 5)
    )
    QTest.mouseMove(multi.view.viewport(), pos=multi.view.mapFromScene(50, 50))
    assert multi.view.gesture
    window.pages.setCurrentRow(1)
    assert multi.view.gesture is None and not multi.selection
    multi.view.select_all()
    assert not multi.selection
    multi.view.set_tool("line")
    drag(qtbot, multi.view, Point(x=10, y=10), Point(x=70, y=80))
    second = multi.selection
    assert second != first
    window.pages.setCurrentRow(0)
    multi.view.select_all()
    assert multi.selection == first
    multi.view.set_tool("ellipse")
    revision = multi.dispatcher.snapshot.revision
    QTest.mousePress(
        multi.view.viewport(), Qt.MouseButton.LeftButton, pos=multi.view.mapFromScene(5, 5)
    )
    QTest.mouseMove(multi.view.viewport(), pos=multi.view.mapFromScene(50, 50))
    assert multi.view.gesture
    window.tabs.setCurrentIndex(0)
    assert window.current is tab and view.selection == tab.selection
    assert multi.view.gesture is None and multi.dispatcher.snapshot.revision == revision
