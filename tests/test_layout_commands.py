from dataclasses import replace
from pathlib import Path

import pytest
from test_commands import engine, node, ok, run

from ltechdesign.commands import (
    Create,
    Delete,
    Move,
    Reorder,
    Reparent,
    ResizeNode,
    SetConstraints,
    SetLayout,
    SetProperties,
)
from ltechdesign.domain import create_node, dump_project, load_project
from ltechdesign.domain.models import Constraints, Layout, NodeId, Point
from ltechdesign.persistence import PersistenceService

pytestmark = pytest.mark.core


@pytest.mark.parametrize("direction", ["horizontal", "vertical"])
@pytest.mark.parametrize("main", ["start", "center", "end"])
@pytest.mark.parametrize("cross", ["start", "center", "end", "stretch"])
def test_padding_gap_alignment_fill_and_single_undo(direction: str, main: str, cross: str) -> None:
    from ltechdesign.domain.typing import typed

    d = engine()
    f = node(d, "f", "frame", width=300, height=200)
    a = node(d, "a", parent_id=f.id, width=30, height=20)
    b = node(d, "b", parent_id=f.id, width=50, height=40)
    ok(d, Create(node=f), Create(node=a), Create(node=b))
    before = d.snapshot.project
    depth = len(d.undo_history)
    layout = typed(
        dict(
            type="stack",
            direction=direction,
            padding=[10, 20, 30, 40],
            gap=7,
            align_main=main,
            align_cross=cross,
            sizing_x="fixed",
            sizing_y="fixed",
        ),
        Layout,
        "$",
        wire=True,
    )
    ok(d, SetLayout(node_id=f.id, layout=layout))
    after = d.snapshot.project
    aa, bb = (after.document.nodes[k] for k in (a.id, b.id))
    horizontal = direction == "horizontal"
    leading = 40 if horizontal else 10
    space = (300 - 40 - 20 - 30 - 50 - 7) if horizontal else (200 - 10 - 30 - 20 - 40 - 7)
    offset = space if main == "end" else space / 2 if main == "center" else 0
    assert (aa.x if horizontal else aa.y) == leading + offset
    assert (bb.x - aa.x if horizontal else bb.y - aa.y) == (
        aa.width if horizontal else aa.height
    ) + 7
    inner = 160 if horizontal else 240
    first_size = aa.height if horizontal else aa.width
    c_offset = (
        inner - first_size
        if cross == "end"
        else (inner - first_size) / 2
        if cross == "center"
        else 0
    )
    assert (aa.y if horizontal else aa.x) == (10 if horizontal else 40) + c_offset
    if cross == "stretch":
        assert first_size == inner
    assert len(d.undo_history) == depth + 1
    assert d.snapshot.revision == 2
    ok(d, action="undo")
    assert d.snapshot.project == before
    ok(d, action="redo")
    assert d.snapshot.project == after
    assert load_project(dump_project(after, {})).document == after.document


def test_nested_stacks_hug_fill_resize_child_edit_and_reorder() -> None:
    d = engine()
    root = node(
        d, "root", "frame", width=360, height=240, layout=Layout(padding=(10, 20, 10, 20), gap=9)
    )
    row = node(
        d,
        "row",
        "frame",
        parent_id=root.id,
        layout=Layout(
            direction="horizontal", sizing_x="fill", sizing_y="hug", padding=(3, 4, 5, 6), gap=8
        ),
    )
    a = node(d, "a", parent_id=row.id, width=60, height=20)
    b = node(
        d, "b", parent_id=row.id, width=15, height=30, constraints=Constraints(sizing_x="fill")
    )
    c = node(d, "c", parent_id=root.id, width=10, height=15)
    ok(d, *(Create(node=n) for n in (root, row, a, b, c)))
    ns = d.snapshot.project.document.nodes
    assert (ns[row.id].width, ns[row.id].height) == (320, 38)
    assert ns[b.id].width == 242 and ns[c.id].y == 57
    original = d.snapshot.project
    ok(d, ResizeNode(node_id=root.id, width=460, height=240, anchor=Point()))
    assert d.snapshot.project.document.nodes[b.id].width == 342
    ok(d, SetProperties(node_ids=(a.id,), property="height", value=90))
    assert d.snapshot.project.document.nodes[row.id].height == 98
    assert d.snapshot.project.document.nodes[c.id].y == 117
    ok(d, Reorder(node_id=a.id, index=1))
    assert d.snapshot.project.document.nodes[b.id].x == 6
    ok(d, Delete(node_id=a.id))
    assert d.snapshot.project.document.nodes[b.id].width == 410
    for _ in range(4):
        ok(d, action="undo")
    assert d.snapshot.project == original


@pytest.mark.parametrize("anchor", ["start", "end", "center", "stretch"])
def test_free_parent_constraints_and_repeated_resize_no_drift(anchor: str) -> None:
    from ltechdesign.domain.typing import typed

    d = engine()
    f = node(d, "f", "frame", width=200, height=160, rotation=25, scale=1.3)
    c = node(
        d,
        "c",
        parent_id=f.id,
        width=60,
        height=30,
        x=15,
        y=20,
        constraints=typed(
            dict(horizontal=anchor, vertical=anchor, sizing_x="fixed", sizing_y="fixed"),
            Constraints,
            "$",
            wire=True,
        ),
    )
    ok(d, Create(node=f), Create(node=c))
    before = d.snapshot.project
    for w, h in ((280, 200), (200, 160), (280, 200)):
        ok(d, ResizeNode(node_id=f.id, width=w, height=h, anchor=Point(x=1, y=1)))
    child = d.snapshot.project.document.nodes[c.id]
    assert child.x == 15 + (80 if anchor == "end" else 40 if anchor == "center" else 0)
    assert child.y == 20 + (40 if anchor == "end" else 20 if anchor == "center" else 0)
    assert child.width == (140 if anchor == "stretch" else 60)
    assert child.height == (70 if anchor == "stretch" else 30)
    for _ in range(3):
        ok(d, action="undo")
    assert d.snapshot.project == before


def test_nested_free_constraints_propagate_and_insufficient_space_clamps() -> None:
    d = engine()
    a = node(d, "a", "frame", width=300, height=200)
    b = node(
        d,
        "b",
        "frame",
        parent_id=a.id,
        width=200,
        height=100,
        x=20,
        constraints=Constraints(horizontal="stretch", vertical="stretch"),
    )
    c = node(
        d,
        "c",
        parent_id=b.id,
        x=150,
        y=50,
        constraints=Constraints(horizontal="end", vertical="center"),
    )
    ok(d, *(Create(node=n) for n in (a, b, c)))
    ok(d, SetProperties(node_ids=(a.id,), property="width", value=400))
    ns = d.snapshot.project.document.nodes
    assert ns[b.id].width == 300 and ns[c.id].x == 250
    ok(d, ResizeNode(node_id=a.id, width=1, height=1, anchor=Point()))
    assert d.snapshot.project.document.nodes[b.id].width == 0.01


def test_overflow_equal_fill_empty_hug_hidden_and_determinism() -> None:
    d = engine()
    f = node(
        d,
        "f",
        "frame",
        width=100,
        height=90,
        layout=Layout(direction="horizontal", padding=(5, 10, 5, 10), gap=4),
    )
    a = node(d, "a", parent_id=f.id, width=120, height=10, visible=False, locked=True)
    b = node(d, "b", parent_id=f.id, constraints=Constraints(sizing_x="fill"))
    c = node(d, "c", parent_id=f.id, constraints=Constraints(sizing_x="fill"))
    ok(d, *(Create(node=n) for n in (f, a, b, c)))
    ns = d.snapshot.project.document.nodes
    assert ns[a.id].width == 120 and ns[b.id].width == ns[c.id].width == 0.01
    assert ns[b.id].x == 134 and ns[c.id].x == 138.01
    ok(d, SetProperties(node_ids=(f.id,), property="width", value=300))
    ns = d.snapshot.project.document.nodes
    assert ns[b.id].width == ns[c.id].width == 76
    before = d.snapshot.project
    ok(d, Move(node_id=f.id, dx=0, dy=0))
    assert d.snapshot.project == before
    for k in (a.id, b.id, c.id):
        ok(d, Delete(node_id=k))
    ok(d, SetLayout(node_id=f.id, layout=Layout(sizing_x="hug", sizing_y="hug")))
    assert d.snapshot.project.document.nodes[f.id].width == 0.01


@pytest.mark.parametrize("kind", ["main", "cross", "text", "root", "transform", "intrinsic"])
def test_invalid_combinations_and_cycles_roll_back_whole_batch(kind: str) -> None:
    from ltechdesign.commands import SetFont
    from ltechdesign.domain.models import Font, FontId, TextData, Typography

    d = engine()
    f = node(d, "f", "frame", layout=Layout(direction="horizontal", sizing_x="hug"))
    a = node(d, "a", parent_id=f.id, constraints=Constraints(sizing_x="fill"))
    if kind == "cross":
        f = replace(f, layout=Layout(sizing_x="hug", align_cross="stretch"))
        a = replace(a, constraints=None)
    if kind == "text":
        font = Font(id=FontId("fnt"), family="Arial")
        ok(d, SetFont(font=font))
        a = replace(
            create_node(
                "text",
                f.page_id,
                node_id=NodeId("a"),
                data=TextData(typography=Typography(font_id=font.id, sizing="auto_height")),
            ),
            parent_id=f.id,
            constraints=Constraints(sizing_x="fill"),
        )
    if kind == "root":
        f = replace(f, layout=Layout(sizing_x="fill"))
        a = replace(a, constraints=None)
    if kind == "transform":
        f = replace(f, layout=Layout())
        a = replace(a, constraints=None, rotation=15)
    if kind == "intrinsic":
        f = replace(f, layout=Layout())
        a = replace(a, constraints=Constraints(sizing_y="hug"))
    before = d.snapshot
    result = run(d, Create(node=f), Create(node=a))
    assert not result.ok and d.snapshot is before
    assert result.error is not None
    if kind in ("main", "cross", "text"):
        assert "layout_dependency_cycle" in result.error.message


def test_native_roundtrip_then_edit_without_relying_on_original_session(tmp_path: Path) -> None:
    from ltechdesign.commands import Dispatcher

    d = engine()
    f = node(d, "f", "frame", layout=Layout(gap=12, sizing_y="hug"))
    c = node(d, "c", parent_id=f.id, height=25)
    ok(d, Create(node=f), Create(node=c))
    service = PersistenceService()
    handle = service.new(d.snapshot.project, {})
    path = tmp_path / "layout.ltechdesign"
    service.save(handle, handle.admission, {}, target=path)
    service.close(handle)
    opened = service.open(path)
    restored = Dispatcher(opened.admission)
    try:
        assert restored.snapshot.project.document == d.snapshot.project.document
        ok(restored, SetProperties(node_ids=(c.id,), property="height", value=75))
        assert restored.snapshot.project.document.nodes[f.id].height == 75
        ok(restored, action="undo")
        assert restored.snapshot.project.document == d.snapshot.project.document
    finally:
        restored.close()
        service.close(opened)


def test_reparent_preservation_and_manual_derived_resize_fail_explicitly() -> None:
    d = engine()
    f = node(d, "f", "frame", layout=Layout())
    c = node(d, "c")
    ok(d, Create(node=f), Create(node=c))
    before = d.snapshot
    result = run(
        d, Reparent(node_id=c.id, page_id=f.page_id, parent_id=f.id), request_id="preserve"
    )
    assert not result.ok and result.error and result.error.code == "unsupported_visual_preservation"
    assert d.snapshot is before
    ok(d, Reparent(node_id=c.id, page_id=f.page_id, parent_id=f.id, preserve_appearance=False))
    ok(d, SetConstraints(node_id=c.id, constraints=Constraints(sizing_x="fill")))
    before = d.snapshot
    assert not run(d, ResizeNode(node_id=c.id, width=120, height=100, anchor=Point())).ok
    assert d.snapshot is before
