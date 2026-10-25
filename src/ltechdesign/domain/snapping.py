"""Qt-free, deterministic screen-tolerance snapping in logical world coordinates."""

import bisect
import math
from dataclasses import dataclass
from typing import Literal

from .editing import roots
from .errors import fail
from .geometry import Bounds, finite, primitive_bounds, world_matrix
from .models import Document, NodeId, Point

Axis = Literal["x", "y"]
AXES: tuple[Axis, Axis] = ("x", "y")


def tolerance(pixels: float, zoom: float, dpr: float) -> float:
    """Physical screen pixels -> scene logical px; Qt event coordinates are DIPs."""
    finite(pixels, zoom, dpr)
    if pixels < 0 or zoom <= 0 or dpr <= 0:
        fail("invalid_screen_tolerance")
    return pixels / zoom / dpr


def editable(document: Document, key: NodeId) -> bool:
    while True:
        node = document.nodes[key]
        if not node.visible or node.locked:
            return False
        if node.parent_id is None:
            return True
        key = node.parent_id


def geometry(document: Document, key: NodeId) -> Bounds:
    return primitive_bounds(document.nodes[key], world_matrix(document, key))


def anchors(bounds: Bounds, axis: Axis) -> tuple[float, ...]:
    lo, hi = (bounds.min_x, bounds.max_x) if axis == "x" else (bounds.min_y, bounds.max_y)
    return tuple(dict.fromkeys((lo, (lo + hi) / 2, hi)))


@dataclass(frozen=True, slots=True)
class Target:
    coordinate: float
    key: NodeId
    bounds: Bounds


@dataclass(frozen=True, slots=True)
class Guide:
    axis: Axis
    coordinate: float
    start: float
    end: float
    kind: Literal["object", "grid"]


@dataclass(frozen=True, slots=True)
class Match:
    delta: float
    target: Target | None
    coordinate: float
    axis: Axis

    def guide(self, bounds: Bounds) -> Guide:
        other = self.target.bounds if self.target else bounds
        lo, hi = (
            (min(bounds.min_y, other.min_y), max(bounds.max_y, other.max_y))
            if self.axis == "x"
            else (min(bounds.min_x, other.min_x), max(bounds.max_x, other.max_x))
        )
        return Guide(self.axis, self.coordinate, lo, hi, "object" if self.target else "grid")


@dataclass(frozen=True, slots=True)
class SnapIndex:
    x: tuple[Target, ...] = ()
    y: tuple[Target, ...] = ()
    xs: tuple[float, ...] = ()
    ys: tuple[float, ...] = ()

    @classmethod
    def build(cls, document: Document, page: int, moving: tuple[NodeId, ...]) -> "SnapIndex":
        excluded: set[NodeId] = set()
        if moving:
            stack = list(roots(document, moving))
            while stack:
                key = stack.pop()
                excluded.add(key)
                stack.extend(document.nodes[key].children)
            for key in moving:
                parent = document.nodes[key].parent_id
                while parent is not None:
                    if document.nodes[parent].type == "group":
                        excluded.add(parent)  # derived geometry would attract its own children
                    parent = document.nodes[parent].parent_id
        targets: dict[Axis, list[Target]] = {"x": [], "y": []}
        for key, node in document.nodes.items():
            if (
                node.page_id != document.pages[page].id
                or key in excluded
                or not editable(document, key)
            ):
                continue
            bound: Bounds | None = geometry(document, key)
            parent = node.parent_id
            while parent is not None and bound is not None:
                ancestor = document.nodes[parent]
                if ancestor.clip_content:
                    bound = bound.intersect(geometry(document, parent))
                parent = ancestor.parent_id
            if bound is None:
                continue
            for axis in AXES:
                targets[axis].extend(Target(v, key, bound) for v in anchors(bound, axis))
        x, y = (tuple(sorted(targets[a], key=lambda t: (t.coordinate, t.key))) for a in AXES)
        return cls(x, y, tuple(t.coordinate for t in x), tuple(t.coordinate for t in y))

    def nearest(
        self,
        coordinate: float,
        axis: Axis,
        distance: float,
        *,
        objects: bool,
        grid: bool,
        spacing: float,
    ) -> Match | None:
        finite(coordinate, distance, spacing)
        if distance < 0 or spacing <= 0:
            fail("invalid_snap_settings")
        candidates: list[Match] = []
        if objects:
            targets, values = (self.x, self.xs) if axis == "x" else (self.y, self.ys)
            index = bisect.bisect_left(values, coordinate)
            # Only the two neighboring coordinates can be nearest. Equal-coordinate
            # targets always use stable ID order, independent of layer z-order.
            for i in (index - 1, index):
                if 0 <= i < len(targets):
                    t = targets[bisect.bisect_left(values, values[i])]
                    candidates.append(Match(t.coordinate - coordinate, t, t.coordinate, axis))
        if grid:
            v = math.floor(coordinate / spacing + 0.5) * spacing
            candidates.append(Match(v - coordinate, None, v, axis))
        candidates = [m for m in candidates if abs(m.delta) <= distance]
        return (
            min(
                candidates,
                key=lambda m: (
                    abs(m.delta),
                    m.target is None,
                    m.coordinate,
                    m.target.key if m.target else "",
                ),
            )
            if candidates
            else None
        )

    def translation(
        self,
        bounds: Bounds,
        delta: Point,
        distance: float,
        *,
        objects: bool,
        grid: bool,
        spacing: float,
        axis_only: Axis | None = None,
    ) -> tuple[Point, tuple[Guide, ...]]:
        moved = bounds.shifted(delta.x, delta.y)
        corrections = {"x": 0.0, "y": 0.0}
        matches: list[Match] = []
        for axis in AXES:
            if axis_only is not None and axis != axis_only:
                continue
            options = [
                m
                for v in anchors(moved, axis)
                if (
                    m := self.nearest(
                        v, axis, distance, objects=objects, grid=grid, spacing=spacing
                    )
                )
                is not None
            ]
            if options:
                match = min(options, key=lambda m: (abs(m.delta), m.target is None, m.coordinate))
                corrections[axis] = match.delta
                matches.append(match)
        corrected = Point(x=delta.x + corrections["x"], y=delta.y + corrections["y"])
        final = bounds.shifted(corrected.x, corrected.y)
        return corrected, tuple(m.guide(final) for m in matches)

    def along(
        self,
        origin: Point,
        vector: Point,
        factor: float,
        minimum: float,
        distance: float,
        *,
        objects: bool,
        grid: bool,
        spacing: float,
    ) -> tuple[float, tuple[Guide, ...]]:
        """Snap a constrained resize handle without breaking its anchor/aspect ratio."""
        length = math.hypot(vector.x, vector.y)
        if length == 0:
            return factor, ()
        choices: list[tuple[float, float, Match]] = []
        directions: tuple[tuple[Axis, float, float], ...] = (
            ("x", origin.x, vector.x),
            ("y", origin.y, vector.y),
        )
        for axis, start, direction in directions:
            if abs(direction) < 1e-12 * length:
                continue
            match = self.nearest(
                start + direction * factor,
                axis,
                distance,
                objects=objects,
                grid=grid,
                spacing=spacing,
            )
            if match:
                changed = factor + match.delta / direction
                displacement = abs(changed - factor) * length
                if changed >= minimum and displacement <= distance:
                    choices.append((displacement, changed, match))
        if not choices:
            return factor, ()
        _, result, match = min(choices, key=lambda c: (c[0], c[2].target is None, c[2].axis))
        p = Point(x=origin.x + vector.x * result, y=origin.y + vector.y * result)
        return result, (match.guide(Bounds(p.x, p.y, p.x, p.y)),)
