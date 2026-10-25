"""Typography intents and text-reflow admission; no Qt or installed-font assumptions."""

from dataclasses import replace
from typing import Literal

from .errors import fail
from .models import FontId, Node, Project, TextData

TypographyProperty = Literal[
    "font_id",
    "font_size",
    "font_weight",
    "italic",
    "alignment",
    "vertical_alignment",
    "line_height_value",
    "line_height_unit",
    "letter_spacing",
    "sizing",
]


def changed(node: Node, field: TypographyProperty, value: float | str | bool) -> Node:
    if not isinstance(node.data, TextData):
        fail("text_target_required")
    t = node.data.typography
    # Dataclass constructors perform the strict per-field range/literal validation.
    if field == "font_id":
        if not isinstance(value, str):
            fail("font_id_required")
        t = replace(t, font_id=FontId(value))
    elif field.startswith("line_height_"):
        from .models import LineHeight
        from .typing import typed

        data: dict[str, object] = {"unit": t.line_height.unit, "value": t.line_height.value}
        if (
            field == "line_height_unit"
            and value in ("multiplier", "px")
            and value != t.line_height.unit
        ):
            data["value"] = (
                t.line_height.value * t.font_size
                if value == "px"
                else t.line_height.value / t.font_size
            )
        data["value" if field.endswith("value") else "unit"] = value
        t = replace(t, line_height=typed(data, LineHeight, "$.line_height", wire=True))
    else:
        from .models import Typography
        from .typing import primitive, typed

        data = primitive(t)
        data[field] = value
        t = typed(data, Typography, "$.typography", wire=True)
    return replace(node, data=replace(node.data, typography=t))


def needs_reflow(before: Project, after: Project, node: Node) -> bool:
    if not isinstance(node.data, TextData):
        return False
    old = before.document.nodes.get(node.id)
    font_id = node.data.typography.font_id
    old_font = next((f for f in before.fonts.fonts if f.id == font_id), None)
    font = next((f for f in after.fonts.fonts if f.id == font_id), None)
    return old is None or old.data != node.data or old.width != node.width or old_font != font


def require_metrics(before: Project, after: Project) -> Project:
    """A headless domain-only dispatcher cannot invent auto dimensions without a metrics port."""
    for node in after.document.nodes.values():
        if (
            isinstance(node.data, TextData)
            and node.data.typography.sizing != "fixed"
            and needs_reflow(before, after, node)
        ):
            fail("text_metrics_required", code="unsupported_capability")
    return after
