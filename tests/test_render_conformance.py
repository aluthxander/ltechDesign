import json
import os
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QFontDatabase, QImage
from pytestqt.qtbot import QtBot

from ltechdesign.domain import ModelError, create_node, create_project
from ltechdesign.domain.models import Fill, FontId, Style, TextData, Typography
from ltechdesign.rendering.text import Resources, layouts

pytestmark = pytest.mark.desktop
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from render_compare import compare  # noqa: E402


def bbox(image: QImage, region: tuple[int, int, int, int]) -> tuple[int, ...]:
    x0, y0, x1, y1 = region
    coordinates = [
        (x, y) for y in range(y0, y1) for x in range(x0, x1) if image.pixelColor(x, y).alpha() > 8
    ]
    return (
        min(x for x, y in coordinates),
        min(y for x, y in coordinates),
        max(x for x, y in coordinates),
        max(y for x, y in coordinates),
    )


def test_real_canvas_png_pdf_and_qgui_offscreen(tmp_path: Path) -> None:
    outputs = {}
    for mode in ("canvas", "offscreen"):
        output = tmp_path / mode
        command = [
            sys.executable,
            str(ROOT / "scripts/check_render_conformance.py"),
            "--mode",
            mode,
            "--output",
            str(output),
        ]
        result = subprocess.run(
            command,
            cwd=tmp_path,
            env={
                **os.environ,
                "QT_QPA_PLATFORM": "windows"
                if mode == "canvas" and os.name == "nt"
                else "offscreen",
            },
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        outputs[mode] = output
    left = json.loads((outputs["canvas"] / "report.json").read_text())
    right = json.loads((outputs["offscreen"] / "report.json").read_text())
    assert left["app"] == "QApplication" and right["app"] == "QGuiApplication"
    assert left["members"] == right["members"]  # exactly the same fixture bytes
    assert left["text_metrics"] == right["text_metrics"]
    assert len(left["text_metrics"]) == 2
    for report in (left, right):
        assert report["probes"]["clip_corner"][3] == 0
        assert report["probes"]["frame_center"][3] == 255
        assert report["probes"]["overlap"][3] == pytest.approx(127, abs=1)
        assert report["probes"]["single_child"][3] == pytest.approx(127, abs=1)
    assert left["text_metrics"][0]["width"] == pytest.approx(139.953125, abs=1e-6)
    reference = QImage(str(outputs["canvas"] / "shared.png"))
    assert reference == QImage(str(outputs["canvas"] / "canvas.png"))
    offscreen = compare(reference, QImage(str(outputs["offscreen"] / "shared.png")))
    assert offscreen["max_error"] <= 4
    assert offscreen["interior_max"] == 0
    pdf_metrics = {}
    for mode, output in outputs.items():
        report = json.loads((output / "report.json").read_text())
        assert report["pdf_points"] == [450, 300]
        assert report["rasterized"] == ["group"]
        assert report["pdf_text"] == ""  # early primitive is outlined, never claimed searchable
        raw = (output / "shared.pdf").read_bytes()
        assert raw.count(b"/Subtype /Image") == 2  # isolated group + actual soft mask
        assert b"/SMask" in raw and b"/FontFile2" not in raw
        image_sizes = re.findall(rb"/Width (\d+)\s*/Height (\d+)", raw)
        assert len(image_sizes) == 2 and image_sizes[0] == image_sizes[1]
        assert QImage(str(output / "shared-2x.png")).size().width() == 1200
        pdf = QImage(str(output / "pdf-raster.png"))
        differences = compare(reference, pdf)
        assert differences["interior_max"] <= 1
        assert differences["max_error"] <= 64  # ONLY antialias coverage within 1px edge band
        for region in ((0, 0, 350, 270), (350, 0, 600, 280), (0, 280, 340, 390)):
            assert all(
                abs(a - b) <= 1
                for a, b in zip(bbox(reference, region), bbox(pdf, region), strict=True)
            )
        assert reference.pixelColor(200, 180).alpha() == pytest.approx(127, abs=1)
        assert pdf.pixelColor(200, 180).alpha() == pytest.approx(127, abs=1)
        pdf_metrics[mode] = differences
    evidence = ROOT / "artifacts/render06a-comparison.json"
    evidence.write_text(
        json.dumps(
            dict(native=left, offscreen=right, pixel_offscreen=offscreen, pdf=pdf_metrics), indent=2
        ),
        encoding="utf-8",
    )


def test_comparison_rejects_interior_alpha_mismatch() -> None:
    reference = QImage(10, 10, QImage.Format.Format_ARGB32_Premultiplied)
    reference.fill(0xFFAA0000)
    damaged = reference.copy()
    damaged.setPixel(5, 5, 0)
    assert compare(reference, damaged)["interior_max"] == 255


def test_text_resources_and_missing_glyph_are_explicit(qtbot: QtBot) -> None:
    from ltechdesign.rendering.drawing import render_image

    font = ROOT / "tests/fixtures/fonts/Abel-Regular.ttf"
    registered = QFontDatabase.addApplicationFont(str(font))
    try:
        project = create_project()
        text = create_node(
            "text",
            project.document.pages[0].id,
            data=TextData(text="Hello", typography=Typography(font_id=FontId("f"))),
        )
        text = replace(text, style=Style(fill=Fill(color="#000000FF")))
        with pytest.raises(ModelError, match="text_font_or_sizing_unavailable"):
            layouts(text, Resources({}))
        with pytest.raises(ModelError, match="text_font_unavailable"):
            layouts(text, Resources({FontId("f"): "Missing-not-installed"}))
        assert isinstance(text.data, TextData)
        data = replace(text.data, text="\U0010ffff")
        text = replace(text, data=data)
        doc = replace(
            project.document,
            pages=(replace(project.document.pages[0], root_ids=(text.id,)),),
            nodes={text.id: text},
        )
        with pytest.raises(ModelError, match="missing_glyph"):
            render_image(
                doc, (text.id,), QRectF(0, 0, 100, 100), resources=Resources({FontId("f"): "Abel"})
            )
    finally:
        QFontDatabase.removeApplicationFont(registered)
