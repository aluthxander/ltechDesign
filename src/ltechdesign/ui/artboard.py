"""Preset/custom artboard intent form; no document mutation inside the dialog."""

from typing import cast

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QWidget,
)

from ltechdesign.domain.authoring import ARTBOARD_PRESETS, Unit, artboard_node
from ltechdesign.domain.errors import ModelError
from ltechdesign.domain.models import Node, PageId, Point


class ArtboardDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Buat artboard")
        form = QFormLayout(self)
        self.preset = QComboBox()
        self.preset.addItems(["Custom"] + [p.name for p in ARTBOARD_PRESETS])
        self.name = QLineEdit("Artboard")
        self.width_input = QDoubleSpinBox()
        self.height_input = QDoubleSpinBox()
        for field, value in ((self.width_input, 1080), (self.height_input, 1350)):
            field.setDecimals(4)
            field.setRange(0.0001, 1_000_000)
            field.setValue(value)
        self.unit = QComboBox()
        self.unit.addItems(["px", "mm", "cm", "in"])
        self.dpi = QDoubleSpinBox()
        self.dpi.setRange(1, 2400)
        self.dpi.setValue(96)
        self.orientation = QComboBox()
        self.orientation.addItems(["Sesuai input", "Portrait", "Landscape"])
        self.background = QLineEdit("#FFFFFFFF")
        self.pixels = QLabel()
        for label, widget in (
            ("Preset", self.preset),
            ("Nama", self.name),
            ("Width", self.width_input),
            ("Height", self.height_input),
            ("Unit", self.unit),
            ("DPI", self.dpi),
            ("Orientasi", self.orientation),
            ("Background #RRGGBBAA", self.background),
            ("Ukuran dokumen", self.pixels),
        ):
            widget.setAccessibleName(label)
            form.addRow(label, widget)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self._loading = False
        self.preset.currentIndexChanged.connect(self.use_preset)
        for spin in (self.width_input, self.height_input, self.dpi):
            spin.valueChanged.connect(self.custom_changed)
        self.unit.currentIndexChanged.connect(self.custom_changed)
        self.orientation.currentIndexChanged.connect(self.custom_changed)
        self.background.textChanged.connect(self.custom_changed)
        self.changed()

    def custom_changed(self, *_: object) -> None:
        if not self._loading:
            self.preset.blockSignals(True)
            self.preset.setCurrentIndex(0)
            self.preset.blockSignals(False)
            self.changed()

    def use_preset(self, index: int) -> None:
        if index == 0:
            return
        preset = ARTBOARD_PRESETS[index - 1]
        self._loading = True
        self.name.setText(preset.name)
        self.width_input.setValue(preset.width)
        self.height_input.setValue(preset.height)
        self.unit.setCurrentText(preset.unit)
        self.dpi.setValue(preset.dpi)
        self.orientation.setCurrentIndex(0)
        self._loading = False
        self.changed()

    def changed(self, *_: object) -> None:
        if self._loading:
            return
        try:
            node = self.node(PageId("size-preview"))
            self.pixels.setText(f"{node.width:.4f} × {node.height:.4f} logical px")
        except ModelError:
            self.pixels.setText("Ukuran / warna tidak valid")

    def node(self, page: PageId, origin: Point | None = None) -> Node:
        unit = cast(Unit, self.unit.currentText())
        orientation = self.orientation.currentIndex()
        return artboard_node(
            page,
            name=self.name.text(),
            width=self.width_input.value(),
            height=self.height_input.value(),
            unit=unit,
            dpi=self.dpi.value(),
            landscape=None if orientation == 0 else orientation == 2,
            origin=origin,
            background=self.background.text(),
        )

    def accept(self) -> None:
        try:
            self.node(PageId("size-preview"))
        except ModelError as error:
            QMessageBox.warning(self, "Artboard tidak valid", str(error))
            return
        super().accept()
