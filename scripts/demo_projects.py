"""Native segment14 visual check: real startup dialog, tabs, recent and saved thumbnail."""

import argparse
import json
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QPoint, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QPushButton

from ltechdesign.domain.models import DocumentSession
from ltechdesign.persistence import read_archive
from ltechdesign.persistence.recovery import RecoveryStore
from ltechdesign.ui.window import StudioWindow


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/projects14"))
    args = parser.parse_args()
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=True)
    profile = output / f"profile-{uuid4()}"
    fixture = Path(__file__).resolve().parents[1] / "examples/proyek-contoh.ltechdesign"
    with fixture.open("rb") as stream:
        loaded = read_archive(stream)
    recovery = RecoveryStore(profile / "recovery")
    original = DocumentSession(project=loaded.project, revision=7)
    recovery.write(original, loaded.blobs)
    recovery.release()
    app = QApplication([])
    window = StudioWindow(data_dir=profile)
    window.projects.timer.stop()
    window.show()
    errors: list[str] = []

    def show_error(error: Exception) -> None:
        errors.append(str(error))

    window.show_error = show_error  # type: ignore[method-assign]
    phase = [0]
    captured = [False]
    report: dict[str, object] = {"visual_inspected": False}
    target = output / "restored-normal.ltechdesign"
    # Avoid overwriting previous demo outputs without a new explicit path choice.
    if target.exists():
        target = output / f"restored-{uuid4()}.ltechdesign"

    def target_dialog(*args: object, **kwargs: object) -> tuple[str, str]:
        return str(target), ""

    QFileDialog.getSaveFileName = target_dialog  # type: ignore[method-assign]

    def poll() -> None:
        modal = app.activeModalWidget()
        if isinstance(modal, QDialog) and modal.windowTitle().startswith("Pulihkan"):
            if not captured[0]:
                assert modal.grab().save(str(output / "startup-recovery.png"))
                captured[0] = True
                for button in modal.findChildren(QPushButton):
                    if button.text() == "Restore":
                        button.click()
                        break
            return
        if errors:
            raise RuntimeError(errors)
        if window.busy:
            return
        if phase[0] == 0:
            phase[0] = 1
            window.projects.startup()
        elif phase[0] == 1 and captured[0] and len(window.documents) == 2:
            tab = window.current
            assert tab and tab.view
            assert tab.dispatcher.snapshot.session_id != original.session_id
            assert tab.dispatcher.dirty and not tab.dispatcher.undo_history
            tab.view.fit_artboard()
            phase[0] = 2
        elif phase[0] == 2:
            assert window.grab().save(str(output / "restored-tabs.png"))
            report["actual_dpr"] = window.devicePixelRatioF()
            window.save_document()
            phase[0] = 3
        elif phase[0] == 3:
            tab = window.current
            assert tab and not tab.dispatcher.dirty and tab.handle.path == target
            with target.open("rb") as stream:
                saved = read_archive(stream)
            (output / "project-thumbnail.png").write_bytes(
                saved.project.opaque_files["thumbnails/project.png"]
            )
            window.projects.refresh_recent()
            window.projects.recent_menu.popup(window.mapToGlobal(QPoint(150, 80)))
            phase[0] = 4
        elif phase[0] == 4:
            assert window.projects.recent_menu.grab().save(str(output / "recent-menu.png"))
            window.projects.recent_menu.hide()
            report.update(
                {
                    "startup_dialog_captured": captured[0],
                    "normal_file": str(target),
                    "new_session": True,
                    "restored_dirty_then_saved_clean": True,
                    "errors": errors,
                }
            )
            (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            timer.stop()
            window.close()

    timer = QTimer(window)
    timer.timeout.connect(poll)
    timer.start(200)
    window.open_path(str(fixture), read_only=True)
    QTimer.singleShot(40000, app.quit)
    result = app.exec()
    if not (output / "report.json").exists():
        raise RuntimeError("Demo did not complete")
    raise SystemExit(result)


if __name__ == "__main__":
    from multiprocessing import freeze_support

    freeze_support()
    main()
