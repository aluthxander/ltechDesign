"""GUI owns dispatchers; one I/O executor serializes persistence side effects."""

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ltechdesign.assets import BlobStore
from ltechdesign.commands import Dispatcher, Request, Update
from ltechdesign.domain import create_project
from ltechdesign.domain.errors import ModelError
from ltechdesign.domain.models import NodeId
from ltechdesign.persistence import FileHandle, PersistenceService, SaveResult
from ltechdesign.rendering.canvas import CanvasView
from ltechdesign.rendering.drawing import warnings as render_warnings


class Completion(QObject):
    done = Signal(object, object)


@dataclass
class Tab:
    handle: FileHandle
    dispatcher: Dispatcher
    store: BlobStore
    widget: QWidget
    view: CanvasView | None = None
    selection: tuple[NodeId, ...] = ()
    active_page: int = 0
    status: str = "Belum disimpan"


class StudioWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ltechDesign Studio")
        self.resize(1200, 800)
        self.service = PersistenceService()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="persistence")
        self.completion = Completion(self)
        self.completion.done.connect(self._completed)
        self.busy = False
        self._exit_requested = False
        self.documents: list[Tab] = []
        self.tabs = QTabWidget()
        self.tabs.setAccessibleName("Dokumen terbuka")
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.refresh)
        self.setCentralWidget(self.tabs)
        self.pages = QListWidget()
        self.pages.setAccessibleName("Pages")
        self.pages.currentRowChanged.connect(self.page_changed)
        self.layers = QTreeWidget()
        self.layers.setHeaderLabel("Layers")
        self.layers.setAccessibleName("Layers — pilih objek")
        self.layers.itemSelectionChanged.connect(self.selection_changed)
        self.layers.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        left = QWidget()
        layout = QVBoxLayout(left)
        layout.addWidget(QLabel("Pages"))
        layout.addWidget(self.pages, 1)
        layout.addWidget(QLabel("Layers"))
        layout.addWidget(self.layers, 3)
        self._dock("Pages / Layers", left, Qt.DockWidgetArea.LeftDockWidgetArea)
        inspector = QWidget()
        form = QFormLayout(inspector)
        self.project_name = QLabel("—")
        self.project_name.setWordWrap(True)
        self.object_name = QLineEdit()
        self.object_name.setAccessibleName("Nama objek terpilih")
        self.object_name.editingFinished.connect(self.rename_object)
        form.addRow("Proyek", self.project_name)
        form.addRow("Nama objek", self.object_name)
        pending = QLabel("Geometri, style dan drawing tersedia pada segmen berikutnya.")
        pending.setWordWrap(True)
        form.addRow(pending)
        self._dock("Inspector", inspector, Qt.DockWidgetArea.RightDockWidgetArea)
        toolbar = QToolBar("Tools")
        self.addToolBar(toolbar)
        self.menu_actions: dict[str, QAction] = {}
        file_menu = self.menuBar().addMenu("&File")
        entries = [
            ("new", "&New…", "Ctrl+N", self.new_document),
            ("open", "&Open…", "Ctrl+O", self.choose_open),
            ("import", "&Import Project…", "", self.choose_open),
            ("save", "&Save", "Ctrl+S", self.save_document),
            ("save_as", "Save &As…", "Ctrl+Shift+S", lambda: self.save_document(as_new=True)),
            ("reload", "&Reload…", "", self.reload_document),
            ("close", "&Close", "Ctrl+W", lambda: self.close_tab(self.tabs.currentIndex())),
        ]
        for key, label, shortcut, callback in entries:
            action = QAction(label, self)
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(callback)
            self.menu_actions[key] = action
            file_menu.addAction(action)
            if key in ("new", "open", "save"):
                toolbar.addAction(action)
        edit_menu = self.menuBar().addMenu("&Edit")
        for key, shortcut in (("undo", "Ctrl+Z"), ("redo", "Ctrl+Shift+Z")):
            action = QAction(key.title(), self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(lambda checked=False, k=key: self.history(k))
            self.menu_actions[key] = action
            edit_menu.addAction(action)
        for label in (
            "Select canvas — belum tersedia",
            "Rectangle — belum tersedia",
            "Text — belum tersedia",
            "Export — belum tersedia",
        ):
            action = toolbar.addAction(label)
            action.setEnabled(False)
        QWidget.setTabOrder(self.tabs, self.pages)
        QWidget.setTabOrder(self.pages, self.layers)
        QWidget.setTabOrder(self.layers, self.object_name)
        self.refresh()

    def _dock(self, title: str, widget: QWidget, area: Qt.DockWidgetArea) -> None:
        dock = QDockWidget(title, self)
        dock.setWidget(widget)
        self.addDockWidget(area, dock)

    @property
    def current(self) -> Tab | None:
        index = self.tabs.currentIndex()
        return self.documents[index] if 0 <= index < len(self.documents) else None

    def job(self, work: Callable[[], Any], success: Callable[[Any], None]) -> None:
        if self.busy:
            return
        self.busy = True
        self.refresh()
        future = self.executor.submit(work)
        future.add_done_callback(lambda f: self.completion.done.emit(f, success))

    def _completed(self, future: Future[Any], success: Callable[[Any], None]) -> None:
        self.busy = False
        try:
            success(future.result())
        except Exception as error:
            self.show_error(error)
        self.refresh()

    def show_error(self, error: Exception) -> None:
        code = error.code if isinstance(error, ModelError) else "io_error"
        self.statusBar().showMessage(f"Gagal: {code}")
        QMessageBox.warning(
            self,
            "Operasi gagal",
            f"{code}\n{error}\n"
            "Dokumen tetap tersedia. Untuk konflik file, pilih Reload atau Save As.",
        )

    def prepare_admission(self, handle: FileHandle) -> tuple[FileHandle, BlobStore, Any]:
        store = BlobStore()
        lease = store.admit(handle.loaded.project.assets.assets, handle.loaded.blobs)
        return handle, store, lease

    def admit(self, prepared: tuple[FileHandle, BlobStore, Any]) -> None:
        handle, store, lease = prepared
        for index, tab in enumerate(self.documents):
            if tab.handle is handle:
                lease.release()
                self.tabs.setCurrentIndex(index)
                return
        dispatcher = Dispatcher(
            handle.admission,
            initially_saved=handle.path is not None,
            assets=store.retention(),
            read_only=handle.read_only,
        )
        lease.release()
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(" ".join(render_warnings(handle.loaded.project.document)))
        label.setWordWrap(True)
        layout.addWidget(label)
        view = CanvasView()
        from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QHBoxLayout, QPushButton

        controls = QHBoxLayout()
        zoom = QDoubleSpinBox()
        zoom.setRange(2, 1600)
        zoom.setValue(100)
        zoom.setSuffix(" %")
        zoom.setAccessibleName("Canvas zoom")
        zoom.valueChanged.connect(lambda value: view.set_zoom(value / 100))

        def zoom_changed(value: float) -> None:
            zoom.blockSignals(True)
            zoom.setValue(value * 100)
            zoom.blockSignals(False)

        view.zoom_changed.connect(zoom_changed)
        controls.addWidget(zoom)
        for title, callback in (
            ("Fit artboard", view.fit_artboard),
            ("Zoom selection", view.zoom_selection),
        ):
            button = QPushButton(title)
            button.clicked.connect(callback)
            controls.addWidget(button)
        controls.addStretch()
        grid = QCheckBox("Grid")
        grid.setAccessibleName("Grid overlay — tidak ikut ekspor")

        def toggle_grid(checked: bool) -> None:
            view.grid = checked
            view.viewport().update()

        grid.toggled.connect(toggle_grid)
        controls.addWidget(grid)
        layout.addLayout(controls)
        layout.addWidget(view, 1)
        tab = Tab(
            handle,
            dispatcher,
            store,
            widget,
            view=view,
            status="Read-only"
            if handle.read_only
            else "Tersimpan"
            if handle.path
            else "Belum disimpan",
        )
        self.documents.append(tab)
        dispatcher.subscribe(lambda event: self.refresh())
        self.tabs.addTab(widget, handle.admission.project.document.name)
        self.tabs.setCurrentWidget(widget)
        self.refresh()

    def new_document(self) -> None:
        name, accepted = QInputDialog.getText(self, "New Project", "Nama proyek:", text="Untitled")
        if accepted and name.strip():
            self.job(
                lambda: self.prepare_admission(self.service.new(create_project(name.strip()), {})),
                self.admit,
            )

    def choose_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open / Import Project", "", "Proyek (*.ltechdesign)"
        )
        if path:
            self.open_path(path)

    def open_path(self, path: str, read_only: bool = False) -> None:
        def work() -> FileHandle:
            try:
                return self.service.open(path, read_only=read_only)
            except ModelError as error:
                if error.code in ("file_owned", "target_in_use") and not read_only:
                    return self.service.open(path, read_only=True)
                raise

        self.job(lambda: self.prepare_admission(work()), self.admit)

    def save_document(
        self,
        checked: bool = False,
        *,
        as_new: bool = False,
        after: Callable[[], None] | None = None,
    ) -> None:
        tab = self.current
        if tab is None or self.busy:
            return
        target = None
        overwrite = False
        if as_new or tab.handle.path is None or tab.handle.read_only:
            target, _ = QFileDialog.getSaveFileName(self, "Save As", "", "Proyek (*.ltechdesign)")
            if not target:
                self._exit_requested = False
                return
            if not target.lower().endswith(".ltechdesign"):
                target += ".ltechdesign"
            overwrite = Path(target).exists()
            if (
                overwrite
                and QMessageBox.question(
                    self,
                    "Replace file?",
                    "Ganti file tujuan yang sudah ada?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                != QMessageBox.StandardButton.Yes
            ):
                self._exit_requested = False
                return
        snapshot = tab.dispatcher.snapshot
        lease = tab.store.pin(snapshot.project.assets.assets)

        def work() -> SaveResult:
            try:
                return self.service.save(
                    tab.handle, snapshot, lease.blobs, target=target, overwrite=overwrite
                )
            finally:
                lease.release()

        def success(result: SaveResult) -> None:
            tab.dispatcher.mark_saved(result.checkpoint)
            tab.dispatcher.set_read_only(False)
            tab.status = "Tersimpan"
            if after:
                after()

        self.job(work, success)

    def unsaved(self, tab: Tab, continuation: Callable[[], None]) -> None:
        if not tab.dispatcher.dirty:
            continuation()
            return
        answer = QMessageBox.question(
            self,
            "Perubahan belum disimpan",
            "Simpan perubahan sebelum melanjutkan?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Discard:
            continuation()
        elif answer == QMessageBox.StandardButton.Save:
            self.save_document(after=continuation)
        else:
            self._exit_requested = False

    def close_tab(self, index: int) -> None:
        if self.busy or not 0 <= index < len(self.documents):
            return
        self.tabs.setCurrentIndex(index)
        tab = self.documents[index]

        def close() -> None:
            def finished(_: Any) -> None:
                tab.dispatcher.close()
                self.documents.remove(tab)
                self.tabs.removeTab(index)
                tab.widget.deleteLater()
                if self._exit_requested:
                    self.close()

            self.job(lambda: self.service.close(tab.handle), finished)

        self.unsaved(tab, close)

    def reload_document(self) -> None:
        tab = self.current
        if tab is None or tab.handle.path is None or self.busy:
            return

        def reload() -> None:
            self.job(
                lambda: self.prepare_admission(self.service.reload(tab.handle)),
                lambda prepared: self.replace_tab(tab, prepared),
            )

        self.unsaved(tab, reload)

    def replace_tab(self, old: Tab, prepared: tuple[FileHandle, BlobStore, Any]) -> None:
        index = self.documents.index(old)
        old.dispatcher.close()
        self.documents.pop(index)
        self.tabs.removeTab(index)
        old.widget.deleteLater()
        self.admit(prepared)

    def page_changed(self, index: int) -> None:
        if self.current and index >= 0:
            self.current.active_page = index
            self.current.selection = ()
            self.refresh()

    def selection_changed(self) -> None:
        tab = self.current
        if tab:
            tab.selection = tuple(
                NodeId(item.data(0, Qt.ItemDataRole.UserRole))
                for item in self.layers.selectedItems()
            )
            self.update_inspector()

    def update_inspector(self) -> None:
        tab = self.current
        if tab and tab.view:
            tab.view.selection = tab.selection
            tab.view.viewport().update()
        selected = (
            tab.dispatcher.snapshot.project.document.nodes[tab.selection[0]]
            if tab and tab.selection
            else None
        )
        self.object_name.setText(selected.name if selected else "")
        self.object_name.setEnabled(
            bool(tab and len(tab.selection) == 1 and not tab.handle.read_only and not self.busy)
        )

    def rename_object(self) -> None:
        from dataclasses import replace

        tab = self.current
        if tab and tab.selection and self.object_name.isEnabled():
            node = tab.dispatcher.snapshot.project.document.nodes[tab.selection[0]]
            if node.name != self.object_name.text():
                self.execute(tab, (Update(node=replace(node, name=self.object_name.text())),))

    def execute(
        self,
        tab: Tab,
        operations: tuple[Any, ...] = (),
        action: Literal["execute", "undo", "redo"] = "execute",
    ) -> None:
        request = Request(
            session_id=tab.dispatcher.snapshot.session_id,
            expected_revision=tab.dispatcher.snapshot.revision,
            request_id=str(uuid4()),
            action_name="Edit",
            source="GUI",
            operations=operations,
            action=action,
        )
        result = tab.dispatcher.dispatch(request, client_id="local-user")
        if not result.ok:
            self.show_error(ValueError(str(result.error)))
        self.refresh()

    def history(self, action: Literal["undo", "redo"]) -> None:
        if self.current:
            self.execute(self.current, action=action)

    def refresh(self, *_: object) -> None:
        tab = self.current
        for key, action in self.menu_actions.items():
            action.setEnabled(
                not self.busy and (key in ("new", "open", "import") or tab is not None)
            )
        self.menu_actions["reload"].setEnabled(bool(tab and tab.handle.path and not self.busy))
        self.menu_actions["undo"].setEnabled(
            bool(tab and tab.dispatcher.undo_history and not tab.handle.read_only and not self.busy)
        )
        self.menu_actions["redo"].setEnabled(
            bool(tab and tab.dispatcher.redo_history and not tab.handle.read_only and not self.busy)
        )
        self.pages.blockSignals(True)
        self.layers.blockSignals(True)
        self.pages.clear()
        self.layers.clear()
        if tab:
            project = tab.dispatcher.snapshot.project
            if tab.view:
                tab.view.adapter.sync(project.document, tab.active_page)
            self.project_name.setText(project.document.name)
            self.pages.addItems([page.name for page in project.document.pages])
            self.pages.setCurrentRow(tab.active_page)

            def add(keys: tuple[NodeId, ...], parent: QTreeWidgetItem | None = None) -> None:
                for key in reversed(keys):
                    node = project.document.nodes[key]
                    item = QTreeWidgetItem([node.name or node.type])
                    item.setData(0, Qt.ItemDataRole.UserRole, key)
                    if parent:
                        parent.addChild(item)
                    else:
                        self.layers.addTopLevelItem(item)
                    item.setSelected(key in tab.selection)
                    add(node.children, item)

            add(project.document.pages[tab.active_page].root_ids)
            self.layers.expandAll()
        else:
            self.project_name.setText("—")
        self.pages.blockSignals(False)
        self.layers.blockSignals(False)
        self.update_inspector()
        for index, document in enumerate(self.documents):
            name = document.dispatcher.snapshot.project.document.name
            self.tabs.setTabText(
                index,
                name
                + (" *" if document.dispatcher.dirty else "")
                + (" [Read-only]" if document.handle.read_only else ""),
            )
        self.statusBar().showMessage(
            "Menyimpan / memuat…"
            if self.busy
            else f"{tab.status} | {tab.handle.path or 'Tanpa path'}"
            if tab
            else "Siap"
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.busy:
            event.ignore()
        elif self.documents:
            event.ignore()
            self._exit_requested = True
            self.close_tab(self.tabs.currentIndex())
        else:
            self.executor.shutdown(wait=False)
            event.accept()
