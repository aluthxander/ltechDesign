"""Typed local intent contract. Transport authentication belongs to the owner adapter."""

from dataclasses import dataclass
from typing import Literal

from ltechdesign.domain.arrangement import ArrangeMode
from ltechdesign.domain.geometry import Matrix
from ltechdesign.domain.inspector import Property
from ltechdesign.domain.models import (
    Asset,
    AssetId,
    Font,
    Node,
    NodeId,
    Nonempty,
    Number,
    Page,
    PageId,
    Point,
    Project,
    Record,
    Revision,
    SessionId,
    Style,
    TextData,
    Tokens,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class Create(Record):
    node: Node
    index: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Update(Record):
    """Replace authoring properties; identity/type/hierarchy cannot be changed here."""

    node: Node


@dataclass(frozen=True, slots=True, kw_only=True)
class Delete(Record):
    node_id: NodeId


@dataclass(frozen=True, slots=True, kw_only=True)
class Move(Record):
    node_id: NodeId
    dx: Number
    dy: Number


@dataclass(frozen=True, slots=True, kw_only=True)
class Reparent(Record):
    node_id: NodeId
    page_id: PageId
    parent_id: NodeId | None = None
    index: int | None = None
    preserve_appearance: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class Reorder(Record):
    node_id: NodeId
    index: int


@dataclass(frozen=True, slots=True, kw_only=True)
class Group(Record):
    node_ids: tuple[NodeId, ...]
    group_id: NodeId
    name: str = "Group"
    preserve_appearance: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class Ungroup(Record):
    node_id: NodeId
    preserve_appearance: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class Duplicate(Record):
    node_id: NodeId
    dx: Number = 0
    dy: Number = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class SetStyle(Record):
    node_id: NodeId
    style: Style


@dataclass(frozen=True, slots=True, kw_only=True)
class SetProperties(Record):
    """One Inspector field across explicit targets, validated and published atomically."""

    node_ids: tuple[NodeId, ...]
    property: Property
    value: Number | str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class SetText(Record):
    node_id: NodeId
    data: TextData


@dataclass(frozen=True, slots=True, kw_only=True)
class SetTokens(Record):
    """Materialized node values must agree at the transaction's final validation."""

    tokens: Tokens


@dataclass(frozen=True, slots=True, kw_only=True)
class SetFont(Record):
    font: Font


@dataclass(frozen=True, slots=True, kw_only=True)
class RegisterAsset(Record):
    asset: Asset
    staging_id: Nonempty


@dataclass(frozen=True, slots=True, kw_only=True)
class RemoveAsset(Record):
    asset_id: AssetId


@dataclass(frozen=True, slots=True, kw_only=True)
class TransformNodes(Record):
    node_ids: tuple[NodeId, ...]
    matrix: Matrix  # world-space positive similarity


@dataclass(frozen=True, slots=True, kw_only=True)
class ArrangeNodes(Record):
    node_ids: tuple[NodeId, ...]
    mode: ArrangeMode


@dataclass(frozen=True, slots=True, kw_only=True)
class ResizeNode(Record):
    node_id: NodeId
    width: Number
    height: Number
    anchor: Point


@dataclass(frozen=True, slots=True, kw_only=True)
class ScaleNodes(Record):
    node_ids: tuple[NodeId, ...]
    factor: Number
    center: Point


@dataclass(frozen=True, slots=True, kw_only=True)
class EditNodes(Record):
    node_ids: tuple[NodeId, ...]
    edit: Literal["delete", "duplicate", "forward", "backward", "ungroup"]


@dataclass(frozen=True, slots=True, kw_only=True)
class ReparentNodes(Record):
    node_ids: tuple[NodeId, ...]
    page_id: PageId
    parent_id: NodeId | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class PasteNodes(Record):
    project: Project  # validated, fresh IDs; assets already staged in the same transaction
    page_id: PageId
    parent_id: NodeId | None = None
    offset: Point = Point(x=10, y=10)


@dataclass(frozen=True, slots=True, kw_only=True)
class CreatePage(Record):
    page: Page
    index: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdatePage(Record):
    page_id: PageId
    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DuplicatePage(Record):
    page_id: PageId
    new_page_id: PageId
    name: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class DeletePage(Record):
    page_id: PageId
    delete_contents: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class SetLayerState(Record):
    node_ids: tuple[NodeId, ...]
    visible: bool | None = None
    locked: bool | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class RelocateNodes(Record):
    node_ids: tuple[NodeId, ...]
    page_id: PageId
    parent_id: NodeId | None = None
    index: int | None = None  # destination index after removing all selected roots
    preserve_appearance: bool = True


Operation = (
    Create
    | Update
    | Delete
    | Move
    | Reparent
    | Reorder
    | Group
    | Ungroup
    | Duplicate
    | SetStyle
    | SetProperties
    | SetText
    | SetTokens
    | SetFont
    | RegisterAsset
    | RemoveAsset
    | TransformNodes
    | ArrangeNodes
    | ResizeNode
    | ScaleNodes
    | EditNodes
    | ReparentNodes
    | PasteNodes
    | CreatePage
    | UpdatePage
    | DuplicatePage
    | DeletePage
    | SetLayerState
    | RelocateNodes
)


@dataclass(frozen=True, slots=True, kw_only=True)
class Request(Record):
    session_id: SessionId
    expected_revision: Revision
    request_id: Nonempty
    action_name: Nonempty
    source: Literal["GUI", "AI"]
    operations: tuple[Operation, ...] = ()
    action: Literal["execute", "undo", "redo"] = "execute"
    history_group: Nonempty | None = None


@dataclass(frozen=True, slots=True)
class Error:
    code: str
    message: str
    details: tuple[tuple[str, str], ...] = ()
    retryable: bool = False
    current_revision: int | None = None

    def to_dict(self) -> dict[str, object]:
        return dict(
            code=self.code,
            message=self.message,
            details=dict(self.details),
            retryable=self.retryable,
            current_revision=self.current_revision,
        )


@dataclass(frozen=True, slots=True)
class Result:
    session_id: SessionId
    document_id: str
    revision: int
    error: Error | None = None
    id_map: tuple[tuple[NodeId, NodeId], ...] = ()
    history_evicted: int = 0

    @property
    def ok(self) -> bool:
        return self.error is None
