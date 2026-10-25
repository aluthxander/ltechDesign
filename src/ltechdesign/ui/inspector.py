"""Inspector is a projection with revision-bound field edits, never a second model."""

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFocusEvent, QKeyEvent
from PySide6.QtWidgets import (
    QColorDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QWidget,
)

from ltechdesign.commands import SetProperties
from ltechdesign.domain.errors import ModelError
from ltechdesign.domain.inspector import Property, supported, value
from ltechdesign.domain.models import NodeId
from ltechdesign.rendering.drawing import color

from .arrangement import ArrangementControls

if TYPE_CHECKING:
    from .window import StudioWindow, Tab


class Field(QLineEdit):
    started = Signal()
    stepped = Signal()

    def __init__(self, numeric: bool) -> None:
        super().__init__()
        self.numeric = numeric
        self.setMinimumWidth(85)

    def focusInEvent(self, event: QFocusEvent) -> None:
        super().focusInEvent(event)
        self.started.emit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.numeric and event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            try:
                number = float(self.text())
            except ValueError:
                return
            self.started.emit()
            step = 10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            self.setText(format(number + (step if event.key() == Qt.Key.Key_Up else -step), ".12g"))
            self.stepped.emit()
            event.accept()
            return
        super().keyPressEvent(event)


@dataclass
class Edit:
    tab: "Tab"
    selection: tuple[NodeId, ...]
    revision: int
    group: str


class InspectorPanel(QScrollArea):
    def __init__(self, window: "StudioWindow") -> None:
        super().__init__(window)
        self.setMinimumWidth(320)
        self.studio = window
        self.setWidgetResizable(True)
        body = QWidget()
        self.setWidget(body)
        form = QFormLayout(body)
        self.project_name = QLabel("—")
        self.project_name.setWordWrap(True)
        self.object_name = QLineEdit()
        self.object_name.setAccessibleName("Nama objek terpilih")
        self.object_name.editingFinished.connect(window.rename_object)
        form.addRow("Proyek", self.project_name)
        form.addRow("Nama objek", self.object_name)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        form.addRow(self.summary)
        self.arrangement = ArrangementControls(window)
        form.addRow(self.arrangement)
        self.fields: dict[str, Field] = {}
        self.pickers: dict[str, QPushButton] = {}
        self.edits: dict[str, Edit] = {}
        self.publishing = False
        self.context: tuple[object, ...] | None = None
        labels = (
            ("x", "X · parent px"),
            ("y", "Y · parent px"),
            ("width", "Width"),
            ("height", "Height"),
            ("rotation", "Rotation °"),
            ("opacity", "Opacity · 0–1"),
            ("fill", "Fill"),
            ("stroke", "Stroke · center"),
            ("stroke_width", "Stroke width"),
            ("radius", "Radius · all corners"),
            ("background", "Frame background"),
            ("shadow_enabled", "Shadow · 0/1"),
            ("shadow_x", "Shadow X"),
            ("shadow_y", "Shadow Y"),
            ("shadow_blur", "Shadow blur σ"),
            ("shadow_spread", "Shadow spread"),
            ("shadow_color", "Shadow color"),
        )
        colors = {"fill", "stroke", "background", "shadow_color"}
        for key, title in labels:
            field = Field(key not in colors)
            field.setAccessibleName(title)
            field.setObjectName(f"inspector_{key}")
            field.started.connect(lambda k=key: self.begin(k))
            field.textEdited.connect(lambda text, k=key: self.begin(k))
            field.stepped.connect(lambda k=key: self.commit(k))
            field.editingFinished.connect(lambda k=key: self.finish(k))
            self.fields[key] = field
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(field, 1)
            if key in colors:
                field.setToolTip("#RRGGBB / #RRGGBBAA; none untuk tanpa fill/stroke/background")
                picker = QPushButton("…")
                picker.setAccessibleName(f"Color picker {title}")
                picker.setFixedWidth(28)
                picker.clicked.connect(lambda checked=False, k=key: self.pick(k))
                layout.addWidget(picker)
                self.pickers[key] = picker
            form.addRow(title, row)
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(0, 100)
        self.opacity.setAccessibleName("Opacity slider percent; Mixed memakai input angka")
        self.opacity.sliderPressed.connect(lambda: self.begin("opacity"))
        self.opacity.valueChanged.connect(self.slide)
        self.opacity.sliderReleased.connect(lambda: self.edits.pop("opacity", None))
        opacity_row = self.fields["opacity"].parentWidget()
        assert opacity_row is not None
        row_index = cast(tuple[int, object], form.getWidgetPosition(opacity_row))[0]
        form.insertRow(row_index + 1, self.opacity)
        self.feedback = QLabel()
        self.feedback.setWordWrap(True)
        self.feedback.setAccessibleName("Validasi Inspector")
        form.addRow(self.feedback)
        note = QLabel(
            "Mixed = nilai berbeda. Width/Height group menjaga rasio dan mencakup scale. "
            "Shadow mengedit efek pertama; efek lain tetap tersimpan."
        )
        note.setWordWrap(True)
        form.addRow(note)
        self.foreground = "#80B8E8FF"
        self.background = "#FFFFFFFF"
        self.foreground_button = QPushButton()
        self.background_button = QPushButton()
        for key, title in (
            ("foreground", "Foreground · new shapes"),
            ("background", "Background · new frames/artboards"),
        ):
            button = self.foreground_button if key == "foreground" else self.background_button
            button.setAccessibleName(title)
            button.clicked.connect(lambda checked=False, k=key: self.pick_palette(k))
            form.addRow(title, button)
        self.sync_palette()

    def begin(self, key: str) -> None:
        tab = self.studio.current
        if tab and tab.selection and self.fields[key].isEnabled() and key not in self.edits:
            self.edits[key] = Edit(
                tab, tab.selection, tab.dispatcher.snapshot.revision, str(uuid4())
            )

    def finish(self, key: str) -> None:
        self.commit(key)
        self.edits.pop(key, None)

    def commit(self, key: str) -> None:
        edit = self.edits.get(key)
        if edit is None:
            return
        tab = self.studio.current
        if (
            tab is not edit.tab
            or tab.selection != edit.selection
            or tab.dispatcher.snapshot.revision != edit.revision
            or not self.fields[key].isEnabled()
        ):
            self.edits.pop(key, None)
            self.sync()
            self.feedback.setText("Edit dibatalkan: selection atau revision berubah.")
            return
        field = self.fields[key]
        try:
            text = field.text().strip()
            supplied: float | str | None
            if field.numeric:
                supplied = float(text)
                if not math.isfinite(supplied):
                    raise ValueError("Gunakan angka finite.")
            else:
                supplied = None if text.lower() == "none" else text.upper()
                if supplied is not None and len(supplied) == 7:
                    supplied += "FF"
            from ltechdesign.domain.inspector import inspected

            nodes = tab.dispatcher.snapshot.project.document.nodes
            changed = [inspected(nodes[k], key, supplied) for k in edit.selection]
            if all(n == nodes[n.id] for n in changed):
                self.sync()
                return
            self.publishing = True
            try:
                success = self.studio.execute(
                    tab,
                    (
                        SetProperties(
                            node_ids=edit.selection, property=cast(Property, key), value=supplied
                        ),
                    ),
                    expected_revision=edit.revision,
                    action_name=f"Inspector {key}",
                    history_group=edit.group,
                )
            finally:
                self.publishing = False
            if success:
                edit.revision = tab.dispatcher.snapshot.revision
                self.feedback.setText("")
        except (ValueError, ModelError) as error:
            self.feedback.setText(f"Nilai {key} tidak valid: {error}")
            field.setStyleSheet("border: 1px solid #C74444")

    def slide(self, number: int) -> None:
        self.begin("opacity")
        self.fields["opacity"].setText(format(number / 100, ".2f"))
        self.commit("opacity")
        if not self.opacity.isSliderDown():
            self.edits.pop("opacity", None)

    def pick(self, key: str) -> None:
        self.begin(key)
        edit = self.edits.get(key)
        if edit is None:
            return
        text = self.fields[key].text()
        initial = color(text) if text.startswith("#") and len(text) == 9 else color(self.foreground)
        selected = QColorDialog.getColor(
            initial,
            self,
            "Pilih warna",
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if selected.isValid():
            self.fields[key].setText(
                f"#{selected.red():02X}{selected.green():02X}"
                f"{selected.blue():02X}{selected.alpha():02X}"
            )
            # Keep the captured revision, including while a dialog's nested event loop runs.
            self.edits[key] = edit
            self.commit(key)
        self.edits.pop(key, None)

    def pick_palette(self, key: str) -> None:
        selected = QColorDialog.getColor(
            color(getattr(self, key)),
            self,
            key.title(),
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if selected.isValid():
            setattr(
                self,
                key,
                f"#{selected.red():02X}{selected.green():02X}"
                f"{selected.blue():02X}{selected.alpha():02X}",
            )
            self.sync_palette()

    def sync_palette(self) -> None:
        self.foreground_button.setText(self.foreground)
        self.background_button.setText(self.background)
        for tab in self.studio.documents:
            if tab.view:
                tab.view.foreground = self.foreground
                tab.view.background = self.background

    def sync(self) -> None:
        self.arrangement.sync()
        tab = self.studio.current
        context = (tab, tab.selection, tab.dispatcher.snapshot.revision) if tab else None
        if context != self.context and not self.publishing:
            self.edits.clear()
        self.context = context
        nodes = (
            [tab.dispatcher.snapshot.project.document.nodes[k] for k in tab.selection]
            if tab
            else []
        )
        writable = bool(nodes and tab and not tab.handle.read_only and not self.studio.busy)
        self.summary.setText(f"{len(nodes)} selected" if nodes else "Pilih objek untuk mengedit.")
        for key, field in self.fields.items():
            enabled = writable and all(supported(n, key) for n in nodes)
            field.setEnabled(enabled)
            if key in self.pickers:
                self.pickers[key].setEnabled(enabled)
            values = [value(n, key) for n in nodes] if enabled else []
            mixed = bool(
                values
                and (
                    any(v != values[0] for v in values)
                    or (key == "radius" and any(len(set(n.style.radius)) > 1 for n in nodes))
                )
            )
            field.setPlaceholderText("Mixed" if mixed else "—")
            actual = values[0] if values and not mixed else None
            field.setText(
                ""
                if not values or mixed
                else "none"
                if actual is None
                else format(actual, ".12g")
                if isinstance(actual, (int, float))
                else actual
            )
            field.setStyleSheet("")
            field.setAccessibleDescription("Mixed values" if mixed else "")
        self.opacity.blockSignals(True)
        self.opacity.setEnabled(writable and len({n.opacity for n in nodes}) == 1)
        self.opacity.setValue(round(nodes[0].opacity * 100) if nodes else 100)
        self.opacity.blockSignals(False)
        self.sync_palette()
