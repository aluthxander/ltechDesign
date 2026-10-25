"""Inline input buffer; the model is published on every edit through the dispatcher.

QTextEdit supplies Unicode/clipboard/IME input only. It is never shown or used to
draw the design: glyphs, selection hit positions and caret use shared QTextLayout.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from PySide6.QtCore import QMimeData, QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QInputMethodEvent,
    QKeyEvent,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QTextCursor,
)
from PySide6.QtWidgets import QApplication, QTextEdit

from ltechdesign.commands import Create, SetFont, SetText
from ltechdesign.commands.contracts import Operation
from ltechdesign.domain.errors import ModelError
from ltechdesign.domain.geometry import Matrix, world_matrix
from ltechdesign.domain.models import (
    Fill,
    Font,
    FontId,
    Node,
    NodeId,
    PageId,
    Point,
    Style,
    TextData,
    Typography,
    create_node,
    new_id,
)
from ltechdesign.rendering.drawing import path, transform
from ltechdesign.rendering.fonts import default_family
from ltechdesign.rendering.hit_testing import drawing_parent, eligible, hit_test
from ltechdesign.rendering.text import (
    MAX_TEXT_CHARACTERS,
    Resources,
    cursor_rect,
    cursor_x,
    font_for,
    normalized_text,
    position_at,
    utf16_length,
    visual_rows,
)

if TYPE_CHECKING:
    from .canvas import EditorCanvas


@dataclass
class TextPlacement:
    start: Point
    screen: QPoint
    parent: NodeId | None
    page: PageId
    revision: int
    inverse: Matrix
    end: Point


class TextInput(QTextEdit):
    def __init__(self, view: "EditorCanvas", warning: Callable[[str], None]) -> None:
        super().__init__(view)
        self.warning = warning

    def keyPressEvent(self, event: QKeyEvent) -> None:
        super().keyPressEvent(event)
        event.accept()  # never propagate an unhandled shortcut back to the canvas

    def canInsertFromMimeData(self, source: QMimeData) -> bool:
        return source.hasText()

    def insertFromMimeData(self, source: QMimeData) -> None:
        if not source.hasText():
            return
        text = normalized_text(source.text())
        cursor = self.textCursor()
        if len(self.toPlainText()) + len(text) > MAX_TEXT_CHARACTERS + len(cursor.selectedText()):
            self.warning("Paste melebihi batas karakter text box.")
            return
        cursor.insertText(text)


class InlineTextController:
    def __init__(self, view: "EditorCanvas") -> None:
        self.view = view
        self.input = TextInput(view, lambda message: view.message.emit(message))
        self.input.hide()
        self.input.setAcceptRichText(False)
        self.input.setUndoRedoEnabled(False)
        self.input.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.input.textChanged.connect(self.changed)
        self.input.cursorPositionChanged.connect(self.cursor_changed)
        self.key: NodeId | None = None
        self.revision = 0
        self.group = new_id()
        self.last_edit = 0.0
        self.updating = False
        self.publishing = False
        self.history_pending = False
        self.dragging = False
        self.preedit = ""
        self.placement: TextPlacement | None = None
        self.base_resources: Resources | None = None

    @property
    def active(self) -> bool:
        return self.key is not None

    def node(self) -> Node | None:
        return (
            self.view.dispatcher.snapshot.project.document.nodes.get(self.key) if self.key else None
        )

    def begin(self, key: NodeId) -> bool:
        doc = self.view.dispatcher.snapshot.project.document
        node = doc.nodes.get(key)
        if (
            node is None
            or not isinstance(node.data, TextData)
            or not self.view.writable
            or not eligible(doc, key)
        ):
            return False
        self.finish()
        self.view.cancel_gesture()
        self.view.set_selection((key,))
        self.key, self.revision = key, self.view.dispatcher.snapshot.revision
        self.group = new_id()
        self.base_resources = self.view.adapter.resources
        self.updating = True
        if self.base_resources:
            self.input.document().setDefaultFont(font_for(node, self.base_resources))
        self.input.setPlainText(normalized_text(node.data.text))
        self.updating = False
        self.view.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)
        self.view.setFocus(Qt.FocusReason.MouseFocusReason)
        self.view.setCursor(Qt.CursorShape.IBeamCursor)
        self.input.moveCursor(QTextCursor.MoveOperation.End)
        self.view.viewport().update()
        return True

    def finish(self) -> None:
        if (
            self.base_resources is not None
            and self.preedit
            and self.view.adapter.resources
            and self.view.adapter.resources.previews
        ):
            self.view.adapter.resources = self.base_resources
            if self.view.adapter.document:
                self.view.adapter.sync(self.view.adapter.document, self.view.adapter.page)
        self.key = None
        self.preedit = ""
        self.dragging = False
        self.group = new_id()
        self.view.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, False)
        self.view.setCursor(
            Qt.CursorShape.CrossCursor if self.view.tool else Qt.CursorShape.ArrowCursor
        )
        self.view.viewport().update()

    def sync(self) -> None:
        if not self.active or self.publishing:
            return
        node = self.node()
        if (
            node is None
            or not isinstance(node.data, TextData)
            or self.view.selection != (self.key,)
        ):
            self.finish()
            return
        revision = self.view.dispatcher.snapshot.revision
        if revision != self.revision:
            if not self.history_pending:
                self.finish()
                self.view.message.emit("Edit teks selesai: revision berubah dari kendali lain.")
                return
            cursor = self.input.textCursor().position()
            self.updating = True
            self.input.setPlainText(normalized_text(node.data.text))
            c = self.input.textCursor()
            c.setPosition(min(cursor, utf16_length(self.input.toPlainText())))
            self.input.setTextCursor(c)
            self.updating = False
            self.revision = revision
            self.base_resources = self.view.adapter.resources

    def changed(self) -> None:
        if self.updating or not self.active:
            return
        node = self.node()
        if node is None or not isinstance(node.data, TextData):
            self.finish()
            return
        if self.revision != self.view.dispatcher.snapshot.revision:
            self.finish()
            return
        text = self.input.toPlainText()
        if text == node.data.text:
            return
        if len(text) > MAX_TEXT_CHARACTERS:
            self.view.message.emit("Teks melewati batas100.000 karakter per box.")
            self.updating = True
            self.input.setPlainText(normalized_text(node.data.text))
            self.updating = False
            return
        if time.monotonic() - self.last_edit > 1:
            self.group = new_id()
        self.publishing = True
        try:
            success = self.view.submit_text(
                (SetText(node_id=node.id, data=replace(node.data, text=text)),),
                self.revision,
                "Edit text",
                self.group,
            )
        finally:
            self.publishing = False
        if success:
            self.revision = self.view.dispatcher.snapshot.revision
            self.base_resources = self.view.adapter.resources
            self.last_edit = time.monotonic()
        else:
            self.finish()
        self.view.viewport().update()

    def cursor_changed(self) -> None:
        self.view.viewport().update()
        if QApplication.inputMethod():
            QApplication.inputMethod().update(Qt.InputMethodQuery.ImCursorRectangle)

    def handle_key(self, event: QKeyEvent) -> bool:
        if not self.active:
            return False
        if event.key() == Qt.Key.Key_Escape or (
            event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.finish()
            event.accept()
            return True
        if (
            event.key() in (Qt.Key.Key_Home, Qt.Key.Key_End)
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            cursor = self.input.textCursor()
            cursor.setPosition(
                0 if event.key() == Qt.Key.Key_Home else utf16_length(self.input.toPlainText()),
                QTextCursor.MoveMode.KeepAnchor
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier
                else QTextCursor.MoveMode.MoveAnchor,
            )
            self.input.setTextCursor(cursor)
            self.group = new_id()
            return True
        for standard, action in (
            (QKeySequence.StandardKey.Undo, "undo"),
            (QKeySequence.StandardKey.Redo, "redo"),
        ):
            if event.matches(standard):
                self.history_pending = True
                try:
                    self.view.action_requested.emit(action)
                finally:
                    self.history_pending = False
                    self.group = new_id()
                return True
        node, resources = self.node(), self.view.adapter.resources
        if (
            node
            and resources
            and event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Home, Qt.Key.Key_End)
        ):
            cursor = self.input.textCursor()
            rect = cursor_rect(node, resources, cursor.position())
            y = rect.center().y()
            x = rect.x()
            if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                rows = visual_rows(node, resources)
                current = min(
                    range(len(rows)),
                    key=lambda i: abs(rows[i][2].y() + rows[i][1].position().y() - rect.y()),
                )
                target = max(
                    0, min(len(rows) - 1, current + (-1 if event.key() == Qt.Key.Key_Up else 1))
                )
                _, layout, line = rows[target]
                y = layout.position().y() + line.y() + line.height() / 2
            else:
                x = -1e9 if event.key() == Qt.Key.Key_Home else 1e9
            cursor.setPosition(
                position_at(node, resources, QPointF(x, y)),
                QTextCursor.MoveMode.KeepAnchor
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier
                else QTextCursor.MoveMode.MoveAnchor,
            )
            self.input.setTextCursor(cursor)
            self.group = new_id()
            event.accept()
            return True
        separate = event.matches(QKeySequence.StandardKey.Cut) or event.matches(
            QKeySequence.StandardKey.Paste
        )
        if separate:
            self.group = new_id()
        QApplication.sendEvent(self.input, event)
        if separate or event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            self.group = new_id()
        event.accept()
        return True

    def input_method(self, event: QInputMethodEvent) -> None:
        if not self.active:
            return
        self.preedit = event.preeditString()
        self.input.inputMethodEvent(event)
        node, resources = self.node(), self.base_resources
        if node is not None and isinstance(node.data, TextData) and resources:
            if self.preedit:
                cursor = self.input.textCursor().position()
                raw = normalized_text(node.data.text).encode("utf-16-le")
                text = (
                    raw[: cursor * 2].decode("utf-16-le")
                    + self.preedit
                    + raw[cursor * 2 :].decode("utf-16-le")
                )
                preview = replace(node, data=replace(node.data, text=text))
                self.view.adapter.resources = replace(resources, previews={node.id: preview})
            else:
                self.view.adapter.resources = resources
            if self.view.adapter.document:
                self.view.adapter.sync(self.view.adapter.document, self.view.adapter.page)
        self.view.viewport().update()

    def place_cursor(self, point: QPointF, *, extend: bool = False, word: bool = False) -> None:
        node, resources = self.node(), self.view.adapter.resources
        if node is None or resources is None:
            return
        p = (
            world_matrix(self.view.dispatcher.snapshot.project.document, node.id)
            .inverse()
            .point(Point(x=point.x(), y=point.y()))
        )
        cursor = self.input.textCursor()
        cursor.setPosition(
            position_at(node, resources, QPointF(p.x, p.y)),
            QTextCursor.MoveMode.KeepAnchor if extend else QTextCursor.MoveMode.MoveAnchor,
        )
        if word:
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        self.input.setTextCursor(cursor)

    def press(self, point: QPointF, screen: QPoint, modifiers: Qt.KeyboardModifier) -> bool:
        doc = self.view.dispatcher.snapshot.project.document
        hit = hit_test(
            doc, self.view.adapter.page, point, self.view.zoom, self.view.devicePixelRatioF()
        )
        if self.active:
            if hit == self.key:
                self.place_cursor(point, extend=bool(modifiers & Qt.KeyboardModifier.ShiftModifier))
                self.dragging = True
                return True
            self.finish()
        if self.view.tool != "text":
            return False
        if hit is not None and doc.nodes[hit].type == "text":
            if self.begin(hit):
                self.place_cursor(point)
                self.dragging = True
            return True
        if not self.view.writable:
            return True
        parent = drawing_parent(doc, self.view.adapter.page, point)
        inverse = world_matrix(doc, parent).inverse() if parent else Matrix()
        self.view.aids.prepare(())
        start = self.view.aids.point(Point(x=point.x(), y=point.y()))
        self.placement = TextPlacement(
            start,
            screen,
            parent,
            doc.pages[self.view.adapter.page].id,
            self.view.dispatcher.snapshot.revision,
            inverse,
            start,
        )
        return True

    def move(self, point: QPointF) -> bool:
        if self.dragging and self.active:
            self.place_cursor(point, extend=True)
            return True
        if self.placement:
            self.placement.end = self.view.aids.point(Point(x=point.x(), y=point.y()))
            self.view.viewport().update()
            return True
        return False

    def release(self, screen: QPoint) -> bool:
        if self.dragging:
            self.dragging = False
            return True
        g = self.placement
        if g is None:
            return False
        self.placement = None
        if g.revision != self.view.dispatcher.snapshot.revision:
            return True
        start, end = g.inverse.point(g.start), g.inverse.point(g.end)
        dragged = (screen - g.screen).manhattanLength() * self.view.devicePixelRatioF() >= 3
        width = max(1, abs(end.x - start.x)) if dragged else 240
        height = max(28.8, abs(end.y - start.y)) if dragged else 28.8
        project = self.view.dispatcher.snapshot.project
        family = default_family()
        font = next(
            (f for f in project.fonts.fonts if f.family == family and f.source == "system"), None
        )
        operations: tuple[Operation, ...] = ()
        if font is None:
            font = Font(id=FontId(new_id()), family=family)
            operations = (SetFont(font=font),)
        node = replace(
            create_node(
                "text",
                g.page,
                width=width,
                height=height,
                data=TextData(
                    typography=Typography(
                        font_id=font.id, font_size=24, sizing="fixed" if dragged else "auto_width"
                    )
                ),
            ),
            x=min(start.x, end.x) if dragged else start.x,
            y=min(start.y, end.y) if dragged else start.y,
            parent_id=g.parent,
            name="Text",
            style=Style(fill=Fill(color=self.view.foreground)),
        )
        self.view.aids.clear()
        if self.view.apply_operations and self.view.apply_operations(
            operations + (Create(node=node),), g.revision, "Create text"
        ):
            self.view.set_selection((node.id,))
            self.begin(node.id)
        return True

    def draw(self, painter: QPainter) -> None:
        if self.placement:
            g = self.placement
            a, b = g.inverse.point(g.start), g.inverse.point(g.end)
            painter.save()
            pen = QPen(QColor("#0067C0"), 1, Qt.PenStyle.DashLine)
            pen.setCosmetic(True)
            painter.setPen(pen)
            self.clip_ancestors(painter, g.parent)
            outline = QPainterPath()
            outline.addRect(
                QRectF(
                    min(a.x, b.x), min(a.y, b.y), max(1, abs(b.x - a.x)), max(28.8, abs(b.y - a.y))
                )
            )
            painter.drawPath(transform(g.inverse.inverse()).map(outline))
            painter.restore()
        node, resources = self.node(), self.view.adapter.resources
        if node is None or resources is None:
            return
        painter.save()
        try:
            self.clip_ancestors(painter, node.parent_id)
            painter.setWorldTransform(
                transform(world_matrix(self.view.dispatcher.snapshot.project.document, node.id)),
                True,
            )
            painter.setClipRect(
                QRectF(0, 0, node.width, node.height), Qt.ClipOperation.IntersectClip
            )
            cursor = self.input.textCursor()
            start, end = cursor.selectionStart(), cursor.selectionEnd()
            for offset, layout, line in visual_rows(node, resources):
                lo, hi = (
                    max(start - offset, line.textStart()),
                    min(end - offset, line.textStart() + line.textLength()),
                )
                if hi > lo:
                    x, right = cursor_x(line, lo), cursor_x(line, hi)
                    painter.fillRect(
                        QRectF(
                            min(x, right),
                            line.y() + layout.position().y(),
                            abs(right - x),
                            line.height(),
                        ),
                        QColor(0, 103, 192, 65),
                    )
            rect = cursor_rect(node, resources, cursor.position())
            pen = QPen(QColor("#111111"), 1)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.drawLine(rect.topLeft(), rect.bottomLeft())
        except ModelError:
            pass  # node's shared renderer/warning label already reports the failure
        finally:
            painter.restore()

    def clip_ancestors(self, painter: QPainter, key: NodeId | None) -> None:
        document = self.view.dispatcher.snapshot.project.document
        while key is not None:
            ancestor = document.nodes[key]
            if ancestor.clip_content:
                painter.setClipPath(
                    transform(world_matrix(document, key)).map(path(ancestor)),
                    Qt.ClipOperation.IntersectClip,
                )
            key = ancestor.parent_id
