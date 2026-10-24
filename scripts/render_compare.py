"""Strict premultiplied pixel/edge diagnostics for the 06A proof, not a renderer."""

from PySide6.QtGui import QImage


def pixels(image: QImage) -> list[tuple[int, int, int, int]]:
    converted = image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    values = []
    for y in range(image.height()):
        for x in range(image.width()):
            value = converted.pixel(x, y)
            values.append((value >> 24, (value >> 16) & 255, (value >> 8) & 255, value & 255))
    return values


def compare(reference: QImage, actual: QImage) -> dict[str, int]:
    assert reference.size() == actual.size()
    left, right = pixels(reference), pixels(actual)
    width, height = reference.width(), reference.height()
    count = max_error = interior_max = edge_count = 0
    for y in range(height):
        for x in range(width):
            i = y * width + x
            error = max(abs(a - b) for a, b in zip(left[i], right[i], strict=True))
            if error == 0:
                continue
            count += 1
            max_error = max(max_error, error)
            edge = any(
                max(abs(a - b) for a, b in zip(left[i], left[yy * width + xx], strict=True)) > 8
                for yy in range(max(0, y - 1), min(height, y + 2))
                for xx in range(max(0, x - 1), min(width, x + 2))
            )
            if edge:
                edge_count += 1
            else:
                interior_max = max(interior_max, error)
    return dict(
        changed=count, max_error=max_error, interior_max=interior_max, edge_changed=edge_count
    )
