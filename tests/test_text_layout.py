from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QFontDatabase, QImage, QPainter
from pytestqt.qtbot import QtBot
from test_commands import ok, run

from ltechdesign.commands import Create, Dispatcher, SetFont, SetTypography
from ltechdesign.domain import (
    DocumentSession,
    ModelError,
    create_node,
    create_project,
    dump_project,
    load_project,
)
from ltechdesign.domain.models import (
    Fill,
    Font,
    FontId,
    LineHeight,
    Point,
    Stroke,
    Style,
    TextData,
    Typography,
)
from ltechdesign.rendering.canvas import CanvasView
from ltechdesign.rendering.drawing import render_image
from ltechdesign.rendering.fonts import FontResolver
from ltechdesign.rendering.text import layouts, outlined, reflow

pytestmark = pytest.mark.desktop
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def text_engine(qtbot: QtBot) -> Iterator[tuple[Dispatcher, FontResolver, FontId]]:
    registered = QFontDatabase.addApplicationFont(
        str(ROOT / "tests/fixtures/fonts/Abel-Regular.ttf")
    )
    resolver = FontResolver()
    d = Dispatcher(
        DocumentSession(project=create_project()),
        text_layout=lambda before, after: reflow(before, after, resolver.resolve(after)),
    )
    font_id = FontId("abel")
    ok(d, SetFont(font=Font(id=font_id, family="Abel")))
    try:
        yield d, resolver, font_id
    finally:
        d.close()
        resolver.close()
        QFontDatabase.removeApplicationFont(registered)


def test_wrapping_blank_and_trailing_lines_use_explicit_units(
    text_engine: tuple[Dispatcher, FontResolver, FontId],
) -> None:
    d, resolver, font_id = text_engine
    n = create_node(
        "text",
        d.snapshot.project.document.pages[0].id,
        width=120,
        height=300,
        data=TextData(
            text="Long paragraph with wrapping\n\nLast\n",
            typography=Typography(
                font_id=font_id, font_size=24, line_height=LineHeight(unit="px", value=35)
            ),
        ),
    )
    ok(d, Create(node=n))
    _, metrics = layouts(n, resolver.resolve(d.snapshot.project))
    assert len(metrics) >= 6
    assert [b["y"] - a["y"] for a, b in zip(metrics, metrics[1:], strict=False)] == [35] * (
        len(metrics) - 1
    )
    assert metrics[-1]["width"] == 0 and metrics[-3]["width"] == 0


@pytest.mark.parametrize("sizing", ["auto_width", "auto_height"])
def test_autosizing_is_atomic_anchored_and_roundtrips(
    text_engine: tuple[Dispatcher, FontResolver, FontId], sizing: str
) -> None:
    d, resolver, font_id = text_engine
    n = create_node(
        "text",
        d.snapshot.project.document.pages[0].id,
        width=80,
        height=120,
        data=TextData(
            text="A long text for wrapping", typography=Typography(font_id=font_id, font_size=24)
        ),
    )
    n = replace(n, x=30, y=40, rotation=31, style=Style(fill=Fill()))
    ok(d, Create(node=n))
    before = d.snapshot.project
    from ltechdesign.domain.geometry import local_matrix

    anchor = local_matrix(n).point(Point())
    ok(d, SetTypography(node_ids=(n.id,), property="sizing", value=sizing))
    node = d.snapshot.project.document.nodes[n.id]
    assert local_matrix(node).point(Point()).x == pytest.approx(anchor.x)
    assert local_matrix(node).point(Point()).y == pytest.approx(anchor.y)
    metrics = layouts(node, resolver.resolve(d.snapshot.project))[1]
    if sizing == "auto_width":
        assert node.width > 80 and len(metrics) == 1
    else:
        assert node.width == 80 and len(metrics) >= 3
    assert node.height >= metrics[-1]["y"] + metrics[-1]["height"]
    loaded = load_project(dump_project(d.snapshot.project, {}))
    assert loaded.document == d.snapshot.project.document
    ok(d, action="undo")
    assert d.snapshot.project == before


def test_missing_font_and_unicode_fallback_preserve_metadata_and_warn(
    text_engine: tuple[Dispatcher, FontResolver, FontId],
) -> None:
    d, resolver, _ = text_engine
    font = Font(
        id=FontId("missing"), family="FontDefinitelyNotInstalled11", fallback_families=("Abel",)
    )
    n = create_node(
        "text",
        d.snapshot.project.document.pages[0].id,
        width=320,
        height=150,
        data=TextData(
            text="e\u0301 Ω العربية 中文 \U0001f600 \U0010ffff",
            typography=Typography(font_id=font.id, font_size=24),
        ),
    )
    n = replace(n, style=Style(fill=Fill()))
    ok(d, SetFont(font=font), Create(node=n))
    before = d.snapshot.project
    resources = resolver.resolve(before)
    assert resources.families[font.id] == "Abel" and any(
        "font_missing" in note for note in resources.notes
    )
    notes: list[str] = []
    image = render_image(
        before.document, (n.id,), QRectF(0, 0, 320, 150), resources=resources, notes=notes
    )
    assert not image.isNull() and any("missing_glyph" in note for note in notes)
    assert any("emoji_" in note for note in notes)
    assert d.snapshot.project == before and before.fonts.fonts[-1] == font
    assert load_project(dump_project(before, {})).fonts == before.fonts


def test_shared_scene_png_font_metrics_and_visuals_match(
    text_engine: tuple[Dispatcher, FontResolver, FontId], qtbot: QtBot
) -> None:
    d, resolver, font_id = text_engine
    n = create_node(
        "text",
        d.snapshot.project.document.pages[0].id,
        width=240,
        height=180,
        data=TextData(
            text="Multiline text\nShared shaping",
            typography=Typography(
                font_id=font_id,
                font_size=28,
                font_weight=650,
                italic=True,
                alignment="center",
                line_height=LineHeight(value=1.5),
                letter_spacing=1.25,
            ),
        ),
    )
    n = replace(n, x=40, y=30, rotation=7, opacity=0.75, style=Style(fill=Fill(color="#1266AAFF")))
    ok(d, Create(node=n))
    resources = resolver.resolve(d.snapshot.project)
    bounds = QRectF(0, 0, 360, 280)
    expected = render_image(d.snapshot.project.document, (n.id,), bounds, resources=resources)
    view = CanvasView()
    qtbot.addWidget(view)
    view.adapter.resources = resources
    view.adapter.sync(d.snapshot.project.document)
    actual = QImage(360, 280, QImage.Format.Format_ARGB32_Premultiplied)
    actual.fill(0)
    painter = QPainter(actual)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    view.scene().render(painter, bounds, bounds)
    painter.end()
    assert actual == expected


def test_text_metrics_limits_and_stroke_failure_are_not_hidden_by_cache(
    text_engine: tuple[Dispatcher, FontResolver, FontId],
) -> None:
    d, resolver, font_id = text_engine
    n = create_node(
        "text",
        d.snapshot.project.document.pages[0].id,
        data=TextData(text="Valid", typography=Typography(font_id=font_id)),
    )
    ok(d, Create(node=n))
    resources = resolver.resolve(d.snapshot.project)
    outlined(n, resources)
    with pytest.raises(ModelError, match="text_stroke_unavailable"):
        outlined(replace(n, style=Style(stroke=Stroke())), resources)
    before = d.snapshot
    result = run(d, SetTypography(node_ids=(n.id,), property="font_size", value=100000))
    assert not result.ok and result.error and result.error.code == "limit_exceeded"
    assert d.snapshot is before
