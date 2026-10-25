import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QImage

pytestmark = pytest.mark.desktop
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from render_compare import compare  # noqa: E402


def test_text_native_offscreen_pdf_and_embedded_restore(tmp_path: Path) -> None:
    outputs = {}
    for mode in ("canvas", "offscreen"):
        output = tmp_path / mode
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/check_text_conformance.py"),
                "--mode",
                mode,
                "--output",
                str(output),
            ],
            cwd=tmp_path,
            env={
                **os.environ,
                "QT_QPA_PLATFORM": "windows"
                if mode == "canvas" and os.name == "nt"
                else "offscreen",
            },
            capture_output=True,
            text=True,
            timeout=45,
        )
        assert result.returncode == 0, result.stderr
        outputs[mode] = output
    native, offscreen = (
        json.loads((outputs[m] / "report.json").read_text(encoding="utf8"))
        for m in ("canvas", "offscreen")
    )
    assert native["metrics"] == offscreen["metrics"]
    assert native["notes"] == offscreen["notes"]
    assert any("font_missing" in n for n in native["notes"])
    assert any("emoji_" in n for n in native["notes"])
    reference = QImage(str(outputs["canvas"] / "shared.png"))
    assert reference == QImage(str(outputs["canvas"] / "canvas.png"))
    differences = compare(reference, QImage(str(outputs["offscreen"] / "shared.png")))
    assert differences["interior_max"] == 0
    assert differences["max_error"] <= 64  # outline backend coverage at glyph edges only
    pdf = {}
    for mode, output in outputs.items():
        report = json.loads((output / "report.json").read_text(encoding="utf8"))
        assert report["roundtrip"] and report["embedded_font_from_reopened_bytes"]
        assert report["rasterized"] == ["group"]
        diff = compare(
            QImage(str(output / "shared-2x.png")), QImage(str(output / "pdf-raster-2x.png"))
        )
        assert diff["max_error"] <= 64
        # Nested isolated alpha over an opaque coloured frame has two rounding steps.
        assert diff["interior_max"] <= 2
        pdf[mode] = diff
    (ROOT / "artifacts/text11-comparison.json").write_text(
        json.dumps(dict(native=native, offscreen=offscreen, pixels=differences, pdf=pdf), indent=2),
        encoding="utf8",
    )
