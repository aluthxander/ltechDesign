"""Immutable content records. No filesystem, Qt, renderer or transport dependencies.

Constructors validate types and local invariants; Document and Project additionally
validate their complete reference graphs. Defaults apply to construction only:
the wire format always requires every field, including nullable fields.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Annotated, Literal, NewType
from uuid import uuid4

SCHEMA_VERSION: Literal["1.0"] = "1.0"
MAX_REVISION = 9007199254740991
DocumentId = NewType("DocumentId", str)
PageId = NewType("PageId", str)
NodeId = NewType("NodeId", str)
AssetId = NewType("AssetId", str)
FontId = NewType("FontId", str)
TokenId = NewType("TokenId", str)
SessionId = NewType("SessionId", str)
Number = Annotated[float, "finite"]
Positive = Annotated[float, "finite", "positive"]
Nonnegative = Annotated[float, "finite", "nonnegative"]
Opacity = Annotated[float, "finite", "unit_interval"]
Color = Annotated[str, "color"]
Digest = Annotated[str, "sha256"]
Nonempty = Annotated[str, "nonempty"]
EntryPath = Annotated[str, "entry_path"]
Revision = Annotated[int, "revision"]
ByteLength = Annotated[int, "nonnegative", "safe_integer"]
Weight = Annotated[int, "weight"]
Version = Literal["1.0"]
NodeType = Literal[
    "artboard", "frame", "group", "rectangle", "ellipse", "line", "polygon", "text", "image", "svg"
]
Sizing = Literal["fixed", "hug", "fill"]


def new_id() -> str:
    return str(uuid4())


@dataclass(frozen=True, slots=True, kw_only=True)
class Record:
    def __post_init__(self) -> None:
        from .typing import check_record
        from .validation import validate_local

        check_record(self)
        validate_local(self)


@dataclass(frozen=True, slots=True, kw_only=True)
class Point(Record):
    x: Number = 0
    y: Number = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class Fill(Record):
    color: Color = "#000000FF"
    type: Literal["solid"] = "solid"


@dataclass(frozen=True, slots=True, kw_only=True)
class Stroke(Record):
    color: Color = "#000000FF"
    width: Positive = 1


@dataclass(frozen=True, slots=True, kw_only=True)
class Shadow(Record):
    offset_x: Number = 0
    offset_y: Number = 0
    blur: Nonnegative = 0
    spread: Nonnegative = 0
    color: Color = "#00000080"


@dataclass(frozen=True, slots=True, kw_only=True)
class Style(Record):
    fill: Fill | None = None
    stroke: Stroke | None = None
    radius: tuple[Nonnegative, Nonnegative, Nonnegative, Nonnegative] = (0, 0, 0, 0)
    shadows: Annotated[tuple[Shadow, ...], "max_eight"] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class EmptyData(Record):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class FrameData(Record):
    unit: Literal["px", "mm", "cm", "in"] = "px"
    dpi: Positive = 96
    background: Color | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class LineData(Record):
    start: Point
    end: Point


@dataclass(frozen=True, slots=True, kw_only=True)
class PolygonData(Record):
    points: Annotated[tuple[Point, ...], "min_three"]


@dataclass(frozen=True, slots=True, kw_only=True)
class LineHeight(Record):
    unit: Literal["multiplier", "px"] = "multiplier"
    value: Positive = 1.2


@dataclass(frozen=True, slots=True, kw_only=True)
class Typography(Record):
    font_id: FontId
    font_size: Positive = 16
    font_weight: Weight = 400
    italic: bool = False
    alignment: Literal["left", "center", "right", "justify"] = "left"
    vertical_alignment: Literal["top", "center", "bottom"] = "top"
    line_height: LineHeight = field(default_factory=LineHeight)
    letter_spacing: Number = 0
    sizing: Literal["fixed", "auto_width", "auto_height"] = "fixed"


@dataclass(frozen=True, slots=True, kw_only=True)
class TextData(Record):
    typography: Typography
    text: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class Crop(Record):
    x: Nonnegative = 0
    y: Nonnegative = 0
    width: Positive = 1
    height: Positive = 1


@dataclass(frozen=True, slots=True, kw_only=True)
class MediaData(Record):
    asset_id: AssetId
    fit: Literal["fit", "fill", "stretch"] = "fit"
    crop: Crop = field(default_factory=Crop)


NodeData = EmptyData | FrameData | LineData | PolygonData | TextData | MediaData


@dataclass(frozen=True, slots=True, kw_only=True)
class Layout(Record):
    type: Literal["stack"] = "stack"
    direction: Literal["horizontal", "vertical"] = "vertical"
    padding: tuple[Nonnegative, Nonnegative, Nonnegative, Nonnegative] = (0, 0, 0, 0)
    gap: Nonnegative = 0
    align_main: Literal["start", "center", "end"] = "start"
    align_cross: Literal["start", "center", "end", "stretch"] = "start"
    sizing_x: Sizing = "fixed"
    sizing_y: Sizing = "fixed"


@dataclass(frozen=True, slots=True, kw_only=True)
class Constraints(Record):
    horizontal: Literal["start", "end", "center", "stretch"] = "start"
    vertical: Literal["start", "end", "center", "stretch"] = "start"
    sizing_x: Sizing = "fixed"
    sizing_y: Sizing = "fixed"


@dataclass(frozen=True, slots=True, kw_only=True)
class Node(Record):
    id: NodeId
    type: NodeType
    page_id: PageId
    width: Nonnegative
    height: Nonnegative
    pivot: Point
    data: NodeData
    name: str = ""
    parent_id: NodeId | None = None
    children: tuple[NodeId, ...] = ()
    x: Number = 0
    y: Number = 0
    rotation: Number = 0
    scale: Positive = 1
    visible: bool = True
    locked: bool = False
    opacity: Opacity = 1
    clip_content: bool = False
    style: Style = field(default_factory=Style)
    layout: Layout | None = None
    constraints: Constraints | None = None


def create_node(
    kind: NodeType,
    page_id: PageId,
    *,
    width: float = 100,
    height: float = 100,
    data: NodeData | None = None,
    node_id: NodeId | None = None,
) -> Node:
    """New IDs and explicit create defaults; references must be supplied by callers."""
    if data is None:
        if kind in ("frame", "artboard"):
            data = FrameData()
        elif kind == "line":
            data = LineData(start=Point(), end=Point(x=width, y=height))
        elif kind == "polygon":
            data = PolygonData(points=(Point(), Point(x=width), Point(x=width / 2, y=height)))
        else:
            data = EmptyData()
    if kind == "group":
        width = height = 0
    return Node(
        id=node_id if node_id is not None else NodeId(new_id()),
        type=kind,
        page_id=page_id,
        width=width,
        height=height,
        pivot=Point(x=width / 2, y=height / 2),
        data=data,
        clip_content=kind == "artboard",
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class Page(Record):
    id: PageId = field(default_factory=lambda: PageId(new_id()))
    name: str = "Page 1"
    root_ids: tuple[NodeId, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class Document(Record):
    document_id: DocumentId = field(default_factory=lambda: DocumentId(new_id()))
    name: str = "Untitled"
    pages: Annotated[tuple[Page, ...], "min_one"] = field(default_factory=lambda: (Page(),))
    nodes: Mapping[NodeId, Node] = field(default_factory=dict)
    schema_version: Version = SCHEMA_VERSION


@dataclass(frozen=True, slots=True, kw_only=True)
class Asset(Record):
    id: AssetId
    path: EntryPath
    media_type: Literal[
        "image/png", "image/jpeg", "image/webp", "image/svg+xml", "font/ttf", "font/otf"
    ]
    byte_length: ByteLength
    sha256: Digest


@dataclass(frozen=True, slots=True, kw_only=True)
class AssetsIndex(Record):
    assets: tuple[Asset, ...] = ()
    schema_version: Version = SCHEMA_VERSION


@dataclass(frozen=True, slots=True, kw_only=True)
class FontLicense(Record):
    identifier: str
    url: str
    embedding_allowed: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class Font(Record):
    id: FontId
    family: str
    style: str = "Regular"
    weight: Weight = 400
    italic: bool = False
    postscript_name: str | None = None
    source: Literal["system", "embedded"] = "system"
    asset_id: AssetId | None = None
    fallback_families: tuple[str, ...] = ()
    license: FontLicense | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Fonts(Record):
    fonts: tuple[Font, ...] = ()
    schema_version: Version = SCHEMA_VERSION


@dataclass(frozen=True, slots=True, kw_only=True)
class ColorToken(Record):
    id: TokenId
    name: str
    value: Color
    type: Literal["color"] = "color"


@dataclass(frozen=True, slots=True, kw_only=True)
class NumberToken(Record):
    id: TokenId
    name: str
    value: Number
    type: Literal["number"] = "number"


@dataclass(frozen=True, slots=True, kw_only=True)
class StringToken(Record):
    id: TokenId
    name: str
    value: str
    type: Literal["string"] = "string"


Token = ColorToken | NumberToken | StringToken
PropertyPath = Literal[
    "style.fill.color",
    "style.stroke.color",
    "x",
    "y",
    "width",
    "height",
    "rotation",
    "scale",
    "opacity",
    "data.typography.font_size",
    "data.typography.letter_spacing",
    "data.text",
]


@dataclass(frozen=True, slots=True, kw_only=True)
class Binding(Record):
    node_id: NodeId
    property: PropertyPath
    token_id: TokenId


@dataclass(frozen=True, slots=True, kw_only=True)
class Tokens(Record):
    tokens: tuple[Token, ...] = ()
    bindings: tuple[Binding, ...] = ()
    schema_version: Version = SCHEMA_VERSION


@dataclass(frozen=True, slots=True, kw_only=True)
class View(Record):
    page_id: PageId
    pan: Point = field(default_factory=Point)
    zoom: Positive = 1


@dataclass(frozen=True, slots=True, kw_only=True)
class Workspace(Record):
    active_page_id: PageId
    views: tuple[View, ...] = ()
    schema_version: Version = SCHEMA_VERSION


@dataclass(frozen=True, slots=True, kw_only=True)
class Writer(Record):
    name: Nonempty
    version: Nonempty


@dataclass(frozen=True, slots=True, kw_only=True)
class InventoryEntry(Record):
    path: EntryPath
    media_type: Nonempty
    byte_length: ByteLength
    sha256: Digest


@dataclass(frozen=True, slots=True, kw_only=True)
class Extension(Record):
    id: Annotated[str, "extension_id"]
    version: Nonempty
    capability: Nonempty
    paths: tuple[EntryPath, ...]
    edit_policy: Literal["requires_support", "preserve_opaque"]
    asset_ids: tuple[AssetId, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class Manifest(Record):
    document_id: DocumentId
    saved_at: Annotated[str, "timestamp"]
    writer: Writer
    required_capabilities: tuple[Nonempty, ...]
    optional_capabilities: tuple[Nonempty, ...] = ()
    files: tuple[InventoryEntry, ...] = ()
    extensions: tuple[Extension, ...] = ()
    saved_revision: Revision = 0
    format_id: Literal["ltechdesign.project"] = "ltechdesign.project"
    format_version: Version = SCHEMA_VERSION
    document_schema_version: Version = SCHEMA_VERSION


@dataclass(frozen=True, slots=True, kw_only=True)
class Project(Record):
    """In-memory aggregate, not an additional archive member or wire envelope."""

    manifest: Manifest
    document: Document
    tokens: Tokens = field(default_factory=Tokens)
    fonts: Fonts = field(default_factory=Fonts)
    assets: AssetsIndex = field(default_factory=AssetsIndex)
    workspace: Workspace | None = None
    opaque_files: Mapping[str, bytes] = field(default_factory=dict)


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentSession(Record):
    """Runtime snapshot identity. Admission never resumes saved_revision."""

    project: Project
    session_id: SessionId = field(default_factory=lambda: SessionId(new_id()))
    revision: Revision = 0
