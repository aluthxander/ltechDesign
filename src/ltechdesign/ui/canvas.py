"""Editor gestures are session state; only a successful release creates content."""

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QContextMenuEvent,
    QFocusEvent,
    QHideEvent,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPen,
)

from ltechdesign.commands import Dispatcher
from ltechdesign.commands.contracts import Operation
from ltechdesign.domain.authoring import drawn_node
from ltechdesign.domain.errors import ModelError
from ltechdesign.domain.geometry import Matrix, world_matrix
from ltechdesign.domain.models import Node, NodeId, NodeType, Point, new_id
from ltechdesign.rendering.canvas import CanvasView
from ltechdesign.rendering.drawing import path, transform
from ltechdesign.rendering.hit_testing import (
    drawing_parent,
    eligible,
    hit_test,
    marquee_hits,
    paint_order,
)

from .transforms import TransformController, edit_shortcut


@dataclass
class Gesture:
    start: QPointF
    end: QPointF
    screen_start: QPoint
    revision: int
    parent: NodeId | None
    inverse: Matrix
    key: NodeId
    original_selection: tuple[NodeId, ...]
    additive: bool
    hit: NodeId | None


class EditorCanvas(CanvasView):
    selection_changed = Signal(object)
    message = Signal(str)
    action_requested = Signal(str)
    context_requested = Signal(object)

    def __init__(self, dispatcher: Dispatcher, submit: Callable[[Node, int], bool]) -> None:
        super().__init__()
        self.dispatcher = dispatcher
        self.submit = submit
        self.tool: NodeType | None = None  # None = select; text/image have no placeholder tools.
        self.sides = 5
        self.writable = True
        self.gesture: Gesture | None = None
        self.preview: Node | None = None
        self.apply_operations: Callable[[tuple[Operation, ...], int, str], bool] | None = None
        self.transforms = TransformController(self)
        self.setMouseTracking(True)
        self.setAccessibleName(
            "Canvas — drawing drag; Shift/Ctrl multiselect; Esc cancel; Ctrl+A select all"
        )

    def sync(self, page: int, *, writable: bool) -> None:
        revision = self.dispatcher.snapshot.revision
        active = self.transforms.active
        if active and (active.revision != revision or active.page != page or not writable):
            self.cancel_gesture()
            self.message.emit("Transform dibatalkan: dokumen atau halaman berubah.")
        if self.gesture and (
            self.gesture.revision != revision or self.adapter.page != page or not writable
        ):
            self.cancel_gesture()
            self.message.emit("Drawing dibatalkan: dokumen atau halaman berubah.")
        self.writable = writable
        self.adapter.sync(self.dispatcher.snapshot.project.document, page)

    def set_tool(self, tool: NodeType | None) -> None:
        if tool not in (None, "frame", "rectangle", "ellipse", "line", "polygon"):
            raise ValueError("Unsupported drawing tool")
        self.cancel_gesture()
        self.tool = tool
        self.setCursor(Qt.CursorShape.CrossCursor if tool else Qt.CursorShape.ArrowCursor)

    def set_selection(self, keys: tuple[NodeId, ...]) -> None:
        doc = self.adapter.document
        allowed = set(paint_order(doc, self.adapter.page)) if doc else set()
        selected = tuple(
            dict.fromkeys(k for k in keys if doc and k in allowed and eligible(doc, k))
        )
        if selected != self.selection:
            self.selection = selected
            self.selection_changed.emit(selected)
        self.viewport().update()

    def select_all(self) -> None:
        doc = self.adapter.document
        if doc:
            self.set_selection(paint_order(doc, self.adapter.page))

    def cancel_gesture(self) -> None:
        self.transforms.cancel()
        self.gesture = None
        self.preview = None
        self.viewport().update()

    def _preview(self, position: QPoint) -> None:
        gesture = self.gesture
        if gesture is None:
            return
        gesture.end = self.mapToScene(position)
        self.preview = None
        if self.tool:
            start = gesture.inverse.point(Point(x=gesture.start.x(), y=gesture.start.y()))
            end = gesture.inverse.point(Point(x=gesture.end.x(), y=gesture.end.y()))
            if (position - gesture.screen_start).manhattanLength() >= 3:
                try:
                    self.preview = drawn_node(
                        self.tool,
                        self.dispatcher.snapshot.project.document.pages[self.adapter.page].id,
                        start,
                        end,
                        parent_id=gesture.parent,
                        sides=self.sides,
                        node_id=gesture.key,
                    )
                except ModelError:
                    # A zero-area shape has no valid content intent; release cancels it.
                    pass
        self.viewport().update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() in (Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton):
            self.cancel_gesture()
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        doc = self.adapter.document
        if doc is None or (self.tool is not None and not self.writable):
            event.accept()
            return
        screen = event.position().toPoint()
        point = self.mapToScene(screen)
        additive = bool(
            event.modifiers()
            & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier)
        )
        if self.tool is None and not additive and self.transforms.press(point, screen):
            event.accept()
            return
        hit = (
            hit_test(doc, self.adapter.page, point, self.zoom, self.devicePixelRatioF())
            if self.tool is None
            else None
        )
        parent = drawing_parent(doc, self.adapter.page, point) if self.tool else None
        inverse = world_matrix(doc, parent).inverse() if parent else Matrix()
        self.gesture = Gesture(
            point,
            point,
            screen,
            self.dispatcher.snapshot.revision,
            parent,
            inverse,
            NodeId(new_id()),
            self.selection,
            additive,
            hit,
        )
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.transforms.active:
            self.transforms.update(event.position().toPoint(), event.modifiers())
            event.accept()
        elif self.gesture is not None:
            self._preview(event.position().toPoint())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.transforms.active:
            self.transforms.release(event.position().toPoint(), event.modifiers())
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton and self.gesture is not None:
            gesture = self.gesture
            if gesture.revision != self.dispatcher.snapshot.revision:
                self.cancel_gesture()
                self.message.emit("Drawing dibatalkan: revision berubah.")
                event.accept()
                return
            self._preview(event.position().toPoint())
            preview = self.preview
            self.cancel_gesture()
            if self.tool:
                if preview is not None and self.writable and self.submit(preview, gesture.revision):
                    self.set_selection((preview.id,))
            elif self.adapter.document:
                if (event.position().toPoint() - gesture.screen_start).manhattanLength() < 3:
                    hit = gesture.hit
                    selected = gesture.original_selection
                    if gesture.additive:
                        if hit in selected:
                            selected = tuple(k for k in selected if k != hit)
                        elif hit is not None:
                            selected += (hit,)
                    else:
                        selected = (hit,) if hit is not None else ()
                    self.set_selection(selected)
                else:
                    rect = QRectF(gesture.start, gesture.end).normalized()
                    hits = marquee_hits(self.adapter.document, self.adapter.page, rect)
                    self.set_selection(
                        gesture.original_selection + hits if gesture.additive else hits
                    )
            event.accept()
        else:
            super().mouseReleaseEvent(event)
            if event.button() == Qt.MouseButton.MiddleButton:
                self.setCursor(
                    Qt.CursorShape.CrossCursor if self.tool else Qt.CursorShape.ArrowCursor
                )

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_gesture()
            event.accept()
        elif event.matches(QKeySequence.StandardKey.SelectAll):
            self.select_all()
            event.accept()
        elif action := edit_shortcut(event):
            self.cancel_gesture()
            self.action_requested.emit(action)
            event.accept()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        self.cancel_gesture()
        doc = self.adapter.document
        if doc:
            hit = hit_test(
                doc,
                self.adapter.page,
                self.mapToScene(event.pos()),
                self.zoom,
                self.devicePixelRatioF(),
            )
            if hit is not None:
                ancestor: NodeId | None = hit
                while ancestor is not None and ancestor not in self.selection:
                    ancestor = doc.nodes[ancestor].parent_id
                if ancestor is None:
                    self.set_selection((hit,))
        self.context_requested.emit(event.globalPos())
        event.accept()

    def focusOutEvent(self, event: QFocusEvent) -> None:
        self.cancel_gesture()
        super().focusOutEvent(event)

    def hideEvent(self, event: QHideEvent) -> None:
        self.cancel_gesture()
        super().hideEvent(event)

    def drawForeground(self, painter: QPainter, rect: QRectF | QRect) -> None:
        if len(self.selection) <= 50:
            super().drawForeground(painter, rect)
        painter.save()
        pen = QPen(QColor("#0067C0"), 1, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self.gesture and self.tool is None:
            painter.drawRect(QRectF(self.gesture.start, self.gesture.end).normalized())
        elif self.preview and self.gesture:
            # Only an outline overlay, outside scene/model/export and history.
            parent_world = self.gesture.inverse.inverse()
            from ltechdesign.domain.geometry import local_matrix

            painter.save()
            doc = self.adapter.document
            parent = self.gesture.parent
            while doc is not None and parent is not None:
                ancestor = doc.nodes[parent]
                if ancestor.clip_content:
                    painter.setClipPath(
                        transform(world_matrix(doc, parent)).map(path(ancestor)),
                        Qt.ClipOperation.IntersectClip,
                    )
                parent = ancestor.parent_id
            painter.drawPath(
                transform(parent_world @ local_matrix(self.preview)).map(path(self.preview))
            )
            painter.restore()
        if len(self.selection) > 1 and self.adapter.document:
            painter.drawRect(self.transforms.selection_bounds())
        painter.restore()
        self.transforms.draw(painter)
