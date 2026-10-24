"""Pure whole-project clone for a NEW admission, never a mutation of an open model."""

from dataclasses import replace

from ltechdesign.domain.errors import fail
from ltechdesign.domain.models import (
    AssetId,
    AssetsIndex,
    DocumentId,
    FontId,
    Fonts,
    MediaData,
    NodeId,
    PageId,
    Project,
    TextData,
    TokenId,
    Tokens,
    new_id,
)


def duplicate_project(project: Project) -> Project:
    if project.manifest.extensions:
        fail("extension_remapper_unavailable", code="unsupported_capability")
    document_id = DocumentId(new_id())
    pages = {p.id: PageId(new_id()) for p in project.document.pages}
    nodes = {key: NodeId(new_id()) for key in project.document.nodes}
    assets = {a.id: AssetId(new_id()) for a in project.assets.assets}
    fonts = {f.id: FontId(new_id()) for f in project.fonts.fonts}
    tokens = {t.id: TokenId(new_id()) for t in project.tokens.tokens}
    cloned = {}
    for key, node in project.document.nodes.items():
        data = node.data
        if isinstance(data, MediaData):
            data = replace(data, asset_id=assets[data.asset_id])
        elif isinstance(data, TextData):
            data = replace(
                data, typography=replace(data.typography, font_id=fonts[data.typography.font_id])
            )
        cloned[nodes[key]] = replace(
            node,
            id=nodes[key],
            page_id=pages[node.page_id],
            parent_id=nodes[node.parent_id] if node.parent_id else None,
            children=tuple(nodes[c] for c in node.children),
            data=data,
        )
    workspace = project.workspace
    if workspace is not None:
        workspace = replace(
            workspace,
            active_page_id=pages[workspace.active_page_id],
            views=tuple(replace(v, page_id=pages[v.page_id]) for v in workspace.views),
        )
    return replace(
        project,
        manifest=replace(project.manifest, document_id=document_id, saved_revision=0),
        document=replace(
            project.document,
            document_id=document_id,
            nodes=cloned,
            pages=tuple(
                replace(p, id=pages[p.id], root_ids=tuple(nodes[n] for n in p.root_ids))
                for p in project.document.pages
            ),
        ),
        assets=AssetsIndex(
            assets=tuple(replace(a, id=assets[a.id]) for a in project.assets.assets)
        ),
        fonts=Fonts(
            fonts=tuple(
                replace(f, id=fonts[f.id], asset_id=assets[f.asset_id] if f.asset_id else None)
                for f in project.fonts.fonts
            )
        ),
        tokens=Tokens(
            tokens=tuple(replace(t, id=tokens[t.id]) for t in project.tokens.tokens),
            bindings=tuple(
                replace(b, node_id=nodes[b.node_id], token_id=tokens[b.token_id])
                for b in project.tokens.bindings
            ),
        ),
        workspace=workspace,
    )
