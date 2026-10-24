"""Pure selection and anchor math shared by command planning and editor previews."""

import math
from collections.abc import Mapping
from dataclasses import replace

from .errors import fail
from .geometry import Matrix, local_matrix, translation, with_matrix
from .models import Document, LineData, Node, NodeId, Point, PolygonData

MIN_SIZE = 0.01


def roots(document: Document, keys: tuple[NodeId, ...]) -> tuple[NodeId, ...]:
    return selection_roots(document.nodes, keys)


def selection_roots(nodes: Mapping[NodeId, Node], keys: tuple[NodeId, ...]) -> tuple[NodeId, ...]:
    if not keys or len(set(keys)) != len(keys) or len(keys) > 10000:
        fail("invalid_selection")
    selected = set(keys)
    result = []
    for key in keys:
        if key not in nodes:
            fail("missing_node", node_id=key)
        parent = nodes[key].parent_id
        while parent is not None and parent not in selected:
            parent = nodes[parent].parent_id
        if parent is None:
            result.append(key)
    return tuple(result)


def around(center: Point, *, factor: float = 1, angle: float = 0) -> Matrix:
    if factor <= 0:
        fail("positive_scale_required")
    a = math.cos(math.radians(angle)) * factor
    b = math.sin(math.radians(angle)) * factor
    return translation(center.x, center.y) @ Matrix(a, b, -b, a) @ translation(-center.x, -center.y)


def resized(node: Node, width: float, height: float, anchor: Point) -> Node:
    """Geometry resize in local axes; fixed world anchor, no implicit child scaling."""
    if node.type == "group":
        fail("group_resize_requires_uniform_scale")
    if node.layout is not None or node.constraints is not None:
        fail("layout_evaluator_unavailable", code="unsupported_capability")
    if not 0 <= anchor.x <= 1 or not 0 <= anchor.y <= 1:
        fail("invalid_anchor")
    width, height = max(MIN_SIZE, width), max(MIN_SIZE, height)
    if node.type == "line":
        if node.width == 0:
            width = 0
        if node.height == 0:
            height = 0
    sx, sy = width / node.width if node.width else 1, height / node.height if node.height else 1
    data = node.data

    def scaled(p: Point) -> Point:
        return Point(
            x=width if p.x == node.width else p.x * sx, y=height if p.y == node.height else p.y * sy
        )

    if isinstance(data, LineData):
        data = LineData(start=scaled(data.start), end=scaled(data.end))
    elif isinstance(data, PolygonData):
        data = PolygonData(points=tuple(scaled(p) for p in data.points))
    offset = Point(x=anchor.x * (node.width - width), y=anchor.y * (node.height - height))
    changed = replace(
        node, width=width, height=height, pivot=Point(x=width / 2, y=height / 2), data=data
    )
    return with_matrix(changed, local_matrix(node) @ translation(offset.x, offset.y))
