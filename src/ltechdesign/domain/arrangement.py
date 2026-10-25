"""World geometry alignment/distribution, independent of Qt and z-order."""

from typing import Literal

from .editing import roots
from .errors import fail
from .models import Document, NodeId, Point
from .snapping import editable, geometry

ArrangeMode = Literal[
    "left",
    "hcenter",
    "right",
    "top",
    "vcenter",
    "bottom",
    "distribute_x",
    "distribute_y",
]


def translations(
    document: Document,
    selected: tuple[NodeId, ...],
    mode: ArrangeMode,
) -> tuple[tuple[NodeId, Point], ...]:
    keys = roots(document, selected)
    distribution = mode in ("distribute_x", "distribute_y")
    if len(keys) < (3 if distribution else 2):
        fail("arrangement_selection_too_small")
    if len({document.nodes[k].page_id for k in keys}) != 1:
        fail("arrangement_requires_one_page")
    if any(not editable(document, k) for k in selected):
        fail("arrangement_target_hidden_or_locked")
    bounds = {k: geometry(document, k) for k in keys}
    union = bounds[keys[0]]
    for bound in bounds.values():
        union = union.union(bound)
    if distribution:
        horizontal = mode == "distribute_x"
        ordered = sorted(
            keys,
            key=lambda k: (
                bounds[k].min_x if horizontal else bounds[k].min_y,
                k,
            ),
        )
        first, last = bounds[ordered[0]], bounds[ordered[-1]]
        start = first.min_x if horizontal else first.min_y
        end = last.max_x if horizontal else last.max_y
        extents = {k: bounds[k].width if horizontal else bounds[k].height for k in keys}
        gap = (end - start - sum(extents.values())) / (len(keys) - 1)
        cursor = start
        result = []
        for key in ordered:
            delta = cursor - (bounds[key].min_x if horizontal else bounds[key].min_y)
            result.append((key, Point(x=delta) if horizontal else Point(y=delta)))
            cursor += extents[key] + gap
        return tuple(result)
    result = []
    for key in keys:
        b = bounds[key]
        dx = {
            "left": union.min_x - b.min_x,
            "hcenter": (union.min_x + union.max_x - b.min_x - b.max_x) / 2,
            "right": union.max_x - b.max_x,
        }.get(mode, 0)
        dy = {
            "top": union.min_y - b.min_y,
            "vcenter": (union.min_y + union.max_y - b.min_y - b.max_y) / 2,
            "bottom": union.max_y - b.max_y,
        }.get(mode, 0)
        result.append((key, Point(x=dx, y=dy)))
    return tuple(result)
