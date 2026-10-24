"""Pure create intents; dimensions remain logical pixels in the document."""

import math
from dataclasses import dataclass, replace
from typing import Literal

from .errors import fail
from .geometry import finite
from .models import (
    Fill,
    FrameData,
    LineData,
    Node,
    NodeData,
    NodeId,
    NodeType,
    PageId,
    Point,
    PolygonData,
    Stroke,
    Style,
    create_node,
)

Unit = Literal["px", "mm", "cm", "in"]


@dataclass(frozen=True, slots=True)
class ArtboardPreset:
    name: str
    width: float
    height: float
    unit: Unit = "px"
    dpi: float = 96


ARTBOARD_PRESETS = (
    ArtboardPreset("Web desktop 1440 × 900", 1440, 900),
    ArtboardPreset("Web desktop 1920 × 1080", 1920, 1080),
    ArtboardPreset("Tablet 768 × 1024", 768, 1024),
    ArtboardPreset("Mobile UI 390 × 844", 390, 844),
    ArtboardPreset("Mobile UI 430 × 932", 430, 932),
    ArtboardPreset("Instagram Portrait 1080 × 1350", 1080, 1350),
    ArtboardPreset("Instagram Square 1080 × 1080", 1080, 1080),
    ArtboardPreset("Story / Reels / TikTok 1080 × 1920", 1080, 1920),
    ArtboardPreset("Presentasi 1920 × 1080", 1920, 1080),
    ArtboardPreset("A4 210 × 297 mm", 210, 297, "mm", 300),
    ArtboardPreset("A3 297 × 420 mm", 297, 420, "mm", 300),
)


def artboard_node(
    page_id: PageId,
    *,
    name: str,
    width: float,
    height: float,
    unit: Unit = "px",
    dpi: float = 96,
    landscape: bool | None = None,
    origin: Point | None = None,
    background: str = "#FFFFFFFF",
) -> Node:
    finite(width, height, dpi)
    origin = origin or Point()
    data = FrameData(unit=unit, dpi=dpi, background=background)
    if width <= 0 or height <= 0:
        fail("invalid_dimensions")
    if landscape is not None and (width > height) != landscape:
        width, height = height, width
    factor = {"px": 1.0, "mm": dpi / 25.4, "cm": dpi / 2.54, "in": dpi}[unit]
    return replace(
        create_node("artboard", page_id, width=width * factor, height=height * factor, data=data),
        name=name,
        x=origin.x,
        y=origin.y,
    )


def drawn_node(
    kind: NodeType,
    page_id: PageId,
    start: Point,
    end: Point,
    *,
    parent_id: NodeId | None = None,
    sides: int = 5,
    node_id: NodeId | None = None,
) -> Node:
    """Endpoints are already in parent space, never scene bounds or device pixels."""
    if kind not in ("frame", "rectangle", "ellipse", "line", "polygon"):
        fail("unsupported_drawing_tool")
    x, y = min(start.x, end.x), min(start.y, end.y)
    width, height = abs(end.x - start.x), abs(end.y - start.y)
    data: NodeData | None = None
    style = Style(fill=Fill(color="#80B8E8FF"))
    if kind == "line":
        data = LineData(
            start=Point(x=start.x - x, y=start.y - y),
            end=Point(x=end.x - x, y=end.y - y),
        )
        style = Style(stroke=Stroke(color="#243746FF", width=2))
    elif kind == "polygon":
        if type(sides) is not int or not 3 <= sides <= 64:
            fail("invalid_polygon_sides")
        raw = [
            (
                math.cos(-math.pi / 2 + i * math.tau / sides),
                math.sin(-math.pi / 2 + i * math.tau / sides),
            )
            for i in range(sides)
        ]
        left, right = min(p[0] for p in raw), max(p[0] for p in raw)
        top, bottom = min(p[1] for p in raw), max(p[1] for p in raw)
        data = PolygonData(
            points=tuple(
                Point(
                    x=width if a == right else (a - left) / (right - left) * width,
                    y=height if b == bottom else (b - top) / (bottom - top) * height,
                )
                for a, b in raw
            )
        )
    elif kind == "frame":
        style = Style(stroke=Stroke(color="#526778FF"))
    return replace(
        create_node(kind, page_id, width=width, height=height, data=data, node_id=node_id),
        name=kind.title(),
        x=x,
        y=y,
        parent_id=parent_id,
        style=style,
    )
