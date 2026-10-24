"""Console entry point. Desktop imports are lazy."""

import argparse
from collections.abc import Sequence

from ltechdesign import __version__


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ltechdesign-cli")
    parser.add_argument("--version", action="version", version=f"ltechdesign {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    gui = commands.add_parser("gui", help="Open the minimal desktop window")
    gui.add_argument("--smoke", action="store_true", help="Exit after one Qt event-loop turn")
    args = parser.parse_args(argv)
    if args.command == "gui":
        from ltechdesign.main import main as desktop_main

        return desktop_main(["--smoke"] if args.smoke else [])
    return 2
