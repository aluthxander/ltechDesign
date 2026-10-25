import io
from dataclasses import replace
from pathlib import Path

import pytest
from test_commands import engine, node, ok, run
from test_editing_commands import assert_matrix

from ltechdesign.assets import BlobStore
from ltechdesign.commands import (
    Create,
    CreatePage,
    DeletePage,
    Dispatcher,
    DuplicatePage,
    RelocateNodes,
    SetLayerState,
    UpdatePage,
)
from ltechdesign.domain import create_project, dump_project, load_project
from ltechdesign.domain.geometry import world_matrix
from ltechdesign.domain.models import (
    DocumentSession,
    InventoryEntry,
    MediaData,
    NodeId,
    Page,
    PageId,
    View,
    Workspace,
)
from ltechdesign.persistence import read_archive, write_archive

pytestmark = pytest.mark.core


def test_page_crud_order_explicit_contents_last_page_and_atomic_failure() -> None:
    d = engine()
    first = d.snapshot.project.document.pages[0]
    second = Page(name="Second")
    ok(d, CreatePage(page=second, index=0), UpdatePage(page_id=first.id, name="Renamed"))
    assert tuple(p.id for p in d.snapshot.project.document.pages) == (second.id, first.id)
    shape = node(d, "shape", page_id=first.id)
    ok(d, Create(node=shape))
    before = d.snapshot
    history = d.undo_history
    result = run(d, DeletePage(page_id=first.id), request_id="no_implicit_delete")
    assert not result.ok and d.snapshot is before and d.undo_history == history
    result = run(
        d,
        UpdatePage(page_id=first.id, name="Must rollback"),
        CreatePage(page=Page(id=first.id)),
        request_id="collision",
    )
    assert not result.ok and d.snapshot is before
    ok(d, DeletePage(page_id=first.id, delete_contents=True))
    assert not d.snapshot.project.document.nodes
    ok(d, action="undo")
    assert d.snapshot.project == before.project
    ok(d, action="redo")
    snapshot = d.snapshot
    assert not run(d, DeletePage(page_id=second.id), request_id="last_page").ok
    assert d.snapshot is snapshot


def test_page_duplicate_preserves_graph_assets_fonts_tokens_and_portable_restore() -> None:
    with Path("examples/proyek-contoh.ltechdesign").open("rb") as file:
        loaded = read_archive(file)
    store = BlobStore()
    lease = store.admit(loaded.project.assets.assets, loaded.blobs)
    d = Dispatcher(DocumentSession(project=loaded.project), assets=store.retention())
    lease.release()
    source = d.snapshot.project
    page = source.document.pages[0]
    new_id = PageId("copied-page")
    receipt = ok(d, DuplicatePage(page_id=page.id, new_page_id=new_id))
    project = d.snapshot.project
    mapping = dict(receipt.id_map)
    assert set(mapping) == {k for k, n in source.document.nodes.items() if n.page_id == page.id}
    assert not (set(mapping.values()) & source.document.nodes.keys())
    assert project.document.pages[1].id == new_id
    assert project.document.pages[1].root_ids == tuple(mapping[k] for k in page.root_ids)
    for key, new in mapping.items():
        old = source.document.nodes[key]
        copied = project.document.nodes[new]
        assert copied.parent_id == (mapping[old.parent_id] if old.parent_id else None)
        assert copied.children == tuple(mapping[k] for k in old.children)
        assert copied.data == old.data and copied.page_id == new_id
        assert_matrix(world_matrix(project.document, new), world_matrix(source.document, key))
        if isinstance(copied.data, MediaData):
            assert any(a.id == copied.data.asset_id for a in project.assets.assets)
    assert project.assets == source.assets and project.fonts == source.fonts
    for binding in source.tokens.bindings:
        if binding.node_id in mapping:
            assert replace(binding, node_id=mapping[binding.node_id]) in project.tokens.bindings
    with store.pin(project.assets.assets) as lease:
        archive = io.BytesIO()
        write_archive(archive, project, lease.blobs)
        archive.seek(0)
        restored = read_archive(archive)
    assert restored.project.document == project.document
    assert dict(restored.blobs) == dict(loaded.blobs)
    ok(d, action="undo")
    store.collect()
    ok(d, action="redo")
    assert d.snapshot.project == project
    assert load_project(dump_project(project, restored.blobs)).document == project.document


def test_duplicate_empty_page_and_invalid_ids() -> None:
    d = engine()
    page = d.snapshot.project.document.pages[0]
    ok(d, DuplicatePage(page_id=page.id, new_page_id=PageId("empty-copy"), name="Blank"))
    assert not d.snapshot.project.document.pages[1].root_ids
    before = d.snapshot
    assert not run(
        d, DuplicatePage(page_id=page.id, new_page_id=page.id), request_id="duplicate_page_id"
    ).ok
    assert not run(
        d, DuplicatePage(page_id=PageId("missing"), new_page_id=PageId("x")), request_id="missing"
    ).ok
    assert not run(
        d, CreatePage(page=Page(root_ids=(NodeId("unknown"),))), request_id="nonempty"
    ).ok
    assert d.snapshot is before


def test_workspace_deleted_page_references_are_sanitized_and_undoable() -> None:
    project = create_project()
    first, second, third = project.document.pages[0], Page(name="Second"), Page(name="Third")
    workspace = Workspace(
        active_page_id=first.id, views=(View(page_id=first.id), View(page_id=second.id))
    )
    project = replace(
        project,
        document=replace(project.document, pages=(first, second, third)),
        workspace=workspace,
        manifest=replace(
            project.manifest,
            optional_capabilities=project.manifest.optional_capabilities + ("workspace.view/1",),
            files=project.manifest.files
            + (
                InventoryEntry(
                    path="workspace.json",
                    media_type="application/json",
                    byte_length=0,
                    sha256="0" * 64,
                ),
            ),
        ),
    )
    d = Dispatcher(DocumentSession(project=project))
    ok(d, DeletePage(page_id=first.id))
    actual = d.snapshot.project
    assert actual.workspace and actual.workspace.active_page_id == second.id
    assert actual.workspace.views == (View(page_id=second.id),)
    assert load_project(dump_project(actual, {})).workspace == actual.workspace
    ok(d, action="undo")
    assert d.snapshot.project == project
    malicious = Dispatcher(
        DocumentSession(project=project),
        layout=lambda p: replace(p, workspace=Workspace(active_page_id=third.id)),
    )
    before = malicious.snapshot
    result = run(malicious, DeletePage(page_id=first.id), request_id="layout_workspace_rewrite")
    assert not result.ok and malicious.snapshot is before


def test_relocate_nested_multi_order_world_pose_cycles_and_atomic_rollback() -> None:
    d = engine()
    p = node(d, "parent", "frame", rotation=27, scale=1.4)
    q = node(d, "target", "frame", rotation=-39, x=400, scale=0.7)
    a = node(d, "a", parent_id=p.id, x=20, rotation=13)
    b = node(d, "b", "frame", parent_id=p.id, x=130)
    child = node(d, "child", parent_id=b.id)
    ok(d, *(Create(node=n) for n in (p, q, a, b, child)))
    before = d.snapshot.project
    world = {key: world_matrix(before.document, key) for key in (a.id, b.id, child.id)}
    ok(
        d,
        RelocateNodes(node_ids=(b.id, a.id, child.id), page_id=p.page_id, parent_id=q.id, index=0),
    )
    doc = d.snapshot.project.document
    assert doc.nodes[q.id].children == (a.id, b.id)
    for key, matrix in world.items():
        assert_matrix(world_matrix(doc, key), matrix)
    snapshot = d.snapshot
    assert not run(
        d, RelocateNodes(node_ids=(q.id,), page_id=p.page_id, parent_id=b.id), request_id="cycle"
    ).ok
    assert d.snapshot is snapshot
    ok(d, action="undo")
    assert d.snapshot.project == before
    ok(d, RelocateNodes(node_ids=(a.id,), page_id=p.page_id, parent_id=p.id, index=1))
    assert d.snapshot.project.document.nodes[p.id].children == (b.id, a.id)


def test_relocate_clip_context_is_explicit_and_flags_do_not_rewrite_descendants() -> None:
    d = engine()
    frame = node(d, "clip", "frame", clip_content=True, rotation=25)
    a = node(d, "a", x=20)
    ok(d, Create(node=frame), Create(node=a))
    before = d.snapshot
    assert not run(
        d, RelocateNodes(node_ids=(a.id,), page_id=a.page_id, parent_id=frame.id), request_id="clip"
    ).ok
    assert d.snapshot is before
    world = world_matrix(before.project.document, a.id)
    ok(
        d,
        RelocateNodes(
            node_ids=(a.id,), page_id=a.page_id, parent_id=frame.id, preserve_appearance=False
        ),
    )
    assert_matrix(world_matrix(d.snapshot.project.document, a.id), world)
    child = d.snapshot.project.document.nodes[a.id]
    ok(d, SetLayerState(node_ids=(frame.id,), locked=True, visible=False))
    assert d.snapshot.project.document.nodes[a.id] == child
    ok(d, action="undo")
    assert d.snapshot.project.document.nodes[frame.id].visible


def test_cross_page_move_reassigns_subtree_owner_and_artboard_remains_root_only() -> None:
    d = engine()
    second = Page(name="Second")
    parent = node(d, "p", "frame")
    child = node(d, "c", parent_id=parent.id)
    board = node(d, "board", "artboard")
    ok(d, CreatePage(page=second), Create(node=parent), Create(node=child), Create(node=board))
    ok(d, RelocateNodes(node_ids=(parent.id,), page_id=second.id))
    assert all(
        d.snapshot.project.document.nodes[k].page_id == second.id for k in (parent.id, child.id)
    )
    before = d.snapshot
    assert not run(
        d,
        RelocateNodes(node_ids=(board.id,), page_id=second.id, parent_id=parent.id),
        request_id="nested_board",
    ).ok
    assert d.snapshot is before


def test_relocate_out_of_group_normalizes_empty_parent_and_preserves_world() -> None:
    from ltechdesign.commands import Group

    d = engine()
    a = node(d, "a", x=40, y=80, rotation=34)
    target = node(d, "target", "frame", x=400, y=50, rotation=-19)
    ok(d, Create(node=a), Create(node=target), Group(node_ids=(a.id,), group_id=NodeId("g")))
    before = d.snapshot.project
    matrix = world_matrix(before.document, a.id)
    ok(d, RelocateNodes(node_ids=(a.id,), page_id=a.page_id, parent_id=target.id))
    group = d.snapshot.project.document.nodes[NodeId("g")]
    assert group.children == () and group.width == group.height == 0
    assert_matrix(world_matrix(d.snapshot.project.document, a.id), matrix)
    ok(d, action="undo")
    assert d.snapshot.project == before
