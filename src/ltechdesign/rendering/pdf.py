"""Single-page proof adapter; export jobs/dialogs/multipage policy belong to 15–17."""

from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, QSizeF
from PySide6.QtGui import QPageLayout, QPageSize, QPainter, QPdfWriter

from ltechdesign.domain.errors import fail
from ltechdesign.domain.models import Document, NodeId

from .drawing import draw_node, warnings
from .text import Resources


def render_pdf(
    document: Document,
    roots: tuple[NodeId, ...],
    bounds: QRectF,
    target: Path,
    *,
    resources: Resources | None = None,
    dpi: int = 96,
) -> tuple[NodeId, ...]:
    if warnings(document, resources) or bounds.isEmpty() or dpi < 72 or dpi > 600:
        fail("unsupported_pdf_input", code="unsupported_capability")
    writer = QPdfWriter(str(target))
    writer.setResolution(dpi * 2)
    writer.setPageSize(
        QPageSize(
            QSizeF(bounds.width() * 72 / dpi, bounds.height() * 72 / dpi),
            QPageSize.Unit.Point,
            "ltechDesign",
            QPageSize.SizeMatchPolicy.ExactMatch,
        )
    )
    writer.setPageMargins(QMarginsF(), QPageLayout.Unit.Point)
    painter = QPainter(writer)
    if not painter.isActive():
        fail("pdf_painter_failed", code="io_error")
    rasterized: list[NodeId] = []

    def visit(key: NodeId) -> None:
        node = document.nodes[key]
        if not node.visible or node.opacity == 0:
            return
        if node.opacity != 1:
            rasterized.append(key)
        for child in node.children:
            visit(child)

    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering)
        painter.scale(2, 2)
        painter.translate(-bounds.x(), -bounds.y())
        for key in roots:
            visit(key)
            draw_node(painter, document, key, resources=resources)
    finally:
        painter.end()
    del writer
    return tuple(rasterized)
