"""Local import jobs and image controls; every content publication uses dispatcher."""

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from PySide6.QtCore import QObject, QPointF, QSize, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ltechdesign.assets.importing import StagedImage, check_cancel, stage_image
from ltechdesign.assets.store import BlobLease
from ltechdesign.commands import Create, RegisterAsset, SetMedia
from ltechdesign.domain import create_node
from ltechdesign.domain.errors import ModelError, fail
from ltechdesign.domain.geometry import Matrix, world_matrix
from ltechdesign.domain.models import AssetId, Crop, MediaData, Node, NodeId, Point, Style
from ltechdesign.rendering.hit_testing import drawing_parent
from ltechdesign.rendering.media import MAX_PREPARED_BYTES, MediaSource

if TYPE_CHECKING:
    from .window import StudioWindow, Tab

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.webp *.svg)"
MAX_IMPORT_FILES = 32  # Register + Create fits the existing 100-operation batch ceiling.


@dataclass
class ImportJob:
    tab: "Tab"
    revision: int
    page: int
    point: QPointF
    target: Node | None
    lease: BlobLease
    id: str = field(default_factory=lambda: str(uuid4()))
    state: Literal["queued", "running", "succeeded", "failed", "cancelled"] = "queued"
    progress: float = 0
    cancel: Event = field(default_factory=Event)
    error: dict[str, object] | None = None
    session_id: str = ""
    document_id: str = ""
    result: tuple[NodeId, ...] = ()


class ImageImports(QObject):
    completed = Signal(object, object)

    def __init__(self, studio: "StudioWindow") -> None:
        super().__init__(studio)
        self.studio = studio
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="image-import")
        self.active: ImportJob | None = None
        self.jobs: dict[str, dict[str, object]] = {}
        self.completed.connect(self.finish, Qt.ConnectionType.QueuedConnection)
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_status)

    def status(self, job_id: str) -> dict[str, object]:
        job = self.active
        if job is not None and job.id == job_id:
            return self.record(job)
        record = self.jobs.get(job_id)
        if record is None:
            fail("job_not_found", code="job_not_found")
        return dict(record)

    @staticmethod
    def record(job: ImportJob) -> dict[str, object]:
        return dict(
            id=job.id,
            session_id=job.session_id,
            document_id=job.document_id,
            source_revision=job.revision,
            state=job.state,
            progress=job.progress,
            error=job.error,
            result=job.result,
        )

    def cancel(self, job_id: str) -> None:
        job = self.active
        if job is not None and job.id == job_id:
            job.cancel.set()
        elif job_id not in self.jobs:
            fail("job_not_found", code="job_not_found")

    def choose(self, *, replace_image: bool = False) -> None:
        tab = self.studio.current
        if not tab or not tab.view:
            return
        target = None
        if replace_image:
            if len(tab.selection) != 1:
                return
            target = tab.dispatcher.snapshot.project.document.nodes[tab.selection[0]]
            if not isinstance(target.data, MediaData):
                return
            path, _ = QFileDialog.getOpenFileName(self.studio, "Replace image", "", IMAGE_FILTER)
            paths = [path] if path else []
        else:
            paths, _ = QFileDialog.getOpenFileNames(self.studio, "Import images", "", IMAGE_FILTER)
        if paths:
            center = tab.view.mapToScene(tab.view.viewport().rect().center())
            self.start(tab, paths, center, target)

    def start(
        self, tab: "Tab", paths: list[str], point: QPointF, target: Node | None = None
    ) -> str | None:
        if (
            self.active
            or self.studio.busy
            or tab.handle.read_only
            or tab not in self.studio.documents
        ):
            return None
        if not 1 <= len(paths) <= MAX_IMPORT_FILES or (target and len(paths) != 1):
            self.studio.inspector.images.feedback.setText("Maksimum 32 file per impor atomik.")
            return None
        snapshot = tab.dispatcher.snapshot
        if target is not None and (
            not isinstance(target.data, MediaData)
            or snapshot.project.document.nodes.get(target.id) != target
        ):
            self.studio.inspector.images.feedback.setText("Replace dibatalkan: target berubah.")
            return None
        lease = tab.store.pin(snapshot.project.assets.assets)
        job = ImportJob(
            tab,
            snapshot.revision,
            tab.active_page,
            point,
            target,
            lease,
            session_id=snapshot.session_id,
            document_id=snapshot.project.document.document_id,
        )
        self.active = job
        # Retain bounded terminal job records, never evict a running job.
        while len(self.jobs) >= 32:
            self.jobs.pop(next(iter(self.jobs)))
        prepared_cost = sum(s.cost for s in tab.media.values())

        def work() -> tuple[StagedImage, ...]:
            job.state = "running"
            staged: list[StagedImage] = []
            cost = prepared_cost
            try:
                for index, path in enumerate(paths):
                    check_cancel(job.cancel.is_set)
                    image = stage_image(
                        Path(path),
                        tab.store,
                        job.cancel.is_set,
                        byte_budget=MAX_PREPARED_BYTES - cost,
                    )
                    staged.append(image)
                    cost += image.source.cost
                    if cost > MAX_PREPARED_BYTES:
                        fail("prepared_image_bytes", code="limit_exceeded")
                    job.progress = (index + 1) / len(paths) * 0.9
                check_cancel(job.cancel.is_set)
                return tuple(staged)
            except Exception:
                tab.store.discard_staging(tuple(i.staging_id for i in staged))
                raise

        future = self.executor.submit(work)
        future.add_done_callback(lambda f: self.completed.emit(job, f))
        self.timer.start()
        self.update_status()
        self.studio.refresh()
        return job.id

    @Slot(object, object)
    def finish(self, job: ImportJob, future: Future[tuple[StagedImage, ...]]) -> None:
        tab = job.tab
        images: tuple[StagedImage, ...] = ()
        old_media = tab.media
        try:
            images = future.result()
            check_cancel(job.cancel.is_set)
            if (
                tab not in self.studio.documents
                or tab.dispatcher.snapshot.session_id != job.session_id
            ):
                fail("session_closed", code="session_closed")
            if tab.active_page != job.page or tab.dispatcher.snapshot.revision != job.revision:
                fail("Import source changed", code="revision_conflict")
            operations: list[RegisterAsset | SetMedia | Create] = []
            keys: list[NodeId] = []
            for index, image in enumerate(images):
                operations.append(RegisterAsset(asset=image.asset, staging_id=image.staging_id))
                if job.target:
                    assert isinstance(job.target.data, MediaData)
                    operations.append(
                        SetMedia(
                            node_id=job.target.id,
                            data=replace(job.target.data, asset_id=image.asset.id),
                        )
                    )
                    keys.append(job.target.id)
                else:
                    node = self.node(
                        tab,
                        image.asset.id,
                        image.source,
                        job.point + QPointF(index * 24, index * 24),
                        image.name,
                    )
                    operations.append(Create(node=node))
                    keys.append(node.id)
            # Resources must exist when the dispatcher's publication synchronizes the scene.
            tab.media = old_media | {i.asset.id: i.source for i in images}
            if not self.studio.execute(
                tab,
                tuple(operations),
                expected_revision=job.revision,
                action_name="Replace image" if job.target else "Import images",
            ):
                fail("image_publication_failed")
            job.state = "succeeded"  # Commit barrier passed; late cancel cannot change this.
            job.progress = 1
            job.result = tuple(keys)
            if tab.view:
                tab.view.set_selection(tuple(keys))
        except Exception as error:
            if job.state != "succeeded":
                tab.media = old_media
            job.error = dict(
                code=error.code if isinstance(error, ModelError) else "io_error",
                message=str(error),
                details=dict(error.details) if isinstance(error, ModelError) else {},
                retryable=False,
            )
            if job.state != "succeeded":
                job.state = (
                    "cancelled"
                    if isinstance(error, ModelError) and error.code == "cancelled"
                    else "failed"
                )
        finally:
            tab.store.discard_staging(tuple(i.staging_id for i in images))
            job.lease.release()
            tab.store.collect()
            # Terminal job metadata must not keep closed sessions/decoded bytes alive.
            self.jobs[job.id] = self.record(job)
            self.active = None
            self.timer.stop()
            self.update_status(job)
            self.studio.refresh()
            if self.studio._exit_requested:
                self.studio.close()

    def update_status(self, finished: ImportJob | None = None) -> None:
        job = self.active or finished
        panel = self.studio.inspector.images
        panel.cancel_button.setEnabled(self.active is not None)
        if job:
            panel.feedback.setText(
                f"Import {job.state} · {job.progress:.0%}"
                + (f" · {job.error['code']}: {job.error['message']}" if job.error else "")
            )

    @staticmethod
    def node(tab: "Tab", asset_id: AssetId, source: MediaSource, point: QPointF, name: str) -> Node:
        doc = tab.dispatcher.snapshot.project.document
        parent = drawing_parent(doc, tab.active_page, point)
        inverse = world_matrix(doc, parent).inverse() if parent else Matrix()
        position = inverse.point(Point(x=point.x(), y=point.y()))
        scale = min(1, 640 / source.width, 480 / source.height)
        return replace(
            create_node(
                "svg" if source.svg is not None else "image",
                doc.pages[tab.active_page].id,
                width=source.width * scale,
                height=source.height * scale,
                data=MediaData(asset_id=asset_id),
            ),
            name=name,
            x=position.x,
            y=position.y,
            parent_id=parent,
            style=Style(),
        )


class ImagePanel(QWidget):
    def __init__(self, studio: "StudioWindow") -> None:
        super().__init__()
        self.studio = studio
        self.context: tuple[object, ...] | None = None
        self.publishing = False
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.import_button = QPushButton("Import images…")
        self.replace_button = QPushButton("Replace image…")
        self.import_button.clicked.connect(lambda: studio.images.choose())
        self.replace_button.clicked.connect(lambda: studio.images.choose(replace_image=True))
        row.addWidget(self.import_button)
        row.addWidget(self.replace_button)
        layout.addLayout(row)
        self.gallery = QListWidget()
        self.gallery.setAccessibleName("Embedded image assets")
        self.gallery.setIconSize(QSize(96, 72))
        self.gallery.setMaximumHeight(140)
        self.gallery.itemDoubleClicked.connect(self.place)
        layout.addWidget(self.gallery)
        self.gallery_keys: tuple[AssetId, ...] = ()
        form = QFormLayout()
        self.fit = QComboBox()
        self.fit.addItems(["fit", "fill", "stretch"])
        self.fit.setAccessibleName("Image fit mode")
        self.fit.activated.connect(lambda _: self.apply())
        form.addRow("Image mode", self.fit)
        self.crop: dict[str, QLineEdit] = {}
        for key in ("x", "y", "width", "height"):
            edit = QLineEdit()
            edit.setAccessibleName(f"Crop {key} normalized")
            self.crop[key] = edit
            form.addRow(f"Crop {key} · 0–1", edit)
        layout.addLayout(form)
        row = QHBoxLayout()
        self.apply_button = QPushButton("Apply crop")
        self.reset_button = QPushButton("Reset crop")
        self.apply_button.clicked.connect(self.apply)
        self.reset_button.clicked.connect(self.reset)
        row.addWidget(self.apply_button)
        row.addWidget(self.reset_button)
        layout.addLayout(row)
        self.cancel_button = QPushButton("Cancel import")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        layout.addWidget(self.cancel_button)
        self.feedback = QLabel()
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)

    def cancel(self) -> None:
        job = self.studio.images.active
        if job:
            self.studio.images.cancel(job.id)

    def sync(self) -> None:
        tab = self.studio.current
        active = getattr(self.studio, "images", None)
        self.setVisible(
            bool(tab and (tab.media or (active and active.active) or self.feedback.text()))
        )
        writable = bool(tab and not tab.handle.read_only and not self.studio.busy)
        self.import_button.setEnabled(writable and not (active and active.active))
        context = (
            (tab.dispatcher.snapshot.session_id, tab.selection, tab.dispatcher.snapshot.revision)
            if tab
            else None
        )
        node = (
            tab.dispatcher.snapshot.project.document.nodes[tab.selection[0]]
            if tab and len(tab.selection) == 1
            else None
        )
        enabled = writable and node is not None and isinstance(node.data, MediaData)
        self.replace_button.setEnabled(enabled and not (active and active.active))
        for control in (self.fit, self.apply_button, self.reset_button, *self.crop.values()):
            control.setEnabled(enabled)
        if context != self.context and not self.publishing:
            self.context = context
            data = node.data if node and isinstance(node.data, MediaData) else None
            self.fit.setCurrentText(data.fit if data else "fit")
            for key, control in self.crop.items():
                control.setText(format(getattr(data.crop, key), ".12g") if data else "")
        keys = (
            tuple(a.id for a in tab.dispatcher.snapshot.project.assets.assets if a.id in tab.media)
            if tab
            else ()
        )
        if keys != self.gallery_keys or self.gallery.property("session") != (
            context[0] if context else None
        ):
            self.gallery.clear()
            self.gallery_keys = keys
            self.gallery.setProperty("session", context[0] if context else None)
            if tab:
                for key in keys:
                    source = tab.media[key]
                    item = QListWidgetItem(
                        QIcon(QPixmap.fromImage(source.thumbnail)),
                        f"{'SVG' if source.svg else 'Image'} {source.width:g} × {source.height:g}",
                    )
                    item.setData(Qt.ItemDataRole.UserRole, key)
                    item.setToolTip(f"Embedded {key}\nDouble click untuk menempatkan aset")
                    self.gallery.addItem(item)

    def apply(self, *, reset: bool = False) -> None:
        tab = self.studio.current
        if not tab or not self.apply_button.isEnabled():
            return
        context = (
            tab.dispatcher.snapshot.session_id,
            tab.selection,
            tab.dispatcher.snapshot.revision,
        )
        if context != self.context:
            self.sync()
            return
        node = tab.dispatcher.snapshot.project.document.nodes[tab.selection[0]]
        assert isinstance(node.data, MediaData)
        try:
            crop = Crop() if reset else Crop(**{k: float(v.text()) for k, v in self.crop.items()})
            data = MediaData(asset_id=node.data.asset_id, fit=self.fit.currentText(), crop=crop)  # type: ignore[arg-type]
            if data == node.data:
                return
            self.publishing = True
            self.studio.execute(
                tab,
                (SetMedia(node_id=node.id, data=data),),
                expected_revision=context[2],
                action_name="Image crop / fit",
            )
        except (ValueError, ModelError) as error:
            self.feedback.setText(f"Crop tidak valid: {error}")
        finally:
            self.publishing = False
            self.context = None
            self.sync()

    def reset(self) -> None:
        self.apply(reset=True)

    def place(self, item: QListWidgetItem) -> None:
        tab = self.studio.current
        if not tab or not tab.view or tab.handle.read_only or self.studio.busy:
            return
        key = AssetId(item.data(Qt.ItemDataRole.UserRole))
        source = tab.media.get(key)
        if source:
            point = tab.view.mapToScene(tab.view.viewport().rect().center())
            node = self.studio.images.node(tab, key, source, point, "Image")
            if self.studio.execute(tab, (Create(node=node),), action_name="Place embedded image"):
                tab.view.set_selection((node.id,))
