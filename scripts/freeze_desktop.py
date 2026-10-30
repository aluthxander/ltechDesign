"""PyInstaller bootstrap for the desktop entry point only."""

from multiprocessing import freeze_support

from ltechdesign.main import main

if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
