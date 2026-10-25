"""Behavioral Inspector/undo contracts run without importing Qt."""

from dataclasses import replace

import pytest
from test_commands import engine, node, ok, request, run

from ltechdesign.commands import Create, Group, Move, SetProperties
from ltechdesign.domain import ModelError, dump_project, load_project
from ltechdesign.domain.geometry import local_matrix, world_matrix
from ltechdesign.domain.inspector import Property, inspected, value
from ltechdesign.domain.models import Fill, LineData, NodeId, Point, Shadow, Style

pytestmark = pytest.mark.core


def test_nested_parent_translation_resize_pivot_rotation_and_undo() -> None:
    d = engine()
    parent = node(d, "parent", "frame", x=100, y=70, rotation=38, scale=1.7)
    child = node(d, "child", parent_id=parent.id, x=20, y=35, rotation=-19, scale=1.2)
    ok(d, Create(node=parent), Create(node=child))
    before = d.snapshot.project
    ok(d, SetProperties(node_ids=(child.id,), property="x", value=60))
    actual = d.snapshot.project.document.nodes[child.id]
    assert actual.x == 60 and actual.y == 35 and actual.rotation == -19 and actual.scale == 1.2
    old = world_matrix(before.document, child.id).point(Point())
    new = world_matrix(d.snapshot.project.document, child.id).point(Point())
    pm = world_matrix(before.document, parent.id)
    assert new.x - old.x == pytest.approx(pm.a * 40)
    assert new.y - old.y == pytest.approx(pm.b * 40)
    anchor = local_matrix(actual).point(Point())
    ok(d, SetProperties(node_ids=(child.id,), property="width", value=180))
    resized = d.snapshot.project.document.nodes[child.id]
    assert resized.width == 180 and resized.pivot == Point(x=90, y=50)
    assert local_matrix(resized).point(Point()).x == pytest.approx(anchor.x)
    assert local_matrix(resized).point(Point()).y == pytest.approx(anchor.y)
    ok(d, SetProperties(node_ids=(child.id,), property="rotation", value=51))
    assert d.snapshot.project.document.nodes[child.id].rotation == 51
    for _ in range(3):
        ok(d, action="undo")
    assert d.snapshot.project == before


def test_group_dimensions_uniform_scale_and_style_do_not_rewrite_children() -> None:
    d = engine()
    a = node(d, "a", x=10, y=20)
    b = node(d, "b", x=80, y=50)
    ok(d, Create(node=a), Create(node=b), Group(node_ids=(a.id, b.id), group_id=NodeId("g")))
    before = d.snapshot.project
    g = before.document.nodes[NodeId("g")]
    ok(d, SetProperties(node_ids=(g.id,), property="width", value=g.width * 2))
    changed = d.snapshot.project.document.nodes[g.id]
    assert changed.scale == 2 and changed.width == g.width and changed.height == g.height
    assert value(changed, "height") == g.height * 2
    assert d.snapshot.project.document.nodes[a.id] == before.document.nodes[a.id]
    ok(d, SetProperties(node_ids=(g.id,), property="opacity", value=0.4))
    assert d.snapshot.project.document.nodes[g.id].opacity == 0.4
    ok(d, action="undo")
    assert d.snapshot.project.document.nodes[g.id] == changed


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("width", -1),
        ("height", 0),
        ("opacity", 1.1),
        ("stroke_width", 0),
        ("radius", -2),
        ("shadow_blur", -1),
        ("shadow_spread", -1),
        ("fill", "red"),
        ("shadow_color", None),
        ("shadow_enabled", 2),
    ],
)
def test_invalid_property_is_atomic(field: Property, bad: float | str | None) -> None:
    d = engine()
    a, b = node(d, "a"), node(d, "b")
    ok(d, Create(node=a), Create(node=b))
    before, history = d.snapshot, d.undo_history
    result = run(d, SetProperties(node_ids=(a.id, b.id), property=field, value=bad))
    assert not result.ok and d.snapshot is before and d.undo_history is history


def test_mixed_target_validation_rolls_back_and_line_zero_extent_stays_valid() -> None:
    d = engine()
    a, b = node(d, "a"), node(d, "b", "ellipse")
    ok(d, Create(node=a), Create(node=b))
    before = d.snapshot
    result = run(d, SetProperties(node_ids=(a.id, b.id), property="radius", value=20))
    assert not result.ok and d.snapshot is before
    line = node(
        d,
        "line",
        "line",
        width=0,
        pivot=Point(y=50),
        data=LineData(start=Point(), end=Point(y=100)),
    )
    assert inspected(line, "width", 0).width == 0
    with pytest.raises(ModelError, match="line_zero_extent_resize"):
        inspected(line, "width", 20)
    for number in (float("inf"), float("nan")):
        with pytest.raises(ModelError):
            inspected(a, "x", number)


def test_all_style_properties_roundtrip_and_undo_without_changing_schema() -> None:
    d = engine()
    a = node(d, "a", style=Style(fill=Fill(), shadows=(Shadow(), Shadow(offset_x=-20))))
    ok(d, Create(node=a))
    before = d.snapshot.project
    edits: tuple[tuple[Property, float | str | None], ...] = (
        ("fill", "#1188CC80"),
        ("stroke", "#F04020FF"),
        ("stroke_width", 8),
        ("radius", 17),
        ("shadow_x", 12),
        ("shadow_y", -6),
        ("shadow_blur", 5),
        ("shadow_spread", 2),
        ("shadow_color", "#22446699"),
        ("opacity", 0.6),
    )
    for field, supplied in edits:
        ok(d, SetProperties(node_ids=(a.id,), property=field, value=supplied))
    project = d.snapshot.project
    assert project.document.nodes[a.id].style.shadows[1] == a.style.shadows[1]
    assert load_project(dump_project(project, {})).document == project.document
    for _ in edits:
        ok(d, action="undo")
    assert d.snapshot.project == before
    for _ in edits:
        ok(d, action="redo")
    assert d.snapshot.project == project


def test_undo_merge_revision_dedup_save_and_other_client_boundaries() -> None:
    d = engine(initially_saved=True)
    a = node(d, "a")
    ok(d, Create(node=a))
    baseline = len(d.undo_history)
    first = request(
        d, SetProperties(node_ids=(a.id,), property="opacity", value=0.8), history_group="gesture"
    )
    r = d.dispatch(first, client_id="local-user")
    assert r.ok
    ok(d, SetProperties(node_ids=(a.id,), property="opacity", value=0.4), history_group="gesture")
    assert len(d.undo_history) == baseline + 1
    revision = d.snapshot.revision
    assert d.dispatch(first, client_id="local-user") == r and d.snapshot.revision == revision
    ok(d, action="undo")
    assert d.snapshot.project.document.nodes[a.id].opacity == 1
    ok(d, action="redo")
    ok(d, SetProperties(node_ids=(a.id,), property="opacity", value=0.3), history_group="gesture")
    assert len(d.undo_history) == baseline + 2
    checkpoint = d.capture_checkpoint()
    d.mark_saved(checkpoint)
    ok(d, SetProperties(node_ids=(a.id,), property="opacity", value=0.2), history_group="gesture")
    ok(d, action="undo")
    assert not d.dirty and d.snapshot.project.document.nodes[a.id].opacity == 0.3
    ok(d, Move(node_id=a.id, dx=2, dy=0), source="AI")
    depth = len(d.undo_history)
    r2 = request(
        d, SetProperties(node_ids=(a.id,), property="opacity", value=0.7), history_group="gesture"
    )
    assert d.dispatch(r2, client_id="another-client").ok
    assert len(d.undo_history) == depth + 1
    # Even an otherwise identical group string cannot absorb another client's command.
    ok(d, SetProperties(node_ids=(a.id,), property="opacity", value=0.6), history_group="gesture")
    assert len(d.undo_history) == depth + 2


def test_frame_background_and_clear_paints_are_explicit_content() -> None:
    d = engine()
    frame = node(d, "frame", "frame")
    ok(d, Create(node=frame))
    ok(d, SetProperties(node_ids=(frame.id,), property="background", value="#33445580"))
    changed = d.snapshot.project.document.nodes[frame.id]
    assert value(changed, "background") == "#33445580"
    no_fill = inspected(replace(frame, style=Style(fill=Fill())), "fill", None)
    assert no_fill.style.fill is None
