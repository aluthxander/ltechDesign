"""Local and cross-member invariants beyond structural JSON Schema."""

from collections.abc import Iterable
from typing import Any

from . import models as m
from .errors import fail

CORE_CAPABILITIES = frozenset(
    {
        "document.core/1",
        "geometry.similarity/1",
        "assets.embedded/1",
        "tokens.core/1",
        "fonts.metadata/1",
    }
)
SUPPORTED_CAPABILITIES = CORE_CAPABILITIES | {
    "render.isolated-opacity/1",
    "render.clipping/1",
    "tokens.bindings/1",
    "assets.svg/1",
    "fonts.embedded/1",
}
OPTIONAL_CAPABILITIES = frozenset({"workspace.view/1", "preview.thumbnail/1"})
DATA_TYPES: dict[str, type[m.Record]] = {
    "rectangle": m.EmptyData,
    "ellipse": m.EmptyData,
    "group": m.EmptyData,
    "artboard": m.FrameData,
    "frame": m.FrameData,
    "line": m.LineData,
    "polygon": m.PolygonData,
    "text": m.TextData,
    "image": m.MediaData,
    "svg": m.MediaData,
}
CONTAINERS = frozenset({"artboard", "frame", "group"})


def unique(values: Iterable[Any], path: str) -> None:
    seen = set()
    for value in values:
        if value in seen:
            fail("duplicate_id", path, value=value)
        seen.add(value)


def validate_local(value: m.Record) -> None:
    if isinstance(value, m.Node):
        validate_node(value)
    elif isinstance(value, m.Document):
        validate_document(value)
    elif isinstance(value, m.Project):
        validate_project(value)
    elif isinstance(value, m.Page):
        unique(value.root_ids, "$.root_ids")
    elif isinstance(value, m.Crop):
        if value.x + value.width > 1 or value.y + value.height > 1:
            fail("invalid_crop")
    elif isinstance(value, m.Asset):
        if value.path != "assets/data/" + value.sha256:
            fail("asset_path_mismatch", "$.path")
    elif isinstance(value, m.AssetsIndex):
        unique((a.id for a in value.assets), "$.assets")
        blobs: dict[str, m.Asset] = {}
        for asset in value.assets:
            other = blobs.get(asset.path)
            if other and (other.byte_length, other.media_type) != (
                asset.byte_length,
                asset.media_type,
            ):
                fail("asset_metadata_mismatch", "$.assets")
            blobs[asset.path] = asset
    elif isinstance(value, m.Font):
        if (value.source == "system") != (value.asset_id is None):
            fail("invalid_font_source", "$.asset_id")
        if value.source == "embedded" and (
            value.license is None or not value.license.embedding_allowed
        ):
            fail("font_embedding_not_declared", "$.license")
    elif isinstance(value, m.Fonts):
        unique((f.id for f in value.fonts), "$.fonts")
    elif isinstance(value, m.Tokens):
        unique((t.id for t in value.tokens), "$.tokens")
        unique(((b.node_id, b.property) for b in value.bindings), "$.bindings")
    elif isinstance(value, m.Workspace):
        unique((v.page_id for v in value.views), "$.views")
    elif isinstance(value, m.Extension):
        unique(value.paths, "$.paths")
        unique(value.asset_ids, "$.asset_ids")
        if any(not p.startswith(f"extensions/{value.id}/") for p in value.paths):
            fail("invalid_extension_path", "$.paths")
    elif isinstance(value, m.Manifest):
        validate_manifest(value)


def validate_node(node: m.Node) -> None:
    if type(node.data) is not DATA_TYPES[node.type]:
        fail("invalid_node_payload", "$.data", node_type=node.type)
    unique(node.children, "$.children")
    if node.type not in CONTAINERS:
        if node.children:
            fail("leaf_has_children", "$.children")
        if node.clip_content:
            fail("leaf_clip_content", "$.clip_content")
    if node.type == "artboard" and node.parent_id is not None:
        fail("nested_artboard", "$.parent_id")
    if node.type not in ("line", "group"):
        if node.width <= 0:
            fail("invalid_dimensions", "$.width")
        if node.height <= 0:
            fail("invalid_dimensions", "$.height")
    if node.layout is not None and node.type not in ("artboard", "frame"):
        fail("invalid_layout_target", "$.layout")
    if node.type not in ("rectangle", "frame", "artboard", "image", "svg"):
        if any(node.style.radius):
            fail("invalid_radius_target", "$.style.radius")
    if node.type == "group" and (node.style.fill is not None or node.style.stroke is not None):
        fail("invalid_group_style", "$.style")
    if isinstance(node.data, (m.LineData, m.PolygonData)):
        points = (
            (node.data.start, node.data.end)
            if isinstance(node.data, m.LineData)
            else node.data.points
        )
        if isinstance(node.data, m.LineData) and node.data.start == node.data.end:
            fail("degenerate_line", "$.data")
        # Authoring vertices are canonical: exact zero minima and exact stored maxima.
        if (
            min(p.x for p in points),
            min(p.y for p in points),
            max(p.x for p in points),
            max(p.y for p in points),
        ) != (0, 0, node.width, node.height):
            fail("geometry_extent_mismatch", "$.data")
    if node.type == "group" and not node.children:
        if node.width != 0 or node.height != 0 or node.pivot != m.Point():
            fail("empty_group_geometry")


def validate_document(document: m.Document) -> None:
    unique((p.id for p in document.pages), "$.pages")
    pages = {p.id: p for p in document.pages}
    nodes = document.nodes
    membership = dict.fromkeys(nodes, 0)
    for key, node in nodes.items():
        path = f"$.nodes[{key}]"
        if node.id != key or str(key) in {str(p) for p in pages}:
            fail("id_mismatch", path)
        if node.page_id not in pages:
            fail("missing_page", path + ".page_id")
        if node.parent_id is not None and node.parent_id not in nodes:
            fail("missing_node", path + ".parent_id")
    # Follow parents first: disconnected cycles must be diagnosed, not treated as roots.
    done: set[m.NodeId] = set()
    for key in nodes:
        chain: set[m.NodeId] = set()
        cursor: m.NodeId | None = key
        while cursor is not None and cursor not in done:
            if cursor in chain:
                fail("hierarchy_cycle", f"$.nodes[{cursor}].parent_id")
            chain.add(cursor)
            cursor = nodes[cursor].parent_id
        done.update(chain)
    for page in document.pages:
        for key in page.root_ids:
            if key not in nodes:
                fail("missing_node", f"$.pages[{page.id}].root_ids", node_id=key)
            if nodes[key].page_id != page.id or nodes[key].parent_id is not None:
                fail("root_ownership_mismatch", f"$.pages[{page.id}].root_ids", node_id=key)
            membership[key] += 1
    for node in nodes.values():
        for key in node.children:
            if key not in nodes:
                fail("missing_node", f"$.nodes[{node.id}].children", node_id=key)
            child = nodes[key]
            if child.parent_id != node.id or child.page_id != node.page_id:
                fail("parent_mismatch", f"$.nodes[{key}].parent_id")
            membership[key] += 1
    for key, count in membership.items():
        if count != 1:
            fail("invalid_membership", f"$.nodes[{key}]", actual=count)
    # Bound hierarchy separately from JSON nesting: the registry is flat on disk.
    stack = [(key, 1) for page in document.pages for key in page.root_ids]
    while stack:
        key, depth = stack.pop()
        if depth > 64:
            fail("hierarchy_depth", f"$.nodes[{key}]", code="limit_exceeded", maximum=64)
        stack.extend((child, depth + 1) for child in nodes[key].children)
    from .geometry import close, subtree_geometry_bounds

    for node in nodes.values():
        if node.type == "group" and node.children:
            bounds = subtree_geometry_bounds(document, node.id)
            expected = (0, 0, node.width, node.height)
            if bounds is None or not all(
                close(a, b) for a, b in zip(bounds.extents, expected, strict=False)
            ):
                fail("group_geometry_mismatch", f"$.nodes[{node.id}]", expected=expected)


def validate_manifest(manifest: m.Manifest) -> None:
    unique(manifest.required_capabilities, "$.required_capabilities")
    unique(manifest.optional_capabilities, "$.optional_capabilities")
    required, optional = set(manifest.required_capabilities), set(manifest.optional_capabilities)
    if required & optional:
        fail("capability_overlap")
    if not CORE_CAPABILITIES <= required:
        fail(
            "missing_capability",
            "$.required_capabilities",
            required=sorted(CORE_CAPABILITIES - required),
        )
    unique((e.path.casefold() for e in manifest.files), "$.files")
    unique((e.id for e in manifest.extensions), "$.extensions")
    paths = {e.path for e in manifest.files}
    if "manifest.json" in paths:
        fail("recursive_inventory", "$.files")
    extension_paths: list[str] = []
    for extension in manifest.extensions:
        target = required if extension.edit_policy == "requires_support" else optional
        if extension.capability not in target:
            fail("missing_capability", "$.extensions", required=[extension.capability])
        if not set(extension.paths) <= paths:
            fail("missing_entry", "$.extensions")
        extension_paths.extend(extension.paths)
    unique(extension_paths, "$.extensions")


def required_capabilities(project: m.Project) -> frozenset[str]:
    required = set(CORE_CAPABILITIES)
    if project.tokens.bindings:
        required.add("tokens.bindings/1")
    if any(a.media_type == "image/svg+xml" for a in project.assets.assets):
        required.add("assets.svg/1")
    if any(f.source == "embedded" for f in project.fonts.fonts):
        required.add("fonts.embedded/1")
    for node in project.document.nodes.values():
        if node.type == "group" and node.opacity != 1:
            required.add("render.isolated-opacity/1")
        if node.clip_content or (node.type in ("image", "svg") and any(node.style.radius)):
            required.add("render.clipping/1")
        if node.layout is not None:
            required.add("layout.stack/1")
        if node.type == "svg":
            required.add("assets.svg/1")
    return frozenset(required)


def validate_project(project: m.Project) -> None:
    manifest, document = project.manifest, project.document
    required = set(manifest.required_capabilities)
    unsupported = required - SUPPORTED_CAPABILITIES
    if unsupported:
        fail(
            "unsupported_capability",
            "$.manifest.required_capabilities",
            code="unsupported_capability",
            required=sorted(unsupported),
            supported=sorted(SUPPORTED_CAPABILITIES),
        )
    if manifest.document_id != document.document_id:
        fail("document_identity_mismatch", "$.manifest.document_id")
    missing = required_capabilities(project) - required
    if missing:
        fail("missing_capability", "$.manifest.required_capabilities", required=sorted(missing))
    assets = {a.id: a for a in project.assets.assets}
    fonts = {f.id: f for f in project.fonts.fonts}
    tokens = {t.id: t for t in project.tokens.tokens}
    for font in fonts.values():
        if font.asset_id is not None:
            if font.asset_id not in assets:
                fail("missing_asset", f"$.fonts[{font.id}].asset_id")
            if assets[font.asset_id].media_type not in ("font/ttf", "font/otf"):
                fail("asset_media_mismatch", f"$.fonts[{font.id}].asset_id")
    for node in document.nodes.values():
        path = f"$.document.nodes[{node.id}]"
        if node.layout is not None or node.constraints is not None:
            fail("layout_evaluator_unavailable", path, code="unsupported_capability")
        if isinstance(node.data, m.TextData) and node.data.typography.font_id not in fonts:
            fail("missing_font", path + ".data.typography.font_id")
        if isinstance(node.data, m.MediaData):
            asset = assets.get(node.data.asset_id)
            if asset is None:
                fail("missing_asset", path + ".data.asset_id")
            allowed = (
                ("image/svg+xml",)
                if node.type == "svg"
                else ("image/png", "image/jpeg", "image/webp")
            )
            if asset.media_type not in allowed:
                fail("asset_media_mismatch", path + ".data.asset_id")
    for binding in project.tokens.bindings:
        path = f"$.tokens.bindings[{binding.node_id}/{binding.property}]"
        bound_node = document.nodes.get(binding.node_id)
        token = tokens.get(binding.token_id)
        if bound_node is None or token is None:
            fail("missing_binding_reference", path)
        expected = (
            "color"
            if binding.property.endswith(".color")
            else "string"
            if binding.property == "data.text"
            else "number"
        )
        if token.type != expected:
            fail("binding_type_mismatch", path)
        target: Any = bound_node
        for component in binding.property.split("."):
            if not hasattr(target, component):
                fail("invalid_binding_target", path)
            target = getattr(target, component)
        if target != token.value:
            fail("binding_value_mismatch", path)
    if project.workspace is not None:
        page_ids = {p.id for p in document.pages}
        if project.workspace.active_page_id not in page_ids or any(
            v.page_id not in page_ids for v in project.workspace.views
        ):
            fail("missing_page", "$.workspace")
    expected_paths = {"document.json", "assets/index.json", "fonts.json", "tokens.json"}
    if project.workspace is not None:
        expected_paths.add("workspace.json")
    expected_paths.update(a.path for a in assets.values())
    extension_paths: set[str] = set()
    for extension in manifest.extensions:
        # No extension adapters exist yet, even if a descriptor borrows a core capability.
        if extension.edit_policy != "preserve_opaque":
            fail(
                "extension_adapter_unavailable",
                "$.manifest.extensions",
                code="unsupported_capability",
                required=[extension.capability],
            )
        if any(a not in assets for a in extension.asset_ids):
            fail("missing_asset", "$.manifest.extensions")
        extension_paths.update(extension.paths)
    inventory = {e.path: e for e in manifest.files}
    previews = {p for p in inventory if p.startswith("thumbnails/") and p.endswith(".png")}
    if previews and "preview.thumbnail/1" not in manifest.optional_capabilities:
        fail("missing_capability", "$.manifest.optional_capabilities")
    if project.workspace and "workspace.view/1" not in manifest.optional_capabilities:
        fail("missing_capability", "$.manifest.optional_capabilities")
    opaque_paths = extension_paths | previews
    if set(project.opaque_files) != opaque_paths:
        fail("opaque_inventory_mismatch", "$.opaque_files")
    expected_paths.update(opaque_paths)
    if set(inventory) != expected_paths:
        fail("inventory_mismatch", "$.manifest.files", expected=sorted(expected_paths))
    for path, entry in inventory.items():
        if (
            path
            in {"document.json", "assets/index.json", "fonts.json", "tokens.json", "workspace.json"}
            and entry.media_type != "application/json"
        ):
            fail("invalid_media_type", "$.manifest.files", member=path)
        if path in previews and entry.media_type != "image/png":
            fail("invalid_media_type", "$.manifest.files", member=path)
    for asset in assets.values():
        entry = inventory[asset.path]
        if (entry.media_type, entry.byte_length, entry.sha256) != (
            asset.media_type,
            asset.byte_length,
            asset.sha256,
        ):
            fail("asset_metadata_mismatch", "$.assets", asset_id=asset.id)
    # Opaque bytes are already present, so verify them at this boundary too.
    import hashlib

    for path, payload in project.opaque_files.items():
        entry = inventory[path]
        if len(payload) != entry.byte_length or hashlib.sha256(payload).hexdigest() != entry.sha256:
            fail("integrity_mismatch", "$.opaque_files", member=path)
