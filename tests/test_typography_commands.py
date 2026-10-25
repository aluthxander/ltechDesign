from dataclasses import replace

import pytest
from test_commands import engine, ok, run

from ltechdesign.commands import Create, SetFont, SetText, SetTypography
from ltechdesign.domain import create_node, dump_project, load_project
from ltechdesign.domain.editing import resized
from ltechdesign.domain.models import Font, FontId, LineHeight, Node, Point, TextData, Typography
from ltechdesign.domain.typography import TypographyProperty

pytestmark = pytest.mark.core


def text(d: object) -> Node:
    from ltechdesign.commands import Dispatcher

    assert isinstance(d, Dispatcher)
    font = Font(id=FontId("font"), family="Local missing font", fallback_families=("Arial",))
    n = create_node(
        "text",
        d.snapshot.project.document.pages[0].id,
        data=TextData(text="e\u0301 العربية Ω\nline2", typography=Typography(font_id=font.id)),
    )
    ok(d, SetFont(font=font), Create(node=n))
    return n


def test_typography_units_unicode_roundtrip_and_style_undo() -> None:
    d = engine()
    n = text(d)
    original = d.snapshot.project
    edits: tuple[tuple[TypographyProperty, float | str | bool], ...] = (
        ("font_size", 28),
        ("font_weight", 650),
        ("italic", True),
        ("alignment", "justify"),
        ("vertical_alignment", "center"),
        ("line_height_unit", "px"),
        ("line_height_value", 40),
        ("letter_spacing", -0.5),
    )
    for property, value in edits:
        ok(d, SetTypography(node_ids=(n.id,), property=property, value=value))
    project = d.snapshot.project
    current = project.document.nodes[n.id]
    assert isinstance(current.data, TextData)
    assert current.data.text == n.data.text  # type: ignore[union-attr]
    assert current.data.typography.line_height == LineHeight(unit="px", value=40)
    assert current.data.typography.letter_spacing == -0.5
    restored = load_project(dump_project(project, {}))
    assert restored.document == project.document and restored.fonts == project.fonts
    for _ in edits:
        ok(d, action="undo")
    assert d.snapshot.project == original
    for _ in edits:
        ok(d, action="redo")
    assert d.snapshot.project == project


@pytest.mark.parametrize(
    ("property", "value"),
    [
        ("font_size", 0),
        ("font_weight", 1001),
        ("font_weight", 400.5),
        ("italic", "true"),
        ("alignment", "wrong"),
        ("line_height_value", -1),
        ("line_height_unit", "percent"),
        ("letter_spacing", True),
        ("sizing", "auto_fit"),
        ("font_id", "missing-id"),
    ],
)
def test_invalid_typography_batch_rolls_back(
    property: TypographyProperty, value: float | str | bool
) -> None:
    d = engine()
    n = text(d)
    before = d.snapshot
    assert isinstance(n.data, TextData)
    result = run(
        d,
        SetText(node_id=n.id, data=replace(n.data, text="must rollback")),
        SetTypography(node_ids=(n.id,), property=property, value=value),
    )
    assert not result.ok and d.snapshot is before


def test_auto_sizing_requires_real_metrics_and_does_not_fake_geometry() -> None:
    d = engine()
    n = text(d)
    before = d.snapshot
    result = run(d, SetTypography(node_ids=(n.id,), property="sizing", value="auto_width"))
    assert not result.ok and result.error and result.error.code == "unsupported_capability"
    assert d.snapshot is before


def test_text_resize_policy_keeps_autoheight_for_width_only_otherwise_fixed() -> None:
    d = engine()
    n = text(d)
    assert isinstance(n.data, TextData)
    n = replace(
        n, data=replace(n.data, typography=replace(n.data.typography, sizing="auto_height"))
    )
    changed = resized(n, n.width / 2, n.height, Point())
    assert isinstance(changed.data, TextData) and changed.data.typography.sizing == "auto_height"
    fixed = resized(n, n.width, n.height * 2, Point())
    assert isinstance(fixed.data, TextData) and fixed.data.typography.sizing == "fixed"
