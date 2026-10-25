"""Local edit actions, safe focus routing and asynchronous structured clipboard."""

from typing import TYPE_CHECKING, Literal, cast

from PySide6.QtCore import QEvent, QMimeData, QObject, QPoint
from PySide6.QtGui import QAction, QKeyEvent
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QTextEdit,
)

from ltechdesign.commands import (
    EditNodes,
    Group,
    PasteNodes,
    RegisterAsset,
    ReparentNodes,
    TransformNodes,
)
from ltechdesign.commands.contracts import Operation
from ltechdesign.domain.editing import roots
from ltechdesign.domain.geometry import translation
from ltechdesign.domain.models import NodeId, new_id
from ltechdesign.persistence.clipboard import LIMITS, MIME, decode_selection, encode_selection
from ltechdesign.rendering.hit_testing import eligible

from .transforms import edit_shortcut

if TYPE_CHECKING:
    from .canvas import EditorCanvas
    from .window import StudioWindow, Tab

LABELS = {
    "delete": "Delete (Delete)",
    "duplicate": "Duplicate (Ctrl+D)",
    "cut": "Cut (Ctrl+X)",
    "copy": "Copy (Ctrl+C)",
    "paste": "Paste (Ctrl+V)",
    "group": "Group (Ctrl+G)",
    "ungroup": "Ungroup (Ctrl+Shift+G)",
    "forward": "Bring Forward (Ctrl+])",
    "backward": "Send Backward (Ctrl+[)",
}


class EditingActions(QObject):
    def __init__(self, window: "StudioWindow", menu: QMenu) -> None:
        super().__init__(window)
        self.window = window
        self.actions: dict[str, QAction] = {}
        for key, label in LABELS.items():
            action = menu.addAction(label)
            action.triggered.connect(lambda checked=False, k=key: self.perform(k))
            self.actions[key] = action
        window.layers.installEventFilter(self)
        self.context: QMenu | None = None

    def bind(self, tab: "Tab", view: "EditorCanvas") -> None:
        view.apply_operations = lambda ops, revision, name: self.window.execute(
            tab, ops, expected_revision=revision, action_name=name
        )
        view.action_requested.connect(self.perform)
        view.context_requested.connect(lambda pos: self.show_context(tab, pos))

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.window.layers and event.type() == QEvent.Type.KeyPress:
            if isinstance(
                QApplication.focusWidget(), (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox)
            ):
                return False
            assert isinstance(event, QKeyEvent)
            if action := edit_shortcut(event):
                self.perform(action)
                return True
        return super().eventFilter(watched, event)

    def refresh(self) -> None:
        tab = self.window.current
        for key, action in self.actions.items():
            action.setEnabled(
                bool(
                    tab
                    and not self.window.busy
                    and (key == "paste" or tab.selection)
                    and (key == "copy" or not tab.handle.read_only)
                )
            )

    def perform(self, action: str) -> None:
        window, tab = self.window, self.window.current
        if tab is None or tab.view is None:
            return
        if action == "select_all":
            tab.view.select_all()
            return
        if action in ("undo", "redo"):
            window.history(cast(Literal["undo", "redo"], action))
            return
        if window.busy or (tab.handle.read_only and action != "copy"):
            return
        tab.view.cancel_gesture()
        if action in ("copy", "cut"):
            if tab.selection:
                self.copy(tab, cut=action == "cut")
            return
        if action == "paste":
            self.paste(tab)
            return
        if not tab.selection:
            return
        document = tab.dispatcher.snapshot.project.document
        selected = roots(document, tab.selection)
        revision = tab.dispatcher.snapshot.revision
        operations: tuple[Operation, ...]
        selection = selected
        if action.startswith("nudge_"):
            _, direction, amount = action.split("_")
            step = int(amount)
            dx, dy = {"left": (-step, 0), "right": (step, 0), "up": (0, -step), "down": (0, step)}[
                direction
            ]
            operations = (TransformNodes(node_ids=selected, matrix=translation(dx, dy)),)
        elif action == "group":
            key = NodeId(new_id())
            operations = (Group(node_ids=selected, group_id=key),)
            selection = (key,)
        elif action in ("delete", "duplicate", "forward", "backward", "ungroup"):
            operations = (
                EditNodes(
                    node_ids=selected,
                    edit=cast(
                        Literal["delete", "duplicate", "forward", "backward", "ungroup"], action
                    ),
                ),
            )
            if action == "ungroup":
                selection = tuple(child for k in selected for child in document.nodes[k].children)
        else:
            return
        if window.execute(tab, operations, expected_revision=revision, action_name=action.title()):
            after = tab.dispatcher.snapshot.project.document
            if action == "duplicate":
                added = after.nodes.keys() - document.nodes.keys()
                selection = tuple(k for k in added if after.nodes[k].parent_id not in added)
            tab.view.set_selection(selection if action != "delete" else ())

    def copy(self, tab: "Tab", *, cut: bool) -> None:
        snapshot = tab.dispatcher.snapshot
        keys = roots(snapshot.project.document, tab.selection)
        lease = tab.store.pin(snapshot.project.assets.assets)

        def work() -> bytes:
            try:
                return encode_selection(snapshot.project, keys, lease.blobs)
            finally:
                lease.release()

        def success(payload: bytes) -> None:
            mime = QMimeData()
            mime.setData(MIME, payload)
            QApplication.clipboard().setMimeData(mime)
            if cut:
                self.window.execute(
                    tab,
                    (EditNodes(node_ids=keys, edit="delete"),),
                    expected_revision=snapshot.revision,
                    action_name="Cut",
                )

        self.window.job(work, success)

    def paste(self, tab: "Tab") -> None:
        mime = QApplication.clipboard().mimeData()
        if mime is None or not mime.hasFormat(MIME):
            return
        data = mime.data(MIME)
        if data.size() > LIMITS.archive_bytes:
            self.window.show_error(ValueError("clipboard_bytes"))
            return
        payload = bytes(data.data())
        snapshot = tab.dispatcher.snapshot
        page = snapshot.project.document.pages[tab.active_page].id
        parent = None
        if len(tab.selection) == 1:
            node = snapshot.project.document.nodes[tab.selection[0]]
            if node.type in ("frame", "artboard"):
                parent = node.id

        def work() -> tuple[tuple[Operation, ...], tuple[NodeId, ...], tuple[str, ...]]:
            staged: list[str] = []
            try:
                loaded = decode_selection(payload)
                project = loaded.project
                ops: list[Operation] = []
                for asset in project.assets.assets:
                    key = tab.store.stage(asset, loaded.blobs[asset.path])
                    staged.append(key)
                    ops.append(RegisterAsset(asset=asset, staging_id=key))
                target = (
                    None
                    if any(n.type == "artboard" for n in project.document.nodes.values())
                    else parent
                )
                ops.append(PasteNodes(project=project, page_id=page, parent_id=target))
                return tuple(ops), project.document.pages[0].root_ids, tuple(staged)
            except Exception:
                tab.store.discard_staging(tuple(staged))
                raise

        def success(
            prepared: tuple[tuple[Operation, ...], tuple[NodeId, ...], tuple[str, ...]],
        ) -> None:
            operations, keys, staged = prepared
            try:
                if self.window.execute(
                    tab, operations, expected_revision=snapshot.revision, action_name="Paste"
                ):
                    tab.selection = keys
                    self.window.refresh()
            finally:
                tab.store.discard_staging(staged)

        self.window.job(work, success)

    def menu(self, tab: "Tab") -> QMenu:
        menu = QMenu(self.window)
        for key, label in LABELS.items():
            action = menu.addAction(label)
            action.setObjectName(key)
            action.setEnabled(self.actions[key].isEnabled())
            action.triggered.connect(lambda checked=False, k=key: self.perform(k))
        if tab.selection and not tab.handle.read_only:
            reparent = menu.addMenu("Reparent (preserve appearance)")
            doc = tab.dispatcher.snapshot.project.document
            keys = roots(doc, tab.selection)
            targets = [None] + [
                n.id
                for n in doc.nodes.values()
                if n.type in ("frame", "artboard")
                and n.page_id == doc.nodes[keys[0]].page_id
                and eligible(doc, n.id)
            ]
            for target in targets:
                ancestor = target
                while ancestor is not None and ancestor not in keys:
                    ancestor = doc.nodes[ancestor].parent_id
                if ancestor in keys:
                    continue
                item = reparent.addAction(
                    "Page root" if target is None else doc.nodes[target].name or str(target)
                )
                item.triggered.connect(lambda checked=False, t=target: self.reparent(tab, keys, t))
        return menu

    def reparent(self, tab: "Tab", keys: tuple[NodeId, ...], parent: NodeId | None) -> None:
        self.window.execute(
            tab,
            (
                ReparentNodes(
                    node_ids=keys,
                    page_id=tab.dispatcher.snapshot.project.document.pages[tab.active_page].id,
                    parent_id=parent,
                ),
            ),
            action_name="Reparent",
        )

    def show_context(self, tab: "Tab", position: QPoint) -> None:
        if self.context:
            self.context.close()
            self.context.deleteLater()
        self.context = self.menu(tab)
        self.context.popup(position)
