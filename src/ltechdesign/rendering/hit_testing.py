"""Screen-tolerant paths share geometry, transforms and clipping with drawing."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainterPath, QPainterPathStroker

from ltechdesign.domain.geometry import world_matrix
from ltechdesign.domain.models import Document, NodeId

from .drawing import path, transform


def paint_order(document: Document, page: int) -> tuple[NodeId, ...]:
    keys: list[NodeId] = []

    def visit(key: NodeId) -> None:
        keys.append(key)
        for child in document.nodes[key].children:
            visit(child)

    for root in document.pages[page].root_ids:
        visit(root)
    return tuple(keys)


def eligible(document: Document, key: NodeId) -> bool:
    while True:
        node = document.nodes[key]
        if not node.visible or node.locked:
            return False
        if node.parent_id is None:
            return True
        key = node.parent_id


def clipped_path(document: Document, key: NodeId, tolerance: float = 0) -> QPainterPath:
    node = document.nodes[key]
    matrix = world_matrix(document, key)
    shape = transform(matrix).map(path(node))
    width = node.style.stroke.width * matrix.similarity_scale() if node.style.stroke else 0
    if width or tolerance or node.type == "line":
        stroker = QPainterPathStroker()
        stroker.setWidth(max(1e-6, width + 2 * tolerance))
        stroker.setCapStyle(Qt.PenCapStyle.SquareCap)
        stroker.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        stroker.setMiterLimit(2)
        shape = shape.united(stroker.createStroke(shape))
    parent = node.parent_id
    while parent is not None:
        ancestor = document.nodes[parent]
        if ancestor.clip_content:
            clip = transform(world_matrix(document, parent)).map(path(ancestor))
            shape = shape.intersected(clip)
        parent = ancestor.parent_id
    return shape


def hit_test(
    document: Document, page: int, point: QPointF, zoom: float, dpr: float = 1
) -> NodeId | None:
    return next(
        (
            key
            for key in reversed(paint_order(document, page))
            if eligible(document, key)
            and clipped_path(document, key, 4 / (zoom * dpr)).contains(point)
        ),
        None,
    )


def drawing_parent(document: Document, page: int, point: QPointF) -> NodeId | None:
    return next(
        (
            key
            for key in reversed(paint_order(document, page))
            if document.nodes[key].type in ("frame", "artboard")
            and eligible(document, key)
            and clipped_path(document, key).contains(point)
        ),
        None,
    )


def marquee_hits(document: Document, page: int, rect: QRectF) -> tuple[NodeId, ...]:
    return tuple(
        key
        for key in paint_order(document, page)
        if eligible(document, key)
        and not clipped_path(document, key).isEmpty()
        and rect.contains(clipped_path(document, key).boundingRect())
    )
