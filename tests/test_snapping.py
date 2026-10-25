from dataclasses import replace

import pytest
from test_commands import engine, node, ok

from ltechdesign.commands import Create, Group
from ltechdesign.domain import ModelError
from ltechdesign.domain.geometry import Bounds
from ltechdesign.domain.models import NodeId, Point
from ltechdesign.domain.snapping import SnapIndex, Target, geometry, tolerance

pytestmark = pytest.mark.core


def point_index(x: float) -> SnapIndex:
    return SnapIndex(x=(Target(x, NodeId("target"), Bounds(x, 0, x, 0)),), xs=(x,))


@pytest.mark.parametrize("zoom", [0.25, 1, 4])
@pytest.mark.parametrize("dpr", [1, 1.5, 2])
def test_physical_screen_tolerance_is_applied_once(zoom: float, dpr: float) -> None:
    index = point_index(100)
    distance = tolerance(8, zoom, dpr)
    inside = index.nearest(
        100 + 7.9 / zoom / dpr, "x", distance, objects=True, grid=False, spacing=20
    )
    outside = index.nearest(
        100 + 8.1 / zoom / dpr, "x", distance, objects=True, grid=False, spacing=20
    )
    assert inside is not None and outside is None
    assert inside.coordinate == 100


def test_grid_logical_origin_negative_coordinates_and_object_tie_priority() -> None:
    index = point_index(20)
    delta, guides = index.translation(
        Bounds(18, 19, 28, 29), Point(), 2, objects=True, grid=True, spacing=20
    )
    assert delta == Point(x=2, y=1)
    assert guides[0].kind == "object" and guides[1].kind == "grid"
    snap = SnapIndex().nearest(-19, "x", 2, objects=False, grid=True, spacing=20)
    assert snap is not None and snap.coordinate == -20
    unchanged, guides = index.translation(
        Bounds(18, 19, 28, 29), Point(), 2, objects=False, grid=False, spacing=20
    )
    assert unchanged == Point() and not guides


def test_snap_index_rotated_targets_excludes_moving_descendants_hidden_locked_and_clipped() -> None:
    d = engine()
    parent = node(d, "parent", "frame", x=200, y=70, rotation=34, scale=1.5)
    target = node(d, "target", parent_id=parent.id, x=20, y=30)
    moving = node(d, "moving")
    child = node(d, "child", parent_id=parent.id, x=200)
    hidden = node(d, "hidden", visible=False)
    hidden_child = node(d, "hidden-child", "frame", visible=False)
    locked = node(d, "locked", "frame", locked=True)
    clipped = node(d, "clipped", "frame", clip_content=True)
    outside = node(d, "outside", parent_id=clipped.id, x=500)
    for n in (parent, target, moving, child, hidden, hidden_child, locked, clipped, outside):
        ok(d, Create(node=n))
    ok(
        d,
        Create(node=node(d, "inside-locked", parent_id=locked.id)),
        Create(node=node(d, "inside-hidden", parent_id=hidden_child.id)),
    )
    doc = d.snapshot.project.document
    index = SnapIndex.build(doc, 0, (moving.id,))
    ids = {t.key for t in index.x}
    assert target.id in ids and moving.id not in ids
    assert not ids.intersection(
        {
            hidden.id,
            hidden_child.id,
            locked.id,
            outside.id,
            NodeId("inside-locked"),
            NodeId("inside-hidden"),
        }
    )
    b = geometry(doc, target.id)
    assert {t.coordinate for t in index.x if t.key == target.id} == {
        b.min_x,
        (b.min_x + b.max_x) / 2,
        b.max_x,
    }
    assert not {t.key for t in SnapIndex.build(doc, 0, (parent.id,)).x}.intersection(
        {parent.id, child.id, target.id}
    )


def test_derived_group_does_not_attract_its_own_children_and_order_is_deterministic() -> None:
    d = engine()
    a, b = node(d, "a"), node(d, "b", x=150)
    ok(d, Create(node=a), Create(node=b), Group(node_ids=(a.id, b.id), group_id=NodeId("g")))
    doc = d.snapshot.project.document
    index = SnapIndex.build(doc, 0, (a.id,))
    assert NodeId("g") not in {t.key for t in index.x}
    flipped = replace(doc, nodes=dict(reversed(tuple(doc.nodes.items()))))
    assert SnapIndex.build(flipped, 0, (a.id,)) == index


def test_shift_axis_and_uniform_resize_preserve_constraints() -> None:
    index = point_index(104)
    moved, guides = index.translation(
        Bounds(0, 0, 100, 100), Point(), 8, objects=True, grid=False, spacing=20, axis_only="y"
    )
    assert moved == Point() and not guides
    factor, guides = index.along(
        Point(), Point(x=100, y=100), 1, 0.1, 8, objects=True, grid=False, spacing=20
    )
    assert factor == pytest.approx(1.04) and guides[0].coordinate == 104
    # Axis distance 6px is close, but actual constrained-handle displacement is >8px.
    factor, guides = point_index(106).along(
        Point(), Point(x=100, y=100), 1, 0.1, 8, objects=True, grid=False, spacing=20
    )
    assert factor == 1 and not guides


@pytest.mark.parametrize(("pixels", "zoom", "dpr"), [(-1, 1, 1), (8, 0, 1), (8, 1, 0)])
def test_invalid_tolerance_rejected(pixels: float, zoom: float, dpr: float) -> None:
    with pytest.raises(ModelError):
        tolerance(pixels, zoom, dpr)
