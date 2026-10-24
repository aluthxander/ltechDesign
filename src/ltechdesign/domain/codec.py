"""Strict in-memory JSON/member codec. No ZIP, disk IO, decoding or GUI admission."""

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, TypeVar, cast

from .errors import ModelError, fail
from .models import (
    AssetsIndex,
    Document,
    Fonts,
    InventoryEntry,
    Manifest,
    Project,
    Record,
    Tokens,
    Workspace,
    Writer,
)
from .typing import primitive, typed
from .validation import CORE_CAPABILITIES, SUPPORTED_CAPABILITIES

MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_JSON_DEPTH = 64
MEMBER_TYPES: dict[str, type[Record]] = {
    "manifest.json": Manifest,
    "document.json": Document,
    "tokens.json": Tokens,
    "fonts.json": Fonts,
    "assets/index.json": AssetsIndex,
    "workspace.json": Workspace,
}
T = TypeVar("T", bound=Record)


def parse_json(payload: str | bytes) -> Any:
    if type(payload) not in (str, bytes):
        fail("invalid_type", expected="str or bytes")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                fail("duplicate_key", f"$..{key}")
            result[key] = value
        return result

    def constant(value: str) -> None:
        fail("nonfinite_number", actual=value)

    def real(value: str) -> float:
        number = float(value)
        if not math.isfinite(number):
            fail("nonfinite_number", actual=value)
        return number

    try:
        size = len(payload.encode("utf-8")) if isinstance(payload, str) else len(payload)
        if size > MAX_JSON_BYTES:
            fail("json_bytes", code="limit_exceeded", actual=size, maximum=MAX_JSON_BYTES)
        text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        if text.startswith("\ufeff"):
            fail("invalid_json", reason_detail="BOM is not allowed")
        data = json.loads(text, object_pairs_hook=pairs, parse_constant=constant, parse_float=real)
        stack = [(data, 1)]
        while stack:
            value, depth = stack.pop()
            if depth > MAX_JSON_DEPTH:
                fail("json_depth", code="limit_exceeded", maximum=MAX_JSON_DEPTH)
            if isinstance(value, dict):
                stack.extend((v, depth + 1) for v in value.values())
            elif isinstance(value, list):
                stack.extend((v, depth + 1) for v in value)
        return data
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as error:
        if isinstance(error, ModelError):
            raise
        fail("invalid_json")


def to_data(record: Record) -> dict[str, Any]:
    if type(record) not in MEMBER_TYPES.values():
        fail("not_a_file_member", actual=type(record).__name__)
    return cast(dict[str, Any], primitive(record))


def from_data[T: Record](cls: type[T], data: Any) -> T:
    if cls not in MEMBER_TYPES.values():
        fail("not_a_file_member", actual=cls.__name__)
    if isinstance(data, dict):
        version_fields = (
            ("format_version", "document_schema_version")
            if cls is Manifest
            else ("schema_version",)
        )
        for key in version_fields:
            if key in data and data[key] != "1.0":
                fail(
                    "unsupported_version",
                    f"$.{key}",
                    code="unsupported_version",
                    actual=data[key],
                    supported=["1.0"],
                )
    return cast(T, typed(data, cls, "$", wire=True))


def json_bytes(data: Any) -> bytes:
    try:
        return json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode(
            "utf-8"
        )
    except (ValueError, TypeError, UnicodeError):
        fail("invalid_json")


def dumps(record: Record) -> str:
    payload = json_bytes(to_data(record))
    # Apply the same byte/depth budget on both directions.
    parse_json(payload)
    return payload.decode("utf-8")


def loads[T: Record](cls: type[T], payload: str | bytes) -> T:
    return from_data(cls, parse_json(payload))


def load_project(payloads: Mapping[str, bytes]) -> Project:
    """Validate a complete member snapshot and integrity before publishing the aggregate.

    This does not claim to decode images/fonts, sanitize SVG, evaluate layout,
    acquire locks, or read ZIP. Those are additional persistence admission gates.
    """
    if not isinstance(payloads, Mapping) or any(
        type(path) is not str or type(payload) is not bytes for path, payload in payloads.items()
    ):
        fail("invalid_type", expected="mapping of paths to bytes")
    if "manifest.json" not in payloads:
        fail("missing_entry", member="manifest.json")
    manifest = loads(Manifest, payloads["manifest.json"])
    unsupported = set(manifest.required_capabilities) - SUPPORTED_CAPABILITIES
    if unsupported:
        fail(
            "unsupported_capability",
            "$.required_capabilities",
            code="unsupported_capability",
            required=sorted(unsupported),
            supported=sorted(SUPPORTED_CAPABILITIES),
        )
    inventory = {e.path: e for e in manifest.files}
    if set(payloads) != set(inventory) | {"manifest.json"}:
        fail("inventory_mismatch")
    for path, entry in inventory.items():
        payload = payloads[path]
        if type(payload) is not bytes:
            fail("invalid_type", member=path, expected="bytes")
        if len(payload) != entry.byte_length or hashlib.sha256(payload).hexdigest() != entry.sha256:
            fail("integrity_mismatch", member=path)
    for path in MEMBER_TYPES.keys() - {"workspace.json"}:
        if path not in payloads:
            fail("missing_entry", member=path)
    assets = loads(AssetsIndex, payloads["assets/index.json"])
    blob_paths = {a.path for a in assets.assets}
    return Project(
        manifest=manifest,
        document=loads(Document, payloads["document.json"]),
        tokens=loads(Tokens, payloads["tokens.json"]),
        fonts=loads(Fonts, payloads["fonts.json"]),
        assets=assets,
        workspace=loads(Workspace, payloads["workspace.json"])
        if "workspace.json" in payloads
        else None,
        opaque_files={
            p: b for p, b in payloads.items() if p not in MEMBER_TYPES and p not in blob_paths
        },
    )


def dump_project(project: Project, asset_blobs: Mapping[str, bytes]) -> dict[str, bytes]:
    """Produce complete JSON/blob members and hashes from their final bytes, without IO."""
    expected_blobs = {a.path for a in project.assets.assets}
    if set(asset_blobs) != expected_blobs:
        fail("asset_inventory_mismatch")
    for asset in project.assets.assets:
        payload = asset_blobs[asset.path]
        if (
            type(payload) is not bytes
            or len(payload) != asset.byte_length
            or hashlib.sha256(payload).hexdigest() != asset.sha256
        ):
            fail("integrity_mismatch", member=asset.path)
    members: dict[str, Record] = {
        "document.json": project.document,
        "tokens.json": project.tokens,
        "fonts.json": project.fonts,
        "assets/index.json": project.assets,
    }
    if project.workspace is not None:
        members["workspace.json"] = project.workspace
    result = {name: dumps(record).encode("utf-8") for name, record in members.items()}
    result.update(asset_blobs)
    result.update(project.opaque_files)
    media = {e.path: e.media_type for e in project.manifest.files}
    inventory = tuple(
        InventoryEntry(
            path=p, media_type=media[p], byte_length=len(b), sha256=hashlib.sha256(b).hexdigest()
        )
        for p, b in sorted(result.items())
    )
    manifest = replace(project.manifest, files=inventory)
    result["manifest.json"] = dumps(manifest).encode("utf-8")
    load_project(result)
    return result


def semantic_content(project: Project) -> dict[str, Any]:
    """Portable design meaning; exclude writer/checkpoint/workspace/preview encodings."""
    extension_paths = {p for e in project.manifest.extensions for p in e.paths}
    return {
        "document": to_data(project.document),
        "tokens": to_data(project.tokens),
        "fonts": to_data(project.fonts),
        "assets": to_data(project.assets),
        "extensions": primitive(project.manifest.extensions),
        "extension_bytes": {p: project.opaque_files[p] for p in extension_paths},
        "required_capabilities": sorted(project.manifest.required_capabilities),
        "optional_capabilities": sorted(
            set(project.manifest.optional_capabilities)
            - {"workspace.view/1", "preview.thumbnail/1"}
        ),
    }


def create_project(name: str = "Untitled", *, saved_at: str | None = None) -> Project:
    """Construct an empty, fully valid project without a GUI or filesystem access."""
    document, tokens, fonts, assets = Document(name=name), Tokens(), Fonts(), AssetsIndex()
    members = {
        "document.json": document,
        "tokens.json": tokens,
        "fonts.json": fonts,
        "assets/index.json": assets,
    }
    encoded = {p: dumps(record).encode("utf-8") for p, record in members.items()}
    manifest = Manifest(
        document_id=document.document_id,
        saved_at=saved_at
        if saved_at is not None
        else datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        writer=Writer(name="ltechDesign", version="0.1.0"),
        required_capabilities=tuple(sorted(CORE_CAPABILITIES)),
        files=tuple(
            InventoryEntry(
                path=p,
                media_type="application/json",
                byte_length=len(b),
                sha256=hashlib.sha256(b).hexdigest(),
            )
            for p, b in sorted(encoded.items())
        ),
    )
    return Project(manifest=manifest, document=document, tokens=tokens, fonts=fonts, assets=assets)
