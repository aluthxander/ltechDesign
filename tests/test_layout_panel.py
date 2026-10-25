from dataclasses import replace
from pathlib import Path

import pytest
import test_drawing_tools as drawing
from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QComboBox
from pytestqt.qtbot import QtBot

from ltechdesign.commands import Create, SetFont, SetProperties, SetText
from ltechdesign.domain import create_node
from ltechdesign.domain.geometry import world_matrix
from ltechdesign.domain.models import (
    Constraints,
    Fill,
    Font,
    FontId,
    Layout,
    Point,
    Style,
    TextData,
    Typography,
)
from ltechdesign.rendering.drawing import render_image
from ltechdesign.rendering.pdf import render_pdf
from ltechdesign.ui.canvas import EditorCanvas
from ltechdesign.ui.window import StudioWindow, Tab

pytestmark = pytest.mark.desktop
editor = drawing.editor


def set_field(window: StudioWindow, key: str, value: str) -> None:
    field = window.inspector.layout_panel.fields[key]
    if isinstance(field, QComboBox):
        field.setCurrentText(value)
    else:
        field.setText(value)


def test_inspector_stack_padding_gap_alignment_and_undo(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas]
) -> None:
    window, tab, view = editor
    f = drawing.add(window, tab, "frame", width=350, height=200)
    a = drawing.add(window, tab, "rectangle", parent_id=f.id, width=50, height=30)
    b = drawing.add(window, tab, "ellipse", parent_id=f.id, width=40, height=40)
    view.set_selection((f.id,))
    panel = window.inspector.layout_panel
    before = tab.dispatcher.snapshot.project
    set_field(window, "stack", "horizontal")
    set_field(window, "padding", "10, 20, 30, 40")
    set_field(window, "gap", "8")
    set_field(window, "align_cross", "center")
    panel.apply_button.click()
    ns = tab.dispatcher.snapshot.project.document.nodes
    assert ns[a.id].x == 40 and ns[b.id].x == 98
    assert ns[a.id].y == 75 and ns[b.id].y == 70
    assert view.adapter.items[b.id].mapToScene(0, 0).x() == 98
    window.history("undo")
    assert tab.dispatcher.snapshot.project == before
    assert panel.text("stack") == "none"
    window.history("redo")
    assert panel.text("gap") == "8"


def test_inspector_constraints_then_parent_resize(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas]
) -> None:
    window, tab, view = editor
    f = drawing.add(window, tab, "frame", width=300, height=160)
    c = drawing.add(window, tab, "rectangle", parent_id=f.id, x=20, y=15, width=50, height=20)
    view.set_selection((c.id,))
    set_field(window, "horizontal", "end")
    set_field(window, "vertical", "stretch")
    window.inspector.layout_panel.apply_button.click()
    view.set_selection((f.id,))
    panel = window.inspector
    for key, value in (("width", "400"), ("height", "200")):
        panel.begin(key)
        panel.fields[key].setText(value)
        panel.finish(key)
    changed = tab.dispatcher.snapshot.project.document.nodes[c.id]
    assert changed.x == 120 and changed.y == 15 and changed.height == 60


def test_wrapped_fill_text_changes_nested_hug_in_same_history_entry(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas]
) -> None:
    window, tab, view = editor
    f = drawing.add(
        window,
        tab,
        "frame",
        width=180,
        height=200,
        layout=Layout(padding=(8, 10, 8, 10), gap=6, sizing_y="hug"),
    )
    nested = drawing.add(
        window, tab, "frame", parent_id=f.id, layout=Layout(sizing_x="fill", sizing_y="hug")
    )
    # The real shared Qt/font metrics port measures both initial and allocated widths.
    font = Font(id=FontId("layout-font"), family="Arial")
    text = replace(
        create_node(
            "text",
            nested.page_id,
            data=TextData(
                text="Short", typography=Typography(font_id=font.id, sizing="auto_height")
            ),
        ),
        parent_id=nested.id,
        constraints=Constraints(sizing_x="fill"),
    )
    assert window.execute(tab, (SetFont(font=font), Create(node=text)))
    assert isinstance(text.data, TextData)
    before = tab.dispatcher.snapshot.project
    depth = len(tab.dispatcher.undo_history)
    revision = tab.dispatcher.snapshot.revision
    assert window.execute(
        tab,
        (
            SetText(
                node_id=text.id,
                data=replace(
                    text.data,
                    typography=replace(text.data.typography, sizing="auto_height"),
                    text="Words wrap into multiple lines when the frame becomes narrow. " * 4,
                ),
            ),
        ),
    )
    after = tab.dispatcher.snapshot.project
    ns = after.document.nodes
    assert ns[text.id].width == 160
    assert ns[nested.id].height == ns[text.id].height
    assert ns[f.id].height == ns[text.id].height + 16
    assert ns[text.id].height > before.document.nodes[text.id].height
    assert len(tab.dispatcher.undo_history) == depth + 1
    assert tab.dispatcher.snapshot.revision == revision + 1
    assert window.execute(tab, (SetProperties(node_ids=(f.id,), property="width", value=300),))
    wider = tab.dispatcher.snapshot.project.document.nodes
    assert wider[text.id].width == 280 and wider[text.id].height < ns[text.id].height
    window.history("undo")
    assert tab.dispatcher.snapshot.project == after
    window.history("undo")
    assert tab.dispatcher.snapshot.project == before


def test_layout_scene_png_pdf_and_native_roundtrip(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas], tmp_path: Path
) -> None:
    window, tab, view = editor
    f = drawing.add(
        window,
        tab,
        "frame",
        width=240,
        height=120,
        x=10,
        y=15,
        layout=Layout(direction="horizontal", padding=(10, 15, 10, 15), gap=5),
    )
    drawing.add(
        window,
        tab,
        "rectangle",
        parent_id=f.id,
        width=40,
        height=40,
        style=Style(fill=Fill(color="#AABBCCFF")),
    )
    b = drawing.add(
        window,
        tab,
        "rectangle",
        parent_id=f.id,
        width=40,
        height=40,
        constraints=Constraints(sizing_x="fill"),
        style=Style(fill=Fill(color="#FF6611FF")),
    )
    project = tab.dispatcher.snapshot.project
    scene_point = view.adapter.items[b.id].mapToScene(3, 5)
    expected = world_matrix(project.document, b.id).point(Point(x=3, y=5))
    assert scene_point.x() == expected.x and scene_point.y() == expected.y
    image = render_image(project.document, (f.id,), QRectF(0, 0, 270, 150))
    assert image.pixelColor(30, 30).name() == "#aabbcc"
    assert image.pixelColor(100, 30).name() == "#ff6611"
    pdf = tmp_path / "layout.pdf"
    render_pdf(project.document, (f.id,), QRectF(0, 0, 270, 150), pdf)
    assert pdf.read_bytes().startswith(b"%PDF")
    target = tmp_path / "layout.ltechdesign"
    window.service.save(tab.handle, tab.dispatcher.snapshot, {}, target=target)
    # Reopen with an independent read-only admission while original writer is alive.
    from ltechdesign.persistence import PersistenceService

    reader = PersistenceService()
    loaded = reader.open(target, read_only=True)
    try:
        assert loaded.loaded.project.document == project.document
        reopened = render_image(loaded.loaded.project.document, (f.id,), QRectF(0, 0, 270, 150))
        assert reopened == image
    finally:
        reader.close(loaded)


def test_layout_invalid_inspector_input_does_not_publish(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas]
) -> None:
    window, tab, view = editor
    f = drawing.add(window, tab, "frame")
    view.set_selection((f.id,))
    before = tab.dispatcher.snapshot
    set_field(window, "stack", "vertical")
    for bad in ("-1, 0, 0, 0", "nan, 0, 0, 0", "1, 2, 3"):
        set_field(window, "padding", bad)
        window.inspector.layout_panel.apply()
        assert tab.dispatcher.snapshot is before
        assert "tidak valid" in window.inspector.layout_panel.message.text()
    assert not window.inspector.layout_panel.fields["horizontal"].isEnabled()
    set_field(window, "padding", "0, 0, 0, 0")
    set_field(window, "horizontal", "end")
    window.inspector.layout_panel.apply()
    assert tab.dispatcher.snapshot is before
    assert "memerlukan parent" in window.inspector.layout_panel.message.text()


def test_pointer_resize_parent_runs_layout_and_one_undo(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas]
) -> None:
    from PySide6.QtCore import QPointF
    from test_editor_transforms import gesture

    window, tab, view = editor
    f = drawing.add(
        window,
        tab,
        "frame",
        width=240,
        height=140,
        x=40,
        y=50,
        layout=Layout(direction="horizontal", padding=(10, 10, 10, 10), gap=5),
    )
    c = drawing.add(
        window,
        tab,
        "rectangle",
        parent_id=f.id,
        constraints=Constraints(sizing_x="fill", sizing_y="fill"),
    )
    view.set_selection((f.id,))
    view.set_tool(None)
    view.centerOn(220, 170)
    view.set_zoom(1)
    before = tab.dispatcher.snapshot.project
    depth = len(tab.dispatcher.undo_history)
    handle = view.transforms.handles()["se"]
    target = world_matrix(before.document, f.id).point(Point(x=320, y=200))
    gesture(qtbot, view, handle, QPointF(target.x, target.y))
    nodes = tab.dispatcher.snapshot.project.document.nodes
    assert nodes[f.id].width == pytest.approx(320, abs=1)
    assert nodes[f.id].height == pytest.approx(200, abs=1)
    assert nodes[c.id].width == nodes[f.id].width - 20
    assert nodes[c.id].height == nodes[f.id].height - 20
    assert len(tab.dispatcher.undo_history) == depth + 1
    window.history("undo")
    assert tab.dispatcher.snapshot.project == before


def test_inline_text_recalculates_hug_parent_and_is_undoable(
    qtbot: QtBot, editor: tuple[StudioWindow, Tab, EditorCanvas]
) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    window, tab, view = editor
    f = drawing.add(
        window, tab, "frame", layout=Layout(direction="horizontal", sizing_x="hug", sizing_y="hug")
    )
    font = Font(id=FontId("inline-layout-font"), family="Arial")
    text = replace(
        create_node(
            "text",
            f.page_id,
            data=TextData(text="Hi", typography=Typography(font_id=font.id, sizing="auto_width")),
        ),
        parent_id=f.id,
    )
    assert window.execute(tab, (SetFont(font=font), Create(node=text)))
    before = tab.dispatcher.snapshot.project
    assert view.text.begin(text.id)
    QTest.keyClick(view, Qt.Key.Key_End)
    QTest.keyClicks(view, " more words")
    nodes = tab.dispatcher.snapshot.project.document.nodes
    assert nodes[f.id].width == nodes[text.id].width
    assert nodes[f.id].height == nodes[text.id].height
    assert nodes[f.id].width > before.document.nodes[f.id].width
    QTest.keyClick(view, Qt.Key.Key_Escape)
    window.history("undo")
    assert tab.dispatcher.snapshot.project == before
