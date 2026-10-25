"""Inspector alignment actions publish through the same dispatcher as gestures."""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QGridLayout, QPushButton, QWidget

from ltechdesign.commands import ArrangeNodes
from ltechdesign.domain.arrangement import ArrangeMode, translations
from ltechdesign.domain.editing import roots

if TYPE_CHECKING:
    from .window import StudioWindow


class ArrangementControls(QWidget):
    def __init__(self, studio: "StudioWindow") -> None:
        super().__init__()
        self.studio = studio
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.buttons: dict[ArrangeMode, QPushButton] = {}
        entries: tuple[tuple[ArrangeMode, str], ...] = (
            ("left", "Left"),
            ("hcenter", "Center X"),
            ("right", "Right"),
            ("top", "Top"),
            ("vcenter", "Center Y"),
            ("bottom", "Bottom"),
            ("distribute_x", "Space H"),
            ("distribute_y", "Space V"),
        )
        for i, (mode, title) in enumerate(entries):
            button = QPushButton(title)
            button.setAccessibleName(f"Arrange {mode} in world geometry")
            button.setToolTip("Selection world geometry; Space = equal gaps, outer objects fixed.")
            button.clicked.connect(lambda checked=False, m=mode: self.perform(m))
            layout.addWidget(button, i // 3, i % 3)
            self.buttons[mode] = button

    def sync(self) -> None:
        tab = self.studio.current
        count = (
            len(roots(tab.dispatcher.snapshot.project.document, tab.selection))
            if tab and tab.selection
            else 0
        )
        writable = bool(tab and not tab.handle.read_only and not self.studio.busy)
        for mode, button in self.buttons.items():
            button.setEnabled(writable and count >= (3 if mode.startswith("distribute") else 2))

    def perform(self, mode: ArrangeMode) -> None:
        tab = self.studio.current
        if tab is None or not self.buttons[mode].isEnabled():
            return
        doc = tab.dispatcher.snapshot.project.document
        if not any(
            abs(p.x) > 1e-9 or abs(p.y) > 1e-9 for _, p in translations(doc, tab.selection, mode)
        ):
            return
        if tab.view:
            tab.view.cancel_gesture()
        self.studio.execute(
            tab,
            (ArrangeNodes(node_ids=tab.selection, mode=mode),),
            expected_revision=tab.dispatcher.snapshot.revision,
            action_name=f"Arrange {mode}",
        )
