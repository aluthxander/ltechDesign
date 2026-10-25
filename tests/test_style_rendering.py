import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image, ImageFilter
from PySide6.QtCore import QRectF, QSize
from PySide6.QtGui import QImage, QPainter
from PySide6.QtPdf import QPdfDocument
from pytestqt.qtbot import QtBot
from test_commands import engine, node, ok

from ltechdesign.commands import Create, Group, SetProperties, Update
from ltechdesign.domain import ModelError
from ltechdesign.domain.geometry import visual_bounds
from ltechdesign.domain.models import (
    Fill,
    LineData,
    NodeId,
    Point,
    PolygonData,
    Shadow,
    Stroke,
    Style,
)
from ltechdesign.rendering.canvas import CanvasView
from ltechdesign.rendering.drawing import local_visual, path, render_image
from ltechdesign.rendering.pdf import render_pdf
from ltechdesign.rendering.shadow import dilate

pytestmark = pytest.mark.desktop
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from render_compare import compare  # noqa: E402


def test_group_shadow_from_composited_alpha_and_opacity_once(qtbot: QtBot) -> None:
    d = engine()
    a = node(
        d,
        "a",
        x=20,
        y=20,
        width=60,
        height=40,
        pivot=Point(x=30, y=20),
        style=Style(fill=Fill(color="#FF0000FF")),
    )
    b = replace(a, id=NodeId("b"), x=50, style=Style(fill=Fill(color="#0000FFFF")))
    ok(d, Create(node=a), Create(node=b), Group(node_ids=(a.id, b.id), group_id=NodeId("g")))
    g = d.snapshot.project.document.nodes[NodeId("g")]
    ok(
        d,
        Update(
            node=replace(
                g, opacity=0.5, style=Style(shadows=(Shadow(offset_y=70, color="#00000080"),))
            )
        ),
    )
    doc = d.snapshot.project.document
    image = render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 150, 150))
    for x in (30, 60, 100):
        assert image.pixelColor(x, 30).alpha() == pytest.approx(128, abs=1)
        assert image.pixelColor(x, 100).alpha() == pytest.approx(64, abs=1)
    assert image.pixelColor(10, 100).alpha() == 0
    ok(d, SetProperties(node_ids=(g.id,), property="opacity", value=1))
    doc = d.snapshot.project.document
    full = render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 150, 150))
    assert full.pixelColor(60, 100).alpha() == pytest.approx(128, abs=1)
    ok(d, action="undo")
    assert (
        render_image(d.snapshot.project.document, doc.pages[0].root_ids, QRectF(0, 0, 150, 150))
        == image
    )


def test_blur_spread_tint_and_hidden_shadow_resource_limit(qtbot: QtBot) -> None:
    d = engine()
    a = node(
        d,
        "a",
        x=30,
        y=30,
        width=20,
        height=20,
        pivot=Point(x=10, y=10),
        style=Style(
            fill=Fill(), shadows=(Shadow(offset_x=35, blur=3, spread=2, color="#00FF00FF"),)
        ),
    )
    ok(d, Create(node=a))
    doc = d.snapshot.project.document
    image = render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 120, 100))
    assert image.pixelColor(75, 40).green() == 255
    assert 0 < image.pixelColor(88, 40).alpha() < image.pixelColor(82, 40).alpha()
    assert image.pixelColor(110, 40).alpha() == 0
    assert path(a).boundingRect() == QRectF(0, 0, 20, 20)
    vb = visual_bounds(doc, a.id)
    assert vb is not None and vb.max_x == 96
    huge = replace(a, style=replace(a.style, shadows=(Shadow(blur=10000),)))
    ok(d, Update(node=huge))
    with pytest.raises(ModelError, match="isolation_pixels"):
        doc = d.snapshot.project.document
        render_image(doc, doc.pages[0].root_ids, QRectF(0, 0, 1, 1))
    extreme = replace(a, style=replace(a.style, shadows=(Shadow(blur=1e100),)))
    ok(d, Update(node=extreme))
    with pytest.raises(ModelError, match="isolation_bounds"):
        render_image(d.snapshot.project.document, (a.id,), QRectF(0, 0, 1, 1))
    ok(d, Update(node=replace(huge, visible=False)))
    assert (
        render_image(d.snapshot.project.document, doc.pages[0].root_ids, QRectF(0, 0, 20, 20))
        .pixelColor(5, 5)
        .alpha()
        == 0
    )


def test_centered_stroke_radius_and_ancestor_clip_with_shadow(qtbot: QtBot) -> None:
    d = engine()
    frame = node(
        d,
        "frame",
        "frame",
        width=100,
        height=100,
        pivot=Point(x=50, y=50),
        clip_content=True,
        style=Style(radius=(30, 30, 30, 30)),
    )
    child = node(
        d,
        "child",
        parent_id=frame.id,
        x=1,
        y=1,
        width=98,
        height=98,
        pivot=Point(x=49, y=49),
        opacity=0.5,
        style=Style(
            fill=Fill(color="#FF0000FF"),
            stroke=Stroke(width=8),
            shadows=(Shadow(offset_x=10, offset_y=10, blur=5),),
        ),
    )
    ok(d, Create(node=frame), Create(node=child))
    doc = d.snapshot.project.document
    image = render_image(doc, doc.pages[0].root_ids, QRectF(-10, -10, 130, 130))
    assert image.pixelColor(11, 11).alpha() == 0
    assert image.pixelColor(115, 60).alpha() == 0  # shadow clipped by ancestor
    assert image.pixelColor(60, 60).alpha() == pytest.approx(128, abs=1)
    # Center alignment extends equally inside/outside a non-clipped primitive.
    leaf = replace(
        child,
        id=NodeId("leaf"),
        parent_id=None,
        x=0,
        y=0,
        opacity=1,
        style=Style(stroke=Stroke(color="#00FF00FF", width=8)),
    )
    ok(d, Create(node=leaf))
    doc = d.snapshot.project.document
    stroke = render_image(doc, (leaf.id,), QRectF(-10, -10, 120, 120))
    assert stroke.pixelColor(7, 50).green() == 255  # x=-3 outside
    assert stroke.pixelColor(12, 50).green() == 255  # x=2 inside
    assert stroke.pixelColor(5, 50).alpha() == 0
    assert stroke.pixelColor(15, 50).alpha() == 0


def test_multi_shadows_bounds_are_union_not_cumulative(qtbot: QtBot) -> None:
    d = engine()
    a = node(
        d,
        "a",
        style=Style(
            fill=Fill(),
            shadows=(
                Shadow(offset_x=20),
                Shadow(offset_x=-20),
            ),
        ),
    )
    ok(d, Create(node=a))
    bounds = local_visual(d.snapshot.project.document, a.id)
    assert bounds == QRectF(-20, 0, 140, 100)


@pytest.mark.parametrize("kind", ["rectangle", "polygon", "line"])
def test_thick_centered_stroke_bounds_prevent_isolation_or_selection_crop(
    qtbot: QtBot,
    kind: str,
) -> None:
    d = engine()
    kwargs: dict[str, object] = {}
    if kind == "polygon":
        kwargs["data"] = PolygonData(points=(Point(), Point(x=100), Point(x=2, y=100)))
    elif kind == "line":
        kwargs["data"] = LineData(start=Point(), end=Point(x=100, y=100))
    a = node(
        d,
        "a",
        kind,
        x=60,
        y=70,
        rotation=37,
        **kwargs,
        style=Style(stroke=Stroke(color="#1188CCFF", width=30)),
    )
    ok(d, Create(node=a))
    doc = d.snapshot.project.document
    bounds = QRectF(-50, -50, 350, 350)
    full = render_image(doc, (a.id,), bounds)
    ok(d, Update(node=replace(a, opacity=0.5)))
    faded = render_image(d.snapshot.project.document, (a.id,), bounds)
    world = visual_bounds(doc, a.id)
    assert world is not None
    view_bounds = QRectF(world.min_x, world.min_y, world.width, world.height)
    for y in range(full.height()):
        for x in range(full.width()):
            alpha = full.pixelColor(x, y).alpha()
            if alpha:
                assert faded.pixelColor(x, y).alpha() == pytest.approx(alpha / 2, abs=1)
                assert view_bounds.adjusted(-1, -1, 1, 1).contains(x + bounds.x(), y + bounds.y())


def test_empty_group_shadow_does_not_allocate_effect_surface(qtbot: QtBot) -> None:
    d = engine()
    empty = node(d, "empty", "group", style=Style(shadows=(Shadow(blur=10000),)))
    ok(d, Create(node=empty))
    doc = d.snapshot.project.document
    assert local_visual(doc, empty.id).isEmpty()
    assert render_image(doc, (empty.id,), QRectF(0, 0, 20, 20)).pixelColor(10, 10).alpha() == 0


def test_native_dilation_matches_max_filter(qtbot: QtBot) -> None:
    mask = Image.new("L", (33, 25))
    mask.putpixel((13, 10), 255)
    mask.putpixel((0, 0), 120)
    for radius in (1, 2, 3, 5, 8):
        actual = dilate(dilate(mask, radius, False), radius, True)
        assert actual.tobytes() == mask.filter(ImageFilter.MaxFilter(2 * radius + 1)).tobytes()


def test_shadow_shared_scene_png_pdf_nested_transform_evidence(
    qtbot: QtBot,
    tmp_path: Path,
) -> None:
    d = engine()
    parent = node(
        d,
        "parent",
        "frame",
        x=70,
        y=50,
        width=160,
        height=130,
        pivot=Point(x=80, y=65),
        rotation=17,
        scale=1.1,
        style=Style(fill=Fill(color="#F8F4EEFF"), radius=(20, 20, 20, 20)),
    )
    child = node(
        d,
        "child",
        parent_id=parent.id,
        x=30,
        y=25,
        width=75,
        height=60,
        pivot=Point(x=37.5, y=30),
        rotation=-29,
        style=Style(
            fill=Fill(color="#2882D2FF"),
            stroke=Stroke(width=5),
            radius=(10, 18, 10, 18),
            shadows=(Shadow(offset_x=12, offset_y=10, blur=4, spread=2),),
        ),
    )
    ok(d, Create(node=parent), Create(node=child))
    doc = d.snapshot.project.document
    bounds = QRectF(0, 0, 336, 256)
    expected = render_image(doc, doc.pages[0].root_ids, bounds)
    view = CanvasView()
    qtbot.addWidget(view)
    view.adapter.sync(doc)
    canvas = QImage(336, 256, QImage.Format.Format_ARGB32_Premultiplied)
    canvas.fill(0)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    view.scene().render(painter, bounds, bounds)
    painter.end()
    assert canvas == expected
    assert expected.save(str(tmp_path / "shadow-shared.png"))
    assert canvas.save(str(tmp_path / "shadow-scene.png"))
    rasterized = render_pdf(doc, doc.pages[0].root_ids, bounds, tmp_path / "shadow-shared.pdf")
    assert rasterized == (child.id,)
    pdf = QPdfDocument()
    assert pdf.load(str(tmp_path / "shadow-shared.pdf")) == QPdfDocument.Error.None_
    actual = pdf.render(0, QSize(672, 512))
    assert actual.save(str(tmp_path / "shadow-pdf-raster.png"))
    # Whole image (including soft shadow); existing 06A allows up to 64 on antialiased edges.
    reference_2x = render_image(doc, doc.pages[0].root_ids, bounds, scale=2)
    assert reference_2x.save(str(tmp_path / "shadow-shared-2x.png"))
    differences = compare(reference_2x, actual)
    assert differences["interior_max"] <= 3
    assert differences["max_error"] <= 64
    (tmp_path / "report.json").write_text(
        json.dumps(
            {
                "scene_png_equal": canvas == expected,
                "pdf": differences,
                "pdf_rasterized": list(rasterized),
            },
            indent=2,
        ),
        encoding="utf8",
    )
