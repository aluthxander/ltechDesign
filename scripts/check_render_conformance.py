"""06A one-fixture proof. Native canvas and QGui offscreen are separate processes."""

import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from demo_renderer import fixture as shape_fixture
from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QFontDatabase, QGuiApplication, QImage, QPainter
from PySide6.QtPdf import QPdfDocument

from ltechdesign.domain import create_node, dump_project
from ltechdesign.domain.geometry import world_matrix
from ltechdesign.domain.models import (
    DocumentId,
    Fill,
    Font,
    FontId,
    Fonts,
    FrameData,
    NodeId,
    PageId,
    Point,
    Project,
    Style,
    TextData,
    Typography,
)
from ltechdesign.rendering.drawing import render_image
from ltechdesign.rendering.pdf import render_pdf
from ltechdesign.rendering.text import Resources, layouts

ROOT = Path(__file__).resolve().parents[1]


def fixture() -> Project:
    project = shape_fixture()
    doc = project.document
    font_id = FontId("abel")
    text = create_node(
        "text",
        doc.pages[0].id,
        width=280,
        height=90,
        node_id=NodeId("text"),
        data=TextData(
            text="Shared drawing\nAbel 06A", typography=Typography(font_id=font_id, font_size=24)
        ),
    )
    text = replace(
        text, parent_id=NodeId("board"), x=35, y=285, style=Style(fill=Fill(color="#142850FF"))
    )
    nodes = dict(doc.nodes)
    nodes[NodeId("board")] = replace(
        nodes[NodeId("board")],
        data=FrameData(background=None),
        children=nodes[NodeId("board")].children + (text.id,),
    )
    nodes[NodeId("frame")] = replace(nodes[NodeId("frame")], rotation=-17)
    nodes[NodeId("ellipse")] = replace(nodes[NodeId("ellipse")], rotation=13)
    nodes[text.id] = text
    page_id = PageId("page-conformance")
    nodes = {key: replace(value, page_id=page_id) for key, value in nodes.items()}
    return replace(
        project,
        document=replace(
            doc,
            document_id=DocumentId("conformance"),
            pages=(replace(doc.pages[0], id=page_id),),
            nodes=nodes,
        ),
        manifest=replace(
            project.manifest, document_id=DocumentId("conformance"), saved_at="2026-10-23T00:00:00Z"
        ),
        fonts=Fonts(fonts=(Font(id=font_id, family="Abel"),)),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("canvas", "offscreen"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    app: QGuiApplication
    if args.mode == "canvas":
        from PySide6.QtWidgets import QApplication

        app = QApplication([])
    else:
        app = QGuiApplication([])
    font_path = ROOT / "tests/fixtures/fonts/Abel-Regular.ttf"
    assert (
        hashlib.sha256(font_path.read_bytes()).hexdigest()
        == "8809dcad25318225052f88333e208c5aad4adcb7b2c934c135735ec19aa410b4"
    )
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    assert QFontDatabase.applicationFontFamilies(font_id) == ["Abel"]
    resources = Resources({FontId("abel"): "Abel"})
    project = fixture()
    doc = project.document
    bounds = QRectF(0, 0, 600, 400)
    roots = doc.pages[0].root_ids
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    image = render_image(doc, roots, bounds, resources=resources)
    assert image.save(str(output / "shared.png"))
    assert render_image(doc, roots, bounds, scale=2, resources=resources).save(
        str(output / "shared-2x.png")
    )
    report: dict[str, Any] = {
        "app": type(app).__name__,
        "font_sha256": hashlib.sha256(font_path.read_bytes()).hexdigest(),
        "text_metrics": layouts(doc.nodes[NodeId("text")], resources)[1],
        "members": {p: hashlib.sha256(b).hexdigest() for p, b in dump_project(project, {}).items()},
    }

    def probe(key: str, x: float, y: float) -> list[int]:
        point = world_matrix(doc, NodeId(key)).point(Point(x=x, y=y))
        pixel = image.pixelColor(round(point.x), round(point.y))
        return [pixel.red(), pixel.green(), pixel.blue(), pixel.alpha()]

    report["probes"] = {
        "clip_corner": probe("frame", 1, 1),
        "frame_center": probe("frame", 80, 90),
        "overlap": probe("group", 120, 70),
        "single_child": probe("group", 30, 30),
    }
    if args.mode == "canvas":
        from ltechdesign.rendering.canvas import CanvasView

        view = CanvasView()
        view.resize(750, 550)
        view.adapter.resources = resources
        view.adapter.sync(doc)
        view.show()
        view.fit_artboard()
        app.processEvents()
        assert view.grab().save(str(output / "canvas-window.png"))
        canvas = QImage(600, 400, QImage.Format.Format_ARGB32_Premultiplied)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        view.scene().render(painter, bounds, bounds)
        painter.end()
        assert canvas.save(str(output / "canvas.png"))
        view.close()
    rasterized = render_pdf(doc, roots, bounds, output / "shared.pdf", resources=resources)
    pdf = QPdfDocument()
    assert pdf.load(str(output / "shared.pdf")) == QPdfDocument.Error.None_
    assert pdf.pageCount() == 1
    page = pdf.render(0, QSize(600, 400))
    assert not page.isNull() and page.save(str(output / "pdf-raster.png"))
    report.update(
        pdf_text=pdf.getAllText(0).text(),
        rasterized=list(rasterized),
        pdf_points=[pdf.pagePointSize(0).width(), pdf.pagePointSize(0).height()],
    )
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
