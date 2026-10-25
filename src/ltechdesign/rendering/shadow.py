"""Alpha-mask drop shadows shared by every painter target; no scene effects."""

import math

from PIL import Image, ImageChops, ImageFilter
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QImage, QPainter, QTransform

from ltechdesign.domain.models import Node


def dilate(mask: Image.Image, radius: int, vertical: bool) -> Image.Image:
    """Square max morphology in O(log radius) native image passes, with zero padding."""
    covered = 0
    while covered < radius:
        step = min(covered + 1, radius - covered)
        merged = mask
        for sign in (-1, 1):
            shifted = Image.new("L", mask.size)
            shifted.paste(mask, (0, sign * step) if vertical else (sign * step, 0))
            merged = ImageChops.lighter(merged, shifted)
        mask = merged
        covered += step
    return mask


def composite(source: QImage, node: Node, matrix: QTransform) -> QImage:
    """Effects use pre-opacity subtree alpha, then the source is painted over them."""
    rgba = source.convertToFormat(QImage.Format.Format_RGBA8888)
    alpha = Image.frombytes("RGBA", (rgba.width(), rgba.height()), bytes(rgba.constBits()))
    alpha = alpha.getchannel("A")
    scale = math.hypot(matrix.m11(), matrix.m12())
    result = QImage(source.size(), QImage.Format.Format_ARGB32_Premultiplied)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    try:
        for shadow in node.style.shadows:
            mask = alpha
            extent = shadow.spread * scale
            radius = math.floor(extent)
            if extent:
                mask = dilate(dilate(mask, radius, False), radius, True)
                if extent != radius:
                    expanded = dilate(dilate(mask, 1, False), 1, True)
                    mask = Image.blend(mask, expanded, extent - radius)
            if shadow.blur:
                # Domain blur is sigma in logical px, with a conservative 3-sigma buffer.
                mask = mask.filter(ImageFilter.GaussianBlur(shadow.blur * scale))
            components = tuple(int(shadow.color[i : i + 2], 16) for i in (1, 3, 5, 7))
            tint = Image.new("RGBA", mask.size, components[:3] + (0,))
            tint.putalpha(mask.point([round(i * components[3] / 255) for i in range(256)]))
            data = tint.tobytes()
            image = QImage(data, tint.width, tint.height, QImage.Format.Format_RGBA8888)
            dx = matrix.m11() * shadow.offset_x + matrix.m21() * shadow.offset_y
            dy = matrix.m12() * shadow.offset_x + matrix.m22() * shadow.offset_y
            painter.drawImage(QPointF(dx, dy), image)
        painter.drawImage(QPointF(), source)
    finally:
        painter.end()
    return result
