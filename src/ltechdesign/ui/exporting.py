"""Raster options/progress dialog. Widgets only poll immutable service records."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ltechdesign.domain.errors import ModelError
from ltechdesign.domain.models import NodeId
from ltechdesign.exports import ExportOptions, ExportService, ExportTarget, JobStatus
from ltechdesign.exports.contracts import TERMINAL

if TYPE_CHECKING:
    from .window import StudioWindow, Tab


class ExportDialog(QDialog):
    def __init__(self, controller: ExportController, tab: Tab) -> None:
        super().__init__(controller.window)
        self.controller, self.tab = controller, tab
        self.job_id: str | None = None
        self._last_status: JobStatus | None = None
        self.setWindowTitle("Export raster — ltechDesign Studio")
        self.resize(740, 740)
        layout = QVBoxLayout(self)
        self.identity = QLabel(
            "Snapshot diambil saat Export; edit berikutnya tidak mengubah job ini."
        )
        self.identity.setWordWrap(True)
        layout.addWidget(self.identity)
        form = QFormLayout()
        self.target = QComboBox()
        self.target.addItems(["Artboard", "Selected objects", "All artboards"])
        self.target.setToolTip("All artboards mengikuti urutan dokumen; artboard hidden dilewati.")
        self.target.setAccessibleName("Target export")
        form.addRow("Target", self.target)
        self.artboard = QComboBox()
        self.artboard.setAccessibleName("Artboard export")
        self._listed_revision = -1
        self.refresh_artboards()
        form.addRow("Artboard", self.artboard)
        self.format = QComboBox()
        self.format.addItems(["PNG", "JPG", "WebP"])
        form.addRow("Format", self.format)
        self.scale = QComboBox()
        self.scale.addItems(["1x", "2x", "3x", "Custom pixels"])
        form.addRow("Scale", self.scale)
        dimensions = QHBoxLayout()
        self.pixel_width, self.pixel_height = QSpinBox(), QSpinBox()
        for control, value, name in (
            (self.pixel_width, 1920, "Lebar export px"),
            (self.pixel_height, 1080, "Tinggi export px"),
        ):
            control.setRange(1, 32768)
            control.setValue(value)
            control.setAccessibleName(name)
        dimensions.addWidget(self.pixel_width)
        dimensions.addWidget(QLabel("×"))
        dimensions.addWidget(self.pixel_height)
        form.addRow("Custom px (proporsi tetap + padding)", dimensions)
        self.dpi = QSpinBox()
        self.dpi.setRange(36, 1200)
        self.dpi.setValue(96)
        self.dpi.setToolTip("DPI menentukan metadata fisik; ukuran pixel mengikuti scale/custom.")
        form.addRow("DPI", self.dpi)
        self.quality = QSpinBox()
        self.quality.setRange(1, 100)
        self.quality.setValue(90)
        form.addRow("Quality JPG/WebP", self.quality)
        self.lossless = QCheckBox("Lossless WebP")
        form.addRow("WebP", self.lossless)
        background = QHBoxLayout()
        self.background = QComboBox()
        self.background.addItems(["Transparent", "Solid"])
        self.color = QLineEdit("#FFFFFF")
        self.color.setAccessibleName("Warna background RGB")
        choose_color = QPushButton("Color…")
        choose_color.clicked.connect(self.choose_color)
        background.addWidget(self.background)
        background.addWidget(self.color)
        background.addWidget(choose_color)
        form.addRow("Background", background)
        output = QHBoxLayout()
        folder = tab.handle.path.parent if tab.handle.path else Path.home()
        self.folder = QLineEdit(str(folder))
        self.folder.setAccessibleName("Folder output export")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.choose_folder)
        output.addWidget(self.folder)
        output.addWidget(browse)
        form.addRow("Output folder", output)
        self.pattern = QLineEdit("{project}-{artboard}-{index:03d}")
        self.pattern.setToolTip(
            "{project}, {page}, {artboard}, {index:03d}, {id}; ekstensi otomatis."
        )
        form.addRow("Naming pattern", self.pattern)
        self.overwrite = QCheckBox("Izinkan replace file yang sudah ada di folder pilihan ini")
        form.addRow("Collision", self.overwrite)
        layout.addLayout(form)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setAccessibleName("Progress export")
        layout.addWidget(self.progress)
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setAccessibleName("Hasil dan error export")
        layout.addWidget(self.report, 1)
        actions = QHBoxLayout()
        self.export_button = QPushButton("Export")
        self.export_button.setDefault(True)
        self.export_button.clicked.connect(self.start)
        self.cancel_button = QPushButton("Cancel job")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        close = QPushButton("Close")
        close.clicked.connect(self.hide)
        actions.addWidget(self.export_button)
        actions.addWidget(self.cancel_button)
        actions.addStretch()
        actions.addWidget(close)
        layout.addLayout(actions)
        self.target.currentIndexChanged.connect(self.options_changed)
        self.format.currentIndexChanged.connect(self.options_changed)
        self.scale.currentIndexChanged.connect(self.options_changed)
        self.background.currentIndexChanged.connect(self.options_changed)
        self.options_changed()

    def refresh_artboards(self) -> None:
        snapshot = self.tab.dispatcher.snapshot
        if snapshot.revision == self._listed_revision:
            return
        previous = self.artboard.currentData()
        self.artboard.clear()
        first_active = None
        selected = None
        for page in snapshot.project.document.pages:
            for key in page.root_ids:
                node = snapshot.project.document.nodes[key]
                if node.type == "artboard":
                    index = self.artboard.count()
                    suffix = " [hidden]" if not node.visible else ""
                    self.artboard.addItem(
                        f"{page.name} / {node.name} ({node.width:g}?{node.height:g}){suffix}", key
                    )
                    if first_active is None and page.id == self.tab.active_page_id:
                        first_active = index
                    if key in self.tab.selection:
                        selected = index
        index = self.artboard.findData(previous) if previous is not None else -1
        if index < 0:
            index = selected if selected is not None else first_active or 0
        self.artboard.setCurrentIndex(index)
        self._listed_revision = snapshot.revision

    def options_changed(self) -> None:
        jpg, webp = self.format.currentIndex() == 1, self.format.currentIndex() == 2
        self.artboard.setEnabled(self.target.currentIndex() == 0)
        self.pixel_width.setEnabled(self.scale.currentIndex() == 3)
        self.pixel_height.setEnabled(self.scale.currentIndex() == 3)
        self.quality.setEnabled(jpg or webp)
        self.lossless.setEnabled(webp)
        if jpg:
            self.background.setCurrentIndex(1)
        self.background.setEnabled(not jpg)
        self.color.setEnabled(self.background.currentIndex() == 1)

    def choose_color(self) -> None:
        color = QColorDialog.getColor(parent=self, title="Export background")
        if color.isValid():
            self.color.setText(color.name())

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Export folder", self.folder.text())
        if folder:
            self.folder.setText(folder)

    def options(self) -> ExportOptions:
        kind = self.target.currentIndex()
        target = (
            ExportTarget("artboard", artboard_id=NodeId(self.artboard.currentData()))
            if kind == 0 and self.artboard.currentData()
            else ExportTarget("selection", node_ids=self.tab.selection)
            if kind == 1
            else ExportTarget("all_artboards")
            if kind == 2
            else ExportTarget()
        )
        custom = self.scale.currentIndex() == 3
        return ExportOptions(
            folder=self.folder.text().strip(),
            target=target,
            format=("png", "jpg", "webp")[self.format.currentIndex()],
            scale=self.scale.currentIndex() + 1 if not custom else 1,
            width=self.pixel_width.value() if custom else None,
            height=self.pixel_height.value() if custom else None,
            dpi=self.dpi.value(),
            quality=self.quality.value(),
            background=self.color.text().strip() if self.background.currentIndex() else None,
            pattern=self.pattern.text(),
            overwrite=self.overwrite.isChecked(),
            lossless=self.lossless.isChecked() and self.format.currentIndex() == 2,
        )

    def start(self) -> None:
        if (
            self.job_id
            and self.controller.service.get_job_status(self.job_id).state not in TERMINAL
        ):
            return
        try:
            if self.tab not in self.controller.window.documents or self.tab.closing:
                raise ModelError("source_session_closed", code="session_closed")
            options = self.options()
            options.validate()
            self.controller.service.grant_directory(Path(options.folder))
            snapshot = self.tab.dispatcher.snapshot
            job = self.controller.service.submit(
                snapshot,
                self.tab.store,
                options,
                expected_revision=snapshot.revision,
                request_id=str(uuid4()),
            )
            self.job_id = job.id
            self.render_status(job)
        except (ModelError, OSError, ValueError) as error:
            self.report.setPlainText(str(error))

    def render_status(self, job: JobStatus) -> None:
        self._last_status = job
        self.identity.setText(
            f"Snapshot revision {job.source_revision}; edit baru tidak mengubah hasil ekspor ini."
        )
        self.progress.setValue(round(job.progress * 1000))
        self.progress.setFormat(f"{job.state} — {job.phase} — %p%")
        self.cancel_button.setEnabled(job.state not in TERMINAL)
        self.export_button.setEnabled(job.state in TERMINAL)
        lines = [f"{job.state} | source revision {job.source_revision} | DPI {job.dpi}"]
        if job.error or job.message:
            lines.append(f"{job.error or ''} {job.message or ''}")
        for output in job.outputs:
            lines.append(
                f"{output.state}: {output.path or output.name} "
                f"({output.width}×{output.height}) {output.encoder or ''}"
            )
            if output.error or output.message:
                lines.append(f"  {output.error or ''}: {output.message or ''}")
            lines.extend("  " + note for note in output.notes)
        if job.cancel_requested and job.committed:
            lines.append("File yang sudah dipublikasikan tetap tersedia; tidak di-rollback.")
        self.report.setPlainText("\n".join(lines))

    def cancel(self) -> None:
        if self.job_id:
            self.render_status(self.controller.service.cancel_job(self.job_id))


class ExportController(QObject):
    def __init__(self, window: StudioWindow) -> None:
        super().__init__(window)
        self.window = window
        self.service = ExportService()
        self.dialogs: list[ExportDialog] = []
        self.pending_close: dict[str, Callable[[], None]] = {}
        self.exit_pending = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(100)

    def open(self) -> None:
        tab = self.window.current
        if tab is None or tab.closing:
            return
        dialog = next((d for d in self.dialogs if d.tab is tab), None)
        if dialog is None:
            dialog = ExportDialog(self, tab)
            self.dialogs.append(dialog)
        dialog.refresh_artboards()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def poll(self) -> None:
        for dialog in self.dialogs:
            if dialog.tab in self.window.documents:
                dialog.refresh_artboards()
            if dialog.job_id:
                try:
                    status = self.service.get_job_status(dialog.job_id)
                except ModelError as error:
                    if error.code != "job_not_found":
                        raise
                    dialog.job_id = None
                    dialog.cancel_button.setEnabled(False)
                    dialog.export_button.setEnabled(True)
                    dialog.report.appendPlainText(
                        "Retensi status selesai; file output tetap tersedia."
                    )
                    continue
                if status != dialog._last_status:
                    dialog.render_status(status)
        for session_id, continuation in tuple(self.pending_close.items()):
            if not self.service.active_for(session_id):
                del self.pending_close[session_id]
                continuation()
        if self.exit_pending and not self.service.active_for():
            self.exit_pending = False
            self.window.close()

    def defer_close(self, session_id: str, continuation: Callable[[], None]) -> bool:
        active = self.service.active_for(session_id)
        if not active:
            return False
        for job in active:
            self.service.cancel_job(job.id)
        self.pending_close[session_id] = continuation
        return True

    def defer_exit(self) -> bool:
        active = self.service.active_for()
        if not active:
            return False
        for job in active:
            self.service.cancel_job(job.id)
        self.exit_pending = True
        return True

    def shutdown(self) -> None:
        self.timer.stop()
        self.service.shutdown()

    def release_tab(self, tab: Tab) -> None:
        for dialog in tuple(self.dialogs):
            if dialog.tab is tab:
                self.dialogs.remove(dialog)
                dialog.hide()
                dialog.deleteLater()
