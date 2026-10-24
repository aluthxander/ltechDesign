"""Admission checks; never install fonts, execute SVG, or re-encode original bytes."""

import hashlib
import struct
import xml.etree.ElementTree as ET

from ltechdesign.domain.errors import fail
from ltechdesign.domain.models import Asset

MAX_ASSET_BYTES = 50 * 1024 * 1024
MAX_PIXELS = 40_000_000


def validate_asset(asset: Asset, payload: bytes, *, max_pixels: int = MAX_PIXELS) -> None:
    if len(payload) > MAX_ASSET_BYTES:
        fail("asset_bytes", code="limit_exceeded", maximum=MAX_ASSET_BYTES)
    if len(payload) != asset.byte_length or hashlib.sha256(payload).hexdigest() != asset.sha256:
        fail("integrity_mismatch", member=asset.path)
    validate_media(payload, asset.media_type, max_pixels=max_pixels)


def validate_media(payload: bytes, media: str, *, max_pixels: int = MAX_PIXELS) -> None:
    if media == "image/svg+xml":
        _svg(payload)
    elif media in ("font/ttf", "font/otf"):
        _font(payload, media)
    else:
        _raster(payload, media, max_pixels)


def _raster(payload: bytes, media: str, max_pixels: int) -> None:
    # QImage is reentrant and needs no widget, scene, QPixmap or font database.
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QImageReader

    buffer = QBuffer()
    buffer.setData(QByteArray(payload))
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    reader = QImageReader(buffer)
    reader.setDecideFormatFromContent(True)
    actual = bytes(reader.format().data()).decode("ascii", errors="replace")
    expected = {"image/png": "png", "image/jpeg": "jpeg", "image/webp": "webp"}.get(media)
    if expected is None or actual != expected or not reader.canRead():
        fail("invalid_media", media_type=media)
    size = reader.size()
    if size.width() <= 0 or size.height() <= 0:
        fail("invalid_image_dimensions")
    if size.width() * size.height() > max_pixels:
        fail("raster_pixels", code="limit_exceeded", maximum=max_pixels)
    if reader.supportsAnimation() and reader.imageCount() != 1:
        fail("animated_image_unsupported", code="unsupported_capability")
    decoded = reader.read()
    if decoded.isNull() or decoded.size() != size:
        fail("invalid_image")


def _svg(payload: bytes) -> None:
    # Deliberately bounded static geometry subset; no CSS, DTD, entities, scripts,
    # links, images, fonts, animation or foreignObject. Preserve accepted XML bytes.
    if len(payload) > 4 * 1024 * 1024:
        fail("svg_bytes", code="limit_exceeded")
    try:
        text = payload.decode("utf-8")
        if "<!" in text or "<?" in text:
            fail("unsafe_svg")
        root = ET.fromstring(text)
    except (UnicodeError, ET.ParseError, RecursionError):
        fail("invalid_svg")
    tags = {
        "svg",
        "g",
        "rect",
        "circle",
        "ellipse",
        "line",
        "polyline",
        "polygon",
        "path",
        "title",
        "desc",
    }
    attrs = {
        "id",
        "x",
        "y",
        "x1",
        "y1",
        "x2",
        "y2",
        "width",
        "height",
        "rx",
        "ry",
        "r",
        "cx",
        "cy",
        "d",
        "points",
        "viewBox",
        "preserveAspectRatio",
        "transform",
        "fill",
        "stroke",
        "stroke-width",
        "opacity",
        "fill-opacity",
        "stroke-opacity",
        "fill-rule",
        "stroke-linecap",
        "stroke-linejoin",
        "stroke-miterlimit",
    }
    namespace = "{http://www.w3.org/2000/svg}"
    if root.tag not in ("svg", namespace + "svg"):
        fail("invalid_svg")
    stack = [(root, 1)]
    count = 0
    while stack:
        node, depth = stack.pop()
        count += 1
        if depth > 64 or count > 10000:
            fail("svg_complexity", code="limit_exceeded")
        if node.tag.removeprefix(namespace) not in tags:
            fail("svg_subset", code="unsupported_capability")
        for key, value in node.attrib.items():
            if key not in attrs or any(s in value.lower() for s in ("url", "href", "\\")):
                fail("unsafe_svg")
        stack.extend((child, depth + 1) for child in node)


def _font(payload: bytes, media: str) -> None:
    # Bounded SFNT container validation; actual glyph shaping/resolution belongs to 11.
    signature = b"\x00\x01\x00\x00" if media == "font/ttf" else b"OTTO"
    if len(payload) < 12 or payload[:4] != signature:
        fail("invalid_font")
    count = struct.unpack_from(">H", payload, 4)[0]
    end = 12 + count * 16
    if not 1 <= count <= 256 or end > len(payload):
        fail("invalid_font")
    tables: dict[bytes, tuple[int, int]] = {}
    for index in range(count):
        tag, _, offset, length = struct.unpack_from(">4sIII", payload, 12 + index * 16)
        if tag in tables or offset < end or offset + length > len(payload):
            fail("invalid_font")
        tables[tag] = (offset, length)
    required = {b"head", b"hhea", b"maxp", b"hmtx", b"cmap", b"name", b"OS/2"}
    required |= {b"glyf", b"loca"} if media == "font/ttf" else {b"CFF "}
    if not required <= tables.keys():
        fail("invalid_font")
    offset, length = tables[b"OS/2"]
    if length < 10:
        fail("invalid_font")
    # Restricted-license and bitmap-only embedding cannot be overridden by JSON metadata.
    if struct.unpack_from(">H", payload, offset + 8)[0] & 0x0202:
        fail("font_embedding_restricted", code="unsupported_capability")
