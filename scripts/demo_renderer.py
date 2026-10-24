"""Standalone segment 06 visual fixture; not a production project loader."""

import argparse
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QRectF, QTimer

from ltechdesign.domain import create_node, create_project
from ltechdesign.domain.models import Fill, FrameData, NodeId, Point, Project, Style
from ltechdesign.persistence import PersistenceService
from ltechdesign.rendering.drawing import render_image


def fixture() -> Project:
    project = create_project("Rendering 06 — isolated overlap")
    page = project.document.pages[0]
    art = create_node("artboard", page.id, width=600, height=400, node_id=NodeId("board"))
    art = replace(
        art, data=FrameData(background="#FFFFFFFF"), children=(NodeId("group"), NodeId("frame"))
    )
    group = create_node("group", page.id, node_id=NodeId("group"))
    group = replace(
        group,
        parent_id=art.id,
        x=50,
        y=70,
        width=270,
        height=180,
        pivot=Point(x=135, y=90),
        opacity=0.5,
        rotation=12,
        children=(NodeId("red"), NodeId("blue")),
    )
    a = create_node("rectangle", page.id, width=180, height=140, node_id=NodeId("red"))
    a = replace(a, parent_id=group.id, style=Style(fill=Fill(color="#FF4030FF")))
    b = replace(a, id=NodeId("blue"), x=90, y=40, style=Style(fill=Fill(color="#185DE8FF")))
    frame = create_node("frame", page.id, width=160, height=180, node_id=NodeId("frame"))
    frame = replace(
        frame,
        parent_id=art.id,
        x=390,
        y=100,
        rotation=-10,
        clip_content=True,
        children=(NodeId("ellipse"),),
        style=Style(fill=Fill(color="#11AA77FF"), radius=(40, 40, 40, 40)),
    )
    ellipse = create_node("ellipse", page.id, width=200, height=100, node_id=NodeId("ellipse"))
    ellipse = replace(
        ellipse, parent_id=frame.id, x=-20, y=-20, style=Style(fill=Fill(color="#FFCC00FF"))
    )
    document = replace(
        project.document,
        pages=(replace(page, root_ids=(art.id,)),),
        nodes={n.id: n for n in (art, group, a, b, frame, ellipse)},
    )
    return replace(
        project,
        document=document,
        manifest=replace(
            project.manifest,
            required_capabilities=project.manifest.required_capabilities
            + ("render.isolated-opacity/1", "render.clipping/1"),
        ),
    )


def main() -> None:
    from PySide6.QtWidgets import QApplication

    from ltechdesign.ui.window import StudioWindow

    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path)
    args = parser.parse_args()
    app = QApplication([])
    project = fixture()
    output = Path("artifacts/render06")
    output.mkdir(parents=True, exist_ok=True)
    image = render_image(
        project.document, project.document.pages[0].root_ids, QRectF(0, 0, 600, 400)
    )
    assert image.save(str(output / "shared.png"))
    service = PersistenceService()
    handle = service.new(project, {})
    service.save(
        handle, handle.admission, {}, target=output / "fixture.ltechdesign", overwrite=True
    )
    service.close(handle)
    window = StudioWindow()
    window.show()
    window.open_path(str((output / "fixture.ltechdesign").resolve()))

    def capture() -> None:
        if window.busy:
            QTimer.singleShot(30, capture)
            return
        assert window.current is not None and window.current.view is not None
        window.current.view.fit_artboard()
        if args.capture:
            assert window.grab().save(str(args.capture))
            window.close()

    QTimer.singleShot(50, capture)
    app.exec()


if __name__ == "__main__":
    main()
