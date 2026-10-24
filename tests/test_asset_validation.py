import hashlib
import struct
import zlib

import pytest

from ltechdesign.assets.validation import validate_asset, validate_media
from ltechdesign.domain import ModelError
from ltechdesign.domain.models import Asset

pytestmark = pytest.mark.core


@pytest.mark.parametrize(
    "svg",
    [
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        b'<!DOCTYPE svg [<!ENTITY x "bad">]><svg>&x;</svg>',
        b'<svg><image href="https://remote/image.png"/></svg>',
        b'<svg><rect fill="url(file:///secret)"/></svg>',
        b'<svg><rect onclick="x"/></svg>',
        b'<svg><style>@import "remote";</style></svg>',
        b"<svg><foreignObject/></svg>",
        b"<svg>" + b"<g>" * 65 + b"</g>" * 65 + b"</svg>",
        b"<svg",
    ],
)
def test_svg_cannot_fetch_execute_or_exceed_depth(svg: bytes) -> None:
    with pytest.raises(ModelError):
        validate_media(svg, "image/svg+xml")


def test_raster_pixel_limit_checked_before_decode() -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    # A tiny archive can declare enormous decoded dimensions. No giant allocation needed.
    image = b"\x89PNG\r\n\x1a\n"
    image += chunk(b"IHDR", struct.pack(">2I5B", 10000, 5000, 8, 6, 0, 0, 0))
    image += chunk(b"IDAT", zlib.compress(b"x")) + chunk(b"IEND", b"")
    with pytest.raises(ModelError, match="raster_pixels") as error:
        validate_media(image, "image/png")
    assert error.value.code == "limit_exceeded"


@pytest.mark.parametrize("media", ["image/png", "image/jpeg", "image/webp", "font/ttf", "font/otf"])
def test_matching_hash_cannot_make_invalid_media_valid(media: str) -> None:
    data = b"not the declared media"
    digest = hashlib.sha256(data).hexdigest()
    # Dynamic input still passes through the typed Asset constructor.
    from ltechdesign.domain.typing import typed

    asset = typed(
        dict(
            id="asset",
            path="assets/data/" + digest,
            media_type=media,
            sha256=digest,
            byte_length=len(data),
        ),
        Asset,
        "$",
        wire=True,
    )
    with pytest.raises(ModelError):
        validate_asset(asset, data)


def test_raster_encoders_and_mime_mismatch() -> None:
    from PySide6.QtCore import QBuffer, QIODevice
    from PySide6.QtGui import QImage

    image = QImage(2, 2, QImage.Format.Format_ARGB32)
    image.fill(0xFFFF0000)
    for media, format_name in (
        ("image/png", "PNG"),
        ("image/jpeg", "JPEG"),
        ("image/webp", "WEBP"),
    ):
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        # PySide6 6.10.2 accepts str here; its bytes-only stub disagrees with runtime.
        assert image.save(buffer, format_name)  # type: ignore[call-overload]
        data = bytes(buffer.data().data())
        validate_media(data, media)
        with pytest.raises(ModelError, match="invalid_media"):
            validate_media(data, "image/jpeg" if media != "image/jpeg" else "image/png")


def test_sfnt_table_bounds_and_restricted_embedding() -> None:
    from pathlib import Path

    original = (Path(__file__).parent / "fixtures/fonts/Abel-Regular.ttf").read_bytes()
    validate_media(original, "font/ttf")
    corrupted = bytearray(original)
    struct.pack_into(">I", corrupted, 20, len(original) + 1)
    with pytest.raises(ModelError, match="invalid_font"):
        validate_media(bytes(corrupted), "font/ttf")
    corrupted = bytearray(original)
    for i in range(struct.unpack_from(">H", original, 4)[0]):
        tag, _, offset, _ = struct.unpack_from(">4sIII", original, 12 + i * 16)
        if tag == b"OS/2":
            struct.pack_into(">H", corrupted, offset + 8, 2)
    with pytest.raises(ModelError, match="font_embedding_restricted"):
        validate_media(bytes(corrupted), "font/ttf")
