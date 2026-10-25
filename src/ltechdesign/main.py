"""Minimal desktop bootstrap, without editor/canvas subsystems."""

import argparse
import sys
from collections.abc import Sequence

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMainWindow

from ltechdesign import __version__
from ltechdesign.logging_config import configure_logging


def create_window() -> QMainWindow:
    from ltechdesign.ui.window import StudioWindow

    return StudioWindow()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ltechdesign")
    parser.add_argument("--version", action="version", version=f"ltechdesign {__version__}")
    parser.add_argument("--smoke", action="store_true", help="Close via the Qt event loop")
    args = parser.parse_args(argv)
    logger = configure_logging()
    app = QApplication([sys.argv[0]])
    app.setApplicationName("ltechDesign Studio")
    app.setApplicationVersion(__version__)
    window = create_window()
    window.show()
    logger.info("Desktop started")
    if args.smoke:
        from ltechdesign.rendering.media import codec_smoke

        try:
            codec_result = codec_smoke()
            logger.info("Image codec smoke: %s", codec_result)
            import json
            import os
            from pathlib import Path

            if report_path := os.environ.get("LTECHDESIGN_MEDIA_SMOKE_REPORT"):
                Path(report_path).write_text(json.dumps(codec_result), encoding="utf-8")
        except Exception:
            logger.exception("Image codec smoke failed")
            window.close()
            return 1
        QTimer.singleShot(0, window.close)
    result = app.exec()
    logger.info("Desktop stopped: %s", result)
    return result
