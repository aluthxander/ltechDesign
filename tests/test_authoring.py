import math

import pytest

from ltechdesign.domain import ModelError
from ltechdesign.domain.authoring import ARTBOARD_PRESETS, Unit, artboard_node, drawn_node
from ltechdesign.domain.models import FrameData, LineData, PageId, Point, PolygonData

pytestmark = pytest.mark.core
PAGE = PageId("page")


@pytest.mark.parametrize("index", range(len(ARTBOARD_PRESETS)))
def test_presets_and_orientation(index: int) -> None:
    p = ARTBOARD_PRESETS[index]
    node = artboard_node(PAGE, name=p.name, width=p.width, height=p.height, unit=p.unit, dpi=p.dpi)
    factor = p.dpi / 25.4 if p.unit == "mm" else 1
    assert node.width == pytest.approx(p.width * factor)
    assert node.height == pytest.approx(p.height * factor)
    assert node.clip_content and node.parent_id is None
    assert node.data == FrameData(unit=p.unit, dpi=p.dpi, background="#FFFFFFFF")
    landscape = artboard_node(
        PAGE, name=p.name, width=p.width, height=p.height, unit=p.unit, dpi=p.dpi, landscape=True
    )
    assert landscape.width >= landscape.height


@pytest.mark.parametrize("unit,size", [("px", 300), ("mm", 25.4), ("cm", 2.54), ("in", 1)])
def test_physical_dimensions(unit: Unit, size: float) -> None:
    a = artboard_node(PAGE, name="Custom", width=size, height=size * 2, unit=unit, dpi=300)
    assert (a.width, a.height) == pytest.approx((300, 600))


@pytest.mark.parametrize("value", [0, -1, math.nan, math.inf])
def test_invalid_artboard_dimensions(value: float) -> None:
    with pytest.raises(ModelError):
        artboard_node(PAGE, name="Invalid", width=value, height=100)
    with pytest.raises(ModelError):
        artboard_node(PAGE, name="Invalid DPI", width=100, height=100, dpi=value)


def test_reverse_line_and_polygon_canonical_geometry() -> None:
    line = drawn_node("line", PAGE, Point(x=90, y=10), Point(x=10, y=80))
    assert (line.x, line.y, line.width, line.height) == (10, 10, 80, 70)
    assert line.data == LineData(start=Point(x=80), end=Point(y=70))
    for sides in (3, 5, 6, 64):
        p = drawn_node("polygon", PAGE, Point(x=90, y=80), Point(x=10, y=10), sides=sides)
        assert isinstance(p.data, PolygonData) and len(p.data.points) == sides
        assert min(v.x for v in p.data.points) == min(v.y for v in p.data.points) == 0
        assert max(v.x for v in p.data.points) == 80
        assert max(v.y for v in p.data.points) == 70
