"""Plain typography controls; each field patches only itself on explicit text targets."""

import math
from typing import TYPE_CHECKING, cast

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QLineEdit, QWidget

from ltechdesign.commands import SetFont, SetTypography
from ltechdesign.commands.contracts import Operation
from ltechdesign.domain.errors import ModelError
from ltechdesign.domain.models import Font, FontId, TextData, new_id
from ltechdesign.domain.typography import TypographyProperty, changed
from ltechdesign.rendering.fonts import local_families

if TYPE_CHECKING:
    from .window import StudioWindow


class TypographyPanel(QWidget):
    def __init__(self, studio: "StudioWindow") -> None:
        super().__init__()
        self.studio = studio
        self.loading = False
        self.revision = -1
        self.context: object = None
        form = QFormLayout(self)
        self.family = QComboBox()
        self.family.setEditable(True)
        self.family.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.family.setMinimumContentsLength(12)
        self.family.addItems(local_families())
        self.family.setAccessibleName("Text font family lokal")
        self.family.activated.connect(self.choose_family)
        edit = self.family.lineEdit()
        assert edit is not None
        edit.editingFinished.connect(self.choose_family)
        form.addRow("Font family", self.family)
        self.fields: dict[TypographyProperty, QLineEdit | QComboBox] = {}
        choices = {
            "italic": ("false", "true"),
            "alignment": ("left", "center", "right", "justify"),
            "vertical_alignment": ("top", "center", "bottom"),
            "line_height_unit": ("multiplier", "px"),
            "sizing": ("fixed", "auto_width", "auto_height"),
        }
        entries: tuple[tuple[TypographyProperty, str], ...] = (
            ("font_size", "Font size · px"),
            ("font_weight", "Weight · 1–1000"),
            ("italic", "Italic"),
            ("alignment", "Text alignment"),
            ("vertical_alignment", "Vertical alignment"),
            ("line_height_value", "Line height"),
            ("line_height_unit", "Line height unit"),
            ("letter_spacing", "Letter spacing · px"),
            ("sizing", "Text box sizing"),
        )
        for key, label in entries:
            if key in choices:
                combo = QComboBox()
                combo.addItems(choices[key])
                combo.activated.connect(lambda index, k=key: self.apply(k))
                widget: QComboBox | QLineEdit = combo
            else:
                field = QLineEdit()
                field.editingFinished.connect(lambda k=key: self.apply(k))
                widget = field
            widget.setAccessibleName(label)
            widget.setObjectName(f"text_{key}")
            form.addRow(label, widget)
            self.fields[key] = widget
        self.message = QLabel("Double click/F2 untuk inline edit; Ctrl+Enter/Esc selesai.")
        self.message.setWordWrap(True)
        form.addRow(self.message)

    def sync(self) -> None:
        tab = self.studio.current
        nodes = (
            [tab.dispatcher.snapshot.project.document.nodes[k] for k in tab.selection]
            if tab
            else []
        )
        text_nodes = [n for n in nodes if isinstance(n.data, TextData)]
        self.setVisible(bool(text_nodes))
        enabled = bool(
            text_nodes
            and len(text_nodes) == len(nodes)
            and tab
            and not tab.handle.read_only
            and not self.studio.busy
        )
        self.setEnabled(enabled)
        if not enabled or tab is None:
            return
        self.loading = True
        self.revision = tab.dispatcher.snapshot.revision
        self.context = (tab, tab.selection)
        fonts = {f.id: f for f in tab.dispatcher.snapshot.project.fonts.fonts}
        data = [cast(TextData, n.data).typography for n in text_nodes]
        names = [fonts[t.font_id].family for t in data]
        self.family.setCurrentText(names[0] if len(set(names)) == 1 else "Mixed")
        for key, field in self.fields.items():
            values = [
                getattr(t.line_height, "unit" if key.endswith("unit") else "value")
                if key.startswith("line_height_")
                else getattr(t, key)
                for t in data
            ]
            mixed = any(v != values[0] for v in values)
            text = (
                ""
                if mixed
                else str(values[0]).lower()
                if isinstance(values[0], bool)
                else format(values[0], ".12g")
                if isinstance(values[0], (int, float))
                else str(values[0])
            )
            if isinstance(field, QLineEdit):
                field.setPlaceholderText("Mixed" if mixed else "")
                field.setText(text)
            else:
                field.setCurrentIndex(-1 if mixed else field.findText(text))
                field.setPlaceholderText("Mixed")
        self.loading = False

    def valid_context(self) -> bool:
        tab = self.studio.current
        return bool(
            not self.loading
            and self.isEnabled()
            and tab
            and self.context == (tab, tab.selection)
            and self.revision == tab.dispatcher.snapshot.revision
        )

    def apply(self, key: TypographyProperty) -> None:
        if not self.valid_context():
            return
        tab = self.studio.current
        assert tab is not None
        field = self.fields[key]
        text = field.text().strip() if isinstance(field, QLineEdit) else field.currentText()
        try:
            value: float | str | bool
            if key == "font_weight":
                value = int(text)
            elif key in ("font_size", "line_height_value", "letter_spacing"):
                value = float(text)
                if not math.isfinite(value):
                    raise ValueError("finite number required")
            elif key == "italic":
                value = text == "true"
            else:
                value = text
            nodes = tab.dispatcher.snapshot.project.document.nodes
            if all(changed(nodes[k], key, value) == nodes[k] for k in tab.selection):
                return
            if self.studio.execute(
                tab,
                (SetTypography(node_ids=tab.selection, property=key, value=value),),
                expected_revision=self.revision,
                action_name=f"Typography {key}",
            ):
                self.message.setText("")
        except (ValueError, ModelError) as error:
            self.message.setText(f"Nilai typography tidak valid: {error}")

    def choose_family(self, *_: object) -> None:
        if not self.valid_context():
            return
        tab = self.studio.current
        assert tab is not None
        family = self.family.currentText().strip()
        self.studio.font_resolver.ensure_family(family)
        family = {f.casefold(): f for f in QFontDatabase.families()}.get(family.casefold(), family)
        if family not in QFontDatabase.families():
            self.message.setText("Font family belum terpasang lokal; metadata asli dipertahankan.")
            return
        project = tab.dispatcher.snapshot.project
        existing = next(
            (f for f in project.fonts.fonts if f.family == family and f.source == "system"), None
        )
        ops: tuple[Operation, ...] = ()
        if existing is None:
            existing = Font(id=FontId(new_id()), family=family)
            ops = (SetFont(font=existing),)
        if all(
            cast(TextData, project.document.nodes[k].data).typography.font_id == existing.id
            for k in tab.selection
        ):
            return
        self.studio.execute(
            tab,
            ops + (SetTypography(node_ids=tab.selection, property="font_id", value=existing.id),),
            expected_revision=self.revision,
            action_name="Text font family",
        )
