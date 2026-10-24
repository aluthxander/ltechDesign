"""Record environment evidence; offscreen screens are never physical DPI evidence."""

import argparse
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import qVersion
from PySide6.QtGui import QGuiApplication


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    app = QGuiApplication([sys.argv[0]])
    hardware: object = {"status": "not available on this platform"}
    if sys.platform == "win32":
        probe = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "$ErrorActionPreference = 'Stop'; $cpu = Get-CimInstance Win32_Processor; "
                "$sys = Get-CimInstance Win32_ComputerSystem; "
                "@{cpu=@($cpu.Name); logical_processors=$sys.NumberOfLogicalProcessors; "
                "ram_bytes=$sys.TotalPhysicalMemory} | ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        hardware = (
            json.loads(probe.stdout)
            if probe.returncode == 0 and probe.stdout.strip()
            else {"status": "probe failed", "error": probe.stderr.strip()}
        )
    data = {
        "python": sys.version,
        "os": platform.platform(),
        "architecture": platform.machine(),
        "hardware": hardware,
        "qt": qVersion(),
        "qt_platform": app.platformName(),
        "display_scale_env": {
            key: os.getenv(key)
            for key in ("QT_SCALE_FACTOR", "QT_SCREEN_SCALE_FACTORS", "QT_QPA_PLATFORM")
        },
        "screens": [
            {
                "name": screen.name(),
                "device_pixel_ratio": screen.devicePixelRatio(),
                "logical_dpi": screen.logicalDotsPerInch(),
                "width": screen.size().width(),
                "height": screen.size().height(),
            }
            for screen in app.screens()
        ],
        "display_note": "Qt-reported only; offscreen is synthetic, not physical display scale.",
        "dependencies": dict(
            sorted(
                (dist.metadata["Name"], dist.version) for dist in importlib.metadata.distributions()
            )
        ),
        "manual_gui_inspection": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
