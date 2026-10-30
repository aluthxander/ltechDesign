"""Segment15 native dialog and decoded output evidence using a portable fixture."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from ltechdesign.exports.contracts import TERMINAL
from ltechdesign.ui.window import StudioWindow


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/export15"))
    args = parser.parse_args()
    output = args.output.absolute() / str(uuid4())
    output.mkdir(parents=True)
    app = QApplication([])
    window = StudioWindow(data_dir=output / "profile")
    window.projects.timer.stop()
    window.show()
    errors: list[str] = []

    def show_error(error: Exception) -> None:
        errors.append(str(error))

    window.show_error = show_error  # type: ignore[method-assign]
    phase = [0]
    reports: list[dict[str, object]] = []
    fixture = Path(__file__).resolve().parents[1] / "examples/proyek-contoh.ltechdesign"
    window.open_path(str(fixture), read_only=True)

    def poll() -> None:
        if errors:
            raise RuntimeError(errors)
        if window.busy:
            return
        if phase[0] == 0:
            tab = window.current
            assert tab and tab.view
            group = next(
                n.id
                for n in tab.dispatcher.snapshot.project.document.nodes.values()
                if n.type == "group"
            )
            tab.view.set_selection((group,))
            tab.view.fit_artboard()
            window.menu_actions["export"].trigger()
            dialog = window.exports.dialogs[-1]
            dialog.target.setCurrentIndex(2)
            dialog.folder.setText(str(output))
            dialog.pattern.setText("{index:02d}-{page}-{artboard}")
            dialog.scale.setCurrentIndex(1)
            dialog.dpi.setValue(300)
            phase[0] = 1
        elif phase[0] == 1:
            dialog = window.exports.dialogs[-1]
            assert dialog.grab().save(str(output / "options.png"))
            dialog.start()
            phase[0] = 2
        elif phase[0] in (2, 3, 4):
            dialog = window.exports.dialogs[-1]
            assert dialog.job_id
            status = window.exports.service.get_job_status(dialog.job_id)
            if status.state not in TERMINAL:
                return
            assert status.state == "succeeded", status
            dialog.render_status(status)
            reports.append(asdict(status))
            assert dialog.grab().save(str(output / f"result-{phase[0]}.png"))
            if phase[0] < 4:
                dialog.target.setCurrentIndex(1)
                dialog.format.setCurrentIndex(phase[0] - 1)
                dialog.lossless.setChecked(phase[0] == 3)
                dialog.pattern.setText("selection-{index}")
                dialog.start()
                phase[0] += 1
            else:
                timer.stop()
                result = {
                    "actual_dpr": window.devicePixelRatioF(),
                    "jobs": reports,
                    "output": str(output),
                    "errors": errors,
                    "manual_physical_input": False,
                }
                (args.output / "report.json").write_text(
                    json.dumps(result, indent=2), encoding="utf-8"
                )
                print(json.dumps({"output": str(output), "jobs": len(reports)}), flush=True)
                window.close()

    timer = QTimer(window)
    timer.timeout.connect(poll)
    timer.start(200)
    QTimer.singleShot(40000, app.quit)
    app.exec()
    if len(reports) != 3:
        raise RuntimeError("Export demo did not finish")


if __name__ == "__main__":
    from multiprocessing import freeze_support

    freeze_support()
    main()
