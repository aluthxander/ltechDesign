"""Stable-ID scene indexing with explicit shared subtree painting and session navigation."""

import math

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen, QWheelEvent
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsView,
    QStyleOptionGraphicsItem,
    QWidget,
)

from ltechdesign.domain.errors import ModelError
from ltechdesign.domain.geometry import visual_bounds, world_matrix
from ltechdesign.domain.models import Document, NodeId

from .drawing import draw_node, local_visual, transform
from .text import Resources


class NodeItem(QGraphicsItem):
    def __init__(self, document: Document, key: NodeId) -> None:
        super().__init__()
        self.document, self.key = document, key
        self.resources: Resources | None = None
        self.bounds = local_visual(document, key)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def boundingRect(self) -> QRectF:
        return self.bounds

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None
    ) -> None:
        try:
            draw_node(painter, self.document, self.key, local=True, resources=self.resources)
        except ModelError as error:
            painter.setPen(QColor("red"))
            painter.drawText(self.bounds, str(error.code))


class SceneAdapter:
    def __init__(self, scene: QGraphicsScene) -> None:
        self.scene = scene
        self.items: dict[NodeId, NodeItem] = {}
        self.document: Document | None = None
        self.page = 0
        self.resources: Resources | None = None

    def sync(self, document: Document, page: int = 0) -> None:
        """Reconcile metadata by ID; no scene.clear or replacing unchanged items."""
        roots = document.pages[page].root_ids
        keys: list[NodeId] = []

        def visit(key: NodeId) -> None:
            keys.append(key)
            for child in document.nodes[key].children:
                visit(child)

        for root in roots:
            visit(root)
        for key in self.items.keys() - set(keys):
            self.scene.removeItem(self.items.pop(key))
        old = self.document
        changed_keys = {
            k for k in document.nodes if old is None or old.nodes.get(k) != document.nodes[k]
        }
        if old:
            changed_keys.update(old.nodes.keys() - document.nodes.keys())
        dirty_roots: set[NodeId] = set()
        for source in (old, document):
            if source:
                for key in changed_keys & source.nodes.keys():
                    while source.nodes[key].parent_id is not None:
                        key = source.nodes[key].parent_id  # type: ignore[assignment]
                    dirty_roots.add(key)
        for order, key in enumerate(keys):
            node = document.nodes[key]
            item = self.items.get(key)
            if item is None:
                item = NodeItem(document, key)
                self.items[key] = item
                self.scene.addItem(item)
            bounds = local_visual(document, key)
            if bounds != item.bounds:
                item.prepareGeometryChange()
                item.bounds = bounds
            item.document = document
            item.resources = self.resources
            item.setTransform(transform(world_matrix(document, key)))
            item.setZValue(order)
            item.setFlag(
                QGraphicsItem.GraphicsItemFlag.ItemHasNoContents, node.parent_id is not None
            )
            item.setVisible(node.visible)
            # Root paints its descendants. Any changed subtree invalidates its root,
            # but item identity/indexing survives edits and reorder/reparent operations.
            if key in dirty_roots:
                item.update()
        self.document, self.page = document, page
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-500, -500, 500, 500))


class CanvasView(QGraphicsView):
    zoom_changed = Signal(float)
    MIN_ZOOM = 0.02
    MAX_ZOOM = 16.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.adapter = SceneAdapter(self.scene())
        self.selection: tuple[NodeId, ...] = ()
        self.grid = False
        self._pan: QPoint | None = None
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setAccessibleName("Canvas — pan tombol tengah; Ctrl+wheel untuk zoom")
        self.setBackgroundBrush(QColor("#E6E6E6"))

    @property
    def zoom(self) -> float:
        return self.transform().m11()

    def set_zoom(self, zoom: float, cursor: QPoint | None = None) -> None:
        if not math.isfinite(zoom):
            return
        zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, zoom))
        cursor = cursor or self.viewport().rect().center()
        before = self.mapToScene(cursor)
        self.scale(zoom / self.zoom, zoom / self.zoom)
        after = self.mapToScene(cursor)
        delta = after - before
        self.translate(delta.x(), delta.y())
        self.zoom_changed.emit(zoom)
        self.viewport().update()

    def fit_bounds(self, bounds: QRectF) -> None:
        if bounds.isEmpty():
            return
        ratio = min(
            (self.viewport().width() - 32) / bounds.width(),
            (self.viewport().height() - 32) / bounds.height(),
        )
        self.set_zoom(ratio)
        self.centerOn(bounds.center())

    def fit_artboard(self) -> None:
        doc = self.adapter.document
        if doc is None:
            return
        roots = doc.pages[self.adapter.page].root_ids
        key = next((k for k in roots if doc.nodes[k].type == "artboard"), None)
        if key is not None:
            node = doc.nodes[key]
            self.fit_bounds(
                transform(world_matrix(doc, key)).mapRect(QRectF(0, 0, node.width, node.height))
            )

    def zoom_selection(self) -> None:
        doc = self.adapter.document
        bounds = QRectF()
        if doc:
            for key in self.selection:
                if key in doc.nodes:
                    visual = visual_bounds(doc, key)
                    if visual:
                        bounds = bounds.united(
                            QRectF(visual.min_x, visual.min_y, visual.width, visual.height)
                        )
        self.fit_bounds(bounds)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 2 ** max(-4, min(4, event.angleDelta().y() / 480))
            self.set_zoom(self.zoom * factor, event.position().toPoint())
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._pan is not None:
            current = event.position().toPoint()
            delta = current - self._pan
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._pan = current
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan = None
            self.unsetCursor()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def drawForeground(self, painter: QPainter, rect: QRectF | QRect) -> None:
        # View-only overlay. QGraphicsScene.render and shared drawing never see it.
        doc = self.adapter.document
        pen = QPen(QColor("#0067C0"), 1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if doc:
            for key in self.selection:
                if key in doc.nodes:
                    bounds = visual_bounds(doc, key)
                    if bounds:
                        painter.drawRect(
                            QRectF(bounds.min_x, bounds.min_y, bounds.width, bounds.height)
                        )

    def drawBackground(self, painter: QPainter, rect: QRectF | QRect) -> None:
        super().drawBackground(painter, rect)
        if not self.grid:
            return
        spacing = max(20, 10 / self.zoom)
        pen = QPen(QColor("#CCCCCC"), 1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        x = math.floor(rect.left() / spacing) * spacing
        while x < rect.right():
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            x += spacing
        y = math.floor(rect.top() / spacing) * spacing
        while y < rect.bottom():
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            y += spacing
