"""Admission checks; never install fonts, execute SVG, or re-encode original bytes."""

import hashlib
import math
import re
import struct
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtGui import QImage

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
    if len(payload) > MAX_ASSET_BYTES:
        fail("asset_bytes", code="limit_exceeded", maximum=MAX_ASSET_BYTES)
    if media == "image/svg+xml":
        _svg(payload)
    elif media in ("font/ttf", "font/otf"):
        _font(payload, media)
    else:
        decode_raster(payload, media, max_pixels)


def decode_raster(payload: bytes, media: str, max_pixels: int = MAX_PIXELS) -> "QImage":
    # QImage is reentrant and needs no widget, scene, QPixmap or font database.
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QImageReader

    if len(payload) > MAX_ASSET_BYTES:
        fail("asset_bytes", code="limit_exceeded", maximum=MAX_ASSET_BYTES)

    if media == "image/png":
        offset = 8
        while offset + 12 <= len(payload):
            length = int.from_bytes(payload[offset : offset + 4], "big")
            if payload[offset + 4 : offset + 8] == b"acTL":
                # Qt can report static PNG capability while ignoring APNG frames.
                fail("animated_image_unsupported", code="unsupported_capability")
            offset += length + 12
    buffer = QBuffer()
    buffer.setData(QByteArray(payload))
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    reader = QImageReader(buffer)
    reader.setAutoTransform(True)
    # 40 MP RGBA needs 160 MB. Still enforce our own header AND actual limits.
    QImageReader.setAllocationLimit(256)
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
    if decoded.isNull() or decoded.size() not in (size, size.transposed()):
        fail("invalid_image")
    if decoded.width() * decoded.height() > max_pixels or decoded.sizeInBytes() > max_pixels * 4:
        fail("raster_pixels", code="limit_exceeded", maximum=max_pixels)
    return decoded


def _svg(payload: bytes) -> None:
    # Deliberately bounded static geometry subset; no CSS, DTD, entities, scripts,
    # links, images, fonts, animation or foreignObject. Preserve accepted XML bytes.
    if len(payload) > 4 * 1024 * 1024:
        fail("svg_bytes", code="limit_exceeded")
    try:
        text = payload.decode("utf-8-sig")
        text_without_declaration = re.sub(
            r"^\s*<\?xml\s+version=[\'\"]1\.0[\'\"](?:\s+encoding=[\'\"]UTF-8[\'\"])?(?:\s+standalone=[\'\"](?:yes|no)[\'\"])?\s*\?>",
            "",
            text,
            count=1,
            flags=re.IGNORECASE,
        )
        if "<!" in text_without_declaration or "<?" in text_without_declaration:
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
    numeric_count = 0
    while stack:
        node, depth = stack.pop()
        count += 1
        if depth > 64 or count > 10000:
            fail("svg_complexity", code="limit_exceeded")
        if node.tag.removeprefix(namespace) not in tags:
            fail("svg_subset", code="unsupported_capability")
        if node is not root and node.tag.removeprefix(namespace) == "svg":
            fail("nested_svg_unsupported", code="unsupported_capability")
        for key, value in node.attrib.items():
            if key not in attrs or any(s in value.lower() for s in ("url", "href", "\\")):
                fail("unsafe_svg")
            if re.search(r"(?:nan|inf(?:inity)?)", value, re.IGNORECASE) and key not in (
                "id",
                "fill",
                "stroke",
            ):
                fail("invalid_svg_number")
            if key in ("d", "points", "viewBox"):
                allowed = r"[MmZzLlHhVvCcSsQqTtAa0-9eE.,+\s-]*" if key == "d" else r"[0-9eE.,+\s-]*"
                if not re.fullmatch(allowed, value):
                    fail("invalid_svg_geometry")
            numbers = re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?", value)
            if key not in ("id", "fill", "stroke"):
                numeric_count += len(numbers)
                if numeric_count > 100_000:
                    fail("svg_geometry_complexity", code="limit_exceeded")
            if key not in ("id", "fill", "stroke") and any(
                not math.isfinite(float(v)) or abs(float(v)) > 10_000_000 for v in numbers
            ):
                fail("svg_numeric_limit", code="limit_exceeded")
            if key in ("width", "height") and not re.fullmatch(
                r"\s*\+?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?(?:px)?\s*", value
            ):
                fail("svg_units_unsupported", code="unsupported_capability")
            if key == "preserveAspectRatio" and value not in ("none", "xMidYMid meet", "xMidYMid"):
                fail("svg_aspect_unsupported", code="unsupported_capability")
            if key in ("opacity", "fill-opacity", "stroke-opacity"):
                try:
                    alpha = float(value)
                except ValueError:
                    fail("invalid_svg_opacity")
                if not math.isfinite(alpha) or not 0 <= alpha <= 1:
                    fail("invalid_svg_opacity")
                if (
                    key == "opacity"
                    and node.tag.removeprefix(namespace) in ("svg", "g")
                    and alpha != 1
                ):
                    # Qt6.10 root alpha composites per primitive; group alpha
                    # can introduce hidden raster buffers. Keep this subset vector.
                    fail("svg_group_opacity_unsupported", code="unsupported_capability")
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
