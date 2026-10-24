"""Portable bounded node clipboard: native ZIP members and embedded byte closure."""

import io
from collections.abc import Mapping
from dataclasses import replace

from ltechdesign.domain.editing import roots
from ltechdesign.domain.errors import fail
from ltechdesign.domain.geometry import with_matrix, world_matrix
from ltechdesign.domain.models import (
    AssetsIndex,
    Document,
    Fonts,
    MediaData,
    NodeId,
    Page,
    Project,
    TextData,
    Tokens,
)

from .archive import ArchiveLimits, LoadedProject, read_archive, write_archive
from .duplicate import duplicate_project

MIME = "application/x-ltechdesign-nodes-v1"
LIMITS = ArchiveLimits(archive_bytes=64 * 1024 * 1024, expanded_bytes=64 * 1024 * 1024)


def encode_selection(
    project: Project, keys: tuple[NodeId, ...], blobs: Mapping[str, bytes]
) -> bytes:
    if project.manifest.extensions:
        fail("extension_remapper_unavailable", code="unsupported_capability")
    selected = roots(project.document, keys)
    included: set[NodeId] = set()
    stack = list(selected)
    while stack:
        key = stack.pop()
        included.add(key)
        stack.extend(project.document.nodes[key].children)
    page = Page(root_ids=selected)
    nodes = {}
    for key in included:
        node = project.document.nodes[key]
        if key in selected:
            node = replace(with_matrix(node, world_matrix(project.document, key)), parent_id=None)
        nodes[key] = replace(node, page_id=page.id)
    fonts_needed = {
        n.data.typography.font_id for n in nodes.values() if isinstance(n.data, TextData)
    }
    fonts = tuple(f for f in project.fonts.fonts if f.id in fonts_needed)
    asset_ids = {n.data.asset_id for n in nodes.values() if isinstance(n.data, MediaData)}
    asset_ids.update(f.asset_id for f in fonts if f.asset_id is not None)
    assets = tuple(a for a in project.assets.assets if a.id in asset_ids)
    if len(assets) > 64:
        fail("clipboard_asset_limit", code="limit_exceeded")
    bindings = tuple(b for b in project.tokens.bindings if b.node_id in included)
    token_ids = {b.token_id for b in bindings}
    paths = {"document.json", "tokens.json", "fonts.json", "assets/index.json"}
    paths.update(a.path for a in assets)
    fragment = replace(
        project,
        document=Document(document_id=project.document.document_id, pages=(page,), nodes=nodes),
        manifest=replace(
            project.manifest, files=tuple(e for e in project.manifest.files if e.path in paths)
        ),
        workspace=None,
        opaque_files={},
        assets=AssetsIndex(assets=assets),
        fonts=Fonts(fonts=fonts),
        tokens=Tokens(
            tokens=tuple(t for t in project.tokens.tokens if t.id in token_ids), bindings=bindings
        ),
    )
    stream = io.BytesIO()
    write_archive(stream, fragment, {a.path: blobs[a.path] for a in assets}, limits=LIMITS)
    return stream.getvalue()


def decode_selection(payload: bytes) -> LoadedProject:
    if len(payload) > LIMITS.archive_bytes:
        fail("clipboard_bytes", code="limit_exceeded")
    loaded = read_archive(io.BytesIO(payload), limits=LIMITS)
    if len(loaded.project.document.pages) != 1 or not loaded.project.document.pages[0].root_ids:
        fail("invalid_clipboard_selection")
    if len(loaded.project.assets.assets) > 64:
        fail("clipboard_asset_limit", code="limit_exceeded")
    return LoadedProject(duplicate_project(loaded.project), loaded.blobs)
