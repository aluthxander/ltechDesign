from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
from typing import Any

import pytest
from test_domain import fixture, payloads

from ltechdesign.domain import (
    Document,
    ModelError,
    create_project,
    dump_project,
    from_data,
    load_project,
    semantic_content,
)
from ltechdesign.domain.codec import json_bytes
from ltechdesign.domain.models import (
    Asset,
    AssetId,
    AssetsIndex,
    Font,
    FontId,
    FontLicense,
    InventoryEntry,
    Manifest,
    NodeId,
    Point,
    Workspace,
)

pytestmark = pytest.mark.core


def test_empty_project_is_usable_and_roundtrips_without_gui() -> None:
    project = create_project("New project", saved_at="2026-10-21T00:00:00Z")
    restored = load_project(dump_project(project, {}))
    assert semantic_content(restored) == semantic_content(project)
    assert len(project.document.pages) == 1 and not project.document.nodes
    assert project.manifest.saved_revision == 0


@pytest.mark.parametrize(
    "mutate,reason",
    [
        (
            lambda m: m["manifest.json"]["required_capabilities"].append("future.effect/1"),
            "unsupported_capability",
        ),
        (
            lambda m: m["manifest.json"]["required_capabilities"].append("tokens.core/1"),
            "duplicate_id",
        ),
        (
            lambda m: m["manifest.json"]["required_capabilities"].remove("tokens.core/1"),
            "missing_capability",
        ),
        (
            lambda m: m["manifest.json"]["required_capabilities"].remove("tokens.bindings/1"),
            "missing_capability",
        ),
        (
            lambda m: m["manifest.json"]["required_capabilities"].remove("assets.svg/1"),
            "missing_capability",
        ),
        (
            lambda m: m["manifest.json"]["required_capabilities"].remove("fonts.embedded/1"),
            "missing_capability",
        ),
        (
            lambda m: m["manifest.json"]["required_capabilities"].remove("render.clipping/1"),
            "missing_capability",
        ),
        (
            lambda m: m["manifest.json"]["required_capabilities"].remove(
                "render.isolated-opacity/1"
            ),
            "missing_capability",
        ),
        (
            lambda m: m["manifest.json"]["optional_capabilities"].append("tokens.core/1"),
            "capability_overlap",
        ),
        (
            lambda m: m["manifest.json"]["optional_capabilities"].append("workspace.view/1"),
            "duplicate_id",
        ),
        (lambda m: m["manifest.json"].update(document_id="other"), "document_identity_mismatch"),
        (
            lambda m: m["manifest.json"]["files"].append(deepcopy(m["manifest.json"]["files"][0])),
            "duplicate_id",
        ),
        (
            lambda m: m["tokens.json"]["tokens"].append(deepcopy(m["tokens.json"]["tokens"][0])),
            "duplicate_id",
        ),
        (
            lambda m: m["tokens.json"]["bindings"].append(
                deepcopy(m["tokens.json"]["bindings"][0])
            ),
            "duplicate_id",
        ),
        (
            lambda m: m["tokens.json"]["bindings"][0].update(token_id="missing"),
            "missing_binding_reference",
        ),
        (
            lambda m: m["tokens.json"]["bindings"][0].update(node_id="missing"),
            "missing_binding_reference",
        ),
        (
            lambda m: m["tokens.json"]["bindings"][0].update(property="data.typography.font_size"),
            "binding_type_mismatch",
        ),
        (
            lambda m: m["tokens.json"]["bindings"][0].update(property="style.stroke.color"),
            "invalid_binding_target",
        ),
        (
            lambda m: m["tokens.json"]["tokens"][0].update(value="#FF00FFFF"),
            "binding_value_mismatch",
        ),
        (lambda m: m["tokens.json"]["bindings"][0].update(property="$.x"), "invalid_literal"),
        (lambda m: m["tokens.json"]["tokens"][0].update(type="alias"), "invalid_literal"),
        (
            lambda m: m["fonts.json"]["fonts"].append(deepcopy(m["fonts.json"]["fonts"][0])),
            "duplicate_id",
        ),
        (
            lambda m: m["fonts.json"]["fonts"][0].update(asset_id="asset-abel"),
            "invalid_font_source",
        ),
        (lambda m: m["fonts.json"]["fonts"][1].update(asset_id="missing"), "missing_asset"),
        (
            lambda m: m["fonts.json"]["fonts"][1].update(asset_id="asset-pixel"),
            "asset_media_mismatch",
        ),
        (
            lambda m: m["fonts.json"]["fonts"][1]["license"].update(embedding_allowed=False),
            "font_embedding_not_declared",
        ),
        (
            lambda m: m["document.json"]["nodes"]["text-title"]["data"]["typography"].update(
                font_id="missing"
            ),
            "missing_font",
        ),
        (
            lambda m: m["document.json"]["nodes"]["image-pixel"]["data"].update(asset_id="missing"),
            "missing_asset",
        ),
        (
            lambda m: m["document.json"]["nodes"]["image-pixel"]["data"].update(
                asset_id="asset-svg"
            ),
            "asset_media_mismatch",
        ),
        (
            lambda m: m["document.json"]["nodes"]["svg-logo"]["data"].update(
                asset_id="asset-pixel"
            ),
            "asset_media_mismatch",
        ),
        (
            lambda m: m["assets/index.json"]["assets"].append(
                deepcopy(m["assets/index.json"]["assets"][0])
            ),
            "duplicate_id",
        ),
        (
            lambda m: m["assets/index.json"]["assets"][0].update(path="assets/data/" + "0" * 64),
            "asset_path_mismatch",
        ),
        (
            lambda m: m["assets/index.json"]["assets"][0].update(byte_length=1),
            "asset_metadata_mismatch",
        ),
        (lambda m: m["workspace.json"].update(active_page_id="missing"), "missing_page"),
        (lambda m: m["workspace.json"]["views"][0].update(page_id="missing"), "missing_page"),
        (
            lambda m: m["workspace.json"]["views"].append(
                deepcopy(m["workspace.json"]["views"][0])
            ),
            "duplicate_id",
        ),
        (lambda m: m["workspace.json"]["views"][0].update(zoom=0), "out_of_range"),
    ],
)
def test_project_cross_member_invariants(mutate: Callable[[Any], None], reason: str) -> None:
    wrapper = fixture()
    mutate(wrapper["members"])
    with pytest.raises(ModelError) as caught:
        load_project(payloads(wrapper, rehash=True))
    assert caught.value.reason == reason


@pytest.mark.parametrize(
    "path",
    [
        "/absolute",
        "C:/absolute",
        "a\\b",
        "a//b",
        "a/../b",
        "./a",
        "a/./b",
        "a/",
        "a.",
        "a ",
        "a/con.txt",
        "NUL",
        "a/COM1",
        "a/lpt9.dat",
        "a/COM¹.txt",
        "a\x00b",
        "a\x1fb",
        "a\x7fb",
        "a:b",
        "e\u0301/data",
    ],
)
def test_inventory_path_contract(path: str) -> None:
    with pytest.raises(ModelError, match="unsafe_path"):
        InventoryEntry(path=path, media_type="application/json", byte_length=0, sha256="0" * 64)


@pytest.mark.parametrize(
    "field,value",
    [
        ("saved_revision", True),
        ("saved_revision", 1.0),
        ("saved_revision", -1),
        ("saved_revision", 9007199254740992),
        ("saved_at", "2026-02-30T00:00:00Z"),
        ("saved_at", "2026-10-21T00:00:00+07:00"),
        ("saved_at", "2026-10-21"),
        ("format_id", "other.project"),
    ],
)
def test_manifest_scalars(field: str, value: Any) -> None:
    manifest = fixture()["members"]["manifest.json"]
    manifest[field] = value
    with pytest.raises(ModelError):
        from_data(Manifest, manifest)


def test_inventory_aliases_integrity_and_undeclared_entries() -> None:
    wrapper = fixture()
    entry = deepcopy(wrapper["members"]["manifest.json"]["files"][0])
    entry["path"] = entry["path"].upper()
    wrapper["members"]["manifest.json"]["files"].append(entry)
    with pytest.raises(ModelError, match="duplicate_id"):
        load_project(payloads(wrapper))
    original = payloads(fixture())
    broken = dict(original)
    broken["document.json"] += b" "
    with pytest.raises(ModelError, match="integrity_mismatch"):
        load_project(broken)
    broken = dict(original)
    broken["extra.txt"] = b"unlisted"
    with pytest.raises(ModelError, match="inventory_mismatch"):
        load_project(broken)
    broken = dict(original)
    del broken[next(p for p in broken if p.startswith("assets/data/"))]
    with pytest.raises(ModelError, match="inventory_mismatch"):
        load_project(broken)
    with pytest.raises(ModelError, match="missing_entry"):
        load_project({})


def test_optional_metadata_extension_bytes_are_preserved_exactly() -> None:
    raw = payloads(fixture())
    project = load_project(raw)
    payload = b"\x00metadata\xff\r\n"
    import hashlib

    path = "extensions/example.notes/data.bin"
    wrapper = fixture()
    manifest = wrapper["members"]["manifest.json"]
    manifest["extensions"] = [
        {
            "id": "example.notes",
            "version": "1",
            "capability": "example.notes/1",
            "paths": [path],
            "edit_policy": "preserve_opaque",
            "asset_ids": ["asset-pixel"],
        }
    ]
    manifest["optional_capabilities"].append("example.notes/1")
    manifest["files"].append(
        {
            "path": path,
            "media_type": "application/octet-stream",
            "byte_length": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    )
    raw = payloads(wrapper)
    raw[path] = payload
    extended = load_project(raw)
    assert extended.opaque_files[path] == payload
    blobs = {a.path: raw[a.path] for a in project.assets.assets}
    restored = load_project(dump_project(extended, blobs))
    assert semantic_content(extended) == semantic_content(restored)
    assert restored.opaque_files[path] is payload
    with pytest.raises(ModelError, match="opaque_inventory_mismatch"):
        replace(extended, opaque_files={})
    with pytest.raises(ModelError, match="integrity_mismatch"):
        replace(extended, opaque_files={path: b"lost"})
    manifest["extensions"][0]["asset_ids"] = ["missing"]
    raw["manifest.json"] = json_bytes(manifest)
    with pytest.raises(ModelError, match="missing_asset"):
        load_project(raw)


@pytest.mark.parametrize(
    "edit_policy,capability",
    [
        ("requires_support", "unknown.behavior/1"),
        ("requires_support", "document.core/1"),
    ],
)
def test_required_extensions_cannot_borrow_core_support(edit_policy: str, capability: str) -> None:
    wrapper = fixture()
    manifest = wrapper["members"]["manifest.json"]
    manifest["extensions"] = [
        {
            "id": "x",
            "version": "1",
            "capability": capability,
            "paths": [],
            "edit_policy": edit_policy,
            "asset_ids": [],
        }
    ]
    if capability not in manifest["required_capabilities"]:
        manifest["required_capabilities"].append(capability)
    with pytest.raises(ModelError) as caught:
        load_project(payloads(wrapper))
    assert caught.value.code == "unsupported_capability"


def test_asset_blob_aliases_allowed_but_contradictory_metadata_rejected() -> None:
    asset = Asset(
        id=AssetId("a"),
        path="assets/data/" + "0" * 64,
        media_type="image/png",
        byte_length=20,
        sha256="0" * 64,
    )
    assert len(AssetsIndex(assets=(asset, replace(asset, id=AssetId("b")))).assets) == 2
    with pytest.raises(ModelError, match="asset_metadata_mismatch"):
        AssetsIndex(assets=(asset, replace(asset, id=AssetId("b"), byte_length=21)))


def test_system_font_is_metadata_only_and_embedded_reference_is_required() -> None:
    font = Font(id=FontId("uninstalled"), family="Font definitely not installed")
    assert font.source == "system" and font.asset_id is None
    with pytest.raises(ModelError, match="invalid_font_source"):
        replace(font, source="embedded")
    with pytest.raises(ModelError, match="font_embedding_not_declared"):
        replace(font, source="embedded", asset_id=AssetId("font-asset"))
    embedded = replace(
        font,
        source="embedded",
        asset_id=AssetId("font-asset"),
        license=FontLicense(identifier="OFL", url="", embedding_allowed=True),
    )
    assert embedded.family == font.family


def test_optional_workspace_absence_and_strict_malformed_policy() -> None:
    wrapper = fixture()
    del wrapper["members"]["workspace.json"]
    manifest = wrapper["members"]["manifest.json"]
    manifest["files"] = [e for e in manifest["files"] if e["path"] != "workspace.json"]
    project = load_project(payloads(wrapper))
    assert project.workspace is None
    invalid = fixture()["members"]["workspace.json"]
    invalid["selection"] = ["text-title"]
    with pytest.raises(ModelError, match="unknown_property"):
        from_data(Workspace, invalid)


@pytest.mark.parametrize(
    "property_path,token_type,value",
    [
        ("x", "number", 10),
        ("y", "number", 10),
        ("width", "number", 200),
        ("height", "number", 60),
        ("rotation", "number", 0),
        ("scale", "number", 1),
        ("opacity", "number", 1),
        ("data.typography.letter_spacing", "number", 0),
        ("style.fill.color", "color", "#FFFFFFFF"),
    ],
)
def test_property_path_binding_allowlist(property_path: str, token_type: str, value: Any) -> None:
    wrapper = fixture()
    tokens = wrapper["members"]["tokens.json"]
    tokens["tokens"].append({"id": "bound", "name": "", "type": token_type, "value": value})
    tokens["bindings"].append(
        {"node_id": "text-title", "property": property_path, "token_id": "bound"}
    )
    project = load_project(payloads(wrapper, rehash=True))
    assert project.tokens.bindings[-1].property == property_path


def test_materialized_token_cannot_bypass_target_range() -> None:
    wrapper = fixture()
    wrapper["members"]["document.json"]["nodes"]["text-title"]["data"]["typography"][
        "font_size"
    ] = -20
    wrapper["members"]["tokens.json"]["tokens"][-1]["value"] = -20
    with pytest.raises(ModelError, match="out_of_range"):
        load_project(payloads(wrapper, rehash=True))


def test_hierarchy_depth_budget_and_nested_unknown_fields() -> None:
    data = fixture()["members"]["document.json"]
    frame = deepcopy(data["nodes"]["frame-nested"])
    parent = "artboard-web"
    for index in range(65):
        key = f"deep-{index}"
        node = deepcopy(frame)
        node.update(id=key, page_id="page-web", parent_id=parent, children=[])
        data["nodes"][key] = node
        data["nodes"][parent]["children"].append(key)
        parent = key
    with pytest.raises(ModelError) as caught:
        from_data(Document, data)
    assert caught.value.code == "limit_exceeded"
    data = fixture()["members"]["document.json"]
    data["nodes"]["text-title"]["data"]["typography"]["font_path"] = "C:/font.ttf"
    with pytest.raises(ModelError, match="unknown_property"):
        from_data(Document, data)


def test_epsilon_is_only_for_derived_group_geometry_not_positive_dimensions() -> None:
    data = fixture()["members"]["document.json"]
    data["nodes"]["group-content"]["width"] += 5e-10
    assert from_data(Document, data).nodes[NodeId("group-content")].width > 300
    data["nodes"]["group-content"]["width"] += 1e-5
    with pytest.raises(ModelError, match="group_geometry_mismatch"):
        from_data(Document, data)
    assert Point(x=1e-300).x > 0
