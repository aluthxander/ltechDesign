from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
import test_drawing_tools as drawing_tools
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog
from pytestqt.qtbot import QtBot

from ltechdesign.domain.geometry import world_matrix
from ltechdesign.domain.models import Fill, Point, Style
from ltechdesign.rendering.drawing import render_image
from ltechdesign.ui.canvas import EditorCanvas
from ltechdesign.ui.window import StudioWindow, Tab

pytestmark = pytest.mark.desktop
editor = drawing_tools.editor
add = drawing_tools.add


@pytest.fixture(autouse=True)
def release_test_clipboard(qapp: QApplication) -> Iterator[None]:
    yield
    qapp.clipboard().clear()


def gesture(
    qtbot: QtBot,
    view: EditorCanvas,
    start: QPointF,
    end: QPointF,
    modifier: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    cancel: bool = False,
) -> None:
    a, b = view.mapFromScene(start), view.mapFromScene(end)
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=a)
    # A real event carrying move modifiers; QTest.mouseMove has no modifier parameter.
    from PySide6.QtGui import QMouseEvent

    event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(b),
        QPointF(b),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        modifier,
    )
    QApplication.sendEvent(view.viewport(), event)
    if cancel:
        QTest.keyClick(view, Qt.Key.Key_Escape)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=b, stateKey=modifier)


def test_nested_drag_resize_rotate_and_cancel(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas]
) -> None:
    window, tab, view = editor
    parent = add(window, tab, "frame", x=50, y=70, rotation=31, scale=1.2, width=400, height=300)
    child = add(
        window,
        tab,
        "rectangle",
        parent_id=parent.id,
        x=50,
        y=70,
        width=100,
        height=60,
        rotation=-17,
    )
    view.set_tool(None)
    view.set_selection((child.id,))
    view.centerOn(250, 220)
    view.set_zoom(1.3)
    before = tab.dispatcher.snapshot
    matrix = world_matrix(before.project.document, child.id)
    center = matrix.point(child.pivot)
    start = QPointF(center.x, center.y)
    end = start + QPointF(30, 20)
    gesture(qtbot, view, start, end, cancel=True)
    assert tab.dispatcher.snapshot is before
    gesture(qtbot, view, start, end)
    after = world_matrix(tab.dispatcher.snapshot.project.document, child.id)
    assert (after.tx - matrix.tx, after.ty - matrix.ty) == pytest.approx((30, 20), abs=1)
    assert len(tab.dispatcher.undo_history) == 3
    window.history("undo")
    assert tab.dispatcher.snapshot.project == before.project
    window.history("redo")
    node = tab.dispatcher.snapshot.project.document.nodes[child.id]
    anchor = world_matrix(tab.dispatcher.snapshot.project.document, node.id).point(Point())
    handle = view.transforms.handles()["se"]
    world = world_matrix(tab.dispatcher.snapshot.project.document, node.id)
    target = world.point(Point(x=200, y=120))
    gesture(qtbot, view, handle, QPointF(target.x, target.y), Qt.KeyboardModifier.ShiftModifier)
    changed = tab.dispatcher.snapshot.project.document.nodes[node.id]
    assert (changed.width, changed.height) == pytest.approx((200, 120), abs=2)
    fixed = world_matrix(tab.dispatcher.snapshot.project.document, node.id).point(Point())
    assert (fixed.x, fixed.y) == pytest.approx((anchor.x, anchor.y), abs=1e-8)
    rotation = view.transforms.handles()["rotate"]
    pivot = world_matrix(tab.dispatcher.snapshot.project.document, node.id).point(changed.pivot)
    vector = rotation - QPointF(pivot.x, pivot.y)
    rotate_target = QPointF(pivot.x - vector.y(), pivot.y + vector.x())
    gesture(qtbot, view, rotation, rotate_target, Qt.KeyboardModifier.ShiftModifier)
    rotated = tab.dispatcher.snapshot.project.document.nodes[node.id]
    assert (rotated.rotation - changed.rotation) % 360 == pytest.approx(90, abs=1)


def test_multiselect_group_scale_delete_and_focus_shortcuts(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas]
) -> None:
    window, tab, view = editor
    a = add(window, tab, "rectangle", x=20, y=30, width=50, height=50)
    b = add(window, tab, "ellipse", x=100, y=30, width=50, height=50)
    view.set_selection((a.id, b.id))
    QTest.keyClick(view, Qt.Key.Key_G, modifier=Qt.KeyboardModifier.ControlModifier)
    group = tab.dispatcher.snapshot.project.document.nodes[tab.selection[0]]
    assert group.type == "group"
    from PySide6.QtGui import QContextMenuEvent

    child = tab.dispatcher.snapshot.project.document.nodes[a.id]
    point = world_matrix(tab.dispatcher.snapshot.project.document, a.id).point(
        Point(x=child.width / 2, y=child.height / 2)
    )
    position = view.mapFromScene(point.x, point.y)
    view.contextMenuEvent(
        QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse, position, view.viewport().mapToGlobal(position)
        )
    )
    assert tab.selection == (group.id,)
    assert window.editing.context is not None
    window.editing.context.close()
    content = tuple(tab.dispatcher.snapshot.project.document.nodes[k] for k in group.children)
    start = view.transforms.handles()["se"]
    top = view.transforms.handles()["nw"]
    gesture(qtbot, view, start, top + (start - top) * 2.0)
    changed = tab.dispatcher.snapshot.project.document.nodes[group.id]
    assert changed.scale == pytest.approx(2, abs=0.05)
    assert (
        tuple(tab.dispatcher.snapshot.project.document.nodes[k] for k in group.children) == content
    )
    before = tab.dispatcher.snapshot
    QTest.keyClick(view, Qt.Key.Key_Right)
    QTest.keyClick(view, Qt.Key.Key_Down, modifier=Qt.KeyboardModifier.ShiftModifier)
    moved = tab.dispatcher.snapshot.project.document.nodes[group.id]
    assert (moved.x - changed.x, moved.y - changed.y) == pytest.approx((1, 10))
    window.object_name.setFocus()
    window.object_name.setText("Editing")
    revision = tab.dispatcher.snapshot.revision
    QTest.keyClick(window.object_name, Qt.Key.Key_Left)
    QTest.keyClick(window.object_name, Qt.Key.Key_Delete)
    QTest.keyClick(window.object_name, Qt.Key.Key_A, modifier=Qt.KeyboardModifier.ControlModifier)
    QTest.keyClick(window.object_name, Qt.Key.Key_Z, modifier=Qt.KeyboardModifier.ControlModifier)
    assert tab.dispatcher.snapshot.revision == revision
    view.setFocus()
    window.editing.perform("delete")
    assert not tab.dispatcher.snapshot.project.document.nodes
    window.history("undo")
    assert group.id in tab.dispatcher.snapshot.project.document.nodes
    assert tab.dispatcher.snapshot.revision > before.revision


def test_clipboard_between_documents_cut_duplicate_redo_and_context(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ltechdesign.domain import create_project

    window, source, view = editor
    a = add(window, source, "rectangle", x=20, y=30)
    view.set_selection((a.id,))
    window.editing.perform("copy")
    qtbot.waitUntil(lambda: not window.busy)
    window.admit(window.prepare_admission(window.service.new(create_project("Paste target"), {})))
    target = window.current
    assert target and target.view
    window.editing.perform("paste")
    qtbot.waitUntil(lambda: not window.busy)
    pasted = target.dispatcher.snapshot.project.document.nodes[target.selection[0]]
    assert pasted.id != a.id and (pasted.x, pasted.y) == (30, 40)
    assert len(target.dispatcher.undo_history) == 1
    window.editing.perform("duplicate")
    assert len(target.dispatcher.snapshot.project.document.nodes) == 2
    window.history("undo")
    target.view.set_selection((pasted.id,))
    window.editing.perform("nudge_right_1")
    assert not target.dispatcher.redo_history
    menu = window.editing.menu(target)
    actions = {action.objectName(): action for action in menu.actions()}
    assert actions["group"].isEnabled() and actions["copy"].isEnabled()
    menu.deleteLater()
    window.editing.perform("cut")
    qtbot.waitUntil(lambda: not window.busy)
    assert not target.dispatcher.snapshot.project.document.nodes
    window.editing.perform("paste")
    qtbot.waitUntil(lambda: not window.busy)
    assert len(target.dispatcher.snapshot.project.document.nodes) == 1
    file = tmp_path / "edited.ltechdesign"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(file), ""))
    window.save_document()
    qtbot.waitUntil(lambda: not window.busy)
    expected = target.dispatcher.snapshot.project.document
    window.reload_document()
    qtbot.waitUntil(lambda: not window.busy)
    assert window.current and window.current.dispatcher.snapshot.project.document == expected


def test_at24_actual_pixels_hierarchy_undo_and_handles_visual(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, view = editor
    p = add(window, tab, "frame", x=80, y=80, width=250, height=200, rotation=27, scale=1.2)
    q = add(window, tab, "frame", x=450, y=60, width=200, height=250, rotation=-31, scale=0.8)
    a = add(
        window,
        tab,
        "rectangle",
        parent_id=p.id,
        x=20,
        y=40,
        width=80,
        height=50,
        rotation=14,
        style=Style(fill=Fill(color="#2288CCFF")),
    )
    b = add(
        window,
        tab,
        "ellipse",
        parent_id=p.id,
        x=140,
        y=50,
        width=60,
        height=90,
        style=Style(fill=Fill(color="#E88A22FF")),
    )
    before = tab.dispatcher.snapshot.project
    bounds = QRectF(0, 0, 800, 450)
    expected = render_image(before.document, before.document.pages[0].root_ids, bounds)
    view.set_selection((a.id, b.id))
    window.editing.perform("group")
    group = tab.selection
    window.editing.reparent(tab, group, q.id)
    window.editing.perform("ungroup")
    doc = tab.dispatcher.snapshot.project.document
    actual = render_image(doc, doc.pages[0].root_ids, bounds)
    errors = [
        abs(a - b)
        for a, b in zip(bytes(expected.constBits()), bytes(actual.constBits()), strict=True)
    ]
    assert max(errors) <= 1  # AA only; geometry and semantic hierarchy are also asserted.
    assert doc.nodes[a.id].parent_id == q.id and doc.nodes[b.id].parent_id == q.id
    for _ in range(3):
        window.history("undo")
    assert tab.dispatcher.snapshot.project == before
    view.set_selection((a.id,))
    view.fit_bounds(bounds)
    output = Path("artifacts/editing08")
    output.mkdir(parents=True, exist_ok=True)
    expected.save(str(output / "at24-before.png"))
    actual.save(str(output / "at24-after.png"))
    from PySide6.QtGui import QGuiApplication

    qtbot.wait(30)
    assert window.grab().save(str(output / f"handles-{QGuiApplication.platformName()}.png"))
    menu = window.editing.menu(tab)
    menu.popup(window.mapToGlobal(window.rect().center()))
    qtbot.wait(30)
    assert menu.grab().save(str(output / f"context-{QGuiApplication.platformName()}.png"))
    menu.close()
    menu.deleteLater()


def test_alt_resize_and_multiselect_move_across_parents(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, view = editor
    p = add(window, tab, "frame", rotation=25, x=40, y=20, width=250, height=220)
    a = add(window, tab, "rectangle", parent_id=p.id, x=60, y=50, width=60, height=40)
    b = add(window, tab, "rectangle", x=340, y=100, width=60, height=60)
    view.set_zoom(0.8)
    view.centerOn(250, 150)
    view.set_selection((a.id,))
    old = world_matrix(tab.dispatcher.snapshot.project.document, a.id).point(
        Point(x=a.width / 2, y=a.height / 2)
    )
    handle = view.transforms.handles()["e"]
    axis = world_matrix(tab.dispatcher.snapshot.project.document, a.id)
    delta = QPointF(axis.a * 30, axis.b * 30)
    gesture(qtbot, view, handle, handle + delta, Qt.KeyboardModifier.AltModifier)
    changed = tab.dispatcher.snapshot.project.document.nodes[a.id]
    current = world_matrix(tab.dispatcher.snapshot.project.document, a.id).point(changed.pivot)
    assert (current.x, current.y) == pytest.approx((old.x, old.y))
    assert changed.width == pytest.approx(120, abs=2) and changed.height == 40
    view.set_selection((a.id, b.id))
    before = {k: world_matrix(tab.dispatcher.snapshot.project.document, k) for k in (a.id, b.id)}
    start = before[b.id].point(b.pivot)
    gesture(qtbot, view, QPointF(start.x, start.y), QPointF(start.x + 20, start.y + 30))
    for key, matrix in before.items():
        actual = world_matrix(tab.dispatcher.snapshot.project.document, key)
        assert (actual.tx - matrix.tx, actual.ty - matrix.ty) == pytest.approx((20, 30), abs=2)


def test_gui_asset_clipboard_survives_source_close_and_undo_gc(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ltechdesign.domain import create_project

    window, _, _ = editor
    window.open_path(str(Path("examples/proyek-contoh.ltechdesign").resolve()))
    qtbot.waitUntil(lambda: not window.busy)
    source = window.current
    assert source and source.view
    source.view.set_selection(source.dispatcher.snapshot.project.document.pages[0].root_ids)
    window.editing.perform("copy")
    qtbot.waitUntil(lambda: not window.busy)
    window.close_tab(window.tabs.currentIndex())
    qtbot.waitUntil(lambda: not window.busy)
    window.admit(window.prepare_admission(window.service.new(create_project("Asset paste"), {})))
    target = window.current
    assert target and target.view
    window.editing.perform("paste")
    qtbot.waitUntil(lambda: not window.busy)
    assert target.dispatcher.snapshot.project.assets.assets
    project = target.dispatcher.snapshot.project
    with target.store.pin(project.assets.assets) as lease:
        blobs = dict(lease.blobs)
    window.history("undo")
    target.store.collect()
    window.history("redo")
    with target.store.pin(target.dispatcher.snapshot.project.assets.assets) as lease:
        assert dict(lease.blobs) == blobs
    destination = tmp_path / "assets.ltechdesign"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(destination), ""))
    window.save_document()
    qtbot.waitUntil(lambda: not window.busy)
    window.reload_document()
    qtbot.waitUntil(lambda: not window.busy)
    assert (
        window.current and window.current.dispatcher.snapshot.project.document == project.document
    )


def test_stale_transform_and_invalid_clipboard_leave_history_unchanged(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from PySide6.QtCore import QMimeData

    from ltechdesign.commands import Update
    from ltechdesign.persistence.clipboard import MIME

    window, tab, view = editor
    node = add(window, tab, "rectangle", x=20, y=20, width=100, height=100)
    view.set_selection((node.id,))
    center = view.mapFromScene(70, 70)
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=center)
    QTest.mouseMove(view.viewport(), pos=view.mapFromScene(90, 90))
    assert view.transforms.active
    assert window.execute(tab, (Update(node=replace(node, name="Concurrent")),))
    before = tab.dispatcher.snapshot
    history = tab.dispatcher.undo_history
    assert view.transforms.active is None
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=center)
    errors: list[Exception] = []
    monkeypatch.setattr(window, "show_error", errors.append)
    mime = QMimeData()
    mime.setData(MIME, b"corrupt archive")
    QApplication.clipboard().setMimeData(mime)
    window.editing.perform("paste")
    qtbot.waitUntil(lambda: not window.busy)
    assert errors and tab.dispatcher.snapshot is before and tab.dispatcher.undo_history == history
