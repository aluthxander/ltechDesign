"""Local project workflow orchestration. Live snapshots are captured on the GUI thread."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QInputDialog,
    QLabel,
    QMenu,
    QVBoxLayout,
)

from ltechdesign.domain.models import DocumentSession
from ltechdesign.persistence import duplicate_project
from ltechdesign.persistence.preferences import Preferences, user_data_path
from ltechdesign.persistence.recovery import RecoveryEntry, RecoveryOffer, RecoveryStore

if TYPE_CHECKING:
    from ltechdesign.ui.window import StudioWindow, Tab

logger = logging.getLogger(__name__)


def recovery_time(entry: RecoveryEntry) -> str:
    try:
        return (
            datetime.fromisoformat(entry.timestamp)
            .astimezone(UTC)
            .strftime("%Y-%m-%d %H:%M:%S UTC")
        )
    except ValueError:
        return "Timestamp tidak tersedia (metadata rusak)"


class ProjectWorkflow:
    def __init__(self, window: StudioWindow, menu: QMenu, data_dir: Path | None) -> None:
        self.window = window
        self.root = data_dir or user_data_path()
        self.preferences = Preferences(self.root)
        self.recovery = RecoveryStore(self.root / "recovery")
        self.origins: dict[str, RecoveryOffer] = {}
        self.pending: list[RecoveryOffer] = []
        self.recent_menu = menu.addMenu("Recent projects")
        self.recent_menu.aboutToShow.connect(self.refresh_recent)
        duplicate = menu.addAction("Duplicate Project")
        duplicate.triggered.connect(self.duplicate)
        window.menu_actions["duplicate"] = duplicate
        configure = menu.addAction("Autosave interval…")
        configure.triggered.connect(self.configure)
        self.timer = QTimer(window)
        self.timer.timeout.connect(self.autosave)
        self.set_interval(self.preferences.autosave_seconds)
        self.refresh_recent()

    def set_interval(self, seconds: int) -> None:
        self.timer.stop()
        if seconds:
            self.timer.start(seconds * 1000)

    def configure(self) -> None:
        if self.window.busy:
            return
        seconds, accepted = QInputDialog.getInt(
            self.window,
            "Autosave",
            "Detik: 0 = nonaktif; 10–3600 ke recovery area",
            self.preferences.autosave_seconds,
            0,
            3600,
            10,
        )
        if accepted:
            if 0 < seconds < 10:
                seconds = 10
            self.window.job(
                lambda: self.preferences.set_autosave(seconds), lambda _: self.set_interval(seconds)
            )

    def refresh_recent(self) -> None:
        self.recent_menu.clear()
        for path in self.preferences.recent:
            action = self.recent_menu.addAction(path)
            action.triggered.connect(lambda checked=False, p=path: self.window.open_path(p))
        if not self.preferences.recent:
            self.recent_menu.addAction("Belum ada proyek").setEnabled(False)

    def remember(self, path: Path | None) -> None:
        if path is not None:
            try:
                self.preferences.remember(path)
            except OSError:
                logger.exception("Recent projects could not be updated")

    def duplicate(self) -> None:
        window, tab = self.window, self.window.current
        if tab is None or window.busy:
            return
        snapshot = tab.dispatcher.snapshot
        lease = tab.store.pin(snapshot.project.assets.assets)

        def work() -> Any:
            try:
                return window.prepare_admission(
                    window.service.new(duplicate_project(snapshot.project), lease.blobs)
                )
            finally:
                lease.release()

        window.job(work, window.admit)

    def autosave(self) -> None:
        window = self.window
        if window.busy or window._exit_requested or window.images.active:
            return
        captures = []
        for tab in window.documents:
            snapshot = tab.dispatcher.snapshot
            if (
                not tab.handle.read_only
                and tab.dispatcher.dirty
                and snapshot.revision > tab.autosaved_revision
            ):
                captures.append(
                    (
                        tab,
                        snapshot,
                        tab.store.pin(snapshot.project.assets.assets),
                        tab.handle.path,
                        tab.handle.baseline.digest if tab.handle.baseline else None,
                    )
                )
        if not captures:
            return

        def work() -> list[tuple[Tab, int, Exception | None]]:
            results = []
            for tab, snapshot, lease, source, baseline in captures:
                error = None
                try:
                    self.recovery.write(
                        snapshot, lease.blobs, source=source, source_digest=baseline
                    )
                except Exception as caught:
                    error = caught
                finally:
                    lease.release()
                results.append((tab, snapshot.revision, error))
            return results

        def success(results: list[tuple[Tab, int, Exception | None]]) -> None:
            for tab, revision, error in results:
                if error:
                    tab.status = f"Autosave gagal: {error} — dokumen masih di memori"
                    logger.warning("Autosave failed: %s", error)
                else:
                    tab.autosaved_revision = revision
                    tab.status = (
                        f"Recovery tersimpan r{revision} ({datetime.now(UTC):%H:%M:%S} UTC)"
                    )

        window.job(work, success)

    def saved(self, snapshot: DocumentSession) -> None:
        """Worker cleanup after successful manual save; cleanup failure cannot undo the save."""
        try:
            self.recovery.retire(snapshot.session_id, snapshot.revision)
            origin = self.origins.get(snapshot.session_id)
            if origin:
                self.recovery.discard(origin)
                self.origins.pop(snapshot.session_id, None)
        except OSError:
            logger.exception("Saved project recovery cleanup deferred")

    def closed(self, session_id: str) -> None:
        try:
            self.recovery.close_session(session_id, discard=True)
            origin = self.origins.get(session_id)
            if origin:
                self.recovery.discard(origin)
                self.origins.pop(session_id, None)
        except OSError:
            logger.exception("Closed project recovery cleanup deferred")
            self.recovery.close_session(session_id, discard=False)

    def startup(self) -> None:
        self.window.job(self.recovery.scan, lambda offers: self.pending.extend(offers))

    def choose_recovery(self, offer: RecoveryOffer) -> tuple[str, RecoveryEntry]:
        dialog = QDialog(self.window)
        dialog.setWindowTitle("Pulihkan proyek — ltechDesign Studio")
        layout = QVBoxLayout(dialog)
        explanation = QLabel(
            "Recovery dari sesi sebelumnya tersedia. Restore membuka dokumen belum disimpan; "
            "gunakan Save As untuk menyimpan file normal.\n"
            "Sumber tidak akan ditimpa. Later mempertahankan recovery untuk startup berikutnya."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        choices = QComboBox()
        choices.setMinimumContentsLength(50)
        choices.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        for entry in offer.entries:
            choices.addItem(
                f"{entry.name} | {recovery_time(entry)} | revision {entry.revision}"
                f" | {entry.source or 'Belum bernama'}"
                + (f" | RUSAK: {entry.error}" if entry.error else "")
            )
        layout.addWidget(choices)
        choices.setCurrentIndex(next((i for i, e in enumerate(offer.entries) if not e.error), 0))
        buttons = QDialogButtonBox()
        restore = buttons.addButton("Restore", QDialogButtonBox.ButtonRole.AcceptRole)
        discard = buttons.addButton("Discard recovery", QDialogButtonBox.ButtonRole.DestructiveRole)
        later = buttons.addButton("Later", QDialogButtonBox.ButtonRole.RejectRole)
        result = ["later"]

        def choose(action: str) -> None:
            result[0] = action
            dialog.accept()

        restore.clicked.connect(lambda: choose("restore"))
        discard.clicked.connect(lambda: choose("discard"))
        later.clicked.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.resize(760, 230)
        dialog.exec()
        return result[0], offer.entries[choices.currentIndex()]

    def resume_startup(self) -> None:
        if self.window.busy or self.window._exit_requested or not self.pending:
            return
        offer = self.pending.pop(0)
        action, entry = self.choose_recovery(offer)
        if action == "later":
            offer.release()
            QTimer.singleShot(0, self.resume_startup)
        elif action == "discard":

            def discard() -> None:
                try:
                    self.recovery.discard(offer)
                finally:
                    offer.release()

            self.window.job(discard, lambda _: None)
        else:
            self.restore(offer, entry)

    def restore(self, offer: RecoveryOffer, entry: RecoveryEntry) -> None:
        def work() -> Any:
            try:
                loaded = self.recovery.load(offer, entry)
                return self.window.prepare_admission(
                    self.window.service.new(loaded.project, loaded.blobs)
                )
            except Exception:
                offer.release()
                raise

        def success(prepared: Any) -> None:
            self.window.admit(prepared)
            self.origins[prepared[0].admission.session_id] = offer

        self.window.job(work, success)

    def release(self) -> None:
        self.timer.stop()
        self.recovery.release()
        for offer in (*self.pending, *self.origins.values()):
            offer.release()
