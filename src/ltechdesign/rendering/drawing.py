"""Shared traversal for canvas and offscreen targets. No scene or editor overlays."""

import math
from dataclasses import replace

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QTransform,
)

from ltechdesign.domain.errors import fail
from ltechdesign.domain.geometry import Matrix, local_matrix
from ltechdesign.domain.models import Document, FrameData, LineData, Node, NodeId, PolygonData

from .shadow import composite
from .text import Resources, draw_text


def transform(matrix: Matrix) -> QTransform:
    return QTransform(matrix.a, matrix.b, matrix.c, matrix.d, matrix.tx, matrix.ty)


def color(value: str) -> QColor:
    return QColor(
        int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16), int(value[7:9], 16)
    )


def path(node: Node) -> QPainterPath:
    result = QPainterPath()
    w, h = node.width, node.height
    if node.type == "ellipse":
        result.addEllipse(QRectF(0, 0, w, h))
    elif isinstance(node.data, LineData):
        result.moveTo(node.data.start.x, node.data.start.y)
        result.lineTo(node.data.end.x, node.data.end.y)
    elif isinstance(node.data, PolygonData):
        result.moveTo(node.data.points[0].x, node.data.points[0].y)
        for point in node.data.points[1:]:
            result.lineTo(point.x, point.y)
        result.closeSubpath()
    else:
        a, b, c, d = node.style.radius
        factor = min(
            [1]
            + [
                limit / total
                for limit, total in ((w, a + b), (w, c + d), (h, a + d), (h, b + c))
                if total > 0
            ],
        )
        a, b, c, d = (r * factor for r in (a, b, c, d))
        k = 0.5522847498307936
        result.moveTo(a, 0)
        result.lineTo(w - b, 0)
        result.cubicTo(w - b + k * b, 0, w, b - k * b, w, b)
        result.lineTo(w, h - c)
        result.cubicTo(w, h - c + k * c, w - c + k * c, h, w - c, h)
        result.lineTo(d, h)
        result.cubicTo(d - k * d, h, 0, h - d + k * d, 0, h - d)
        result.lineTo(0, a)
        result.cubicTo(0, a - k * a, a - k * a, 0, a, 0)
        result.closeSubpath()
    return result


def local_visual(document: Document, key: NodeId) -> QRectF:
    """Conservative local visual bounds, separate from primitive geometry/hit bounds."""
    node = document.nodes[key]
    if not node.visible or node.opacity == 0:
        return QRectF()
    result = path(node).boundingRect() if node.type != "group" else QRectF()
    if node.style.stroke and node.type != "group":
        stroker = QPainterPathStroker()
        stroker.setWidth(node.style.stroke.width)
        stroker.setCapStyle(Qt.PenCapStyle.SquareCap)
        stroker.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        stroker.setMiterLimit(2)
        result = result.united(stroker.createStroke(path(node)).boundingRect())
    for child in node.children:
        bounds = transform(local_matrix(document.nodes[child])).mapRect(
            local_visual(document, child)
        )
        if node.clip_content:
            bounds = bounds.intersected(path(node).boundingRect())
        result = result.united(bounds)
    if result.isEmpty():
        return result
    source = result
    for shadow in node.style.shadows:
        pad = shadow.spread + 3 * shadow.blur
        result = result.united(
            source.adjusted(-pad, -pad, pad, pad).translated(shadow.offset_x, shadow.offset_y)
        )
    return result


def warnings(document: Document, resources: Resources | None = None) -> tuple[str, ...]:
    result = set()
    if any(
        n.type in ("image", "svg") or (n.type == "text" and resources is None)
        for n in document.nodes.values()
    ):
        result.add("Text/image/SVG belum dirender; canvas menampilkan placeholder.")
    return tuple(sorted(result))


def draw_node(
    painter: QPainter,
    document: Document,
    key: NodeId,
    *,
    local: bool = False,
    budget: list[int] | None = None,
    resources: Resources | None = None,
) -> None:
    budget = [0] if budget is None else budget
    node = document.nodes[key]
    if not node.visible or node.opacity == 0:
        return
    painter.save()
    try:
        if not local:
            painter.setWorldTransform(transform(local_matrix(node)), True)
        if node.opacity != 1 or node.style.shadows:
            # Composite ONCE. Never use inherited QGraphicsItem opacity on children.
            matrix = painter.deviceTransform()
            device_bounds = matrix.mapRect(local_visual(document, key)).adjusted(-1, -1, 1, 1)
            if any(
                not math.isfinite(v) or abs(v) > 1_000_000_000
                for v in (
                    device_bounds.x(),
                    device_bounds.y(),
                    device_bounds.width(),
                    device_bounds.height(),
                )
            ):
                fail("isolation_bounds", code="limit_exceeded")
            rect = device_bounds.toAlignedRect()
            width, height = rect.width(), rect.height()
            if width <= 0 or height <= 0:
                return
            pixels = width * height * (6 if node.style.shadows else 1)
            if budget[0] + pixels > 64_000_000:
                fail("isolation_pixels", code="limit_exceeded")
            image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
            if image.isNull():
                fail("isolation_allocation", code="limit_exceeded")
            image.fill(Qt.GlobalColor.transparent)
            layer = QPainter(image)
            budget[0] += pixels
            try:
                layer.setRenderHint(QPainter.RenderHint.Antialiasing)
                layer.translate(-rect.x(), -rect.y())
                layer.setWorldTransform(matrix, True)
                draw_body(layer, document, key, budget, resources)
            finally:
                layer.end()
                budget[0] -= pixels
            if node.style.shadows:
                image = composite(image, node, matrix)
            painter.setOpacity(painter.opacity() * node.opacity)
            # Composite a device-aligned buffer, so PDF never resamples a rotated
            # image/soft-mask pair differently from canvas and PNG.
            painter.resetTransform()
            base_inverse, invertible = painter.deviceTransform().inverted()
            if not invertible:
                fail("singular_device_transform")
            painter.setWorldTransform(base_inverse)
            painter.drawImage(QPointF(rect.x(), rect.y()), image)
        else:
            draw_body(painter, document, key, budget, resources)
    finally:
        painter.restore()


def draw_body(
    painter: QPainter,
    document: Document,
    key: NodeId,
    budget: list[int],
    resources: Resources | None,
) -> None:
    node = resources.previews.get(key, document.nodes[key]) if resources else document.nodes[key]
    shape = path(node)
    if node.type == "text" and resources is not None:
        draw_text(painter, node, resources)
    elif node.type != "group":
        painter.setPen(Qt.PenStyle.NoPen)
        if isinstance(node.data, FrameData) and node.data.background:
            painter.fillPath(shape, color(node.data.background))
        if node.style.fill:
            painter.fillPath(shape, color(node.style.fill.color))
        if node.style.stroke:
            pen = QPen(color(node.style.stroke.color), node.style.stroke.width)
            pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
            pen.setMiterLimit(2)
            pen.setCapStyle(Qt.PenCapStyle.SquareCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(shape)
        if node.type in ("text", "image", "svg"):
            painter.setPen(QPen(QColor("#666666"), 1))
            painter.drawRect(QRectF(0, 0, node.width, node.height))
            painter.drawLine(QPointF(0, 0), QPointF(node.width, node.height))
    painter.save()
    try:
        if node.clip_content:
            painter.setClipPath(shape, Qt.ClipOperation.IntersectClip)
        for child in node.children:
            draw_node(painter, document, child, budget=budget, resources=resources)
    finally:
        painter.restore()


def render_image(
    document: Document,
    roots: tuple[NodeId, ...],
    bounds: QRectF,
    scale: float = 1,
    *,
    resources: Resources | None = None,
    notes: list[str] | None = None,
) -> QImage:
    """Strict offscreen contract for preview/export callers; no editor decorations."""
    if resources is not None and resources.previews:
        resources = replace(resources, previews={})
    if notes is not None and resources is not None:
        from .text import diagnostics

        notes.extend(diagnostics(document, resources))
    if warnings(document, resources):
        fail(
            "renderer_feature_unavailable",
            code="unsupported_capability",
            warnings=warnings(document, resources),
        )
    if not math.isfinite(scale) or scale <= 0 or bounds.isEmpty():
        fail("invalid_render_bounds")
    w, h = math.ceil(bounds.width() * scale), math.ceil(bounds.height() * scale)
    if w * h > 64_000_000:
        fail("render_pixels", code="limit_exceeded")
    image = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    if image.isNull():
        fail("render_allocation", code="limit_exceeded")
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(scale, scale)
        painter.translate(-bounds.x(), -bounds.y())
        for key in roots:
            draw_node(painter, document, key, budget=[w * h], resources=resources)
    finally:
        painter.end()
    return image
