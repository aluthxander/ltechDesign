"""Prepared, bounded raster sources and original vector bytes for all paint targets.

Prepare on an I/O worker before GUI publication. No QPixmap or live QObject crosses
threads. A session keeps prepared sources for undo, capped at 256 MiB decoded.
"""

import math
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QPicture
from PySide6.QtSvg import QSvgRenderer

from ltechdesign.assets.validation import MAX_PIXELS, decode_raster, validate_media
from ltechdesign.domain.errors import fail
from ltechdesign.domain.models import Asset, AssetId, MediaData, Node

MAX_PREPARED_BYTES = 256 * 1024 * 1024


@dataclass(frozen=True, eq=False)
class MediaSource:
    width: float
    height: float
    image: QImage | None
    svg: bytes | None
    thumbnail: QImage
    keep_aspect: bool = True
    picture: QPicture | None = None

    @property
    def cost(self) -> int:
        return (
            self.image.sizeInBytes()
            if self.image is not None
            else len(self.svg or b"") + (self.picture.size() if self.picture else 0)
        ) + self.thumbnail.sizeInBytes()


def svg_renderer(payload: bytes, keep_aspect: bool) -> QSvgRenderer:
    renderer = QSvgRenderer()
    renderer.setAnimationEnabled(False)
    if not renderer.load(QByteArray(payload)) or not renderer.isValid() or renderer.animated():
        fail("invalid_svg")
    renderer.setAspectRatioMode(
        Qt.AspectRatioMode.KeepAspectRatio if keep_aspect else Qt.AspectRatioMode.IgnoreAspectRatio
    )
    return renderer


def prepare_source(
    payload: bytes, media_type: str, *, byte_budget: int = MAX_PREPARED_BYTES
) -> MediaSource:
    if type(byte_budget) is not int or not 96 * 72 * 4 <= byte_budget <= MAX_PREPARED_BYTES:
        fail("prepared_image_bytes", code="limit_exceeded")
    if media_type == "image/svg+xml":
        validate_media(payload, media_type)
        root = ET.fromstring(payload)
        keep = root.get("preserveAspectRatio", "xMidYMid meet") != "none"
        renderer = svg_renderer(payload, keep)
        size = renderer.defaultSize()
        w, h = float(size.width()), float(size.height())
        if w <= 0 or h <= 0 or not math.isfinite(w * h) or w * h > MAX_PIXELS:
            fail("svg_dimensions", code="limit_exceeded")
        thumb = QImage(96, 72, QImage.Format.Format_ARGB32_Premultiplied)
        thumb.fill(Qt.GlobalColor.transparent)
        p = QPainter(thumb)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            scale = min(96 / w, 72 / h)
            renderer.render(
                p, QRectF((96 - w * scale) / 2, (72 - h * scale) / 2, w * scale, h * scale)
            )
        finally:
            p.end()
        picture = QPicture()
        recording = QPainter(picture)
        try:
            renderer.render(recording, QRectF(0, 0, w, h))
        finally:
            recording.end()
        if picture.size() > 16 * 1024 * 1024:
            fail("svg_drawing_bytes", code="limit_exceeded")
        return MediaSource(w, h, None, payload, thumb, keep, picture)
    image = decode_raster(
        payload, media_type, max_pixels=min(MAX_PIXELS, (byte_budget - 96 * 72 * 4) // 4)
    )
    thumb = image.scaled(
        96, 72, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
    )
    return MediaSource(image.width(), image.height(), image, None, thumb)


def prepare_sources(
    assets: tuple[Asset, ...], blobs: Mapping[str, bytes], *, byte_budget: int = MAX_PREPARED_BYTES
) -> dict[AssetId, MediaSource]:
    result: dict[AssetId, MediaSource] = {}
    cost = 0
    for asset in assets:
        if asset.media_type.startswith("image/"):
            if asset.path not in blobs:
                fail("missing_image_resource", asset_id=asset.id)
            source = prepare_source(
                blobs[asset.path], asset.media_type, byte_budget=byte_budget - cost
            )
            cost += source.cost
            if cost > byte_budget:
                fail("prepared_image_bytes", code="limit_exceeded", maximum=MAX_PREPARED_BYTES)
            result[asset.id] = source
    return result


def media_rects(node: Node, source: MediaSource) -> tuple[QRectF, QRectF]:
    """Crop source first; map its aspect into the unchanged local container."""
    assert isinstance(node.data, MediaData)
    crop = node.data.crop
    src = QRectF(
        crop.x * source.width,
        crop.y * source.height,
        crop.width * source.width,
        crop.height * source.height,
    )
    w, h = node.width, node.height
    if node.data.fit == "stretch":
        return src, QRectF(0, 0, w, h)
    scale = (min if node.data.fit == "fit" else max)(w / src.width(), h / src.height())
    tw, th = src.width() * scale, src.height() * scale
    return src, QRectF((w - tw) / 2, (h - th) / 2, tw, th)


def draw_media(painter: QPainter, node: Node, source: MediaSource) -> None:
    from .drawing import path

    if node.width == 0 or node.height == 0:
        return
    src, dst = media_rects(node, source)
    painter.save()
    try:
        painter.setClipPath(path(node), Qt.ClipOperation.IntersectClip)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if source.image is not None:
            painter.drawImage(dst, source.image, src)
        else:
            assert source.svg is not None
            # Crop is a viewport; SVG stays vector on QPainter/PDF.
            painter.setClipRect(dst, Qt.ClipOperation.IntersectClip)
            sx, sy = dst.width() / src.width(), dst.height() / src.height()
            painter.translate(dst.x() - src.x() * sx, dst.y() - src.y() * sy)
            painter.scale(sx, sy)
            assert source.picture is not None
            # QPicture playback applies target/source logical DPI automatically.
            # Our geometry is already logical px (PDF painter has its own scale).
            device = painter.device()
            painter.scale(
                source.picture.logicalDpiX() / device.logicalDpiX(),
                source.picture.logicalDpiY() / device.logicalDpiY(),
            )
            painter.drawPicture(0, 0, source.picture)
    finally:
        painter.restore()


def codec_smoke() -> dict[str, object]:
    """Actual encoders/decoders and vector playback, also executed in frozen --smoke."""
    from PySide6.QtCore import QBuffer, QIODevice

    result: dict[str, object] = {}
    image = QImage(8, 6, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.red)
    for format_name, media in (
        ("PNG", "image/png"),
        ("JPEG", "image/jpeg"),
        ("WEBP", "image/webp"),
    ):
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(buffer, format_name):  # type: ignore[call-overload]
            fail("missing_image_encoder", format=format_name)
        source = prepare_source(bytes(buffer.data().data()), media)
        if source.width != 8 or source.height != 6:
            fail("image_codec_smoke")
        result[format_name] = "encoded/decoded"
    source = prepare_source(
        b'<svg width="8" height="6"><rect width="8" height="6" fill="red"/></svg>', "image/svg+xml"
    )
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        assert source.picture is not None
        painter.drawPicture(0, 0, source.picture)
    finally:
        painter.end()
    if image.pixelColor(4, 3).red() != 255 or image.pixelColor(4, 3).alpha() != 255:
        fail("svg_codec_smoke")
    result["SVG"] = "vector recorded/replayed"
    return result
