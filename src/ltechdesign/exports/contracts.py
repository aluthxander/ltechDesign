"""Immutable local export contract; transport/authentication belongs to its caller."""

import math
import re
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ltechdesign.domain.errors import fail
from ltechdesign.domain.models import NodeId
from ltechdesign.rendering.limits import pixel_extent

JobState = Literal["queued", "running", "succeeded", "failed", "cancelled"]
TERMINAL = ("succeeded", "failed", "cancelled")


@dataclass(frozen=True)
class ExportTarget:
    kind: Literal["artboard", "selection", "all_artboards"] = "artboard"
    artboard_id: NodeId | None = None
    node_ids: tuple[NodeId, ...] = ()

    def validate(self) -> None:
        if self.kind not in ("artboard", "selection", "all_artboards"):
            fail("invalid_export_target", code="validation_error")
        if self.kind == "artboard":
            if not self.artboard_id or self.node_ids:
                fail("artboard_id_required", code="validation_error")
        elif self.artboard_id is not None or (self.kind == "all_artboards" and self.node_ids):
            fail("invalid_export_target", code="validation_error")
        elif self.kind == "selection" and (
            not self.node_ids
            or len(self.node_ids) > 10000
            or len(set(self.node_ids)) != len(self.node_ids)
        ):
            fail("invalid_export_selection", code="validation_error")


@dataclass(frozen=True)
class ExportOptions:
    folder: str
    target: ExportTarget
    format: Literal["png", "jpg", "webp"] = "png"
    scale: int = 1
    width: int | None = None
    height: int | None = None
    dpi: int = 96
    quality: int = 90
    background: str | None = None  # None = transparent. JPG requires an opaque RGB choice.
    pattern: str = "{project}-{artboard}-{index:03d}"
    overwrite: bool = False
    lossless: bool = False

    def validate(self) -> None:
        self.target.validate()
        if self.format not in ("png", "jpg", "webp"):
            fail("invalid_export_format", code="validation_error")
        if type(self.scale) is not int or self.scale not in (1, 2, 3):
            fail("invalid_export_scale", code="validation_error")
        if not self.folder or len(self.folder) > 4096:
            fail("invalid_output_folder", code="validation_error")
        if ((self.width is None) != (self.height is None)) or any(
            v is not None and (type(v) is not int or not 1 <= v <= 32768)
            for v in (self.width, self.height)
        ):
            fail("invalid_export_dimensions", code="validation_error")
        if type(self.dpi) is not int or not 36 <= self.dpi <= 1200:
            fail("invalid_export_dpi", code="validation_error")
        if type(self.quality) is not int or not 1 <= self.quality <= 100:
            fail("invalid_export_quality", code="validation_error")
        if self.background is not None and not re.fullmatch(r"#[0-9a-fA-F]{6}", self.background):
            fail("opaque_background_required", code="validation_error")
        if self.format == "jpg" and self.background is None:
            fail("jpg_background_required", code="validation_error")
        if type(self.overwrite) is not bool or type(self.lossless) is not bool:
            fail("invalid_export_flags", code="validation_error")
        if self.lossless and self.format != "webp":
            fail("lossless_is_webp_option", code="validation_error")
        filename(self, project="Project", page="Page", artboard="Artboard", index=1, id="id")


def filename(options: ExportOptions, **values: str | int) -> str:
    if not options.pattern or len(options.pattern) > 200:
        fail("invalid_naming_pattern", code="validation_error")
    try:
        for literal, field, spec, conversion in string.Formatter().parse(options.pattern):
            if re.search(r'[<>:"/\\|?*\x00-\x1f]', literal):
                fail("unsafe_naming_pattern", code="path_not_allowed")
            if field is not None and (
                field not in ("project", "page", "artboard", "index", "id")
                or conversion
                or (spec and not (field == "index" and spec in ("02d", "03d", "04d")))
            ):
                fail("invalid_naming_pattern", code="validation_error")
        safe = {
            key: re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")[:80]
            if isinstance(value, str)
            else value
            for key, value in values.items()
        }
        name = options.pattern.format_map(safe).strip(" .")[:160]
    except (ValueError, KeyError, IndexError) as error:
        fail("invalid_naming_pattern", code="validation_error", message=str(error))
    if not name or name in (".", ".."):
        fail("empty_output_name", code="validation_error")
    if re.fullmatch(r"(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])", name.split(".")[0]):
        name = "_" + name
    return name + "." + options.format


def dimensions(
    width: float, height: float, options: ExportOptions, maximum: int
) -> tuple[int, int]:
    if not all(math.isfinite(v) and v > 0 for v in (width, height)):
        fail("empty_export_bounds", code="validation_error")
    w, h = (
        (options.width, options.height)
        if options.width is not None
        else (pixel_extent(width * options.scale), pixel_extent(height * options.scale))
    )
    assert w is not None and h is not None
    if w > 32768 or h > 32768 or w * h > maximum:
        fail("render_pixels", code="limit_exceeded", width=w, height=h, maximum=maximum)
    return w, h


@dataclass(frozen=True)
class OutputResult:
    name: str
    state: Literal["succeeded", "failed", "cancelled", "not_attempted"]
    path: str | None = None
    width: int = 0
    height: int = 0
    bounds: tuple[float, float, float, float] = (0, 0, 0, 0)
    encoder: str | None = None
    error: str | None = None
    message: str | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class JobStatus:
    id: str
    session_id: str
    document_id: str
    source_revision: int
    state: JobState = "queued"
    progress: float = 0
    phase: str = "queued"
    cancel_requested: bool = False
    outputs: tuple[OutputResult, ...] = ()
    error: str | None = None
    message: str | None = None
    dpi: int = 96

    @property
    def committed(self) -> tuple[Path, ...]:
        return tuple(Path(o.path) for o in self.outputs if o.state == "succeeded" and o.path)
