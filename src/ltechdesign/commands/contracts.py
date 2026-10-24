"""Typed local intent contract. Transport authentication belongs to the owner adapter."""

from dataclasses import dataclass
from typing import Literal

from ltechdesign.domain.models import (
    Asset,
    AssetId,
    Font,
    Node,
    NodeId,
    Nonempty,
    Number,
    PageId,
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
    | SetText
    | SetTokens
    | SetFont
    | RegisterAsset
    | RemoveAsset
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
