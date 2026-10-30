"""Pure raster size conversion shared by planning and painting."""

import math


def pixel_extent(value: float) -> int:
    # Path intersections introduce floating arithmetic noise at integer edges.
    nearest = round(value)
    return (
        nearest
        if nearest > 0 and math.isclose(value, nearest, rel_tol=0, abs_tol=1e-6)
        else math.ceil(value)
    )
