"""Revision-bound layout Inspector. All changes go through the content dispatcher."""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QLineEdit, QPushButton, QWidget

from ltechdesign.commands import SetConstraints, SetLayout
from ltechdesign.commands.contracts import Operation
from ltechdesign.domain.errors import ModelError
from ltechdesign.domain.models import Constraints, Layout
from ltechdesign.domain.typing import typed

if TYPE_CHECKING:
    from .window import StudioWindow


class LayoutPanel(QWidget):
    def __init__(self, studio: "StudioWindow") -> None:
        super().__init__()
        self.studio = studio
        self.context: object = None
        self.fields: dict[str, QLineEdit | QComboBox] = {}
        form = QFormLayout(self)
        choices = {
            "stack": ("none", "horizontal", "vertical"),
            "align_main": ("start", "center", "end"),
            "align_cross": ("start", "center", "end", "stretch"),
            "sizing_x": ("fixed", "hug", "fill"),
            "sizing_y": ("fixed", "hug", "fill"),
            "horizontal": ("start", "end", "center", "stretch"),
            "vertical": ("start", "end", "center", "stretch"),
        }
        for key, label in (
            ("stack", "Stack"),
            ("padding", "Padding T,R,B,L"),
            ("gap", "Gap"),
            ("align_main", "Main alignment"),
            ("align_cross", "Cross alignment"),
            ("sizing_x", "Layout width"),
            ("sizing_y", "Layout height"),
            ("horizontal", "Parent horizontal"),
            ("vertical", "Parent vertical"),
        ):
            if key in choices:
                combo = QComboBox()
                combo.addItems(choices[key])
                field: QLineEdit | QComboBox = combo
            else:
                field = QLineEdit()
            field.setObjectName(f"layout_{key}")
            field.setAccessibleName(label)
            self.fields[key] = field
            form.addRow(label, field)
        self.apply_button = QPushButton("Apply layout / constraints")
        self.apply_button.clicked.connect(self.apply)
        form.addRow(self.apply_button)
        self.message = QLabel()
        self.message.setWordWrap(True)
        form.addRow(self.message)

    def text(self, key: str) -> str:
        field = self.fields[key]
        return field.currentText() if isinstance(field, QComboBox) else field.text().strip()

    def sync(self) -> None:
        tab = self.studio.current
        node = (
            tab.dispatcher.snapshot.project.document.nodes[tab.selection[0]]
            if tab and len(tab.selection) == 1
            else None
        )
        self.setVisible(node is not None)
        self.setEnabled(bool(node and tab and not tab.handle.read_only and not self.studio.busy))
        if node is None or tab is None:
            self.context = None
            return
        self.context = (tab, tab.selection, tab.dispatcher.snapshot.revision)
        layout, constraints = node.layout or Layout(), node.constraints or Constraints()
        source = layout if node.layout else constraints
        values = {
            "stack": node.layout.direction if node.layout else "none",
            "padding": ", ".join(format(v, ".12g") for v in layout.padding),
            "gap": format(layout.gap, ".12g"),
            "align_main": layout.align_main,
            "align_cross": layout.align_cross,
            "sizing_x": source.sizing_x,
            "sizing_y": source.sizing_y,
            "horizontal": constraints.horizontal,
            "vertical": constraints.vertical,
        }
        for key, value in values.items():
            field = self.fields[key]
            if isinstance(field, QComboBox):
                field.setCurrentText(value)
            else:
                field.setText(value)
            field.setEnabled(key != "stack" or node.type in ("frame", "artboard"))
            if key in ("horizontal", "vertical"):
                parent = (
                    tab.dispatcher.snapshot.project.document.nodes.get(node.parent_id)
                    if node.parent_id is not None
                    else None
                )
                field.setEnabled(
                    bool(parent and parent.type in ("frame", "artboard") and not parent.layout)
                )
        self.message.setText(
            "Stack mengatur posisi anak. Overflow tetap terlihat kecuali Clip aktif. "
            "Hug/fill siklik dan transform anak stack ditolak."
        )

    def apply(self) -> None:
        tab = self.studio.current
        if (
            tab is None
            or not self.isEnabled()
            or self.context != (tab, tab.selection, tab.dispatcher.snapshot.revision)
        ):
            self.message.setText("Edit dibatalkan: selection atau revision berubah.")
            return
        node = tab.dispatcher.snapshot.project.document.nodes[tab.selection[0]]
        try:
            direction = self.text("stack")
            layout = (
                None
                if direction == "none"
                else typed(
                    {
                        "type": "stack",
                        "direction": direction,
                        "padding": [float(s.strip()) for s in self.text("padding").split(",")],
                        "gap": float(self.text("gap")),
                        "align_main": self.text("align_main"),
                        "align_cross": self.text("align_cross"),
                        "sizing_x": self.text("sizing_x"),
                        "sizing_y": self.text("sizing_y"),
                    },
                    Layout,
                    "$.layout",
                    wire=True,
                )
            )
            constraints = typed(
                {
                    "horizontal": self.text("horizontal"),
                    "vertical": self.text("vertical"),
                    "sizing_x": "fixed" if layout else self.text("sizing_x"),
                    "sizing_y": "fixed" if layout else self.text("sizing_y"),
                },
                Constraints,
                "$.constraints",
                wire=True,
            )
            # Default root constraints have no parent and are omitted entirely.
            supplied = (
                constraints if node.parent_id is not None and constraints != Constraints() else None
            )
            operations: tuple[Operation, ...] = (
                SetLayout(node_id=node.id, layout=layout),
                SetConstraints(node_id=node.id, constraints=supplied),
            )
            if node.parent_id is None and constraints != Constraints():
                raise ValueError("Constraints memerlukan parent frame.")
            self.studio.execute(
                tab,
                operations,
                expected_revision=tab.dispatcher.snapshot.revision,
                action_name="Layout / constraints",
            )
        except (ValueError, ModelError) as error:
            self.message.setText(f"Layout tidak valid: {error}")
