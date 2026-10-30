"""Runtime raster encoders; these functions run in the render process."""

import os
from pathlib import Path

from PIL import Image, features
from PySide6.QtGui import QColor, QImage, QImageWriter, QPainter

from ltechdesign.domain.errors import fail

from .contracts import ExportOptions


def flattened(image: QImage, background: str | None) -> QImage:
    if background is None:
        return image
    result = QImage(image.size(), QImage.Format.Format_RGB32)
    if result.isNull():
        fail("flatten_allocation", code="limit_exceeded")
    result.fill(QColor(background))
    painter = QPainter(result)
    try:
        painter.drawImage(0, 0, image)
    finally:
        painter.end()
    return result


def encode(
    image: QImage, target: Path, options: ExportOptions, *, prefer_pillow_webp: bool = False
) -> tuple[str, tuple[str, ...]]:
    image = flattened(image, options.background)
    image.setDotsPerMeterX(round(options.dpi / 0.0254))
    image.setDotsPerMeterY(round(options.dpi / 0.0254))
    available = {
        bytes(f.data()).decode("ascii").lower() for f in QImageWriter.supportedImageFormats()
    }
    use_pillow = options.format == "webp" and (
        "webp" not in available or options.lossless or prefer_pillow_webp
    )
    error = ""
    if not use_pillow:
        writer = QImageWriter(str(target), options.format.encode("ascii"))
        writer.setQuality(options.quality)
        if writer.canWrite() and writer.write(image):
            backend = "qt"
        else:
            error = writer.errorString()
            if options.format != "webp":
                fail("encode_failed", code="io_error", message=error)
            use_pillow = True
        del writer  # QImageWriter releases its exclusive QFile before fsync/verification.
    if use_pillow:
        if not features.check("webp"):
            fail("webp_encoder_unavailable", code="unsupported_capability", message=error)
        rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
        data = Image.frombytes("RGBA", (rgba.width(), rgba.height()), bytes(rgba.constBits()))
        data.save(
            target, format="WEBP", quality=options.quality, lossless=options.lossless, method=4
        )
        backend = "pillow"
    with target.open("r+b") as stream:
        stream.flush()
        os.fsync(stream.fileno())
    # Decode the actual file, not merely its extension or codec return code.
    with Image.open(target) as decoded:
        if decoded.size != (image.width(), image.height()):
            fail("encoded_size_mismatch", code="io_error")
        if decoded.format != {"png": "PNG", "jpg": "JPEG", "webp": "WEBP"}[options.format]:
            fail("encoded_format_mismatch", code="io_error")
        if options.format == "jpg" and "A" in decoded.getbands():
            fail("jpeg_alpha", code="io_error")
        decoded.load()
    return backend, (
        ("WebP stores pixel dimensions; DPI is reported in the export result.",)
        if options.format == "webp"
        else ()
    )
