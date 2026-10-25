"""Wireframe transform previews; release submits a single semantic command."""

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPen

from ltechdesign.commands.contracts import Operation, ResizeNode, ScaleNodes, TransformNodes
from ltechdesign.domain.editing import MIN_SIZE, around, resized, roots
from ltechdesign.domain.geometry import (
    Bounds,
    Matrix,
    local_matrix,
    primitive_bounds,
    translation,
    world_matrix,
)
from ltechdesign.domain.models import Document, NodeId, Point
from ltechdesign.domain.snapping import Axis
from ltechdesign.domain.snapping import geometry as snap_geometry
from ltechdesign.rendering.drawing import transform
from ltechdesign.rendering.hit_testing import clipped_path, hit_test

if TYPE_CHECKING:
    from .canvas import EditorCanvas

HANDLES = {
    "nw": (0.0, 0.0),
    "n": (0.5, 0.0),
    "ne": (1.0, 0.0),
    "e": (1.0, 0.5),
    "se": (1.0, 1.0),
    "s": (0.5, 1.0),
    "sw": (0.0, 1.0),
    "w": (0.0, 0.5),
}


def edit_shortcut(event: QKeyEvent) -> str | None:
    control = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
    shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
    key = Qt.Key(event.key())
    if event.modifiers() & (Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier):
        return None
    if control:
        if key == Qt.Key.Key_G:
            return "ungroup" if shift else "group"
        if key == Qt.Key.Key_Z:
            return "redo" if shift else "undo"
        return {
            Qt.Key.Key_C: "copy",
            Qt.Key.Key_X: "cut",
            Qt.Key.Key_V: "paste",
            Qt.Key.Key_D: "duplicate",
            Qt.Key.Key_BracketRight: "forward",
            Qt.Key.Key_BracketLeft: "backward",
            Qt.Key.Key_A: "select_all",
        }.get(key)
    if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
        return "delete"
    arrow = {
        Qt.Key.Key_Left: "left",
        Qt.Key.Key_Right: "right",
        Qt.Key.Key_Up: "up",
        Qt.Key.Key_Down: "down",
    }.get(key)
    return f"nudge_{arrow}_{10 if shift else 1}" if arrow else None


@dataclass
class TransformGesture:
    document: Document
    revision: int
    page: int
    keys: tuple[NodeId, ...]
    mode: Literal["move", "resize", "rotate"]
    start: QPointF
    screen: QPoint
    basis: Matrix
    rect: QRectF
    bounds: Bounds
    handle: str = ""
    operations: tuple[Operation, ...] = ()
    preview: tuple[QPointF, ...] = ()


class TransformController:
    def __init__(self, view: "EditorCanvas") -> None:
        self.view = view
        self.active: TransformGesture | None = None
        self._document: Document | None = None
        self._selection: tuple[NodeId, ...] = ()
        self._geometry: tuple[Matrix, QRectF, tuple[NodeId, ...]] | None = None
        self._bounds: QRectF | None = None

    def cancel(self) -> None:
        self.active = None
        self.view.aids.clear()

    def geometry(self) -> tuple[Matrix, QRectF, tuple[NodeId, ...]] | None:
        doc = self.view.adapter.document
        if doc is self._document and self.view.selection == self._selection:
            return self._geometry
        self._document, self._selection = doc, self.view.selection
        self._geometry = self._geometry_uncached()
        self._bounds = None
        return self._geometry

    def selection_bounds(self) -> QRectF:
        geometry = self.geometry()
        if self._bounds is None:
            self._bounds = QRectF()
            if geometry and self._document:
                for key in geometry[2]:
                    self._bounds = self._bounds.united(
                        clipped_path(self._document, key).boundingRect()
                    )
        return self._bounds

    def _geometry_uncached(self) -> tuple[Matrix, QRectF, tuple[NodeId, ...]] | None:
        doc = self.view.adapter.document
        if doc is None or not self.view.selection:
            return None
        keys = roots(doc, self.view.selection)
        if len(keys) == 1:
            node = doc.nodes[keys[0]]
            return world_matrix(doc, node.id), QRectF(0, 0, node.width, node.height), keys
        rect = QRectF()
        for key in keys:
            node = doc.nodes[key]
            if node.type in ("rectangle", "frame", "artboard", "group"):
                # The adapter already projects this immutable snapshot into world space.
                # Box geometry excludes radius/style, exactly as primitive_bounds does.
                bound = (
                    self.view.adapter.items[key]
                    .sceneTransform()
                    .mapRect(QRectF(0, 0, node.width, node.height))
                )
            else:
                b = primitive_bounds(node, world_matrix(doc, key))
                bound = QRectF(b.min_x, b.min_y, b.width, b.height)
            rect = rect.united(bound)
        return Matrix(), rect, keys

    def handles(self) -> dict[str, QPointF]:
        geometry = self.geometry()
        if geometry is None:
            return {}
        matrix, rect, _ = geometry
        if rect.width() == 0 and rect.height() == 0:
            return {}
        mapping = transform(matrix)
        result = {
            key: mapping.map(
                QPointF(rect.left() + u * rect.width(), rect.top() + v * rect.height())
            )
            for key, (u, v) in HANDLES.items()
        }
        result["rotate"] = mapping.map(
            QPointF(
                rect.center().x(), rect.top() - 24 / (self.view.zoom * matrix.similarity_scale())
            )
        )
        return result

    def press(self, point: QPointF, screen: QPoint) -> bool:
        view = self.view
        doc = view.adapter.document
        if doc is None or not view.writable:
            return False
        distances = {
            key: (view.mapFromScene(p) - screen).manhattanLength()
            for key, p in self.handles().items()
        }
        nearest = min(distances, key=lambda k: distances[k]) if distances else None
        handle = nearest if nearest and distances[nearest] <= 8 / view.devicePixelRatioF() else None
        if handle is None:
            hit = hit_test(doc, view.adapter.page, point, view.zoom, view.devicePixelRatioF())
            if hit is None:
                return False
            ancestor: NodeId | None = hit
            while ancestor is not None and ancestor not in view.selection:
                ancestor = doc.nodes[ancestor].parent_id
            if ancestor is None:
                view.set_selection((hit,))
        geometry = self.geometry()
        assert geometry is not None
        matrix, rect, keys = geometry
        bounds = snap_geometry(doc, keys[0])
        for key in keys[1:]:
            bounds = bounds.union(snap_geometry(doc, key))
        view.aids.prepare(keys)
        self.active = TransformGesture(
            doc,
            view.dispatcher.snapshot.revision,
            view.adapter.page,
            keys,
            "rotate" if handle == "rotate" else "resize" if handle else "move",
            point,
            screen,
            matrix,
            rect,
            bounds,
            handle or "",
        )
        return True

    @staticmethod
    def corners(matrix: Matrix, rect: QRectF) -> tuple[QPointF, ...]:
        mapping = transform(matrix)
        return tuple(
            mapping.map(p)
            for p in (
                rect.topLeft(),
                rect.topRight(),
                rect.bottomRight(),
                rect.bottomLeft(),
                rect.topLeft(),
            )
        )

    def update(self, screen: QPoint, modifiers: Qt.KeyboardModifier) -> None:
        g, view = self.active, self.view
        if g is None:
            return
        if (screen - g.screen).manhattanLength() * view.viewport().devicePixelRatioF() < 3:
            g.operations, g.preview = (), ()
            view.aids.clear()
            return
        point = view.mapToScene(screen)
        shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        alt = bool(modifiers & Qt.KeyboardModifier.AltModifier)
        matrix = Matrix()
        if g.mode == "move":
            dx, dy = point.x() - g.start.x(), point.y() - g.start.y()
            axis: Axis | None = None
            if shift:
                axis = "x" if abs(dx) >= abs(dy) else "y"
                dx, dy = (dx, 0) if abs(dx) >= abs(dy) else (0, dy)
            snapped = view.aids.move(g.bounds, Point(x=dx, y=dy), axis)
            matrix = translation(snapped.x, snapped.y)
        elif g.mode == "rotate":
            node = g.document.nodes[g.keys[0]]
            center = (
                g.basis.point(node.pivot)
                if len(g.keys) == 1
                else Point(x=g.rect.center().x(), y=g.rect.center().y())
            )
            angle = math.degrees(
                math.atan2(point.y() - center.y, point.x() - center.x)
                - math.atan2(g.start.y() - center.y, g.start.x() - center.x)
            )
            if shift:
                angle = round(angle / 15) * 15
            matrix = around(center, angle=angle)
        else:
            u, v = HANDLES[g.handle]
            anchor = Point(x=0.5 if alt else 1 - u, y=0.5 if alt else 1 - v)
            ax, ay = (
                g.rect.left() + anchor.x * g.rect.width(),
                g.rect.top() + anchor.y * g.rect.height(),
            )
            inverse = g.basis.inverse()
            current = inverse.point(Point(x=point.x(), y=point.y()))
            start = inverse.point(Point(x=g.start.x(), y=g.start.y()))
            vx, vy = (u - anchor.x) * g.rect.width(), (v - anchor.y) * g.rect.height()
            dx, dy = current.x - start.x, current.y - start.y
            rx = (vx + dx) / vx if vx else 1
            ry = (vy + dy) / vy if vy else 1
            node = g.document.nodes[g.keys[0]]
            uniform = len(g.keys) > 1 or node.type == "group" or shift or node.type == "line"
            if uniform:
                minimum = max(
                    (
                        MIN_SIZE / extent
                        for extent in (g.rect.width(), g.rect.height())
                        if extent > 0
                    ),
                    default=1,
                )
                denominator = vx * vx + vy * vy
                factor = max(
                    max(
                        (
                            MIN_SIZE / extent
                            for extent in (g.rect.width(), g.rect.height())
                            if extent > 0
                        ),
                        default=1,
                    ),
                    1 + (vx * dx + vy * dy) / denominator if denominator else 1,
                )
                origin = g.basis.point(Point(x=ax, y=ay))
                vector = Point(x=g.basis.a * vx + g.basis.c * vy, y=g.basis.b * vx + g.basis.d * vy)
                factor = view.aids.along(origin, vector, factor, minimum)
                if len(g.keys) > 1 or node.type == "group":
                    matrix = g.basis @ around(Point(x=ax, y=ay), factor=factor) @ g.basis.inverse()
                    g.operations = (
                        ScaleNodes(
                            node_ids=g.keys, factor=factor, center=g.basis.point(Point(x=ax, y=ay))
                        ),
                    )
                    g.preview = self.corners(matrix @ g.basis, g.rect)
                    view.viewport().update()
                    return
                else:
                    rx = ry = factor
            elif vx and vy:
                handle = g.basis.point(Point(x=ax + vx, y=ay + vy))
                snapped = view.aids.point(
                    Point(
                        x=handle.x + point.x() - g.start.x(),
                        y=handle.y + point.y() - g.start.y(),
                    )
                )
                current = inverse.point(snapped)
                rx, ry = (current.x - ax) / vx, (current.y - ay) / vy
                if node.width * rx < MIN_SIZE or node.height * ry < MIN_SIZE:
                    view.aids.clear()
            else:
                origin = g.basis.point(Point(x=ax, y=ay))
                vector = Point(x=g.basis.a * vx + g.basis.c * vy, y=g.basis.b * vx + g.basis.d * vy)
                factor = view.aids.along(
                    origin, vector, rx if vx else ry, MIN_SIZE / (node.width if vx else node.height)
                )
                rx, ry = (factor, ry) if vx else (rx, factor)
            if not (len(g.keys) > 1 or node.type == "group"):
                op = ResizeNode(
                    node_id=node.id,
                    width=max(MIN_SIZE, node.width * rx),
                    height=max(MIN_SIZE, node.height * ry),
                    anchor=anchor,
                )
                changed = resized(node, op.width, op.height, op.anchor)
                parent = world_matrix(g.document, node.parent_id) if node.parent_id else Matrix()
                g.preview = self.corners(
                    parent @ local_matrix(changed), QRectF(0, 0, changed.width, changed.height)
                )
                g.operations = (op,)
                view.viewport().update()
                return
        g.operations = (TransformNodes(node_ids=g.keys, matrix=matrix),)
        g.preview = self.corners(matrix @ g.basis, g.rect)
        view.viewport().update()

    def release(self, screen: QPoint, modifiers: Qt.KeyboardModifier) -> None:
        g = self.active
        if g is None:
            return
        self.update(screen, modifiers)
        self.active = None
        self.view.aids.clear()
        if g.revision != self.view.dispatcher.snapshot.revision:
            self.view.message.emit("Transform dibatalkan: revision berubah.")
        elif g.operations and self.view.apply_operations:
            self.view.apply_operations(g.operations, g.revision, g.mode.title())
        self.view.viewport().update()

    def draw(self, painter: QPainter) -> None:
        if self.view.tool is not None or not self.view.writable:
            return
        painter.save()
        pen = QPen(QColor("#0067C0"), 1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(QColor("white"))
        size = 3 / self.view.zoom
        for name, p in self.handles().items():
            if name == "rotate":
                painter.drawEllipse(p, size, size)
            else:
                painter.drawRect(QRectF(p.x() - size, p.y() - size, 2 * size, 2 * size))
        if self.active and self.active.preview:
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            for a, b in zip(self.active.preview, self.active.preview[1:], strict=False):
                painter.drawLine(a, b)
        painter.restore()
