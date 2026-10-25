"""Real native/QGui text conformance and embedded-native roundtrip proof for11."""

import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

from PySide6.QtCore import QRectF, QSize
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QApplication

from ltechdesign.assets import BlobStore
from ltechdesign.commands import Create, Dispatcher, Group, RegisterAsset, Request, SetFont, Update
from ltechdesign.commands.contracts import Operation
from ltechdesign.domain import DocumentSession, create_node, create_project
from ltechdesign.domain.models import (
    Asset,
    AssetId,
    Fill,
    Font,
    FontId,
    FontLicense,
    LineHeight,
    NodeId,
    Project,
    Style,
    TextData,
    Typography,
)
from ltechdesign.persistence.archive import read_archive, write_archive
from ltechdesign.rendering.canvas import CanvasView
from ltechdesign.rendering.drawing import render_image
from ltechdesign.rendering.fonts import FontResolver
from ltechdesign.rendering.pdf import render_pdf
from ltechdesign.rendering.text import layouts, reflow


def main(mode: str, output: Path) -> None:
    app = QApplication([]) if mode == "canvas" else QGuiApplication([])
    output.mkdir(parents=True, exist_ok=True)
    resolver = FontResolver()
    store = BlobStore()
    project = create_project("Typography11 conformance")

    def text_layout(before: Project, after: Project) -> Project:
        with store.pin(after.assets.assets) as pinned:
            return reflow(before, after, resolver.resolve(after, pinned.blobs))

    d = Dispatcher(
        DocumentSession(project=project),
        assets=store.retention(),
        text_layout=text_layout,
    )

    def commit(*ops: Operation) -> None:
        result = d.dispatch(
            Request(
                session_id=d.snapshot.session_id,
                expected_revision=d.snapshot.revision,
                request_id=str(uuid4()),
                action_name="Text conformance",
                source="GUI",
                operations=ops,
            ),
            client_id="local-proof",
        )
        assert result.ok, result.error

    data = (
        Path(__file__).resolve().parents[1] / "tests/fixtures/fonts/Abel-Regular.ttf"
    ).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    asset = Asset(
        id=AssetId("font-asset"),
        path=f"assets/data/{digest}",
        media_type="font/ttf",
        byte_length=len(data),
        sha256=digest,
    )
    staged = store.stage(asset, data)
    abel, ui, missing = FontId("abel"), FontId("ui"), FontId("missing")
    commit(
        RegisterAsset(asset=asset, staging_id=staged),
        SetFont(
            font=Font(
                id=abel,
                family="Abel",
                source="embedded",
                asset_id=asset.id,
                fallback_families=("Segoe UI",),
                license=FontLicense(
                    identifier="OFL-1.1", url="https://openfontlicense.org/", embedding_allowed=True
                ),
            )
        ),
        SetFont(font=Font(id=ui, family="Segoe UI", fallback_families=("Arial",))),
        SetFont(
            font=Font(
                id=missing,
                family="Missing_Font11_conformance",
                fallback_families=("Abel", "Segoe UI"),
            )
        ),
    )
    page = d.snapshot.project.document.pages[0].id
    frame = replace(
        create_node("frame", page, width=720, height=420, node_id=NodeId("frame")),
        clip_content=True,
        style=Style(fill=Fill(color="#FAF7F1FF"), radius=(20,) * 4),
    )
    commit(Create(node=frame))
    entries = (
        (
            "title",
            30,
            20,
            650,
            60,
            abel,
            "Typography11 — shared layout",
            "auto_width",
            32,
            400,
            False,
            0.5,
        ),
        (
            "wrapped",
            30,
            100,
            240,
            150,
            abel,
            "Wrapping words,\n\nblank paragraphs\nand trailing line\n",
            "auto_height",
            24,
            400,
            False,
            0.75,
        ),
        (
            "unicode",
            310,
            100,
            370,
            130,
            ui,
            "e\u0301 Ω العربية\n中文 — \U0001f600",
            "fixed",
            24,
            400,
            False,
            0,
        ),
        (
            "styled",
            30,
            290,
            600,
            70,
            ui,
            "Semibold / italic / letter spacing",
            "fixed",
            26,
            700,
            True,
            1.25,
        ),
        (
            "missing",
            30,
            360,
            650,
            50,
            missing,
            "Missing font: editable fallback",
            "fixed",
            22,
            400,
            False,
            0,
        ),
    )
    for name, x, y, width, height, font, content, sizing, size, weight, italic, spacing in entries:
        node = create_node(
            "text",
            page,
            width=width,
            height=height,
            node_id=NodeId(name),
            data=TextData(
                text=content,
                typography=Typography(
                    font_id=font,
                    font_size=size,
                    font_weight=weight,
                    italic=italic,
                    letter_spacing=spacing,
                    line_height=LineHeight(value=1.4),
                    sizing=cast(Literal["fixed", "auto_width", "auto_height"], sizing),
                ),
            ),
        )
        commit(
            Create(
                node=replace(
                    node,
                    parent_id=frame.id,
                    x=x,
                    y=y,
                    name=name,
                    style=Style(fill=Fill(color="#165D91FF")),
                )
            )
        )
    commit(Group(node_ids=(NodeId("styled"), NodeId("missing")), group_id=NodeId("group")))
    group = d.snapshot.project.document.nodes[NodeId("group")]
    commit(Update(node=replace(group, opacity=0.7)))
    project = d.snapshot.project
    with store.pin(project.assets.assets) as pinned:
        resources = resolver.resolve(project, pinned.blobs)
        bounds = QRectF(0, 0, 720, 420)
        notes: list[str] = []
        image = render_image(
            project.document, (frame.id,), bounds, resources=resources, notes=notes
        )
        assert image.save(str(output / "shared.png"))
        twice = render_image(project.document, (frame.id,), bounds, 2, resources=resources)
        assert twice.save(str(output / "shared-2x.png"))
        if mode == "canvas":
            view = CanvasView()
            view.adapter.resources = resources
            view.adapter.sync(project.document)
            canvas = QImage(720, 420, QImage.Format.Format_ARGB32_Premultiplied)
            canvas.fill(0)
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            view.scene().render(painter, bounds, bounds)
            painter.end()
            assert canvas == image
            assert canvas.save(str(output / "canvas.png"))
            view.close()
        rasterized = render_pdf(
            project.document,
            (frame.id,),
            bounds,
            output / "shared.pdf",
            resources=resources,
            notes=notes,
        )
        pdf = QPdfDocument()
        assert pdf.load(str(output / "shared.pdf")) == QPdfDocument.Error.None_
        raster = pdf.render(0, QSize(1440, 840))
        assert raster.save(str(output / "pdf-raster-2x.png"))
        metrics = {
            key: layouts(n, resources)[1]
            for key, n in project.document.nodes.items()
            if isinstance(n.data, TextData)
        }
        with (output / "editable-text.ltechdesign").open("wb") as stream:
            write_archive(stream, project, pinned.blobs)
    resolver.close()
    with (output / "editable-text.ltechdesign").open("rb") as input_stream:
        loaded = read_archive(input_stream)
    assert loaded.project.document == project.document
    assert loaded.blobs[asset.path] == data
    resolver = FontResolver()
    reopened = resolver.resolve(loaded.project, loaded.blobs)
    assert render_image(loaded.project.document, (frame.id,), bounds, resources=reopened) == image
    (output / "report.json").write_text(
        json.dumps(
            dict(
                mode=mode,
                platform=app.platformName(),
                font_asset_sha256=digest,
                metrics=metrics,
                notes=sorted(set(notes)),
                rasterized=list(rasterized),
                roundtrip=True,
                embedded_font_from_reopened_bytes=True,
            ),
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf8",
    )
    resolver.close()
    d.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("canvas", "offscreen"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.mode, args.output)
