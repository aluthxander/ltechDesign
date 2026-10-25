"""Real Qt display-scale/gesture spike; caller sets Qt scale before process startup."""

import json
import sys
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

import ltechdesign
from ltechdesign.commands import Create
from ltechdesign.domain import create_node, create_project
from ltechdesign.domain.models import Fill, Point, Style
from ltechdesign.domain.snapping import geometry
from ltechdesign.ui.canvas_aids import CanvasAidControls
from ltechdesign.ui.window import StudioWindow


def main(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    window = StudioWindow()
    window.resize(1500, 900)
    window.admit(window.prepare_admission(window.service.new(create_project("Canvas aids10B"), {})))
    window.show()
    app.processEvents()
    tab = window.current
    assert tab is not None and tab.view is not None
    view = tab.view
    page = tab.dispatcher.snapshot.project.document.pages[0].id
    first = replace(
        create_node("rectangle", page, width=80, height=60),
        x=40,
        y=60,
        style=Style(fill=Fill(color="#2080C0FF")),
    )
    target = replace(
        create_node("rectangle", page, width=60, height=60),
        x=180,
        y=200,
        style=Style(fill=Fill(color="#E08030FF")),
    )
    assert window.execute(tab, (Create(node=first), Create(node=target)))
    control = tab.widget.findChild(CanvasAidControls)
    assert control is not None
    control.checks["snap"].setChecked(True)
    control.checks["grid_snap"].setChecked(False)
    control.checks["grid"].setChecked(True)
    QTest.qWait(200)  # finish native checkbox transitions before evidence screenshots
    view.set_selection((first.id,))
    dpr = view.viewport().devicePixelRatioF()
    reports: list[dict[str, object]] = []
    try:
        for zoom in (0.5, 1, 2, 4):
            view.set_zoom(zoom)
            start = QPointF(80, 90)
            delta = 60 - 3 / zoom / dpr
            end = start + QPointF(delta, 0)
            view.centerOn((start.x() + end.x()) / 2, (start.y() + end.y()) / 2)
            app.processEvents()
            view.aids.prepare((first.id,))
            bounds = geometry(tab.dispatcher.snapshot.project.document, first.id)
            near = view.aids.move(bounds, Point(x=60 - 7.9 / zoom / dpr))
            near_snap = abs(near.x - 60) < 1e-8
            raw_far = 60 - 8.1 / zoom / dpr
            far = view.aids.move(bounds, Point(x=raw_far))
            far_snap = abs(far.x - raw_far) > 1e-8
            assert near_snap and not far_snap
            before, depth = tab.dispatcher.snapshot, len(tab.dispatcher.undo_history)
            a, b = view.mapFromScene(start), view.mapFromScene(end)
            QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=a)
            QApplication.sendEvent(
                view.viewport(),
                QMouseEvent(
                    QMouseEvent.Type.MouseMove,
                    QPointF(b),
                    QPointF(b),
                    Qt.MouseButton.NoButton,
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier,
                ),
            )
            assert tab.dispatcher.snapshot is before and view.aids.guides, dict(
                zoom=zoom,
                dpr=dpr,
                a=[a.x(), a.y()],
                b=[b.x(), b.y()],
                viewport=[view.viewport().width(), view.viewport().height()],
                active=str(view.transforms.active),
                guides=str(view.aids.guides),
            )
            app.processEvents()
            if zoom == 1:
                assert window.grab().save(str(output / "canvas-aids-native.png"))
            QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=b)
            doc = tab.dispatcher.snapshot.project.document
            assert abs(geometry(doc, first.id).max_x - 180) < 1e-8
            assert float(window.inspector.fields["x"].text()) == doc.nodes[first.id].x
            assert len(tab.dispatcher.undo_history) == depth + 1
            window.history("undo")
            assert tab.dispatcher.snapshot.project == before.project
            reports.append(
                dict(
                    zoom=zoom,
                    near_snap=near_snap,
                    far_snap=far_snap,
                    one_undo=True,
                    source_revision=before.revision,
                    session_id=str(tab.dispatcher.snapshot.session_id),
                    inspector_sync=True,
                    guides_cleared=not view.aids.guides,
                )
            )
        report = dict(
            dpr=dpr,
            zooms=reports,
            platform=app.platformName(),
            package_path=ltechdesign.__file__,
            run_id=str(uuid4()),
        )
        (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf8")
        print(json.dumps(report))
    finally:
        tab.dispatcher.close()
        window.service.close(tab.handle)
        window.documents.clear()
        window.close()


if __name__ == "__main__":
    main(Path(sys.argv[1]))
