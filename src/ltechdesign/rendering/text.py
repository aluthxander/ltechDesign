"""Early fixed-box text primitive. Font resolution is explicit and shared by all targets."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QFont,
    QFontDatabase,
    QImage,
    QPainter,
    QPainterPath,
    QTextLayout,
    QTextOption,
)

from ltechdesign.domain.errors import fail
from ltechdesign.domain.models import FontId, Node, TextData

_REFERENCE = QImage(1, 1, QImage.Format.Format_ARGB32_Premultiplied)
_REFERENCE.setDotsPerMeterX(round(96 / 0.0254))
_REFERENCE.setDotsPerMeterY(round(96 / 0.0254))


@dataclass(frozen=True)
class Resources:
    families: Mapping[FontId, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "families", MappingProxyType(dict(self.families)))


def layouts(node: Node, resources: Resources) -> tuple[list[QTextLayout], list[dict[str, float]]]:
    assert isinstance(node.data, TextData)
    typography = node.data.typography
    if node.style.stroke is not None:
        fail("text_stroke_unavailable", code="unsupported_capability")
    family = resources.families.get(typography.font_id)
    if family is None or typography.sizing != "fixed":
        fail("text_font_or_sizing_unavailable", code="unsupported_capability")
    if family not in QFontDatabase.families():
        fail("text_font_unavailable", code="unsupported_capability")
    font = QFont(family)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.NoFontMerging)
    font.setPointSizeF(typography.font_size * 72 / 96)
    font.setWeight(QFont.Weight(typography.font_weight))
    font.setItalic(typography.italic)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, typography.letter_spacing)
    # A fixed metrics device prevents PDF resolution or screen DPI from changing layout.
    reference = _REFERENCE
    option = QTextOption()
    option.setUseDesignMetrics(True)
    option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
    option.setAlignment(
        {
            "left": Qt.AlignmentFlag.AlignLeft,
            "center": Qt.AlignmentFlag.AlignHCenter,
            "right": Qt.AlignmentFlag.AlignRight,
            "justify": Qt.AlignmentFlag.AlignJustify,
        }[typography.alignment]
    )
    result: list[QTextLayout] = []
    metrics: list[dict[str, float]] = []
    y = 0.0
    advance = typography.line_height.value * (
        typography.font_size if typography.line_height.unit == "multiplier" else 1
    )
    for paragraph in node.data.text.split("\n"):
        layout = QTextLayout(paragraph, font, reference)
        layout.setTextOption(option)
        layout.beginLayout()
        while True:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(node.width)
            line.setPosition(QPointF(0, y))
            metrics.append(
                dict(y=y, ascent=line.ascent(), width=line.naturalTextWidth(), height=line.height())
            )
            y += advance
        layout.endLayout()
        result.append(layout)
        if not paragraph:
            y += advance
    content_height = max((m["y"] + m["height"] for m in metrics), default=y)
    offset = {
        "top": 0,
        "center": max(0, (node.height - content_height) / 2),
        "bottom": max(0, node.height - content_height),
    }[typography.vertical_alignment]
    for layout in result:
        layout.setPosition(QPointF(0, offset))
    for metric in metrics:
        metric["y"] += offset
    return result, metrics


def draw_text(painter: QPainter, node: Node, resources: Resources) -> None:
    # Imported here to keep the shared color codec in one location.
    from .drawing import color

    text_layouts, _ = layouts(node, resources)
    painter.save()
    try:
        painter.setClipRect(QRectF(0, 0, node.width, node.height), Qt.ClipOperation.IntersectClip)
        painter.setPen(
            color(node.style.fill.color) if node.style.fill else Qt.GlobalColor.transparent
        )
        for layout in text_layouts:
            outline = QPainterPath()
            for run in layout.glyphRuns():
                raw = run.rawFont()
                for glyph, position in zip(run.glyphIndexes(), run.positions(), strict=True):
                    if glyph == 0:
                        fail("missing_glyph", code="unsupported_capability")
                    glyph_path = raw.pathForGlyph(glyph)
                    glyph_path.translate(position + layout.position())
                    outline.addPath(glyph_path)
            painter.fillPath(outline, painter.pen().color())
    finally:
        painter.restore()
