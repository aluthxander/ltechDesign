"""Segment 13 native Inspector/canvas and portable PNG/PDF layout proof."""

import argparse
import json
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, QTimer
from PySide6.QtGui import QImage
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QApplication

from ltechdesign.commands import Create, SetFont
from ltechdesign.commands.contracts import Operation
from ltechdesign.domain import create_node, create_project
from ltechdesign.domain.models import (
    Constraints,
    Fill,
    Font,
    FontId,
    FrameData,
    Layout,
    Node,
    NodeId,
    NodeType,
    Style,
    TextData,
    Typography,
)
from ltechdesign.rendering.drawing import render_image
from ltechdesign.rendering.pdf import render_pdf
from ltechdesign.ui.window import StudioWindow


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("artifacts/layout13"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    window = StudioWindow()
    window.admit(
        window.prepare_admission(window.service.new(create_project("Stack layout 13"), {}))
    )
    tab = window.current
    assert tab and tab.view
    page = tab.dispatcher.snapshot.project.document.pages[0].id
    font = Font(id=FontId("demo-layout-font"), family="Arial")
    nodes: list[Node] = []

    def frame(
        key: str,
        parent: str | None,
        layout: Layout,
        width: float,
        height: float,
        background: str,
        kind: NodeType = "frame",
    ) -> None:
        nodes.append(
            replace(
                create_node(kind, page, node_id=NodeId(key), width=width, height=height),
                parent_id=NodeId(parent) if parent else None,
                name=key,
                layout=layout,
                data=FrameData(background=background),
            )
        )

    def text(key: str, parent: str, message: str, size: float) -> None:
        nodes.append(
            replace(
                create_node(
                    "text",
                    page,
                    node_id=NodeId(key),
                    data=TextData(
                        text=message,
                        typography=Typography(
                            font_id=font.id, font_size=size, sizing="auto_height"
                        ),
                    ),
                ),
                name=key,
                parent_id=NodeId(parent),
                constraints=Constraints(sizing_x="fill"),
                style=Style(fill=Fill(color="#183348FF")),
            )
        )

    frame(
        "Board", None, Layout(padding=(32, 32, 32, 32), gap=24), 820, 540, "#F7F9FCFF", "artboard"
    )
    frame("Header", "Board", Layout(sizing_x="fill", gap=8), 100, 90, "#F7F9FCFF")
    text("Title", "Header", "ltechDesign Studio", 32)
    text("Subtitle", "Header", "Deterministic local layout • editable .ltechdesign", 16)
    frame(
        "Cards",
        "Board",
        Layout(direction="horizontal", sizing_x="fill", sizing_y="fill", gap=20),
        100,
        100,
        "#F7F9FCFF",
    )
    for key, background, title, body in (
        (
            "First-card",
            "#E0EBFFFF",
            "Build with stacks",
            "Horizontal and vertical stacks share padding, gap and alignment. "
            "Fill divides the available space equally.",
        ),
        (
            "Second-card",
            "#D9F1E7FF",
            "Resize with confidence",
            "Text wraps at the allocated width. Nested hug content and parent "
            "constraints update in the same undoable transaction.",
        ),
    ):
        frame(
            key,
            "Cards",
            Layout(sizing_x="fill", sizing_y="fill", padding=(24, 24, 24, 24), gap=18),
            100,
            100,
            background,
        )
        text(key + "-title", key, title, 24)
        text(key + "-body", key, body, 19)
    operations: tuple[Operation, ...] = (SetFont(font=font),) + tuple(Create(node=n) for n in nodes)
    assert window.execute(tab, operations, action_name="Layout demonstration")
    project = tab.dispatcher.snapshot.project
    bounds = QRectF(0, 0, 820, 540)
    resources = tab.view.adapter.resources
    image = render_image(project.document, (NodeId("Board"),), bounds, resources=resources)
    assert image.save(str(args.output / "shared.png"))
    pdf_path = args.output / "shared.pdf"
    render_pdf(project.document, (NodeId("Board"),), bounds, pdf_path, resources=resources)
    pdf = QPdfDocument()
    assert pdf.load(str(pdf_path)) == QPdfDocument.Error.None_
    raster = pdf.render(0, QSize(820, 540)).convertToFormat(QImage.Format.Format_RGBA8888)
    assert raster.save(str(args.output / "pdf.png"))
    # Interior colors exercise actual PDF coordinates after layout, not just a PDF header.
    for x, y in ((80, 250), (500, 250)):
        a, b = image.pixelColor(x, y), raster.pixelColor(x, y)
        assert (
            max(abs(a.red() - b.red()), abs(a.green() - b.green()), abs(a.blue() - b.blue())) <= 2
        )
    saved = window.service.save(
        tab.handle,
        tab.dispatcher.snapshot,
        {},
        target=args.output / "demo.ltechdesign",
        overwrite=True,
    )
    tab.dispatcher.mark_saved(saved.checkpoint)
    window.refresh()
    window.show()
    tab.view.fit_artboard()
    tab.view.set_selection((NodeId("Cards"),))
    window.inspector.ensureWidgetVisible(window.inspector.layout_panel)

    def capture() -> None:
        assert window.grab().save(str(args.output / "inspector.png"))
        report = {
            "platform": app.platformName(),
            "dpr": window.devicePixelRatioF(),
            "revision": tab.dispatcher.snapshot.revision,
            "nodes": len(project.document.nodes),
            "pdf_interior_tolerance": 2,
            "manual_physical_input": False,
        }
        (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        if args.capture:
            for opened in window.documents:
                opened.dispatcher.close()
                window.service.close(opened.handle)
            window.documents.clear()
            window.close()
            app.quit()

    QTimer.singleShot(400, capture)
    app.exec()


if __name__ == "__main__":
    main()
