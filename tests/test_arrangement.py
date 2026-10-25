from collections.abc import Callable
from dataclasses import replace

import pytest
from test_commands import engine, node, ok, run

from ltechdesign.commands import ArrangeNodes, Create, Group, Move
from ltechdesign.domain import dump_project, load_project
from ltechdesign.domain.arrangement import ArrangeMode
from ltechdesign.domain.geometry import Bounds, world_matrix
from ltechdesign.domain.models import NodeId
from ltechdesign.domain.snapping import geometry

pytestmark = pytest.mark.core


@pytest.mark.parametrize("mode", ["left", "hcenter", "right", "top", "vcenter", "bottom"])
def test_world_alignment_across_rotated_parents_preserves_pose_and_history(
    mode: ArrangeMode,
) -> None:
    d = engine()
    p = node(d, "p", "frame", x=50, y=70, rotation=37, scale=1.4)
    q = node(d, "q", "frame", x=350, y=210, rotation=-23, scale=0.8)
    a = node(d, "a", parent_id=p.id, x=20, y=40, rotation=16)
    b = node(d, "b", parent_id=q.id, x=60, y=10, width=80, height=60)
    ok(d, Create(node=p), Create(node=q), Create(node=a), Create(node=b))
    before = d.snapshot.project
    matrices = {k: world_matrix(before.document, k) for k in (a.id, b.id)}
    depth = len(d.undo_history)
    ok(d, ArrangeNodes(node_ids=(a.id, b.id), mode=mode))
    doc = d.snapshot.project.document
    x, y = geometry(doc, a.id), geometry(doc, b.id)
    features: dict[str, Callable[[Bounds], float]] = {
        "left": lambda v: v.min_x,
        "hcenter": lambda v: (v.min_x + v.max_x) / 2,
        "right": lambda v: v.max_x,
        "top": lambda v: v.min_y,
        "vcenter": lambda v: (v.min_y + v.max_y) / 2,
        "bottom": lambda v: v.max_y,
    }
    feature = features[mode]
    assert feature(x) == pytest.approx(feature(y), abs=1e-8)
    for key in (a.id, b.id):
        m = world_matrix(doc, key)
        old = matrices[key]
        assert (m.a, m.b, m.c, m.d) == pytest.approx((old.a, old.b, old.c, old.d))
        assert doc.nodes[key].parent_id == before.document.nodes[key].parent_id
    assert doc.pages == before.document.pages
    assert doc.nodes[p.id].children == before.document.nodes[p.id].children
    assert len(d.undo_history) == depth + 1
    assert load_project(dump_project(d.snapshot.project, {})).document == doc
    after = d.snapshot.project
    ok(d, action="undo")
    assert d.snapshot.project == before
    ok(d, action="redo")
    assert d.snapshot.project == after


@pytest.mark.parametrize("mode", ["distribute_x", "distribute_y"])
def test_equal_gaps_keep_outermost_fixed_with_different_sizes(mode: ArrangeMode) -> None:
    d = engine()
    horizontal = mode == "distribute_x"
    nodes = [
        node(
            d,
            str(i),
            x=pos if horizontal else 20,
            y=20 if horizontal else pos,
            width=size,
            height=size,
        )
        for i, (pos, size) in enumerate(((0, 20), (60, 30), (200, 40)))
    ]
    ok(d, *(Create(node=n) for n in nodes))
    before = d.snapshot.project
    ok(d, ArrangeNodes(node_ids=tuple(n.id for n in reversed(nodes)), mode=mode))
    doc = d.snapshot.project.document
    field = "x" if horizontal else "y"
    assert [getattr(doc.nodes[n.id], field) for n in nodes] == pytest.approx([0, 95, 200])
    assert doc.nodes[nodes[0].id] == before.document.nodes[nodes[0].id]
    assert doc.nodes[nodes[-1].id] == before.document.nodes[nodes[-1].id]
    ok(d, action="undo")
    assert d.snapshot.project == before


def test_group_and_child_selection_is_reduced_once_and_normalization_preserves_world_pose() -> None:
    d = engine()
    a, b, c = node(d, "a", x=20), node(d, "b", x=60), node(d, "c", x=300, y=150)
    ok(
        d,
        Create(node=a),
        Create(node=b),
        Create(node=c),
        Group(node_ids=(a.id, b.id), group_id=NodeId("g")),
    )
    before = d.snapshot.project
    g = NodeId("g")
    child_world = world_matrix(before.document, a.id)
    old_g = geometry(before.document, g)
    ok(d, ArrangeNodes(node_ids=(g, a.id, c.id), mode="right"))
    doc = d.snapshot.project.document
    assert geometry(doc, g).max_x == pytest.approx(geometry(doc, c.id).max_x)
    assert world_matrix(doc, a.id).tx - child_world.tx == pytest.approx(
        geometry(doc, g).min_x - old_g.min_x
    )
    assert doc.nodes[a.id] == before.document.nodes[a.id]
    ok(d, action="undo")
    assert d.snapshot.project == before


@pytest.mark.parametrize("flags", [{"visible": False}, {"locked": True}])
def test_hidden_or_locked_ancestor_causes_atomic_rejection(flags: dict[str, bool]) -> None:
    d = engine()
    parent = replace(
        node(d, "parent", "frame"),
        visible=flags.get("visible", True),
        locked=flags.get("locked", False),
    )
    a, b = node(d, "a", parent_id=parent.id), node(d, "b", x=250)
    ok(d, Create(node=parent), Create(node=a), Create(node=b))
    before, history = d.snapshot, d.undo_history
    result = run(
        d, Move(node_id=b.id, dx=2, dy=4), ArrangeNodes(node_ids=(a.id, b.id), mode="left")
    )
    assert not result.ok and d.snapshot is before and d.undo_history is history


def test_distribution_negative_gaps_and_stable_order_do_not_reorder_layers() -> None:
    d = engine()
    shapes = [node(d, str(i), x=x, width=100) for i, x in enumerate((0, 10, 20))]
    ok(d, *(Create(node=n) for n in shapes))
    page = d.snapshot.project.document.pages[0]
    ok(d, ArrangeNodes(node_ids=tuple(n.id for n in shapes), mode="distribute_x"))
    doc = d.snapshot.project.document
    bounds = [geometry(doc, n.id) for n in shapes]
    assert bounds[1].min_x - bounds[0].max_x == pytest.approx(bounds[2].min_x - bounds[1].max_x)
    assert doc.pages[0] == page


def test_undersized_selection_and_stale_revision_do_not_commit() -> None:
    d = engine()
    a, b = node(d, "a"), node(d, "b", x=200)
    ok(d, Create(node=a), Create(node=b))
    before = d.snapshot
    for op in (
        ArrangeNodes(node_ids=(a.id,), mode="left"),
        ArrangeNodes(node_ids=(a.id, b.id), mode="distribute_x"),
    ):
        assert not run(d, op).ok and d.snapshot is before
    assert not run(d, ArrangeNodes(node_ids=(a.id, b.id), mode="left"), expected_revision=0).ok
    assert d.snapshot is before
