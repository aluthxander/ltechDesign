"""Shared text shaping, outlines, metrics and atomic auto-sizing for every target."""

import math
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import cast

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QFont,
    QFontDatabase,
    QImage,
    QPainter,
    QPainterPath,
    QTextLayout,
    QTextLine,
    QTextOption,
)

from ltechdesign.domain.errors import ModelError, fail
from ltechdesign.domain.models import FontId, Node, NodeId, Project, TextData
from ltechdesign.domain.typography import needs_reflow

MAX_TEXT_CHARACTERS = 100_000

_REFERENCE = QImage(1, 1, QImage.Format.Format_ARGB32_Premultiplied)
_REFERENCE.setDotsPerMeterX(round(96 / 0.0254))
_REFERENCE.setDotsPerMeterY(round(96 / 0.0254))


@dataclass(frozen=True)
class Resources:
    families: Mapping[FontId, str]
    fallbacks: Mapping[FontId, tuple[str, ...]] = field(default_factory=dict)
    notes: tuple[str, ...] = ()
    strict: bool = True
    previews: Mapping[NodeId, Node] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "families", MappingProxyType(dict(self.families)))
        object.__setattr__(self, "fallbacks", MappingProxyType(dict(self.fallbacks)))
        object.__setattr__(self, "previews", MappingProxyType(dict(self.previews)))


def normalized_text(text: str) -> str:
    """Display/input paragraphs only; loading never rewrites authored Unicode content."""
    return (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u2028", "\n")
        .replace("\u2029", "\n")
    )


def utf16_length(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def font_for(node: Node, resources: Resources) -> QFont:
    assert isinstance(node.data, TextData)
    t = node.data.typography
    if (
        t.font_size > 4096
        or abs(t.letter_spacing) > 4096
        or len(node.data.text) * t.font_size > 20_000_000
    ):
        fail("text_metrics_limit", code="limit_exceeded")
    family = resources.families.get(t.font_id)
    if family is None:
        fail("text_font_or_sizing_unavailable", code="unsupported_capability")
    if family not in QFontDatabase.families():
        fail("text_font_unavailable", code="unsupported_capability")
    font = QFont(family)
    font.setFamilies([family, *resources.fallbacks.get(t.font_id, ())])
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    strategy = QFont.StyleStrategy.PreferAntialias
    if resources.strict:
        strategy |= QFont.StyleStrategy.NoFontMerging
    else:
        strategy |= QFont.StyleStrategy.ContextFontMerging
    font.setStyleStrategy(strategy)
    font.setPointSizeF(t.font_size * 72 / 96)
    font.setWeight(QFont.Weight(t.font_weight))
    font.setItalic(t.italic)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, t.letter_spacing)
    return font


_CACHE: OrderedDict[tuple[object, ...], tuple[list[QTextLayout], list[dict[str, float]]]] = (
    OrderedDict()
)


def clear_cache() -> None:
    _CACHE.clear()
    _OUTLINES.clear()


_OUTLINES: OrderedDict[tuple[object, ...], tuple[QPainterPath, tuple[str, ...]]] = OrderedDict()


def layouts(
    node: Node, resources: Resources, *, measure: bool = False
) -> tuple[list[QTextLayout], list[dict[str, float]]]:
    assert isinstance(node.data, TextData)
    typography = node.data.typography
    if node.style.stroke is not None:
        fail("text_stroke_unavailable", code="unsupported_capability")
    if len(node.data.text) > MAX_TEXT_CHARACTERS:
        fail("text_character_limit", code="limit_exceeded")
    font = font_for(node, resources)
    key = (
        node.data,
        node.width,
        node.height,
        font.toString(),
        resources.fallbacks.get(typography.font_id, ()),
        resources.strict,
        measure,
    )
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return _CACHE[key]
    # A fixed metrics device prevents PDF resolution or screen DPI from changing layout.
    reference = _REFERENCE
    option = QTextOption()
    option.setUseDesignMetrics(True)
    option.setWrapMode(
        QTextOption.WrapMode.NoWrap
        if typography.sizing == "auto_width"
        else QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere
    )
    option.setAlignment(
        {
            "left": Qt.AlignmentFlag.AlignLeft,
            "center": Qt.AlignmentFlag.AlignHCenter,
            "right": Qt.AlignmentFlag.AlignRight,
            "justify": Qt.AlignmentFlag.AlignJustify,
        }["left" if measure else typography.alignment]
    )
    result: list[QTextLayout] = []
    metrics: list[dict[str, float]] = []
    y = 0.0
    advance = typography.line_height.value * (
        typography.font_size if typography.line_height.unit == "multiplier" else 1
    )
    for paragraph in normalized_text(node.data.text).split("\n"):
        layout = QTextLayout(paragraph, font, reference)
        layout.setTextOption(option)
        layout.beginLayout()
        count = 0
        while True:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(
                1_000_000_000 if measure and typography.sizing == "auto_width" else node.width
            )
            line.setPosition(QPointF(0, y))
            metrics.append(
                dict(
                    y=y,
                    ascent=line.ascent(),
                    width=line.naturalTextWidth() if resources.strict else line.horizontalAdvance(),
                    height=line.height(),
                )
            )
            y += advance
            count += 1
        layout.endLayout()
        result.append(layout)
        if count == 0:
            y += advance
    content_height = max((m["y"] + m["height"] for m in metrics), default=y)
    offset = (
        0
        if measure
        else {
            "top": 0,
            "center": max(0, (node.height - content_height) / 2),
            "bottom": max(0, node.height - content_height),
        }[typography.vertical_alignment]
    )
    for layout in result:
        layout.setPosition(QPointF(0, offset))
    for metric in metrics:
        metric["y"] += offset
    _CACHE[key] = result, metrics
    while (
        len(_CACHE) > 128
        or sum(len(k[0].text) for k in _CACHE if isinstance(k[0], TextData)) > 1_000_000
    ):
        _CACHE.popitem(last=False)
    return result, metrics


def outlined(node: Node, resources: Resources) -> tuple[QPainterPath, tuple[str, ...]]:
    """Monochrome outlines are identical on QImage/canvas/PDF, including fallback."""
    assert isinstance(node.data, TextData)
    if node.style.stroke is not None:
        fail("text_stroke_unavailable", code="unsupported_capability")
    font = font_for(node, resources)
    cache_key = (
        node.data,
        node.width,
        node.height,
        font.toString(),
        resources.fallbacks.get(node.data.typography.font_id, ()),
        resources.strict,
    )
    if cache_key in _OUTLINES:
        _OUTLINES.move_to_end(cache_key)
        return _OUTLINES[cache_key]
    text_layouts, _ = layouts(node, resources)
    outline = QPainterPath()
    notes: set[str] = set()
    emoji = any(0x1F000 <= ord(ch) <= 0x1FAFF or ord(ch) == 0xFE0F for ch in node.data.text)
    if emoji:
        notes.add(f"emoji_monochrome_outline:{node.id}")
    primary = resources.families.get(node.data.typography.font_id)
    for layout in text_layouts:
        for run in layout.glyphRuns():
            raw = run.rawFont()
            if raw.familyName() != primary:
                notes.add(f"glyph_fallback:{node.id}:{raw.familyName()}")
            for glyph, position in zip(run.glyphIndexes(), run.positions(), strict=True):
                if glyph == 0:
                    if resources.strict:
                        fail("missing_glyph", code="unsupported_capability")
                    notes.add(f"missing_glyph:{node.id}")
                glyph_path = raw.pathForGlyph(glyph)
                if glyph_path.isEmpty() and (
                    glyph == 0 or (emoji and "emoji" in raw.familyName().lower())
                ):
                    notes.add(f"emoji_or_glyph_unavailable:{node.id}")
                    size = node.data.typography.font_size
                    glyph_path.addRect(QRectF(0, -size * 0.75, size * 0.6, size * 0.75))
                glyph_path.translate(position + layout.position())
                outline.addPath(glyph_path)
    _OUTLINES[cache_key] = outline, tuple(sorted(notes))
    while (
        len(_OUTLINES) > 128
        or sum(len(k[0].text) for k in _OUTLINES if isinstance(k[0], TextData)) > 250_000
    ):
        _OUTLINES.popitem(last=False)
    return outline, tuple(sorted(notes))


def diagnostics(document: object, resources: Resources) -> tuple[str, ...]:
    from ltechdesign.domain.models import Document

    assert isinstance(document, Document)
    notes = set(resources.notes)
    for node in document.nodes.values():
        if node.type == "text":
            try:
                notes.update(outlined(node, resources)[1])
            except ModelError as error:
                notes.add(f"text_unavailable:{node.id}:{error}")
    return tuple(sorted(notes))


def display_notes(project: Project, resources: Resources) -> tuple[str, ...]:
    notes = diagnostics(project.document, resources)
    result: list[str] = []
    for font in project.fonts.fonts:
        if any(note.startswith(f"font_missing:{font.id}:") for note in resources.notes):
            result.append(
                f"Font “{font.family}” tidak tersedia; "
                f"memakai “{resources.families.get(font.id)}”. "
                "Metadata font asli dipertahankan."
            )
    for node in project.document.nodes.values():
        if not isinstance(node.data, TextData):
            continue
        name = node.name or "Text"
        if f"missing_glyph:{node.id}" in notes or f"emoji_or_glyph_unavailable:{node.id}" in notes:
            result.append(
                f"Glyph pada “{name}” tidak tersedia; canvas/output memakai tanda pengganti."
            )
        if f"emoji_monochrome_outline:{node.id}" in notes:
            result.append(
                f"Emoji pada “{name}” memakai outline monokrom bila tersedia; "
                "warna emoji tidak dijanjikan."
            )
        for note in notes:
            if note.startswith(f"text_unavailable:{node.id}:"):
                result.append(f"Teks “{name}” belum dapat digambar: {note.split(':', 2)[-1]}")
    return tuple(dict.fromkeys(result))


def reflow(before: Project, after: Project, resources: Resources) -> Project:
    """Runs on the owner Qt thread inside dispatch preparation, before publication."""
    from ltechdesign.commands.planning import Draft
    from ltechdesign.domain.editing import resized
    from ltechdesign.domain.models import Point

    draft = Draft(after)
    changed = False
    for node in after.document.nodes.values():
        if not isinstance(node.data, TextData) or not needs_reflow(before, after, node):
            continue
        _, metrics = layouts(node, resources, measure=True)
        t = node.data.typography
        if t.sizing == "fixed":
            continue
        advance = t.line_height.value * (t.font_size if t.line_height.unit == "multiplier" else 1)
        height = max([advance] + [m["y"] + max(advance, m["height"]) for m in metrics])
        width = (
            max([1.0] + [m["width"] for m in metrics]) if t.sizing == "auto_width" else node.width
        )
        width, height = math.ceil(width * 64) / 64, math.ceil(height * 64) / 64
        adjusted = resized(node, width, height, Point())
        draft.nodes[node.id] = replace(adjusted, data=node.data)
        changed = True
    return draft.finish() if changed else after


def visual_rows(node: Node, resources: Resources) -> list[tuple[int, QTextLayout, QTextLine]]:
    result: list[tuple[int, QTextLayout, QTextLine]] = []
    offset = 0
    for layout in layouts(node, resources)[0]:
        result.extend((offset, layout, layout.lineAt(i)) for i in range(layout.lineCount()))
        offset += utf16_length(layout.text()) + 1
    return result


def cursor_x(line: QTextLine, position: int) -> float:
    result = line.cursorToX(position)
    return float(result[0]) if isinstance(result, tuple) else cast(float, result)


def cursor_rect(node: Node, resources: Resources, position: int) -> QRectF:
    rows = visual_rows(node, resources)
    for i, (offset, layout, line) in enumerate(rows):
        end = offset + line.textStart() + line.textLength()
        if (
            position < end
            or i == len(rows) - 1
            or (position == end and (i + 1 == len(rows) or rows[i + 1][0] != offset))
        ):
            return QRectF(
                cursor_x(line, max(line.textStart(), min(position - offset, end - offset)))
                + layout.position().x(),
                line.y() + layout.position().y(),
                1,
                line.height(),
            )
    return QRectF(0, 0, 1, 24)


def position_at(node: Node, resources: Resources, point: QPointF) -> int:
    rows = visual_rows(node, resources)
    if not rows:
        return 0
    offset, layout, line = min(
        rows,
        key=lambda row: abs(point.y() - (row[2].y() + row[1].position().y() + row[2].height() / 2)),
    )
    return offset + line.xToCursor(point.x() - layout.position().x())


def draw_text(painter: QPainter, node: Node, resources: Resources) -> None:
    # Imported here to keep the shared color codec in one location.
    from .drawing import color

    outline, _ = outlined(node, resources)
    painter.save()
    try:
        painter.setClipRect(QRectF(0, 0, node.width, node.height), Qt.ClipOperation.IntersectClip)
        painter.setPen(
            color(node.style.fill.color) if node.style.fill else Qt.GlobalColor.transparent
        )
        painter.fillPath(outline, painter.pen().color())
    finally:
        painter.restore()
