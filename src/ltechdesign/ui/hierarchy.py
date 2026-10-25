"""Pages/layers are document projections; user intents go through the dispatcher."""

from dataclasses import dataclass, field, replace
from html import escape
from typing import TYPE_CHECKING, Literal, cast

from PySide6.QtCore import (
    QAbstractItemModel,
    QMimeData,
    QModelIndex,
    QPersistentModelIndex,
    QPoint,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QDrag, QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ltechdesign.commands import (
    CreatePage,
    DeletePage,
    DuplicatePage,
    EditNodes,
    RelocateNodes,
    SetLayerState,
    Update,
    UpdatePage,
)
from ltechdesign.commands.contracts import Operation
from ltechdesign.commands.dispatcher import canonical
from ltechdesign.domain.codec import parse_json
from ltechdesign.domain.errors import ModelError
from ltechdesign.domain.models import (
    Document,
    NodeId,
    Page,
    PageId,
    Record,
    Revision,
    SessionId,
    new_id,
)
from ltechdesign.domain.typing import primitive, typed
from ltechdesign.rendering.hit_testing import eligible

if TYPE_CHECKING:
    from .window import StudioWindow, Tab

MIME = "application/x-ltechdesign-layer-move-v1"
DropPlace = Literal["above", "below", "inside", "root"]


@dataclass
class HierarchyState:
    search: str = ""
    type_filter: str = ""
    collapsed: set[NodeId] = field(default_factory=set)


@dataclass(frozen=True, slots=True, kw_only=True)
class LayerDrag(Record):
    session_id: SessionId
    page_id: PageId
    revision: Revision
    node_ids: tuple[NodeId, ...]


class LayerTree(QTreeWidget):
    def __init__(self, panel: "HierarchyPanel") -> None:
        super().__init__(panel)
        self.panel = panel
        self.setHeaderLabels(["Layer", "Type", "Shown", "Locked"])
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setColumnWidth(0, 150)
        self.setColumnWidth(1, 75)
        self.setColumnWidth(2, 50)
        self.setColumnWidth(3, 50)
        self.setAccessibleName("Layers — nama, tipe, visibility, lock dan drag hierarchy")

    def mimeTypes(self) -> list[str]:
        return [MIME]

    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.MoveAction

    def create_mime(self, keys: tuple[NodeId, ...] | None = None) -> QMimeData:
        tab = self.panel.studio.current
        if tab is None:
            return QMimeData()
        selected = (
            keys
            if keys is not None
            else tuple(NodeId(i.data(0, Qt.ItemDataRole.UserRole)) for i in self.selectedItems())
        )
        payload = LayerDrag(
            session_id=tab.dispatcher.snapshot.session_id,
            page_id=tab.dispatcher.snapshot.project.document.pages[tab.active_page].id,
            revision=tab.dispatcher.snapshot.revision,
            node_ids=selected,
        )
        mime = QMimeData()
        mime.setData(MIME, canonical(primitive(payload)))
        return mime

    def startDrag(self, supportedActions: Qt.DropAction) -> None:
        if not self.panel.writable() or not self.selectedItems():
            return
        drag = QDrag(self)
        drag.setMimeData(self.create_mime())
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        mime = event.mimeData()
        if mime and mime.hasFormat(MIME) and self.panel.writable():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        super().dragMoveEvent(event)
        mime = event.mimeData()
        if mime and mime.hasFormat(MIME) and self.panel.writable():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        item = self.itemAt(event.position().toPoint())
        indicator = self.dropIndicatorPosition()
        place: DropPlace = "root"
        if item:
            place = cast(
                DropPlace,
                {
                    QAbstractItemView.DropIndicatorPosition.AboveItem: "above",
                    QAbstractItemView.DropIndicatorPosition.BelowItem: "below",
                }.get(indicator, "inside"),
            )
        mime = event.mimeData()
        key = NodeId(item.data(0, Qt.ItemDataRole.UserRole)) if item else None
        if mime and self.panel.drop_on(mime, key, place):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
        else:
            event.ignore()
        # Never call the Qt implementation: it would mutate the projection independently.
        self.setState(QAbstractItemView.State.NoState)
        self.viewport().update()


class LayerNames(QStyledItemDelegate):
    def __init__(self, panel: "HierarchyPanel") -> None:
        super().__init__(panel.layers)
        self.panel = panel

    # Qt permits a null editor; the PySide stub omits the nullable return.
    def createEditor(  # type: ignore[override]
        self,
        parent: QWidget,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> QWidget | None:
        tab = self.panel.studio.current
        if index.column() != 0 or tab is None or not self.panel.writable():
            return None
        editor = QLineEdit(parent)
        editor.setProperty("node_id", index.data(Qt.ItemDataRole.UserRole))
        editor.setProperty("revision", tab.dispatcher.snapshot.revision)
        editor.setProperty("session_id", tab.dispatcher.snapshot.session_id)
        return editor

    def setEditorData(self, editor: QWidget, index: QModelIndex | QPersistentModelIndex) -> None:
        tab = self.panel.studio.current
        if isinstance(editor, QLineEdit) and tab:
            key = NodeId(editor.property("node_id"))
            editor.setText(tab.dispatcher.snapshot.project.document.nodes[key].name)

    def setModelData(
        self, editor: QWidget, model: QAbstractItemModel, index: QModelIndex | QPersistentModelIndex
    ) -> None:
        if isinstance(editor, QLineEdit) and not self.panel.syncing:
            key = NodeId(editor.property("node_id"))
            name = editor.text()
            revision = int(editor.property("revision"))
            session = str(editor.property("session_id"))
            # Publish after Qt finishes commitData/closeEditor, before rebuilding rows.
            QTimer.singleShot(
                0, lambda: self.panel.rename_node(key, name, revision=revision, session=session)
            )


class HierarchyPanel(QWidget):
    message = Signal(str)

    def __init__(self, window: "StudioWindow") -> None:
        super().__init__(window)
        self.studio = window
        self.items: dict[NodeId, QTreeWidgetItem] = {}
        self.syncing = False
        self._document: Document | None = None
        self._page: PageId | None = None
        self._tab: Tab | None = None
        self._writable = False
        self.context: QMenu | None = None
        self.pages = QListWidget()
        self.pages.setAccessibleName("Pages")
        self.pages.itemDoubleClicked.connect(lambda item: self.page_action("rename"))
        self.artboards = QListWidget()
        self.artboards.setAccessibleName("Artboards pada page aktif")
        self.artboards.currentItemChanged.connect(self.artboard_selected)
        self.artboards.itemDoubleClicked.connect(self.fit_artboard)
        self.layers = LayerTree(self)
        self.layers.setItemDelegate(LayerNames(self))
        self.layers.itemChanged.connect(self.item_changed)
        self.layers.itemCollapsed.connect(lambda item: self.collapse(item, True))
        self.layers.itemExpanded.connect(lambda item: self.collapse(item, False))
        self.layers.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.layers.customContextMenuRequested.connect(self.layer_context)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Cari nama atau tipe layer…")
        self.search.setAccessibleName("Pencarian layer berdasarkan nama atau tipe")
        self.search.textChanged.connect(self.filter_changed)
        self.types = QComboBox()
        self.types.addItems(
            [
                "Semua tipe",
                "artboard",
                "frame",
                "group",
                "rectangle",
                "ellipse",
                "line",
                "polygon",
                "text",
                "image",
                "svg",
            ]
        )
        self.types.setAccessibleName("Filter tipe layer")
        self.types.currentIndexChanged.connect(self.filter_changed)
        self.preserve = QCheckBox("Pertahankan tampilan saat pindah parent")
        self.preserve.setChecked(True)
        self.preserve.setToolTip(
            "Tolak perubahan clip/opacity yang tidak bisa dipertahankan. "
            "Matikan untuk mengubah konteks clip/opacity secara eksplisit."
        )
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Pages"))
        layout.addWidget(self.pages, 1)
        buttons = QHBoxLayout()
        self.page_buttons: dict[str, QPushButton] = {}
        for action, label in (
            ("create", "+ Page"),
            ("rename", "Rename"),
            ("duplicate", "Duplicate"),
            ("delete", "Delete"),
        ):
            button = QPushButton(label)
            button.setAccessibleName(f"{label} page")
            button.clicked.connect(lambda checked=False, a=action: self.page_action(a))
            self.page_buttons[action] = button
            buttons.addWidget(button)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("Artboards"))
        layout.addWidget(self.artboards, 1)
        layout.addWidget(QLabel("Layers"))
        layout.addWidget(self.search)
        layout.addWidget(self.types)
        layout.addWidget(self.layers, 3)
        layout.addWidget(self.preserve)

    def writable(self) -> bool:
        tab = self.studio.current
        return bool(tab and not tab.handle.read_only and not self.studio.busy)

    def page_action(self, action: str) -> None:
        tab = self.studio.current
        if tab is None or not self.writable():
            return
        doc = tab.dispatcher.snapshot.project.document
        page = doc.pages[tab.active_page]
        revision = tab.dispatcher.snapshot.revision
        activate: PageId | None = None
        operation: Operation
        if action in ("create", "rename"):
            name, accepted = QInputDialog.getText(
                self, "Page", "Nama page:", text="New page" if action == "create" else page.name
            )
            if not accepted or not name.strip():
                return
            if action == "create":
                new = Page(name=name.strip())
                operation = CreatePage(page=new)
                activate = new.id
            else:
                operation = UpdatePage(page_id=page.id, name=name.strip())
        elif action == "duplicate":
            activate = PageId(new_id())
            operation = DuplicatePage(page_id=page.id, new_page_id=activate)
        elif action == "delete":
            if len(doc.pages) == 1:
                return
            if (
                page.root_ids
                and QMessageBox.question(
                    self,
                    "Delete page",
                    f"<p>Hapus page <b>{escape(page.name)}</b> beserta seluruh isinya? "
                    "Dapat di-undo.</p>",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                != QMessageBox.StandardButton.Yes
            ):
                return
            operation = DeletePage(page_id=page.id, delete_contents=True)
        else:
            return
        if (
            self.studio.execute(
                tab, (operation,), expected_revision=revision, action_name=action.title() + " page"
            )
            and activate
        ):
            self.studio.activate_page(tab, activate)

    def rename_node(
        self, key: NodeId, name: str, *, revision: int | None = None, session: str | None = None
    ) -> None:
        tab = self.studio.current
        if not tab or not self.writable():
            return
        if session is not None and session != tab.dispatcher.snapshot.session_id:
            self.message.emit("Rename dibatalkan: sesi berubah.")
            return
        doc = tab.dispatcher.snapshot.project.document
        if key in doc.nodes and name != doc.nodes[key].name:
            self.studio.execute(
                tab,
                (Update(node=replace(doc.nodes[key], name=name)),),
                expected_revision=revision,
                action_name="Rename layer",
            )

    def item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self.syncing or not self.writable():
            return
        tab = self.studio.current
        assert tab is not None
        key = NodeId(item.data(0, Qt.ItemDataRole.UserRole))
        revision = tab.dispatcher.snapshot.revision
        operation: Operation
        if column == 0:
            node = tab.dispatcher.snapshot.project.document.nodes[key]
            if node.name == item.text(0):
                return
            operation = Update(node=replace(node, name=item.text(0)))
        elif column in (2, 3):
            checked = item.checkState(column) == Qt.CheckState.Checked
            operation = SetLayerState(
                node_ids=(key,),
                visible=checked if column == 2 else None,
                locked=checked if column == 3 else None,
            )
        else:
            return

        def submit() -> None:
            if tab in self.studio.documents:
                self.studio.execute(
                    tab, (operation,), expected_revision=revision, action_name="Layer edit"
                )

        QTimer.singleShot(0, submit)

    def drop_on(self, mime: QMimeData, target: NodeId | None, place: DropPlace) -> bool:
        tab = self.studio.current
        if not tab or not self.writable() or not mime.hasFormat(MIME):
            return False
        try:
            payload = cast(
                LayerDrag,
                typed(parse_json(bytes(mime.data(MIME).data())), LayerDrag, "$", wire=True),
            )
            snapshot = tab.dispatcher.snapshot
            doc = snapshot.project.document
            page = doc.pages[tab.active_page]
            if payload.session_id != snapshot.session_id or payload.page_id != page.id:
                raise ModelError("drag_session_or_page_changed", code="session_closed")
            if any(
                k not in doc.nodes or doc.nodes[k].page_id != page.id or not eligible(doc, k)
                for k in payload.node_ids
            ):
                raise ModelError("layer_not_draggable", code="validation_error")
            parent = None
            index = None
            if target is not None:
                node = doc.nodes[target]
                if not eligible(doc, target):
                    raise ModelError("target_not_editable", code="validation_error")
                if place == "inside":
                    if node.type not in ("artboard", "frame", "group"):
                        raise ModelError("invalid_parent", code="validation_error")
                    parent = target
                else:
                    parent = node.parent_id
                    siblings = doc.nodes[parent].children if parent else page.root_ids
                    remaining = tuple(k for k in siblings if k not in payload.node_ids)
                    if target not in remaining:
                        return False
                    index = remaining.index(target) + (1 if place == "above" else 0)
            operation = RelocateNodes(
                node_ids=payload.node_ids,
                page_id=page.id,
                parent_id=parent,
                index=index,
                preserve_appearance=self.preserve.isChecked(),
            )
            return self.studio.execute(
                tab, (operation,), expected_revision=payload.revision, action_name="Move layers"
            )
        except (ModelError, KeyError, ValueError) as error:
            self.studio.show_error(error)
            return False

    def collapse(self, item: QTreeWidgetItem, collapsed: bool) -> None:
        tab = self.studio.current
        if not tab or self.syncing:
            return
        key = NodeId(item.data(0, Qt.ItemDataRole.UserRole))
        if collapsed:
            tab.hierarchy_state.collapsed.add(key)
        else:
            tab.hierarchy_state.collapsed.discard(key)

    def filter_changed(self, *_: object) -> None:
        tab = self.studio.current
        if tab and not self.syncing:
            tab.hierarchy_state.search = self.search.text()
            tab.hierarchy_state.type_filter = (
                self.types.currentText() if self.types.currentIndex() > 0 else ""
            )
            self.apply_filter()

    def apply_filter(self) -> None:
        tab = self.studio.current
        if tab is None:
            return
        doc = tab.dispatcher.snapshot.project.document
        query = self.search.text().casefold()
        kind = self.types.currentText() if self.types.currentIndex() > 0 else ""
        visible: set[NodeId] = set()
        for key in self.items:
            node = doc.nodes[key]
            if (not query or query in node.name.casefold() or query in node.type) and (
                not kind or node.type == kind
            ):
                cursor: NodeId | None = key
                while cursor is not None:
                    visible.add(cursor)
                    cursor = doc.nodes[cursor].parent_id
        previous = self.layers.blockSignals(True)
        for key, item in self.items.items():
            item.setHidden(key not in visible)
        self.layers.blockSignals(previous)

    def reveal(self, keys: tuple[NodeId, ...]) -> None:
        if not keys:
            return
        if any(k in self.items and self.items[k].isHidden() for k in keys):
            self.search.clear()
            self.types.setCurrentIndex(0)
        for key in keys:
            item = self.items.get(key)
            if item:
                parent = item.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()
        if keys[0] in self.items:
            self.layers.scrollToItem(self.items[keys[0]])

    def artboard_selected(
        self, item: QListWidgetItem | None, previous: QListWidgetItem | None
    ) -> None:
        tab = self.studio.current
        if item and tab and tab.view and not self.syncing:
            tab.view.set_selection((NodeId(item.data(Qt.ItemDataRole.UserRole)),))

    def fit_artboard(self, item: QListWidgetItem) -> None:
        tab = self.studio.current
        key = NodeId(item.data(Qt.ItemDataRole.UserRole))
        if tab and tab.view and key in tab.view.adapter.items:
            tab.view.fit_bounds(tab.view.adapter.items[key].sceneBoundingRect())

    def sync_artboard_selection(self, keys: tuple[NodeId, ...]) -> None:
        previous = self.artboards.blockSignals(True)
        row = next(
            (
                i
                for i in range(self.artboards.count())
                if self.artboards.item(i).data(Qt.ItemDataRole.UserRole) in keys
            ),
            -1,
        )
        self.artboards.setCurrentRow(row)
        self.artboards.blockSignals(previous)

    def layer_context(self, pos: QPoint) -> None:
        item = self.layers.itemAt(pos)
        tab = self.studio.current
        if item is None or tab is None:
            return
        key = NodeId(item.data(0, Qt.ItemDataRole.UserRole))
        node = tab.dispatcher.snapshot.project.document.nodes[key]
        if self.context:
            self.context.close()
            self.context.deleteLater()
        self.context = QMenu(self)
        for label, op in (
            (
                "Hide" if node.visible else "Show",
                SetLayerState(node_ids=(key,), visible=not node.visible),
            ),
            (
                "Unlock" if node.locked else "Lock",
                SetLayerState(node_ids=(key,), locked=not node.locked),
            ),
            ("Duplicate", EditNodes(node_ids=(key,), edit="duplicate")),
        ):
            action = self.context.addAction(label)
            action.setEnabled(
                self.writable()
                and (
                    label != "Duplicate" or eligible(tab.dispatcher.snapshot.project.document, key)
                )
            )
            action.triggered.connect(
                lambda checked=False, intent=op: self.studio.execute(
                    tab, (intent,), action_name="Layer"
                )
            )
        rename = self.context.addAction("Rename")
        rename.setEnabled(
            self.writable() and eligible(tab.dispatcher.snapshot.project.document, key)
        )
        rename.triggered.connect(lambda: self.layers.editItem(item, 0))
        self.context.popup(self.layers.viewport().mapToGlobal(pos))

    def sync(self) -> None:
        tab = self.studio.current
        self.syncing = True
        self.pages.blockSignals(True)
        self.layers.blockSignals(True)
        self.artboards.blockSignals(True)
        self.search.blockSignals(True)
        self.types.blockSignals(True)
        try:
            for action, button in self.page_buttons.items():
                button.setEnabled(
                    self.writable()
                    and (
                        action != "delete"
                        or bool(tab and len(tab.dispatcher.snapshot.project.document.pages) > 1)
                    )
                )
            if tab is None:
                self.pages.clear()
                self.layers.clear()
                self.artboards.clear()
                self.items.clear()
                self._document = None
                self._tab = None
                return
            doc = tab.dispatcher.snapshot.project.document
            page = doc.pages[tab.active_page]
            self.search.setText(tab.hierarchy_state.search)
            self.types.setCurrentIndex(max(0, self.types.findText(tab.hierarchy_state.type_filter)))
            if (
                doc is not self._document
                or tab is not self._tab
                or self._page != page.id
                or self._writable != self.writable()
            ):
                if self.context:
                    self.context.close()
                    self.context.deleteLater()
                    self.context = None
                scroll = self.layers.verticalScrollBar().value()
                self.pages.clear()
                for p in doc.pages:
                    item = QListWidgetItem(p.name)
                    item.setData(Qt.ItemDataRole.UserRole, p.id)
                    self.pages.addItem(item)
                self.layers.clear()
                self.items.clear()
                self.artboards.clear()

                def add(keys: tuple[NodeId, ...], parent: QTreeWidgetItem | None = None) -> None:
                    for key in reversed(keys):
                        node = doc.nodes[key]
                        item = QTreeWidgetItem([node.name or node.type, node.type])
                        item.setToolTip(0, "<qt>" + escape(node.name or node.type) + "</qt>")
                        item.setData(0, Qt.ItemDataRole.UserRole, key)
                        item.setCheckState(
                            2, Qt.CheckState.Checked if node.visible else Qt.CheckState.Unchecked
                        )
                        item.setCheckState(
                            3, Qt.CheckState.Checked if node.locked else Qt.CheckState.Unchecked
                        )
                        flags = item.flags()
                        if self.writable():
                            flags |= Qt.ItemFlag.ItemIsUserCheckable
                        else:
                            flags &= ~Qt.ItemFlag.ItemIsUserCheckable
                        if eligible(doc, key):
                            if self.writable():
                                flags |= Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled
                            else:
                                flags &= ~(
                                    Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled
                                )
                            if self.writable() and node.type in ("artboard", "frame", "group"):
                                flags |= Qt.ItemFlag.ItemIsDropEnabled
                            else:
                                flags &= ~Qt.ItemFlag.ItemIsDropEnabled
                        else:
                            flags &= ~(
                                Qt.ItemFlag.ItemIsSelectable
                                | Qt.ItemFlag.ItemIsEditable
                                | Qt.ItemFlag.ItemIsDragEnabled
                                | Qt.ItemFlag.ItemIsDropEnabled
                            )
                            item.setForeground(0, QColor("#777777"))
                        item.setFlags(flags)
                        if parent:
                            parent.addChild(item)
                        else:
                            self.layers.addTopLevelItem(item)
                        self.items[key] = item
                        add(node.children, item)
                        item.setExpanded(key not in tab.hierarchy_state.collapsed)

                add(page.root_ids)
                for key in page.root_ids:
                    node = doc.nodes[key]
                    if node.type == "artboard":
                        item = QListWidgetItem(
                            f"{node.name or 'Artboard'} — {node.width:g} × {node.height:g} px"
                        )
                        item.setData(Qt.ItemDataRole.UserRole, key)
                        if not eligible(doc, key):
                            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                        self.artboards.addItem(item)
                self.layers.verticalScrollBar().setValue(scroll)
            self.pages.setCurrentRow(tab.active_page)
            self._document, self._tab, self._page = doc, tab, page.id
            self._writable = self.writable()
            self.apply_filter()
            self.sync_artboard_selection(tab.selection)
        finally:
            self.pages.blockSignals(False)
            self.layers.blockSignals(False)
            self.artboards.blockSignals(False)
            self.search.blockSignals(False)
            self.types.blockSignals(False)
            self.syncing = False
