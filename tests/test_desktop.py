import os
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QFontDatabase
from pytestqt.qtbot import QtBot

from ltechdesign.main import create_window

pytestmark = pytest.mark.desktop


def test_window_lifecycle(qtbot: QtBot) -> None:
    window = create_window()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(window.isVisible)
    assert window.windowTitle() == "ltechDesign Studio"
    assert window.close()
    assert not window.isVisible()


def test_vendored_font_loads(qtbot: QtBot) -> None:
    font = Path(__file__).parent / "fixtures/fonts/Abel-Regular.ttf"
    font_id = QFontDatabase.addApplicationFont(str(font))
    try:
        assert font_id >= 0
        assert QFontDatabase.applicationFontFamilies(font_id) == ["Abel"]
    finally:
        if font_id >= 0:
            QFontDatabase.removeApplicationFont(font_id)


@pytest.mark.parametrize("target", ["desktop", "cli", "module"])
def test_entrypoint_event_loop_shutdown(target: str, tmp_path: Path) -> None:
    scripts = Path(sys.executable).parent
    commands = {
        "desktop": [str(scripts / "ltechdesign.exe"), "--smoke"],
        "cli": [str(scripts / "ltechdesign-cli.exe"), "gui", "--smoke"],
        "module": [sys.executable, "-I", "-m", "ltechdesign", "gui", "--smoke"],
    }
    if sys.platform != "win32":
        commands["desktop"][0] = str(scripts / "ltechdesign")
        commands["cli"][0] = str(scripts / "ltechdesign-cli")
    result = subprocess.run(
        commands[target],
        cwd=tmp_path,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
