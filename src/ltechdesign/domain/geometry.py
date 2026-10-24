"""Similarity transforms and conservative bounds, in logical pixels.

Geometry is independent of visibility/effects. Visual bounds are conservative
AABBs, not exact painted pixels (rounded clips, glyph ink and raster decoding
belong to the shared renderer). Hit bounds add physical screen-pixel tolerance.
"""

import math
from dataclasses import dataclass, replace

from .errors import fail
from .models import Document, LineData, Node, NodeId, Point, PolygonData

ABS_TOL = 1e-9
REL_TOL = 1e-12


def close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def finite(*numbers: float) -> None:
    if any(type(n) not in (int, float) for n in numbers):
        fail("invalid_type", expected="number")
    try:
        valid = all(math.isfinite(n) for n in numbers)
    except OverflowError:
        valid = False
    if not valid:
        fail("nonfinite_number")


@dataclass(frozen=True, slots=True)
class Matrix:
    """Column-vector affine matrix [a c tx; b d ty; 0 0 1]."""

    a: float = 1
    b: float = 0
    c: float = 0
    d: float = 1
    tx: float = 0
    ty: float = 0

    def __post_init__(self) -> None:
        finite(self.a, self.b, self.c, self.d, self.tx, self.ty)

    def __matmul__(self, other: "Matrix") -> "Matrix":
        return Matrix(
            self.a * other.a + self.c * other.b,
            self.b * other.a + self.d * other.b,
            self.a * other.c + self.c * other.d,
            self.b * other.c + self.d * other.d,
            self.a * other.tx + self.c * other.ty + self.tx,
            self.b * other.tx + self.d * other.ty + self.ty,
        )

    def point(self, point: Point) -> Point:
        return Point(
            x=self.a * point.x + self.c * point.y + self.tx,
            y=self.b * point.x + self.d * point.y + self.ty,
        )

    def similarity_scale(self) -> float:
        scale = math.hypot(self.a, self.b)
        finite(scale)
        # Relative residuals: very small transforms must not admit tiny shear/flip.
        if (
            scale <= 0
            or not math.isclose(self.d / scale, self.a / scale, abs_tol=REL_TOL, rel_tol=REL_TOL)
            or not math.isclose(self.c / scale, -self.b / scale, abs_tol=REL_TOL, rel_tol=REL_TOL)
        ):
            fail("unsupported_transform", code="unsupported_capability")
        return scale

    def inverse(self) -> "Matrix":
        scale = self.similarity_scale()
        a, b, c, d = (
            self.d / scale / scale,
            -self.b / scale / scale,
            -self.c / scale / scale,
            self.a / scale / scale,
        )
        return Matrix(a, b, c, d, -(a * self.tx + c * self.ty), -(b * self.tx + d * self.ty))


def translation(x: float, y: float) -> Matrix:
    return Matrix(tx=x, ty=y)


def local_matrix(node: Node) -> Matrix:
    angle = math.radians(node.rotation % 360)
    a, b = math.cos(angle) * node.scale, math.sin(angle) * node.scale
    p = node.pivot
    return Matrix(a, b, -b, a, node.x + p.x - a * p.x + b * p.y, node.y + p.y - b * p.x - a * p.y)


def world_matrix(document: Document, node_id: NodeId) -> Matrix:
    if node_id not in document.nodes:
        fail("missing_node", node_id=node_id)
    chain = []
    node: Node | None = document.nodes[node_id]
    while node is not None:
        chain.append(node)
        node = document.nodes[node.parent_id] if node.parent_id is not None else None
    result = Matrix()
    for ancestor in reversed(chain):
        result = result @ local_matrix(ancestor)
    return result


def with_matrix(node: Node, matrix: Matrix, *, pivot: Point | None = None) -> Node:
    """Represent a positive similarity with an explicit local pivot; reject affine loss."""
    scale = matrix.similarity_scale()
    p = node.pivot if pivot is None else pivot
    return replace(
        node,
        x=matrix.tx - p.x + matrix.a * p.x + matrix.c * p.y,
        y=matrix.ty - p.y + matrix.b * p.x + matrix.d * p.y,
        rotation=math.degrees(math.atan2(matrix.b, matrix.a)),
        scale=scale,
        pivot=p,
    )


def relative_node(node: Node, old_parent_world: Matrix, new_parent_world: Matrix) -> Node:
    """Pure transform plan; the dispatcher will update hierarchy atomically in segment 03."""
    return with_matrix(node, new_parent_world.inverse() @ old_parent_world @ local_matrix(node))


def scale_group(node: Node, factor_x: float, factor_y: float | None = None) -> Node:
    finite(factor_x)
    if factor_y is not None:
        finite(factor_y)
    if node.type != "group" or (node.width == 0 and node.height == 0):
        fail("invalid_group_resize")
    if factor_x <= 0 or (factor_y is not None and factor_x != factor_y):
        fail("unsupported_transform", code="unsupported_capability")
    return replace(node, scale=node.scale * factor_x)


@dataclass(frozen=True, slots=True)
class Bounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def __post_init__(self) -> None:
        finite(*self.extents)
        if self.max_x < self.min_x or self.max_y < self.min_y:
            fail("invalid_bounds")

    @property
    def extents(self) -> tuple[float, float, float, float]:
        return self.min_x, self.min_y, self.max_x, self.max_y

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    def union(self, other: "Bounds") -> "Bounds":
        return Bounds(
            min(self.min_x, other.min_x),
            min(self.min_y, other.min_y),
            max(self.max_x, other.max_x),
            max(self.max_y, other.max_y),
        )

    def intersect(self, other: "Bounds") -> "Bounds | None":
        x, y = max(self.min_x, other.min_x), max(self.min_y, other.min_y)
        right, bottom = min(self.max_x, other.max_x), min(self.max_y, other.max_y)
        return Bounds(x, y, right, bottom) if right >= x and bottom >= y else None

    def inflate(self, amount: float) -> "Bounds":
        finite(amount)
        if amount < 0:
            fail("out_of_range")
        return Bounds(
            self.min_x - amount, self.min_y - amount, self.max_x + amount, self.max_y + amount
        )

    def shifted(self, x: float, y: float) -> "Bounds":
        return Bounds(self.min_x + x, self.min_y + y, self.max_x + x, self.max_y + y)


def points_bounds(points: tuple[Point, ...]) -> Bounds:
    if not points:
        fail("empty_geometry")
    return Bounds(
        min(p.x for p in points),
        min(p.y for p in points),
        max(p.x for p in points),
        max(p.y for p in points),
    )


IDENTITY = Matrix()


def primitive_bounds(node: Node, matrix: Matrix = IDENTITY) -> Bounds:
    points: tuple[Point, ...]
    if isinstance(node.data, LineData):
        points = (node.data.start, node.data.end)
    elif isinstance(node.data, PolygonData):
        points = node.data.points
    elif node.type == "ellipse":
        center = matrix.point(Point(x=node.width / 2, y=node.height / 2))
        rx = math.hypot(matrix.a * node.width / 2, matrix.c * node.height / 2)
        ry = math.hypot(matrix.b * node.width / 2, matrix.d * node.height / 2)
        return Bounds(center.x - rx, center.y - ry, center.x + rx, center.y + ry)
    else:
        points = (
            Point(),
            Point(x=node.width),
            Point(x=node.width, y=node.height),
            Point(y=node.height),
        )
    return points_bounds(tuple(matrix.point(p) for p in points))


def subtree_geometry_bounds(
    document: Document, node_id: NodeId, matrix: Matrix = IDENTITY
) -> Bounds | None:
    """Union primitive subtree geometry in the supplied coordinate space, hidden included."""
    result: Bounds | None = None
    stack = [(node_id, matrix)]
    while stack:
        key, transform = stack.pop()
        node = document.nodes[key]
        if node.type != "group" or not node.children:
            current = primitive_bounds(node, transform)
            result = current if result is None else result.union(current)
        stack.extend(
            (child, transform @ local_matrix(document.nodes[child])) for child in node.children
        )
    return result


def normalize_group(
    group: Node, children: tuple[Node, ...], bounds: Bounds
) -> tuple[Node, tuple[Node, ...]]:
    """Normalize a staged group's subtree bounds, compensating every direct child."""
    if group.type != "group" or tuple(c.id for c in children) != group.children:
        fail("invalid_group_membership")
    origin = Point(x=bounds.min_x, y=bounds.min_y)
    new_pivot = Point(x=bounds.width / 2, y=bounds.height / 2)
    resized = replace(group, width=bounds.width, height=bounds.height, pivot=new_pivot)
    normalized = with_matrix(resized, local_matrix(group) @ translation(origin.x, origin.y))
    moved = tuple(
        with_matrix(child, translation(-origin.x, -origin.y) @ local_matrix(child))
        for child in children
    )
    return normalized, moved


def visual_bounds(document: Document, node_id: NodeId) -> Bounds | None:
    """Conservative world AABB, including effects and ancestor AABB clipping.

    Blur is a Gaussian sigma in local px; the finite support is 3 sigma. The
    renderer must use this same cutoff or provide its own tighter painted bounds.
    """

    def visit(key: NodeId, matrix: Matrix) -> Bounds | None:
        node = document.nodes[key]
        if not node.visible or node.opacity == 0:
            return None
        result: Bounds | None = None
        own = primitive_bounds(node, matrix)
        if node.type != "group":
            paints = (
                node.style.fill is not None
                or node.style.stroke is not None
                or node.type in ("image", "svg")
                or getattr(node.data, "background", None) is not None
            )
            if paints:
                result = own
                if node.style.stroke:
                    result = result.inflate(node.style.stroke.width / 2 * matrix.similarity_scale())
        for child in node.children:
            child_bounds = visit(child, matrix @ local_matrix(document.nodes[child]))
            if child_bounds is not None and node.clip_content:
                child_bounds = child_bounds.intersect(own)
            if child_bounds is not None:
                result = child_bounds if result is None else result.union(child_bounds)
        if result is not None:
            source = result
            for shadow in node.style.shadows:
                dx = matrix.a * shadow.offset_x + matrix.c * shadow.offset_y
                dy = matrix.b * shadow.offset_x + matrix.d * shadow.offset_y
                spread = (shadow.spread + 3 * shadow.blur) * matrix.similarity_scale()
                result = result.union(source.inflate(spread).shifted(dx, dy))
        return result

    result = visit(node_id, world_matrix(document, node_id))
    parent = document.nodes[node_id].parent_id
    while parent is not None and result is not None:
        node = document.nodes[parent]
        if not node.visible or node.opacity == 0:
            return None
        if node.clip_content:
            result = result.intersect(primitive_bounds(node, world_matrix(document, parent)))
        parent = node.parent_id
    return result


def hit_test_bounds(
    document: Document,
    node_id: NodeId,
    *,
    tolerance_px: float = 4,
    zoom: float = 1,
    dpr: float = 1,
) -> Bounds | None:
    finite(tolerance_px, zoom, dpr)
    if tolerance_px < 0 or zoom <= 0 or dpr <= 0:
        fail("out_of_range")
    bounds = visual_bounds(document, node_id)
    return bounds.inflate(tolerance_px / zoom / dpr) if bounds is not None else None
