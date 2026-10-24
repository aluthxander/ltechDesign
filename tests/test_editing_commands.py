import io
from dataclasses import replace
from pathlib import Path

import pytest
from test_commands import engine, node, ok, run

from ltechdesign.assets import BlobStore
from ltechdesign.commands import (
    Create,
    Dispatcher,
    EditNodes,
    Group,
    PasteNodes,
    RegisterAsset,
    ReparentNodes,
    ResizeNode,
    ScaleNodes,
    TransformNodes,
    Update,
)
from ltechdesign.commands.contracts import Operation
from ltechdesign.domain import ModelError, create_project, dump_project, load_project
from ltechdesign.domain.editing import around, resized
from ltechdesign.domain.geometry import Matrix, translation, world_matrix
from ltechdesign.domain.models import DocumentSession, NodeId, Point
from ltechdesign.persistence import read_archive, write_archive
from ltechdesign.persistence.clipboard import decode_selection, encode_selection

pytestmark = pytest.mark.core


def assert_matrix(a: Matrix, b: Matrix) -> None:
    assert (a.a, a.b, a.c, a.d, a.tx, a.ty) == pytest.approx(
        (b.a, b.b, b.c, b.d, b.tx, b.ty), abs=1e-9
    )


def test_nested_world_move_resize_rotate_and_single_history() -> None:
    d = engine()
    parent = node(d, "parent", "frame", rotation=37, scale=1.6, x=80, y=90)
    child = node(d, "child", parent_id=parent.id, x=10, y=20, rotation=-19)
    ok(d, Create(node=parent), Create(node=child))
    before = d.snapshot.project
    old = world_matrix(before.document, child.id)
    ok(d, TransformNodes(node_ids=(child.id,), matrix=translation(23, -14)))
    assert_matrix(world_matrix(d.snapshot.project.document, child.id), translation(23, -14) @ old)
    child = d.snapshot.project.document.nodes[child.id]
    anchor = Point(x=1, y=1)
    fixed = world_matrix(d.snapshot.project.document, child.id).point(
        Point(x=child.width, y=child.height)
    )
    ok(d, ResizeNode(node_id=child.id, width=73, height=143, anchor=anchor))
    changed = d.snapshot.project.document.nodes[child.id]
    actual = world_matrix(d.snapshot.project.document, child.id).point(Point(x=73, y=143))
    assert (actual.x, actual.y) == pytest.approx((fixed.x, fixed.y))
    assert changed.pivot == Point(x=36.5, y=71.5)
    rotation = around(actual, angle=63)
    old = world_matrix(d.snapshot.project.document, child.id)
    ok(d, TransformNodes(node_ids=(child.id,), matrix=rotation))
    assert_matrix(world_matrix(d.snapshot.project.document, child.id), rotation @ old)
    assert len(d.undo_history) == 4
    assert (
        load_project(dump_project(d.snapshot.project, {})).document == d.snapshot.project.document
    )
    ok(d, action="undo")
    ok(d, action="redo")
    assert_matrix(world_matrix(d.snapshot.project.document, child.id), rotation @ old)


def test_uniform_group_resize_frame_fixed_children_and_delete_history() -> None:
    d = engine()
    a, b = node(d, "a", x=20), node(d, "b", x=140)
    ok(d, Create(node=a), Create(node=b), Group(node_ids=(a.id, b.id), group_id=NodeId("g")))
    doc = d.snapshot.project.document
    group = doc.nodes[NodeId("g")]
    child_before = doc.nodes[a.id]
    old = world_matrix(doc, a.id)
    matrix = around(Point(x=20), factor=2)
    ok(d, TransformNodes(node_ids=(group.id, a.id), matrix=matrix))
    assert d.snapshot.project.document.nodes[a.id] == child_before
    assert d.snapshot.project.document.nodes[group.id].scale == 2
    assert_matrix(world_matrix(d.snapshot.project.document, a.id), matrix @ old)
    with pytest.raises(ModelError, match="group_resize_requires_uniform_scale"):
        resized(group, 300, 100, Point())
    before = d.snapshot.project
    ok(d, EditNodes(node_ids=(group.id, a.id), edit="delete"))
    assert not d.snapshot.project.document.nodes
    ok(d, action="undo")
    assert d.snapshot.project == before
    ok(d, action="redo")
    ok(d, action="undo")
    ok(d, TransformNodes(node_ids=(group.id,), matrix=translation(1, 0)))
    assert not d.redo_history and not run(d, action="redo", request_id="empty_redo").ok
    frame = node(d, "frame", "frame")
    inner = node(d, "inner", parent_id=frame.id, x=40)
    ok(d, Create(node=frame), Create(node=inner))
    ok(d, ResizeNode(node_id=frame.id, width=200, height=40, anchor=Point()))
    assert d.snapshot.project.document.nodes[inner.id] == inner


def test_reparent_group_ungroup_at24_and_compositing_rejection() -> None:
    d = engine()
    p = node(d, "p", "frame", rotation=31, scale=1.4)
    q = node(d, "q", "frame", x=400, rotation=-23, scale=0.7)
    a = node(d, "a", parent_id=p.id, x=25, rotation=17)
    b = node(d, "b", parent_id=p.id, x=180)
    ok(d, Create(node=p), Create(node=q), Create(node=a), Create(node=b))
    old = {key: world_matrix(d.snapshot.project.document, key) for key in (a.id, b.id)}
    before = d.snapshot.project
    ok(d, Group(node_ids=(a.id, b.id), group_id=NodeId("g")))
    ok(d, ReparentNodes(node_ids=(NodeId("g"),), page_id=p.page_id, parent_id=q.id))
    ok(d, EditNodes(node_ids=(NodeId("g"),), edit="ungroup"))
    for key, expected in old.items():
        assert_matrix(world_matrix(d.snapshot.project.document, key), expected)
    for _ in range(3):
        ok(d, action="undo")
    assert d.snapshot.project == before
    ok(d, Group(node_ids=(a.id, b.id), group_id=NodeId("alpha")))
    group = d.snapshot.project.document.nodes[NodeId("alpha")]
    ok(d, Update(node=replace(group, opacity=0.5)))
    snapshot = d.snapshot
    result = run(d, EditNodes(node_ids=(group.id,), edit="ungroup"))
    assert not result.ok and result.error and result.error.code == "unsupported_visual_preservation"
    assert d.snapshot is snapshot


def test_clipboard_assets_fonts_tokens_fresh_ids_and_rejected_bytes(tmp_path: Path) -> None:
    native = Path("examples/proyek-contoh.ltechdesign")
    with native.open("rb") as archive_stream:
        loaded = read_archive(archive_stream)
    source = loaded.project
    keys = source.document.pages[0].root_ids
    payload = encode_selection(source, keys, loaded.blobs)
    one, two = decode_selection(payload), decode_selection(payload)
    assert not (one.project.document.nodes.keys() & source.document.nodes.keys())
    assert not (one.project.document.nodes.keys() & two.project.document.nodes.keys())
    assert one.blobs
    assert not ({a.id for a in one.project.assets.assets} & {a.id for a in source.assets.assets})
    assert not ({f.id for f in one.project.fonts.fonts} & {f.id for f in source.fonts.fonts})
    store = BlobStore()
    d = Dispatcher(DocumentSession(project=create_project()), assets=store.retention())
    ops: list[Operation] = []
    for asset in one.project.assets.assets:
        ops.append(RegisterAsset(asset=asset, staging_id=store.stage(asset, one.blobs[asset.path])))
    ops.append(PasteNodes(project=one.project, page_id=d.snapshot.project.document.pages[0].id))
    ok(d, *ops)
    pasted = d.snapshot.project
    assert pasted.fonts.fonts and pasted.assets.assets
    with store.pin(pasted.assets.assets) as lease:
        stream = io.BytesIO()
        write_archive(stream, pasted, lease.blobs)
        stream.seek(0)
        restored = read_archive(stream)
        assert restored.project.document == pasted.document
        assert dict(restored.blobs) == dict(one.blobs)
    ok(d, action="undo")
    store.collect()
    ok(d, action="redo")
    with store.pin(d.snapshot.project.assets.assets) as lease:
        assert dict(lease.blobs) == dict(one.blobs)
    with pytest.raises(ModelError):
        decode_selection(b"untrusted clipboard")


def test_selection_reorder_preserves_relative_order_and_minimums() -> None:
    d = engine()
    children = tuple(node(d, str(i)) for i in range(5))
    ok(d, *(Create(node=n) for n in children))
    ok(d, EditNodes(node_ids=(children[1].id, children[2].id), edit="forward"))
    assert d.snapshot.project.document.pages[0].root_ids == tuple(
        NodeId(s) for s in ("0", "3", "1", "2", "4")
    )
    ok(d, EditNodes(node_ids=(children[1].id, children[2].id), edit="backward"))
    assert d.snapshot.project.document.pages[0].root_ids == tuple(n.id for n in children)
    ok(d, ResizeNode(node_id=children[0].id, width=-100, height=-200, anchor=Point(x=1, y=1)))
    n = d.snapshot.project.document.nodes[children[0].id]
    assert n.width == n.height == 0.01 and n.scale > 0


def test_invalid_affine_and_layout_frame_resize_fail_atomically() -> None:
    from ltechdesign.domain.models import Layout

    d = engine()
    frame = node(d, "frame", "frame")
    ok(d, Create(node=frame))
    before = d.snapshot
    result = run(
        d, TransformNodes(node_ids=(frame.id,), matrix=Matrix(2, 0, 0, 1)), request_id="affine"
    )
    assert not result.ok and d.snapshot is before
    # The evaluator prerequisite is absent; never pretend to apply constraints.
    constrained = replace(frame, layout=Layout())
    with pytest.raises(ModelError, match="layout_evaluator_unavailable"):
        resized(constrained, 200, 200, Point())


def test_resize_member_normalizes_nested_groups_without_moving_sibling() -> None:
    d = engine()
    a, b = node(d, "a", x=20, rotation=23), node(d, "b", x=180, y=50)
    ok(d, Create(node=a), Create(node=b), Group(node_ids=(a.id, b.id), group_id=NodeId("inner")))
    ok(d, Group(node_ids=(NodeId("inner"),), group_id=NodeId("outer")))
    group = d.snapshot.project.document.nodes[NodeId("outer")]
    ok(d, Update(node=replace(group, rotation=37, scale=1.4)))
    before = d.snapshot.project
    sibling = world_matrix(before.document, b.id)
    member = before.document.nodes[a.id]
    anchor = world_matrix(before.document, a.id).point(Point(x=member.width, y=member.height))
    ok(d, ResizeNode(node_id=a.id, width=140, height=160, anchor=Point(x=1, y=1)))
    after = d.snapshot.project.document
    actual = world_matrix(after, a.id).point(Point(x=140, y=160))
    assert (actual.x, actual.y) == pytest.approx((anchor.x, anchor.y))
    assert_matrix(world_matrix(after, b.id), sibling)
    ok(d, action="undo")
    assert d.snapshot.project == before


def test_multiselect_scale_resizes_frame_geometry_without_scaling_contents() -> None:
    d = engine()
    frame = node(d, "frame", "frame", rotation=23, x=40, y=50)
    child = node(d, "child", parent_id=frame.id, x=30, y=20)
    shape = node(d, "shape", x=250)
    ok(d, Create(node=frame), Create(node=child), Create(node=shape))
    old = world_matrix(d.snapshot.project.document, frame.id)
    ok(d, ScaleNodes(node_ids=(frame.id, shape.id), factor=2, center=Point()))
    after = d.snapshot.project.document
    assert after.nodes[frame.id].scale == frame.scale
    assert (after.nodes[frame.id].width, after.nodes[frame.id].height) == (200, 200)
    assert after.nodes[child.id] == child
    new = world_matrix(after, frame.id)
    assert (new.tx, new.ty) == pytest.approx((2 * old.tx, 2 * old.ty))
    assert after.nodes[shape.id].scale == 2
