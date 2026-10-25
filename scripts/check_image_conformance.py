"""Generate segment12 portable native/PNG/PDF and a real application screenshot.

The --verify mode can run in an isolated installed wheel with all sources moved.
"""

import argparse
import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, qVersion
from PySide6.QtGui import QImage, QPainter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QApplication

from ltechdesign.commands import Create, Update
from ltechdesign.domain import create_node, create_project
from ltechdesign.domain.models import Crop, FrameData, MediaData, Style
from ltechdesign.persistence import PersistenceService
from ltechdesign.rendering.drawing import render_image
from ltechdesign.rendering.fonts import FontResolver
from ltechdesign.rendering.pdf import render_pdf
from ltechdesign.ui.window import StudioWindow

VECTOR = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<svg xmlns="http://www.w3.org/2000/svg" width="240" height="180" viewBox="0 0 240 180">'
    b'<rect width="240" height="180" rx="20" fill="#15243a"/>'
    b'<g transform="translate(120 90) rotate(-15)">'
    b'<circle r="65" fill="#51ddc0"/><path d="M-42 30 L0 -45 L42 30 Z" fill="#164a6a"/>'
    b'<circle cy="5" r="14" fill="#fff"/></g></svg>'
)
BOUNDS = QRectF(0, 0, 880, 600)


def wait(app: QApplication, ready: Callable[[], bool]) -> None:
    limit = time.monotonic() + 20
    while not ready():
        app.processEvents()
        if time.monotonic() > limit:
            raise TimeoutError("Image conformance job timed out")


def verify(path: Path, output: Path) -> dict[str, object]:
    service = PersistenceService()
    handle = service.open(path, read_only=True)
    resolver = FontResolver()
    try:
        project = handle.admission.project
        resources = resolver.resolve(project, handle.loaded.blobs)
        roots = project.document.pages[0].root_ids
        png = render_image(project.document, roots, BOUNDS, resources=resources)
        assert png.save(str(output / "shared.png"))
        rasterized = render_pdf(
            project.document, roots, BOUNDS, output / "shared.pdf", resources=resources
        )
        reader = QPdfDocument()
        assert reader.load(str(output / "shared.pdf")) == QPdfDocument.Error.None_
        actual = reader.render(0, QSize(1760, 1200))
        assert actual.save(str(output / "pdf-raster.png"))
        return dict(
            assets=len(project.assets.assets),
            nodes=len(project.document.nodes),
            png_sha256=hashlib.sha256((output / "shared.png").read_bytes()).hexdigest(),
            rasterized=list(rasterized),
            media=[a.media_type for a in project.assets.assets],
            svg_vector_sources=sum(s.picture is not None for s in resources.media.values()),
        )
    finally:
        resolver.close()
        service.close(handle)


def heavy_import(app: QApplication, output: Path) -> dict[str, object]:
    """Actual 36 MP decoder, GUI heartbeat and cancel before publication."""
    source = output / "heavy-36mp.png"
    image = QImage(6000, 6000, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.red)
    assert image.save(str(source))
    del image
    window = StudioWindow()
    window.admit(window.prepare_admission(window.service.new(create_project("Heavy import"), {})))
    window.show()
    app.processEvents()
    tab = window.current
    assert tab
    gaps: list[float] = []
    last = time.perf_counter()
    timer = QTimer(window)
    timer.setInterval(5)

    def tick() -> None:
        nonlocal last
        now = time.perf_counter()
        gaps.append((now - last) * 1000)
        last = now

    timer.timeout.connect(tick)
    timer.start()
    started = time.perf_counter()
    job = window.images.start(tab, [str(source)], QPointF())
    assert job
    QTimer.singleShot(20, lambda: window.images.cancel(job))
    check = QTimer(window)
    check.setInterval(5)
    report: dict[str, object] = {}

    def finished() -> None:
        if window.images.active:
            return
        timer.stop()
        check.stop()
        report.update(
            job=window.images.status(job),
            elapsed_ms=(time.perf_counter() - started) * 1000,
            heartbeat_max_ms=max(gaps, default=0),
            heartbeats=len(gaps),
            nodes=len(tab.dispatcher.snapshot.project.document.nodes),
            staged=len(tab.store._staged),
            blobs=len(tab.store._blobs),
        )
        tab.dispatcher.close()
        window.service.close(tab.handle)
        window.documents.clear()
        window.close()
        app.quit()

    check.timeout.connect(finished)
    check.start()
    app.exec()
    assert report["nodes"] == report["staged"] == report["blobs"] == 0
    assert window.images.status(job)["state"] == "cancelled"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--heavy", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    if args.heavy:
        report = heavy_import(app, args.output)
    elif args.verify:
        report = verify(args.verify, args.output)
    else:
        window = StudioWindow()
        window.resize(1400, 950)
        window.show()
        window.admit(
            window.prepare_admission(
                window.service.new(create_project("Segment12 portable images"), {})
            )
        )
        tab = window.current
        assert tab and tab.view
        sources = args.output / "sources"
        sources.mkdir(exist_ok=True)
        image = QImage(320, 240, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        for x in range(0, 320, 20):
            from PySide6.QtGui import QColor

            painter.fillRect(x, 0, 20, 240, QColor.fromHsv(180 + x // 3, 170, 220))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawEllipse(105, 55, 110, 110)
        painter.end()
        paths = []
        for format_name in ("PNG", "JPEG", "WEBP"):
            path = sources / (format_name.lower() + "." + format_name.lower())
            assert image.save(str(path), format_name)  # type: ignore[call-overload]
            paths.append(str(path))
        vector = sources / "vector.svg"
        vector.write_bytes(VECTOR)
        paths.append(str(vector))
        job = window.images.start(tab, paths, QPointF())
        assert job
        wait(app, lambda: window.images.active is None)
        assert window.images.status(job)["state"] == "succeeded"
        doc = tab.dispatcher.snapshot.project.document
        board = create_node(
            "artboard",
            doc.pages[0].id,
            width=880,
            height=600,
            data=FrameData(background="#F5F7FBFF"),
        )
        ops: list[Create | Update] = [Create(node=board)]
        # Keep images as page roots: the board is just an opaque background.
        for index, key in enumerate(tab.selection):
            node = doc.nodes[key]
            assert isinstance(node.data, MediaData)
            fit: Literal["fit", "fill", "stretch"] = ("fit", "fill", "stretch")[index % 3]
            ops.append(
                Update(
                    node=replace(
                        node,
                        x=60 + (index % 2) * 410,
                        y=50 + (index // 2) * 270,
                        width=340,
                        height=220,
                        rotation=(index - 1) * 7,
                        opacity=0.75 if index == 2 else 1,
                        style=Style(radius=(30, 12, 30, 12)),
                        data=replace(
                            node.data, fit=fit, crop=Crop(x=0.1, y=0.1, width=0.8, height=0.8)
                        ),
                    )
                )
            )
        # Insert the board below existing images in the shared child/root ordering.
        ops[0] = Create(node=board, index=0)
        assert window.execute(tab, tuple(ops), action_name="Image conformance fixture")
        tab.view.set_selection((tab.selection[-1],))
        tab.view.fit_artboard()
        app.processEvents()
        assert window.grab().save(str(args.output / "window.png"))
        snapshot = tab.dispatcher.snapshot
        resources = tab.view.adapter.resources
        roots = snapshot.project.document.pages[0].root_ids
        png = render_image(snapshot.project.document, roots, BOUNDS, resources=resources)
        canvas = QImage(png.size(), png.format())
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tab.view.scene().render(painter, BOUNDS, BOUNDS)
        painter.end()
        assert canvas == png
        checkpoint = tab.dispatcher.capture_checkpoint()
        with tab.store.pin(snapshot.project.assets.assets) as pinned:
            saved = window.service.save(
                tab.handle, snapshot, pinned.blobs, target=args.output / "portable.ltechdesign"
            )
        tab.dispatcher.mark_saved(checkpoint)
        assert saved.path
        for source in sources.iterdir():
            source.rename(source.with_suffix(source.suffix + ".moved"))
        native = args.output / "portable.ltechdesign"
        report = verify(native, args.output)
        assert QImage(str(args.output / "shared.png")).convertToFormat(png.format()) == png
        report.update(canvas_png_exact=True, import_job=window.images.status(job))
        for opened in window.documents:
            opened.dispatcher.close()
            window.service.close(opened.handle)
        window.documents.clear()
        window.close()
    report.update(
        qt=qVersion(), platform=app.platformName(), dpr=app.primaryScreen().devicePixelRatio()
    )
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
