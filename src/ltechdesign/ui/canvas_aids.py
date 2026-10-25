"""Per-view aids. No guide/grid/ruler object is ever inserted into the scene."""

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ltechdesign.domain.geometry import Bounds
from ltechdesign.domain.models import Document, NodeId, Point
from ltechdesign.domain.snapping import Axis, Guide, SnapIndex, tolerance

if TYPE_CHECKING:
    from .canvas import EditorCanvas

RULER_SIZE = 24


@dataclass
class AidSettings:
    rulers: bool = True
    snap: bool = False
    grid_snap: bool = True
    object_snap: bool = True
    smart_guides: bool = True
    tolerance_px: float = 8  # physical display pixels, not Qt DIPs


def ruler_step(zoom: float) -> float:
    raw = 70 / zoom
    power = 10 ** math.floor(math.log10(raw))
    return float(next(m * power for m in (1, 2, 5, 10) if m * power >= raw))


class RulerBar(QWidget):
    def __init__(self, owner: "CanvasAids", axis: Axis | None) -> None:
        super().__init__(owner.view)
        self.owner, self.axis = owner, axis
        self.setAccessibleName(f"Ruler {axis or 'unit'} logical pixels")

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        self.owner.draw_ruler(painter, self.axis, self.width(), self.height())
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        event.accept()  # manual guide creation remains38B

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        event.accept()


class CanvasAids:
    def __init__(self, view: "EditorCanvas") -> None:
        self.view = view
        self.settings = AidSettings()
        self.guides: tuple[Guide, ...] = ()
        self.index = SnapIndex()
        self.document: Document | None = None
        self.moving: tuple[NodeId, ...] = ()
        self.page = -1
        self.top_bar = RulerBar(self, "x")
        self.left_bar = RulerBar(self, "y")
        self.corner = RulerBar(self, None)
        self._margin = -1
        self._layout_timer = QTimer(view)
        self._layout_timer.setSingleShot(True)
        self._layout_timer.timeout.connect(self.layout_rulers)
        view.zoom_changed.connect(lambda value: self.update_rulers())
        for scrollbar in (view.horizontalScrollBar(), view.verticalScrollBar()):
            scrollbar.valueChanged.connect(lambda value: self.update_rulers())
            scrollbar.rangeChanged.connect(lambda lo, hi: self._layout_timer.start(0))

    def update_rulers(self) -> None:
        for bar in (self.top_bar, self.left_bar, self.corner):
            bar.update()

    def layout_rulers(self) -> None:
        margin = RULER_SIZE if self.settings.rulers else 0
        if margin != self._margin:
            self._margin = margin
            self.view.setViewportMargins(margin, margin, 0, 0)
        area = self.view.viewport().geometry()
        self.top_bar.setGeometry(area.x(), area.y() - margin, area.width(), margin)
        self.left_bar.setGeometry(area.x() - margin, area.y(), margin, area.height())
        self.corner.setGeometry(area.x() - margin, area.y() - margin, margin, margin)
        for bar in (self.top_bar, self.left_bar, self.corner):
            bar.setVisible(self.settings.rulers)
            bar.update()

    @property
    def distance(self) -> float:
        return tolerance(
            self.settings.tolerance_px, self.view.zoom, self.view.viewport().devicePixelRatioF()
        )

    def prepare(self, moving: tuple[NodeId, ...]) -> None:
        if not self.settings.snap:
            self.guides = ()
            return
        doc = self.view.adapter.document
        if doc is not None and (
            doc is not self.document or moving != self.moving or self.page != self.view.adapter.page
        ):
            self.document, self.moving, self.page = doc, moving, self.view.adapter.page
            self.index = SnapIndex.build(doc, self.page, moving)
        self.guides = ()

    def clear(self) -> None:
        self.guides = ()

    def move(self, bound: Bounds, delta: Point, axis: Axis | None = None) -> Point:
        s = self.settings
        if not s.snap:
            self.clear()
            return delta
        result, self.guides = self.index.translation(
            bound,
            delta,
            self.distance,
            objects=s.object_snap,
            grid=s.grid_snap,
            spacing=self.view.grid_spacing,
            axis_only=axis,
        )
        return result

    def point(self, point: Point) -> Point:
        delta = self.move(Bounds(point.x, point.y, point.x, point.y), Point())
        return Point(x=point.x + delta.x, y=point.y + delta.y)

    def along(self, origin: Point, vector: Point, factor: float, minimum: float) -> float:
        s = self.settings
        if not s.snap:
            self.clear()
            return factor
        result, self.guides = self.index.along(
            origin,
            vector,
            factor,
            minimum,
            self.distance,
            objects=s.object_snap,
            grid=s.grid_snap,
            spacing=self.view.grid_spacing,
        )
        return result

    def draw_guides(self, painter: QPainter) -> None:
        if not self.settings.smart_guides:
            return
        painter.save()
        pen = QPen(QColor("#B00080"), 1, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        painter.setPen(pen)
        pad = tolerance(12, self.view.zoom, self.view.viewport().devicePixelRatioF())
        for guide in self.guides:
            if guide.axis == "x":
                painter.drawLine(
                    QPointF(guide.coordinate, guide.start - pad),
                    QPointF(guide.coordinate, guide.end + pad),
                )
            else:
                painter.drawLine(
                    QPointF(guide.start - pad, guide.coordinate),
                    QPointF(guide.end + pad, guide.coordinate),
                )
        painter.restore()

    def ticks(self, axis: Axis) -> tuple[tuple[float, float, bool], ...]:
        view = self.view
        mapping = view.viewportTransform()
        inverse, valid = mapping.inverted()
        if not valid:
            return ()
        visible = inverse.mapRect(QRectF(view.viewport().rect()))
        start, end = (
            (visible.left(), visible.right()) if axis == "x" else (visible.top(), visible.bottom())
        )
        major = ruler_step(view.zoom)
        minor = major / 5
        result = []
        for index in range(math.ceil(start / minor), math.floor(end / minor) + 1):
            coordinate = index * minor
            position = (
                mapping.map(QPointF(coordinate, 0)).x()
                if axis == "x"
                else mapping.map(QPointF(0, coordinate)).y()
            )
            result.append((coordinate, position, index % 5 == 0))
        return tuple(result)

    def draw_ruler(self, painter: QPainter, axis: Axis | None, width: int, height: int) -> None:
        painter.fillRect(QRectF(0, 0, width, height), QColor("#F8F8F8"))
        painter.setPen(QColor("#444444"))
        if axis is None:
            painter.drawText(QPointF(3, 16), "px")
            return
        for coordinate, position, major in self.ticks(axis):
            if position < 0:
                continue
            label = format(coordinate, ".8g")
            if axis == "x":
                painter.drawLine(
                    QPointF(position, RULER_SIZE - (8 if major else 4)),
                    QPointF(position, RULER_SIZE),
                )
                if major and position + 3 + painter.fontMetrics().horizontalAdvance(label) <= width:
                    painter.drawText(QPointF(position + 3, 12), label)
            else:
                painter.drawLine(
                    QPointF(RULER_SIZE - (8 if major else 4), position),
                    QPointF(RULER_SIZE, position),
                )
                if major:
                    painter.save()
                    painter.translate(12, position - 3)
                    painter.rotate(-90)
                    painter.drawText(QPointF(), label)
                    painter.restore()


class CanvasAidControls(QWidget):
    def __init__(self, view: "EditorCanvas") -> None:
        super().__init__()
        self.view = view
        self.checks: dict[str, QCheckBox] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        rows = (QHBoxLayout(), QHBoxLayout())
        for row in rows:
            layout.addLayout(row)
        for index, (key, title) in enumerate(
            (
                ("rulers", "Rulers"),
                ("grid", "Grid"),
                ("smart_guides", "Smart guides"),
                ("snap", "Snap"),
                ("grid_snap", "Grid snap"),
                ("object_snap", "Object snap"),
            )
        ):
            control = QCheckBox(title)
            control.setAccessibleName(title + " — sesi canvas")
            control.setChecked(view.grid if key == "grid" else getattr(view.aids.settings, key))
            control.toggled.connect(lambda checked, k=key: self.toggle(k, checked))
            rows[0 if index < 4 else 1].addWidget(control)
            self.checks[key] = control
        rows[0].addStretch()
        rows[1].addWidget(QLabel("Grid px"))
        self.spacing = QDoubleSpinBox()
        self.spacing.setRange(0.01, 1_000_000)
        self.spacing.setDecimals(2)
        self.spacing.setValue(view.grid_spacing)
        self.spacing.setAccessibleName("Grid spacing logical pixel")
        self.spacing.setToolTip(
            "Grid logical tetap; garis dipadatkan saat zoom kecil. Snap:8 physical screen px."
        )
        self.spacing.valueChanged.connect(self.change_spacing)
        rows[1].addWidget(self.spacing)
        rows[1].addStretch()

    def toggle(self, key: str, checked: bool) -> None:
        self.view.cancel_gesture()
        if key == "grid":
            self.view.grid = checked
        else:
            setattr(self.view.aids.settings, key, checked)
        self.view.aids.layout_rulers()
        self.view.viewport().update()

    def change_spacing(self, value: float) -> None:
        self.view.cancel_gesture()
        self.view.grid_spacing = value
        self.view.viewport().update()
