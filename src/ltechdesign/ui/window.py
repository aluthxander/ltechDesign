"""GUI owns dispatchers; one I/O executor serializes persistence side effects."""

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from PySide6.QtCore import QItemSelection, QItemSelectionModel, QObject, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSpinBox,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ltechdesign.assets import BlobStore
from ltechdesign.commands import Create, Dispatcher, Request, Update
from ltechdesign.domain import create_project
from ltechdesign.domain.errors import ModelError
from ltechdesign.domain.models import Node, NodeId, NodeType, PageId, Point
from ltechdesign.persistence import FileHandle, PersistenceService, SaveResult
from ltechdesign.rendering.drawing import warnings as render_warnings
from ltechdesign.rendering.hit_testing import eligible, paint_order
from ltechdesign.ui.artboard import ArtboardDialog
from ltechdesign.ui.canvas import EditorCanvas
from ltechdesign.ui.canvas_aids import CanvasAidControls
from ltechdesign.ui.editing import EditingActions
from ltechdesign.ui.hierarchy import HierarchyPanel, HierarchyState
from ltechdesign.ui.inspector import InspectorPanel


class Completion(QObject):
    done = Signal(object, object)


@dataclass
class Tab:
    handle: FileHandle
    dispatcher: Dispatcher
    store: BlobStore
    widget: QWidget
    view: EditorCanvas | None = None
    selection: tuple[NodeId, ...] = ()
    active_page: int = 0
    active_page_id: PageId | None = None
    hierarchy_state: HierarchyState = field(default_factory=HierarchyState)
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
        self.hierarchy = HierarchyPanel(self)
        self.pages = self.hierarchy.pages
        self.pages.currentRowChanged.connect(self.page_changed)
        self.layers = self.hierarchy.layers
        self._layer_items = self.hierarchy.items
        self.layers.itemSelectionChanged.connect(self.selection_changed)
        self.hierarchy.message.connect(
            lambda message: self.statusBar().showMessage(message, 5000),
            Qt.ConnectionType.QueuedConnection,
        )
        self._dock("Pages / Layers", self.hierarchy, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.inspector = InspectorPanel(self)
        self.project_name = self.inspector.project_name
        self.object_name = self.inspector.object_name
        self._dock("Inspector", self.inspector, Qt.DockWidgetArea.RightDockWidgetArea)
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
            action = QAction(f"{key.title()} (canvas: {shortcut})", self)
            action.triggered.connect(lambda checked=False, k=key: self.history(k))
            self.menu_actions[key] = action
            edit_menu.addAction(action)
        select_all = edit_menu.addAction("Select all (canvas: Ctrl+A)")
        select_all.triggered.connect(self.select_all)
        self.menu_actions["select_all"] = select_all
        self.editing = EditingActions(self, edit_menu)
        insert_menu = self.menuBar().addMenu("&Insert")
        artboard = insert_menu.addAction("Artboard preset / custom…")
        artboard.triggered.connect(self.create_artboard)
        toolbar.addAction(artboard)
        self.menu_actions["artboard"] = artboard
        self.tool_actions: dict[NodeType | None, QAction] = {}
        tools = QActionGroup(self)
        drawing_tools: tuple[tuple[NodeType | None, str], ...] = (
            (None, "Select"),
            ("frame", "Frame"),
            ("rectangle", "Rectangle"),
            ("ellipse", "Ellipse"),
            ("line", "Line"),
            ("polygon", "Polygon"),
        )
        for kind, title in drawing_tools:
            action = toolbar.addAction(title)
            action.setCheckable(True)
            tools.addAction(action)
            action.triggered.connect(lambda checked=False, k=kind: self.set_tool(k))
            self.tool_actions[kind] = action
        toolbar.addWidget(QLabel("Polygon sides:"))
        self.polygon_sides = QSpinBox()
        self.polygon_sides.setRange(3, 64)
        self.polygon_sides.setValue(5)
        self.polygon_sides.setAccessibleName("Jumlah sisi polygon")
        self.polygon_sides.valueChanged.connect(self.set_polygon_sides)
        toolbar.addWidget(self.polygon_sides)
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

        def submit(node: Node, revision: int) -> bool:
            return self.execute(
                tab,
                (Create(node=node),),
                expected_revision=revision,
                action_name=f"Draw {node.type}",
            )

        view = EditorCanvas(dispatcher, submit)
        view.foreground = self.inspector.foreground
        view.background = self.inspector.background
        from PySide6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QPushButton

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
        layout.addLayout(controls)
        layout.addWidget(CanvasAidControls(view))
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
        self.editing.bind(tab, view)
        view.selection_changed.connect(lambda keys: self.canvas_selection(tab, keys))
        view.message.connect(
            lambda message: self.statusBar().showMessage(message, 5000),
            Qt.ConnectionType.QueuedConnection,
        )
        dispatcher.subscribe(lambda event: self.document_changed(tab))
        self.tabs.addTab(widget, handle.admission.project.document.name)
        self.tabs.setCurrentWidget(widget)
        self.refresh()

    def set_tool(self, tool: NodeType | None) -> None:
        if self.current and self.current.view:
            self.current.view.set_tool(tool)

    def set_polygon_sides(self, sides: int) -> None:
        if self.current and self.current.view:
            self.current.view.cancel_gesture()
            self.current.view.sides = sides

    def select_all(self) -> None:
        if self.current and self.current.view:
            self.current.view.select_all()

    def canvas_selection(self, tab: Tab, keys: tuple[NodeId, ...]) -> None:
        tab.selection = keys
        if tab is self.current:
            self.hierarchy.reveal(keys)
            self._sync_layer_selection(keys)
            self.hierarchy.sync_artboard_selection(keys)
            self.update_inspector()
            self.editing.refresh()

    def _sync_layer_selection(self, keys: tuple[NodeId, ...]) -> None:
        previous = self.layers.blockSignals(True)
        selection = QItemSelection()
        for key in keys:
            if key in self._layer_items:
                index = self.layers.indexFromItem(self._layer_items[key])
                selection.select(index, index)
        model = self.layers.selectionModel()
        assert model is not None
        model.select(
            selection,
            QItemSelectionModel.SelectionFlag.ClearAndSelect
            | QItemSelectionModel.SelectionFlag.Rows,
        )
        self.layers.blockSignals(previous)

    def create_artboard(self) -> None:
        tab = self.current
        if tab is None or tab.handle.read_only or self.busy or tab.view is None:
            return
        tab.view.cancel_gesture()
        revision = tab.dispatcher.snapshot.revision
        page = tab.dispatcher.snapshot.project.document.pages[tab.active_page]
        bounds = [tab.view.adapter.items[k].sceneBoundingRect() for k in page.root_ids]
        origin = Point(x=max((b.right() for b in bounds), default=-100) + 100)
        dialog = ArtboardDialog(self)
        dialog.background.setText(self.inspector.background)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        # Append to the right of existing root geometry, independent of pan/zoom.
        node = dialog.node(page.id, origin)
        if self.execute(
            tab, (Create(node=node),), expected_revision=revision, action_name="Create artboard"
        ):
            tab.view.set_selection((node.id,))
            tab.view.fit_bounds(tab.view.adapter.items[node.id].sceneBoundingRect())

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
        tab.dispatcher.end_history_group()
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
        tab = self.current
        if tab and 0 <= index < len(tab.dispatcher.snapshot.project.document.pages):
            self.activate_page(tab, tab.dispatcher.snapshot.project.document.pages[index].id)

    def activate_page(self, tab: Tab, page_id: PageId) -> None:
        pages = tab.dispatcher.snapshot.project.document.pages
        index = next((i for i, p in enumerate(pages) if p.id == page_id), None)
        if index is None:
            return
        if tab.active_page_id != page_id:
            tab.selection = ()
            if tab.view:
                tab.view.cancel_gesture()
        tab.active_page, tab.active_page_id = index, page_id
        if tab is self.current:
            self.refresh()

    def reconcile_tab(self, tab: Tab) -> None:
        doc = tab.dispatcher.snapshot.project.document
        previous = tab.active_page_id
        index = next((i for i, p in enumerate(doc.pages) if p.id == previous), None)
        tab.active_page = index if index is not None else min(tab.active_page, len(doc.pages) - 1)
        tab.active_page_id = doc.pages[tab.active_page].id
        if previous is not None and previous != tab.active_page_id:
            tab.selection = ()
            if tab.view:
                tab.view.cancel_gesture()
        tab.selection = tuple(
            k
            for k in tab.selection
            if k in doc.nodes and doc.nodes[k].page_id == tab.active_page_id and eligible(doc, k)
        )

    def document_changed(self, tab: Tab) -> None:
        if tab in self.documents:
            self.reconcile_tab(tab)
            self.refresh()

    def selection_changed(self) -> None:
        tab = self.current
        if tab:
            keys = tuple(
                NodeId(item.data(0, Qt.ItemDataRole.UserRole))
                for item in self.layers.selectedItems()
            )
            doc = tab.dispatcher.snapshot.project.document
            tab.selection = tuple(k for k in keys if eligible(doc, k))
            self._sync_layer_selection(tab.selection)
            self.hierarchy.sync_artboard_selection(tab.selection)
            self.update_inspector()
            self.editing.refresh()

    def update_inspector(self) -> None:
        tab = self.current
        if tab and tab.view:
            if tab.view.selection != tab.selection:
                tab.view.cancel_gesture()
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
        self.inspector.sync()

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
        *,
        expected_revision: int | None = None,
        action_name: str = "Edit",
        history_group: str | None = None,
    ) -> bool:
        request = Request(
            session_id=tab.dispatcher.snapshot.session_id,
            expected_revision=tab.dispatcher.snapshot.revision
            if expected_revision is None
            else expected_revision,
            request_id=str(uuid4()),
            action_name=action_name,
            source="GUI",
            operations=operations,
            action=action,
            history_group=history_group,
        )
        result = tab.dispatcher.dispatch(request, client_id="local-user")
        if not result.ok:
            assert result.error is not None
            self.show_error(
                ModelError(
                    result.error.message, code=result.error.code, details=dict(result.error.details)
                )
            )
            self.refresh()
        # Successful publication already notified the subscribed GUI once.
        return result.ok

    def history(self, action: Literal["undo", "redo"]) -> None:
        if self.current:
            self.execute(self.current, action=action)

    def refresh(self, *_: object) -> None:
        tab = self.current
        if tab:
            self.reconcile_tab(tab)
        if hasattr(self, "editing"):
            self.editing.refresh()
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
        writable = bool(tab and not tab.handle.read_only)
        self.menu_actions["artboard"].setEnabled(writable and not self.busy)
        for tool, action in self.tool_actions.items():
            action.setEnabled(bool(tab) and (tool is None or writable))
            action.setChecked(bool(tab and tab.view and tab.view.tool == tool))
        self.polygon_sides.setEnabled(writable)
        if tab and tab.view:
            self.polygon_sides.blockSignals(True)
            self.polygon_sides.setValue(tab.view.sides)
            self.polygon_sides.blockSignals(False)
        if tab:
            project = tab.dispatcher.snapshot.project
            allowed = set(paint_order(project.document, tab.active_page))
            tab.selection = tuple(
                k for k in tab.selection if k in allowed and eligible(project.document, k)
            )
            if tab.view:
                tab.view.sync(tab.active_page, writable=writable)
            self.project_name.setText(project.document.name)
        else:
            self.project_name.setText("—")
        self.hierarchy.sync()
        self._sync_layer_selection(tab.selection if tab else ())
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
