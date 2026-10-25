import json
from dataclasses import replace
from pathlib import Path

import pytest
import test_drawing_tools as drawing_tools
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QInputMethodEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog
from pytestqt.qtbot import QtBot

from ltechdesign.commands import SetText, SetTypography
from ltechdesign.domain.models import NodeId, TextData
from ltechdesign.rendering.drawing import render_image
from ltechdesign.rendering.text import layouts
from ltechdesign.ui.canvas import EditorCanvas
from ltechdesign.ui.window import StudioWindow, Tab

pytestmark = pytest.mark.desktop
editor = drawing_tools.editor


def create_text(window: StudioWindow, tab: Tab, view: EditorCanvas, *, box: bool = False) -> NodeId:
    view.centerOn(150, 120)
    window.tool_actions["text"].trigger()
    if box:
        start, end = view.mapFromScene(80, 70), view.mapFromScene(240, 170)
        QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(view.viewport(), pos=end)
        QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=end)
    else:
        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=view.mapFromScene(80, 70))
    assert view.text.active and len(tab.selection) == 1
    return tab.selection[0]


def insert_unicode(view: EditorCanvas, text: str) -> None:
    event = QInputMethodEvent()
    event.setCommitString(text)
    QApplication.sendEvent(view, event)


def test_inline_multiline_clipboard_delete_undo_and_autowidth(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, view = editor
    key = create_text(window, tab, view)
    before = tab.dispatcher.snapshot.project
    QTest.keyClicks(view, "Hello")
    QTest.keyClick(view, Qt.Key.Key_Return)
    QTest.keyClicks(view, "World")
    node = tab.dispatcher.snapshot.project.document.nodes[key]
    assert isinstance(node.data, TextData) and node.data.text == "Hello\nWorld"
    assert node.data.typography.sizing == "auto_width" and node.width > 40
    assert view.text.active
    QTest.keyClick(view, Qt.Key.Key_Z, modifier=Qt.KeyboardModifier.ControlModifier)
    assert tab.dispatcher.snapshot.project == before
    QTest.keyClick(
        view,
        Qt.Key.Key_Z,
        modifier=Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
    )
    assert tab.dispatcher.snapshot.project.document.nodes[key].data == node.data
    QTest.keyClick(view, Qt.Key.Key_A, modifier=Qt.KeyboardModifier.ControlModifier)
    QTest.keyClick(view, Qt.Key.Key_C, modifier=Qt.KeyboardModifier.ControlModifier)
    assert QApplication.clipboard().text() == "Hello\nWorld"
    QTest.keyClick(view, Qt.Key.Key_X, modifier=Qt.KeyboardModifier.ControlModifier)
    assert key in tab.dispatcher.snapshot.project.document.nodes
    assert tab.dispatcher.snapshot.project.document.nodes[key].data.text == ""  # type: ignore[union-attr]
    QTest.keyClick(view, Qt.Key.Key_V, modifier=Qt.KeyboardModifier.ControlModifier)
    assert tab.dispatcher.snapshot.project.document.nodes[key].data == node.data
    QTest.keyClick(view, Qt.Key.Key_A, modifier=Qt.KeyboardModifier.ControlModifier)
    QTest.keyClick(view, Qt.Key.Key_Delete)
    assert key in tab.dispatcher.snapshot.project.document.nodes
    assert tab.dispatcher.snapshot.project.document.nodes[key].data.text == ""  # type: ignore[union-attr]


def test_unicode_typography_wrapping_and_fixed_box_resize(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    window, tab, view = editor
    key = create_text(window, tab, view, box=True)
    insert_unicode(
        view, "Caf\u00e9 e\u0301 — العربية 中文\nSecond paragraph with enough words to wrap"
    )
    node = tab.dispatcher.snapshot.project.document.nodes[key]
    assert isinstance(node.data, TextData) and "العربية" in node.data.text
    QTest.keyClick(view, Qt.Key.Key_Escape)
    assert not view.text.active
    assert window.execute(
        tab, (SetTypography(node_ids=(node.id,), property="sizing", value="auto_height"),)
    )
    node = tab.dispatcher.snapshot.project.document.nodes[key]
    resources = view.adapter.resources
    assert resources
    _, metrics = layouts(node, resources)
    assert len(metrics) >= 3 and node.height >= metrics[-1]["y"] + metrics[-1]["height"]
    before = tab.dispatcher.snapshot.project
    panel = window.inspector
    panel.begin("width")
    panel.fields["width"].setText("80")
    panel.finish("width")
    changed = tab.dispatcher.snapshot.project.document.nodes[key]
    assert changed.width == 80 and changed.height > node.height
    assert isinstance(changed.data, TextData) and changed.data.typography.sizing == "auto_height"
    window.history("undo")
    assert tab.dispatcher.snapshot.project == before


def test_inline_preedit_external_revision_and_editable_save_reopen(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, tab, view = editor
    key = create_text(window, tab, view)
    insert_unicode(view, "Unicode Ω\nMultiline")
    before = tab.dispatcher.snapshot
    canonical = render_image(
        before.project.document,
        before.project.document.pages[0].root_ids,
        QRectF(0, 0, 400, 200),
        resources=view.adapter.resources,
    )
    QApplication.sendEvent(view, QInputMethodEvent("中", []))
    assert tab.dispatcher.snapshot is before and view.adapter.resources.previews  # type: ignore[union-attr]
    assert (
        render_image(
            before.project.document,
            before.project.document.pages[0].root_ids,
            QRectF(0, 0, 400, 200),
            resources=view.adapter.resources,
        )
        == canonical
    )
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtPdf import QPdfDocument

    from ltechdesign.rendering.pdf import render_pdf

    scene = QImage(400, 200, QImage.Format.Format_ARGB32_Premultiplied)
    scene.fill(0)
    painter = QPainter(scene)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    view.scene().render(painter, QRectF(0, 0, 400, 200), QRectF(0, 0, 400, 200))
    painter.end()
    assert scene == canonical
    pdf_images = []
    for name, resources in (
        ("canonical", view.text.base_resources),
        ("preedit", view.adapter.resources),
    ):
        target_pdf = tmp_path / f"{name}.pdf"
        render_pdf(
            before.project.document,
            before.project.document.pages[0].root_ids,
            QRectF(0, 0, 400, 200),
            target_pdf,
            resources=resources,
        )
        pdf = QPdfDocument()
        assert pdf.load(str(target_pdf)) == QPdfDocument.Error.None_
        pdf_images.append(pdf.render(0, QSize(400, 200)))
    assert pdf_images[0] == pdf_images[1]
    insert_unicode(view, "中")
    assert "中" in tab.dispatcher.snapshot.project.document.nodes[key].data.text  # type: ignore[union-attr]
    node = tab.dispatcher.snapshot.project.document.nodes[key]
    assert isinstance(node.data, TextData)
    assert window.execute(
        tab, (SetText(node_id=node.id, data=replace(node.data, text="External Ω")),)
    )
    assert not view.text.active
    assert view.text.begin(node.id)
    insert_unicode(view, " saved")
    QTest.keyClick(view, Qt.Key.Key_Escape)
    doc = tab.dispatcher.snapshot.project.document
    resources = view.adapter.resources
    image = render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 400, 200), resources=resources)
    assert image.save(str(tmp_path / "text.png"))
    assert window.grab().save(str(tmp_path / "text-editor-native.png"))
    (tmp_path / "screen.json").write_text(
        json.dumps(
            {
                "platform": QApplication.platformName(),
                "dpr": view.devicePixelRatioF(),
                "window_logical": [window.width(), window.height()],
                "capture_pixels": [window.grab().width(), window.grab().height()],
            }
        ),
        encoding="utf8",
    )
    target = tmp_path / "editable-text.ltechdesign"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    window.save_document(as_new=True)
    qtbot.waitUntil(lambda: not window.busy)
    window.close_tab(window.tabs.currentIndex())
    qtbot.waitUntil(lambda: not window.busy)
    window.open_path(str(target))
    qtbot.waitUntil(lambda: not window.busy)
    reopened = window.current
    assert reopened and reopened.view
    assert reopened.dispatcher.snapshot.project.document == doc
    assert (
        render_image(
            doc,
            doc.pages[0].root_ids,
            QRectF(0, 0, 400, 200),
            resources=reopened.view.adapter.resources,
        )
        == image
    )


def test_typography_controls_color_opacity_and_literal_validation(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    from PySide6.QtWidgets import QComboBox, QLineEdit

    window, tab, view = editor
    key = create_text(window, tab, view, box=True)
    insert_unicode(view, "Typography controls\nSecond line")
    QTest.keyClick(view, Qt.Key.Key_Escape)
    panel = window.inspector.typography
    assert panel.isVisible() and panel.isEnabled()
    qtbot.waitUntil(lambda: panel.family.height() >= panel.family.minimumSizeHint().height())
    assert panel.height() >= panel.minimumSizeHint().height()
    for property, text in (
        ("font_size", "32"),
        ("font_weight", "700"),
        ("italic", "true"),
        ("alignment", "right"),
        ("vertical_alignment", "center"),
        ("line_height_unit", "px"),
        ("line_height_value", "48"),
        ("letter_spacing", "1.5"),
    ):
        field = panel.fields[property]  # type: ignore[index]
        if isinstance(field, QLineEdit):
            field.setText(text)
            field.editingFinished.emit()
        else:
            assert isinstance(field, QComboBox)
            field.setCurrentText(text)
            field.activated.emit(field.currentIndex())
    node = tab.dispatcher.snapshot.project.document.nodes[key]
    assert isinstance(node.data, TextData)
    t = node.data.typography
    assert (t.font_size, t.font_weight, t.italic, t.alignment) == (32, 700, True, "right")
    assert (t.line_height.unit, t.line_height.value, t.letter_spacing) == ("px", 48, 1.5)
    for property, text in (("fill", "#2266AA80"), ("opacity", "0.5")):
        window.inspector.begin(property)
        window.inspector.fields[property].setText(text)
        window.inspector.finish(property)
    node = tab.dispatcher.snapshot.project.document.nodes[key]
    assert node.style.fill and node.style.fill.color == "#2266AA80" and node.opacity == 0.5
    before = tab.dispatcher.snapshot
    field = panel.fields["font_size"]
    assert isinstance(field, QLineEdit)
    field.setText("NaN")
    field.editingFinished.emit()
    assert tab.dispatcher.snapshot is before and "tidak valid" in panel.message.text()


def test_keyboard_text_tool_reopen_double_click_and_ime_cursor_position(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    from PySide6.QtCore import QRectF

    window, tab, view = editor
    view.setFocus()
    QTest.keyClick(view, Qt.Key.Key_T)
    assert view.tool == "text"
    key = create_text(window, tab, view, box=True)
    QTest.keyClicks(view, "First line")
    QTest.keyClick(view, Qt.Key.Key_Return)
    insert_unicode(view, "مرحبا Ω")
    rect = view.inputMethodQuery(Qt.InputMethodQuery.ImCursorRectangle)
    assert isinstance(rect, QRectF) and rect.width() > 0 and rect.height() > 0
    QTest.keyClick(view, Qt.Key.Key_Up)
    QTest.keyClick(view, Qt.Key.Key_Home)
    QTest.keyClicks(view, "> ")
    node = tab.dispatcher.snapshot.project.document.nodes[key]
    assert isinstance(node.data, TextData) and node.data.text.startswith("> First line")
    QTest.keyClick(view, Qt.Key.Key_Escape)
    window.tool_actions[None].trigger()
    position = view.mapFromScene(node.x + 20, node.y + 10)
    QTest.mouseDClick(view.viewport(), Qt.MouseButton.LeftButton, pos=position)
    assert view.text.active and view.text.key == key


def test_nested_rotated_text_caret_maps_to_viewport_and_session_selection_cancels(
    qtbot: QtBot,
    editor: tuple[StudioWindow, Tab, EditorCanvas],
) -> None:
    from ltechdesign.commands import Create
    from ltechdesign.domain import create_node
    from ltechdesign.domain.geometry import world_matrix
    from ltechdesign.rendering.drawing import transform
    from ltechdesign.rendering.text import cursor_rect

    window, tab, view = editor
    initial = create_text(window, tab, view)
    insert_unicode(view, "Source")
    QTest.keyClick(view, Qt.Key.Key_Escape)
    source = tab.dispatcher.snapshot.project.document.nodes[initial]
    parent = replace(
        create_node("frame", source.page_id, width=400, height=300),
        x=70,
        y=90,
        rotation=31,
        scale=1.2,
        clip_content=True,
    )
    text = replace(
        create_node("text", source.page_id, width=220, height=100, data=source.data),
        x=40,
        y=50,
        rotation=-11,
        parent_id=parent.id,
    )
    assert window.execute(tab, (Create(node=parent), Create(node=text)))
    window.tool_actions[None].trigger()
    view.set_selection((text.id,))
    assert view.text.begin(text.id)
    view.set_zoom(1.8)
    rect = cursor_rect(text, view.adapter.resources, view.text.input.textCursor().position())  # type: ignore[arg-type]
    world = transform(world_matrix(tab.dispatcher.snapshot.project.document, text.id))
    expected = view.viewportTransform().mapRect(world.mapRect(rect))
    actual = view.inputMethodQuery(Qt.InputMethodQuery.ImCursorRectangle)
    assert isinstance(actual, QRectF)
    assert (actual.x(), actual.y(), actual.width(), actual.height()) == pytest.approx(
        (expected.x(), expected.y(), expected.width(), expected.height())
    )
    before = tab.dispatcher.snapshot
    window.layers.clearSelection()
    assert not view.text.active and tab.dispatcher.snapshot is before


def test_mixed_typography_and_explicit_missing_font_replacement(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas]
) -> None:
    from PySide6.QtWidgets import QLineEdit

    from ltechdesign.commands import Create, SetFont
    from ltechdesign.domain import create_node
    from ltechdesign.domain.models import Font, FontId

    window, tab, view = editor
    key = create_text(window, tab, view, box=True)
    insert_unicode(view, "First")
    QTest.keyClick(view, Qt.Key.Key_Escape)
    source = tab.dispatcher.snapshot.project.document.nodes[key]
    assert isinstance(source.data, TextData)
    missing = Font(
        id=FontId("missing-gui"), family="NotInstalledFont11", fallback_families=("Segoe UI",)
    )
    other = replace(
        create_node(
            "text",
            source.page_id,
            width=180,
            height=80,
            data=replace(
                source.data,
                text="Second",
                typography=replace(source.data.typography, font_id=missing.id, font_size=32),
            ),
        ),
        y=150,
    )
    assert window.execute(tab, (SetFont(font=missing), Create(node=other)))
    assert tab.warning_label and "NotInstalledFont11" in tab.warning_label.text()
    view.set_selection((key, other.id))
    panel = window.inspector.typography
    field = panel.fields["font_size"]
    assert isinstance(field, QLineEdit) and field.placeholderText() == "Mixed" and not field.text()
    assert panel.family.currentText() == "Mixed"
    field.setText("28")
    field.editingFinished.emit()
    for k in (key, other.id):
        data = tab.dispatcher.snapshot.project.document.nodes[k].data
        assert isinstance(data, TextData) and data.typography.font_size == 28
    view.set_selection((other.id,))
    panel.family.setCurrentText("Segoe UI")
    panel.choose_family()
    assert "NotInstalledFont11" not in tab.warning_label.text()
    assert missing in tab.dispatcher.snapshot.project.fonts.fonts
    window.history("undo")
    assert "NotInstalledFont11" in tab.warning_label.text()
