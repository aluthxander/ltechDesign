from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
import test_drawing_tools as drawing_tools
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QGuiApplication
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QLineEdit, QMessageBox
from pytestqt.qtbot import QtBot

from ltechdesign.commands import (
    Create,
    CreatePage,
    DeletePage,
    Request,
    SetLayerState,
    Update,
    UpdatePage,
)
from ltechdesign.commands.contracts import Operation
from ltechdesign.domain import create_node, create_project
from ltechdesign.domain.geometry import world_matrix
from ltechdesign.domain.models import Fill, NodeId, Page, Style
from ltechdesign.rendering.drawing import render_image
from ltechdesign.rendering.hit_testing import hit_test
from ltechdesign.ui.canvas import EditorCanvas
from ltechdesign.ui.hierarchy import HierarchyPanel
from ltechdesign.ui.window import StudioWindow, Tab

pytestmark = pytest.mark.desktop
editor = drawing_tools.editor
add = drawing_tools.add


def external(tab: Tab, *operations: Operation) -> None:
    snapshot = tab.dispatcher.snapshot
    result = tab.dispatcher.dispatch(
        Request(
            session_id=snapshot.session_id,
            expected_revision=snapshot.revision,
            request_id=str(uuid4()),
            action_name="External panel test",
            source="AI",
            operations=operations,
        ),
        client_id="external-local-control",
    )
    assert result.ok, result.error


def test_pages_crud_stable_identity_external_changes_and_session_selection(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, tab, view = editor
    panel = window.hierarchy
    original = tab.dispatcher.snapshot.project.document.pages[0]
    shape = add(window, tab, "rectangle", name="Original")
    view.set_selection((shape.id,))
    prefix = Page(name="Inserted first")
    external(tab, CreatePage(page=prefix, index=0))
    assert (
        tab.active_page_id == original.id and tab.active_page == 1 and tab.selection == (shape.id,)
    )
    assert window.pages.count() == 2 and window.pages.currentRow() == 1
    revision = tab.dispatcher.snapshot.revision
    window.pages.setCurrentRow(0)
    assert not tab.selection and not view.selection and tab.dispatcher.snapshot.revision == revision
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Landing", True))
    QTest.mouseClick(panel.page_buttons["create"], Qt.MouseButton.LeftButton)
    new_id = tab.active_page_id
    assert new_id not in (original.id, prefix.id)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Renamed", True))
    panel.page_action("rename")
    assert window.pages.currentItem().text() == "Renamed"
    panel.page_action("duplicate")
    assert tab.active_page_id != new_id
    assert window.pages.currentItem().text() == "Renamed copy"
    panel.page_action("delete")
    assert window.pages.count() == 3
    window.history("undo")
    assert window.pages.count() == 4
    # A command outside the panel can delete the active page; fallback is deterministic.
    current = tab.active_page_id
    assert current is not None
    external(tab, DeletePage(page_id=current, delete_contents=True))
    assert tab.active_page_id != current and not tab.selection
    external(tab, UpdatePage(page_id=original.id, name="Changed elsewhere"))
    assert any(
        window.pages.item(i).text() == "Changed elsewhere" for i in range(window.pages.count())
    )


def test_tree_canvas_selection_search_artboards_and_external_mutations(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, view = editor
    panel = window.hierarchy
    board = add(window, tab, "artboard", name="Portrait", width=1080, height=1350)
    parent = add(window, tab, "frame", name="Container", parent_id=board.id)
    a = add(window, tab, "rectangle", name="Needle <b>card</b>", parent_id=parent.id)
    b = add(window, tab, "ellipse", name="Avatar", parent_id=board.id, x=150)
    spy = QSignalSpy(view.selection_changed)
    assert "&lt;b&gt;card&lt;/b&gt;" in panel.items[a.id].toolTip(0)
    before = tab.dispatcher.snapshot
    view.set_selection((a.id,))
    assert [i.data(0, Qt.ItemDataRole.UserRole) for i in window.layers.selectedItems()] == [a.id]
    assert spy.count() == 1
    window.layers.clearSelection()
    panel.items[b.id].setSelected(True)
    assert tab.selection == view.selection == (b.id,)
    assert spy.count() == 1  # tree->canvas is a guarded projection, not a second signal cycle.
    panel.search.setText("nEeDlE")
    assert not panel.items[a.id].isHidden() and not panel.items[parent.id].isHidden()
    assert panel.items[b.id].isHidden()
    panel.search.clear()
    panel.types.setCurrentText("ellipse")
    assert panel.items[a.id].isHidden() and not panel.items[b.id].isHidden()
    view.set_selection((a.id,))
    assert panel.types.currentIndex() == 0 and not panel.items[a.id].isHidden()
    assert tab.dispatcher.snapshot is before
    panel.artboards.setCurrentRow(0)
    assert (
        tab.selection == (board.id,)
        and panel.artboards.currentItem().data(Qt.ItemDataRole.UserRole) == board.id
    )
    panel.items[parent.id].setExpanded(False)
    external(tab, Update(node=replace(a, name="From command")))
    assert panel.items[a.id].text(0) == "From command" and not panel.items[parent.id].isExpanded()
    child = replace(
        create_node("rectangle", board.page_id), parent_id=parent.id, name="External new"
    )
    external(tab, Create(node=child))
    assert panel.items[child.id].parent() is panel.items[parent.id]
    assert len(window.layers.selectedItems()) == 1


def test_visibility_lock_checkbox_undo_and_search_are_not_canvas_content_shortcuts(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, view = editor
    panel = window.hierarchy
    parent = add(window, tab, "frame", name="Parent")
    child = add(
        window,
        tab,
        "rectangle",
        name="Child",
        parent_id=parent.id,
        style=Style(fill=Fill(color="#E03020FF")),
    )
    view.set_selection((child.id,))
    revision = tab.dispatcher.snapshot.revision
    panel.items[child.id].setCheckState(2, Qt.CheckState.Unchecked)
    qtbot.waitUntil(lambda: tab.dispatcher.snapshot.revision == revision + 1)
    assert not tab.dispatcher.snapshot.project.document.nodes[child.id].visible
    assert not tab.selection and not view.selection
    assert not panel.items[child.id].flags() & Qt.ItemFlag.ItemIsSelectable
    doc = tab.dispatcher.snapshot.project.document
    image = render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 100, 100))
    assert image.pixelColor(20, 20).alpha() == 0
    window.history("undo")
    restored = tab.dispatcher.snapshot.project.document
    assert (
        render_image(restored, restored.pages[0].root_ids, QRectF(0, 0, 100, 100))
        .pixelColor(20, 20)
        .alpha()
        == 255
    )
    assert panel.items[child.id].checkState(2) == Qt.CheckState.Checked
    external(tab, SetLayerState(node_ids=(parent.id,), locked=True))
    assert not panel.items[child.id].flags() & Qt.ItemFlag.ItemIsDragEnabled
    assert hit_test(tab.dispatcher.snapshot.project.document, 0, QPointF(20, 20), 1) is None
    revision = tab.dispatcher.snapshot.revision
    panel.items[parent.id].setCheckState(3, Qt.CheckState.Unchecked)
    qtbot.waitUntil(lambda: tab.dispatcher.snapshot.revision == revision + 1)
    assert panel.items[child.id].flags() & Qt.ItemFlag.ItemIsSelectable
    panel.search.setFocus()
    QTest.keyClicks(panel.search, "Child")
    QTest.keyClick(panel.search, Qt.Key.Key_Delete)
    QTest.keyClick(panel.search, Qt.Key.Key_Z, modifier=Qt.KeyboardModifier.ControlModifier)
    assert tab.dispatcher.snapshot.revision == revision + 1


def test_inline_name_editor_shortcuts_and_deferred_commit(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, _ = editor
    node = add(window, tab, "rectangle", name="Card")
    panel = window.hierarchy
    window.layers.editItem(panel.items[node.id], 0)
    qtbot.waitUntil(lambda: any(w.isVisible() for w in window.layers.findChildren(QLineEdit)))
    field = next(w for w in window.layers.findChildren(QLineEdit) if w.isVisible())
    before = tab.dispatcher.snapshot
    QTest.keyClick(field, Qt.Key.Key_A, modifier=Qt.KeyboardModifier.ControlModifier)
    QTest.keyClicks(field, "New card")
    QTest.keyClick(field, Qt.Key.Key_D, modifier=Qt.KeyboardModifier.ControlModifier)
    QTest.keyClick(field, Qt.Key.Key_Left)
    assert tab.dispatcher.snapshot is before
    QTest.keyClick(field, Qt.Key.Key_Return)
    qtbot.waitUntil(lambda: tab.dispatcher.snapshot.revision == before.revision + 1)
    assert tab.dispatcher.snapshot.project.document.nodes[node.id].name == "New card"
    assert panel.items[node.id].text(0) == "New card"
    window.history("undo")
    assert panel.items[node.id].text(0) == "Card"


def native_drop(
    panel: HierarchyPanel, source: tuple[NodeId, ...], target: NodeId, where: str
) -> bool:
    tree = panel.layers
    tree.scrollToItem(panel.items[target])
    QApplication.processEvents()
    rect = tree.visualItemRect(panel.items[target])
    y = (
        rect.top() + 1
        if where == "above"
        else rect.bottom() - 1
        if where == "below"
        else rect.center().y()
    )
    pos = QPoint(rect.left() + 30, y)
    mime = tree.create_mime(source)
    enter = QDragEnterEvent(
        pos,
        Qt.DropAction.MoveAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(tree.viewport(), enter)
    move = QDragMoveEvent(
        pos,
        Qt.DropAction.MoveAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(tree.viewport(), move)
    drop = QDropEvent(
        QPointF(pos),
        Qt.DropAction.MoveAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(tree.viewport(), drop)
    return drop.isAccepted()


def test_actual_qt_drop_nested_reparent_reorder_zorder_and_undo(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, view = editor
    panel = window.hierarchy
    p = add(window, tab, "frame", name="Source", rotation=17, width=100, height=100)
    q = add(window, tab, "frame", name="Target", x=180, rotation=-27, width=100, height=100)
    a = add(
        window,
        tab,
        "rectangle",
        parent_id=p.id,
        name="Red",
        width=80,
        height=80,
        style=Style(fill=Fill(color="#FF0000FF")),
    )
    add(
        window,
        tab,
        "rectangle",
        parent_id=q.id,
        name="Blue",
        width=80,
        height=80,
        style=Style(fill=Fill(color="#0000FFFF")),
    )
    old = world_matrix(tab.dispatcher.snapshot.project.document, a.id)
    before = tab.dispatcher.snapshot.project
    assert native_drop(panel, (a.id,), q.id, "inside")
    doc = tab.dispatcher.snapshot.project.document
    actual = world_matrix(doc, a.id)
    assert (actual.a, actual.b, actual.c, actual.d, actual.tx, actual.ty) == pytest.approx(
        (old.a, old.b, old.c, old.d, old.tx, old.ty)
    )
    assert panel.items[a.id].parent() is panel.items[q.id]
    window.history("undo")
    assert tab.dispatcher.snapshot.project == before

    assert native_drop(panel, (p.id,), q.id, "above")
    assert tab.dispatcher.snapshot.project.document.pages[0].root_ids == (q.id, p.id)
    top = window.layers.topLevelItem(0)
    assert top is not None and top.data(0, Qt.ItemDataRole.UserRole) == p.id
    window.history("undo")
    assert tab.dispatcher.snapshot.project == before

    red = add(
        window, tab, "rectangle", name="Foreground red", style=Style(fill=Fill(color="#FF0000FF"))
    )
    blue = add(
        window, tab, "rectangle", name="Foreground blue", style=Style(fill=Fill(color="#0000FFFF"))
    )
    doc = tab.dispatcher.snapshot.project.document
    assert (
        render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 100, 100)).pixelColor(20, 20).blue()
        == 255
    )
    assert native_drop(panel, (red.id,), blue.id, "above")
    doc = tab.dispatcher.snapshot.project.document
    assert (
        render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 100, 100)).pixelColor(20, 20).red()
        == 255
    )
    assert view.adapter.items[red.id].zValue() > view.adapter.items[blue.id].zValue()


def test_stale_drag_cycle_preserve_context_and_readonly_controls(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, tab, _ = editor
    panel = window.hierarchy
    p = add(window, tab, "frame", name="Parent")
    child = add(window, tab, "frame", parent_id=p.id)
    clip = add(window, tab, "frame", clip_content=True)
    errors: list[Exception] = []
    monkeypatch.setattr(window, "show_error", errors.append)
    before = tab.dispatcher.snapshot
    assert not panel.drop_on(window.layers.create_mime((p.id,)), child.id, "inside")
    assert errors and tab.dispatcher.snapshot is before
    stale = window.layers.create_mime((child.id,))
    external(tab, Update(node=replace(child, name="Elsewhere")))
    before = tab.dispatcher.snapshot
    assert not panel.drop_on(stale, p.id, "inside") and tab.dispatcher.snapshot is before
    fresh = window.layers.create_mime((child.id,))
    assert not panel.drop_on(fresh, clip.id, "inside")
    panel.preserve.setChecked(False)
    assert panel.drop_on(fresh, clip.id, "inside")
    assert tab.dispatcher.snapshot.project.document.nodes[child.id].parent_id == clip.id
    tab.handle.read_only = True
    tab.dispatcher.set_read_only(True)
    window.refresh()
    assert not panel.page_buttons["create"].isEnabled()
    assert not panel.items[p.id].flags() & Qt.ItemFlag.ItemIsUserCheckable
    assert not panel.drop_on(window.layers.create_mime((p.id,)), clip.id, "inside")


def test_page_asset_duplication_gui_save_reload_and_visual(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, _, _ = editor
    source = tmp_path / "source.ltechdesign"
    source.write_bytes(Path("examples/proyek-contoh.ltechdesign").read_bytes())
    window.open_path(str(source))
    qtbot.waitUntil(lambda: not window.busy)
    tab = window.current
    assert tab and tab.view
    before = tab.dispatcher.snapshot.project
    window.hierarchy.page_action("duplicate")
    assert tab.dispatcher.snapshot.project.assets == before.assets
    assert tab.active_page == 1 and window.pages.count() == len(before.document.pages) + 1
    assert tab.active_page_id != before.document.pages[0].id
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    snapshot = tab.dispatcher.snapshot
    window.hierarchy.page_action("delete")
    assert tab.dispatcher.snapshot is snapshot
    expected = tab.dispatcher.snapshot.project
    path = tmp_path / "pages.ltechdesign"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(path), ""))
    window.save_document(as_new=True)
    qtbot.waitUntil(lambda: not window.busy)
    window.reload_document()
    qtbot.waitUntil(lambda: not window.busy)
    reopened = window.current
    assert reopened and reopened.view
    assert reopened.dispatcher.snapshot.project.document == expected.document
    assert reopened.dispatcher.snapshot.project.assets == expected.assets
    with reopened.store.pin(expected.assets.assets) as lease:
        assert lease.blobs
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    window.hierarchy.page_action("delete")
    assert window.pages.count() == len(expected.document.pages) - 1
    window.history("undo")
    assert (
        window.current and window.current.dispatcher.snapshot.project.document == expected.document
    )
    output = Path("artifacts/hierarchy09")
    output.mkdir(parents=True, exist_ok=True)
    reopened.view.fit_artboard()
    qtbot.wait(30)
    assert window.grab().save(str(output / f"panel-{QGuiApplication.platformName()}.png"))
    (output / "fixture.ltechdesign").write_bytes(path.read_bytes())


def test_inactive_session_projection_and_filter_state_stay_isolated(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, first, _ = editor
    node = add(window, first, "rectangle", name="Alpha")
    original = first.active_page_id
    window.hierarchy.search.setText("Alpha")
    window.admit(window.prepare_admission(window.service.new(create_project("Other tab"), {})))
    other = window.current
    assert other and other is not first
    assert window.hierarchy.search.text() == ""
    prefix = Page(name="External prefix")
    external(first, CreatePage(page=prefix, index=0), Update(node=replace(node, name="Alpha new")))
    assert window.current is other and window.pages.count() == 1 and not window.hierarchy.items
    window.tabs.setCurrentIndex(0)
    assert first.active_page_id == original and first.active_page == 1
    assert window.hierarchy.search.text() == "Alpha"
    assert window.hierarchy.items[node.id].text(0) == "Alpha new"
    assert window.pages.count() == 2


def test_external_revision_during_inline_rename_cannot_overwrite_new_content(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, _ = editor
    node = add(window, tab, "rectangle", name="Initial")
    window.layers.editItem(window.hierarchy.items[node.id], 0)
    qtbot.waitUntil(lambda: any(w.isVisible() for w in window.layers.findChildren(QLineEdit)))
    field = next(w for w in window.layers.findChildren(QLineEdit) if w.isVisible())
    QTest.keyClick(field, Qt.Key.Key_A, modifier=Qt.KeyboardModifier.ControlModifier)
    QTest.keyClicks(field, "Uncommitted")
    external(tab, Update(node=replace(node, name="External value")))
    revision = tab.dispatcher.snapshot.revision
    qtbot.wait(30)
    assert tab.dispatcher.snapshot.project.document.nodes[node.id].name == "External value"
    assert tab.dispatcher.snapshot.revision == revision
    assert window.hierarchy.items[node.id].text(0) == "External value"


def test_layer_context_duplicate_and_collapse_state_survive_external_commands(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, _ = editor
    panel = window.hierarchy
    parent = add(window, tab, "frame", name="Parent")
    child = add(window, tab, "rectangle", parent_id=parent.id, name="Card")
    item = panel.items[child.id]
    window.layers.scrollToItem(item)
    QApplication.processEvents()
    panel.layer_context(window.layers.visualItemRect(item).center())
    menu = panel.context
    assert menu is not None
    action = next(a for a in menu.actions() if a.text() == "Duplicate")
    before = tab.dispatcher.snapshot
    action.trigger()
    doc = tab.dispatcher.snapshot.project.document
    added = doc.nodes.keys() - before.project.document.nodes.keys()
    assert len(added) == 1 and doc.nodes[next(iter(added))].data == child.data
    assert tab.dispatcher.snapshot.revision == before.revision + 1
    window.history("undo")
    assert tab.dispatcher.snapshot.project == before.project
    panel.items[parent.id].setExpanded(False)
    current_parent = tab.dispatcher.snapshot.project.document.nodes[parent.id]
    external(tab, Update(node=replace(current_parent, name="New parent name")))
    assert not panel.items[parent.id].isExpanded()
