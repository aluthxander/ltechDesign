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
        QTimer.singleShot(0, window.close)
    result = app.exec()
    logger.info("Desktop stopped: %s", result)
    return result
