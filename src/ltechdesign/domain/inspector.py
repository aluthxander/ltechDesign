"""Qt-free Inspector semantics. All returned nodes still require aggregate validation."""

import math
from dataclasses import replace
from typing import Literal

from .editing import MIN_SIZE, resized
from .errors import fail
from .models import Fill, FrameData, Node, Point, Shadow, Stroke

Property = Literal[
    "x",
    "y",
    "width",
    "height",
    "rotation",
    "opacity",
    "fill",
    "stroke",
    "stroke_width",
    "radius",
    "background",
    "shadow_enabled",
    "shadow_x",
    "shadow_y",
    "shadow_blur",
    "shadow_spread",
    "shadow_color",
]


def supported(node: Node, field: str) -> bool:
    if field == "background":
        return isinstance(node.data, FrameData)
    if field == "radius":
        return node.type in ("rectangle", "frame", "artboard")
    if field in ("fill", "stroke", "stroke_width"):
        return node.type != "group" and (field != "fill" or node.type != "line")
    return True


def value(node: Node, field: str) -> float | str | None:
    if field in ("width", "height"):
        return float(getattr(node, field)) * (node.scale if node.type == "group" else 1)
    if field in ("x", "y", "rotation", "opacity"):
        return float(getattr(node, field))
    if field in ("fill", "stroke"):
        paint = getattr(node.style, field)
        return paint.color if paint else None
    if field == "stroke_width":
        return node.style.stroke.width if node.style.stroke else 1.0
    if field == "radius":
        return node.style.radius[0] if len(set(node.style.radius)) == 1 else None
    if field == "background" and isinstance(node.data, FrameData):
        return node.data.background
    if field == "shadow_enabled":
        return float(bool(node.style.shadows))
    if field.startswith("shadow_"):
        shadow = node.style.shadows[0] if node.style.shadows else Shadow()
        key = {"shadow_x": "offset_x", "shadow_y": "offset_y"}.get(field, field[7:])
        return getattr(shadow, key)  # type: ignore[no-any-return]
    fail("unknown_inspector_field")


def inspected(node: Node, field: str, supplied: float | str | None) -> Node:
    if not supported(node, field):
        fail("property_not_supported", node_type=node.type, property=field)
    if field in ("fill", "stroke", "background", "shadow_color"):
        if supplied is not None and not isinstance(supplied, str):
            fail("color_required")
        if field == "background" and isinstance(node.data, FrameData):
            return replace(node, data=replace(node.data, background=supplied))
        if field in ("fill", "stroke"):
            if field == "fill":
                return replace(
                    node,
                    style=replace(
                        node.style,
                        fill=Fill(color=supplied) if supplied is not None else None,
                    ),
                )
            return replace(
                node,
                style=replace(
                    node.style,
                    stroke=Stroke(
                        color=supplied,
                        width=node.style.stroke.width if node.style.stroke else 1,
                    )
                    if supplied is not None
                    else None,
                ),
            )
        if supplied is None:
            fail("shadow_color_required")
        shadow = node.style.shadows[0] if node.style.shadows else Shadow()
        shadow = replace(shadow, color=supplied)
        return replace(node, style=replace(node.style, shadows=(shadow,) + node.style.shadows[1:]))
    if not isinstance(supplied, (int, float)) or isinstance(supplied, bool):
        fail("finite_number_required")
    if not math.isfinite(supplied):
        fail("finite_number_required")
    assert isinstance(supplied, (int, float))
    number = float(supplied)
    if field in ("x", "y", "rotation", "opacity"):
        return replace(
            node,
            x=number if field == "x" else node.x,
            y=number if field == "y" else node.y,
            rotation=number if field == "rotation" else node.rotation,
            opacity=number if field == "opacity" else node.opacity,
        )
    if field in ("width", "height"):
        if node.type == "line" and getattr(node, field) == 0 and number != 0:
            fail("line_zero_extent_resize")
        if number < MIN_SIZE and not (
            number == 0 and node.type == "line" and getattr(node, field) == 0
        ):
            fail("invalid_dimensions")
        if node.type == "group":
            extent = float(getattr(node, field))
            if extent <= 0:
                fail("empty_group_resize")
            return replace(node, scale=number / extent)
        return resized(
            node,
            number if field == "width" else node.width,
            number if field == "height" else node.height,
            Point(),
        )
    if field == "stroke_width":
        stroke = node.style.stroke or Stroke()
        return replace(node, style=replace(node.style, stroke=replace(stroke, width=number)))
    if field == "radius":
        return replace(node, style=replace(node.style, radius=(number,) * 4))
    if field == "shadow_enabled":
        if number not in (0, 1):
            fail("boolean_required")
        return replace(
            node,
            style=replace(
                node.style,
                shadows=(node.style.shadows or (Shadow(offset_y=4, blur=4),)) if number else (),
            ),
        )
    key = {
        "shadow_x": "offset_x",
        "shadow_y": "offset_y",
        "shadow_blur": "blur",
        "shadow_spread": "spread",
    }.get(field)
    if key is None:
        fail("unknown_inspector_field")
    shadow = node.style.shadows[0] if node.style.shadows else Shadow()
    shadow = replace(
        shadow,
        offset_x=number if key == "offset_x" else shadow.offset_x,
        offset_y=number if key == "offset_y" else shadow.offset_y,
        blur=number if key == "blur" else shadow.blur,
        spread=number if key == "spread" else shadow.spread,
    )
    return replace(node, style=replace(node.style, shadows=(shadow,) + node.style.shadows[1:]))
