import subprocess
import sys
from collections.abc import Mapping
from concurrent.futures import Future
from dataclasses import replace
from threading import Thread
from typing import Any

import pytest

from ltechdesign.commands import (
    Create,
    Delete,
    Dispatcher,
    Duplicate,
    Group,
    Move,
    RegisterAsset,
    RemoveAsset,
    Reorder,
    Reparent,
    Request,
    Result,
    SetFont,
    SetStyle,
    SetText,
    SetTokens,
    Ungroup,
    Update,
)
from ltechdesign.commands.contracts import Operation
from ltechdesign.commands.dispatcher import ChangeEvent, canonical, retained_size
from ltechdesign.commands.retention import PreparedAssets
from ltechdesign.domain import (
    DocumentSession,
    create_node,
    create_project,
    dump_project,
    load_project,
)
from ltechdesign.domain.errors import fail
from ltechdesign.domain.geometry import Matrix, world_matrix
from ltechdesign.domain.models import (
    Asset,
    AssetId,
    Binding,
    Fill,
    Font,
    FontId,
    Layout,
    MediaData,
    Node,
    NodeId,
    NumberToken,
    Page,
    Point,
    Project,
    SessionId,
    Style,
    TextData,
    TokenId,
    Tokens,
    Typography,
)

pytestmark = pytest.mark.core


def engine(**kwargs: Any) -> Dispatcher:
    return Dispatcher(DocumentSession(project=create_project()), **kwargs)


def node(d: Dispatcher, name: str, kind: Any = "rectangle", **kwargs: Any) -> Node:
    return replace(
        create_node(kind, d.snapshot.project.document.pages[0].id, node_id=NodeId(name)), **kwargs
    )


def request(d: Dispatcher, *ops: Operation, **kwargs: Any) -> Request:
    defaults: dict[str, Any] = dict(
        session_id=d.snapshot.session_id,
        expected_revision=d.snapshot.revision,
        request_id=f"r{d.snapshot.revision}",
        action_name="Edit",
        source="GUI",
        operations=ops,
    )
    defaults.update(kwargs)
    return Request(**defaults)


def run(d: Dispatcher, *ops: Operation, **kwargs: Any) -> Result:
    return d.dispatch(request(d, *ops, **kwargs), client_id="local-user")


def ok(d: Dispatcher, *ops: Operation, **kwargs: Any) -> Result:
    result = run(d, *ops, **kwargs)
    assert result.ok, result.error
    return result


def error(result: Result, code: str) -> None:
    assert result.error is not None
    assert result.error.code == code
    assert result.error.to_dict()["current_revision"] == result.revision


def same_matrix(actual: Matrix, expected: Matrix) -> None:
    for key in ("a", "b", "c", "d", "tx", "ty"):
        assert getattr(actual, key) == pytest.approx(getattr(expected, key), abs=1e-9)


def test_atomic_rollback_retains_history_redo_dirty_and_events() -> None:
    d = engine(initially_saved=True)
    events: list[ChangeEvent] = []
    d.subscribe(events.append)
    a = node(d, "a")
    ok(d, Create(node=a))
    ok(d, Move(node_id=a.id, dx=3, dy=4))
    ok(d, action="undo")
    before = d.snapshot, d.undo_history, d.redo_history, d.dirty, len(events)
    error(
        run(d, Move(node_id=a.id, dx=50, dy=0), Delete(node_id=NodeId("missing"))),
        "validation_error",
    )
    assert (d.snapshot, d.undo_history, d.redo_history, d.dirty, len(events)) == before
    ok(d, action="redo", request_id="redo-after-failure")
    assert d.snapshot.project.document.nodes[a.id].x == 3


def test_one_commit_event_history_and_monotonic_undo_redo() -> None:
    d = engine(initially_saved=True)
    events: list[ChangeEvent] = []

    def observe(event: ChangeEvent) -> None:
        assert d.snapshot is event.snapshot
        assert d.dirty == event.dirty
        events.append(event)

    d.subscribe(observe)
    a, b = node(d, "a"), node(d, "b")
    ok(
        d,
        Create(node=a),
        Create(node=b),
        Move(node_id=a.id, dx=7, dy=8),
        action_name="Drag",
        source="AI",
    )
    assert len(events) == len(d.undo_history) == d.snapshot.revision == 1
    metadata = d.undo_history[0].metadata
    assert (metadata.action_name, metadata.source, metadata.request_id) == ("Drag", "AI", "r0")
    assert metadata.timestamp
    ok(d, action="undo")
    assert not d.dirty and not d.snapshot.project.document.nodes
    ok(d, action="redo")
    assert d.dirty and d.snapshot.revision == 3
    ok(d, Move(node_id=a.id, dx=0, dy=0))
    assert d.snapshot.revision == 4  # Valid no-op is a transaction.


def test_checkpoint_is_semantic_and_late_save_does_not_clean_new_edit() -> None:
    d = engine()
    assert d.dirty
    initial = d.capture_checkpoint()
    a = node(d, "a")
    ok(d, Create(node=a))
    saved = d.capture_checkpoint()
    ok(d, Move(node_id=a.id, dx=1, dy=0))
    d.mark_saved(saved)
    assert d.dirty and d.snapshot.revision == 2
    ok(d, action="undo")
    assert not d.dirty and d.snapshot.revision == 3
    d.mark_saved(initial)
    assert d.dirty
    with pytest.raises(ValueError):
        d.mark_saved(replace(initial, session_id=SessionId("another")))


def test_new_edit_invalidates_redo_and_histories_are_per_admission() -> None:
    d = engine()
    other = Dispatcher(DocumentSession(project=d.snapshot.project))
    a = node(d, "a")
    ok(d, Create(node=a))
    ok(d, action="undo")
    ok(d, Create(node=node(d, "b")))
    assert not d.redo_history
    error(run(d, action="redo"), "history_empty")
    assert other.snapshot.revision == 0 and not other.undo_history
    assert d.snapshot.session_id != other.snapshot.session_id


def test_retry_precedes_stale_revision_and_digest_includes_action_and_source() -> None:
    d = engine()
    req = request(d, Create(node=node(d, "a")))
    result = d.dispatch(req, client_id="client")
    ok(d, Move(node_id=NodeId("a"), dx=1, dy=2))
    assert d.dispatch(req, client_id="client") is result
    assert d.snapshot.revision == 2
    for changed in (
        replace(req, source="AI"),
        replace(req, expected_revision=2),
        replace(req, action_name="Another"),
    ):
        error(d.dispatch(changed, client_id="client"), "request_id_conflict")
    error(d.dispatch(req, client_id="different-client"), "revision_conflict")
    stale = replace(req, request_id="stale")
    failure = d.dispatch(stale, client_id="client")
    error(failure, "revision_conflict")
    ok(d, Move(node_id=NodeId("a"), dx=1, dy=0))
    assert d.dispatch(stale, client_id="client") is failure


def test_operation_discriminator_and_numeric_canonicalization() -> None:
    d = engine()
    ok(d, Create(node=node(d, "a")))
    req = request(d, Move(node_id=NodeId("a"), dx=1, dy=-0.0))
    first = d.dispatch(req, client_id="c")
    retry = replace(req, operations=(Move(node_id=NodeId("a"), dx=1.0, dy=0),))
    assert d.dispatch(retry, client_id="c") is first
    req = request(d, Delete(node_id=NodeId("a")))
    assert d.dispatch(req, client_id="c").ok
    error(
        d.dispatch(replace(req, operations=(Ungroup(node_id=NodeId("a")),)), client_id="c"),
        "request_id_conflict",
    )
    assert canonical({"z": 1.0, "a": -0.0}) == canonical({"a": 0, "z": 1})


def test_capacity_retention_error_cache_close_and_restart_boundaries() -> None:
    now = [0.0]
    d = engine(dedup_capacity=1, clock=lambda: now[0])
    req = request(d, Create(node=node(d, "a")))
    first = d.dispatch(req, client_id="c")
    now[0] = 1799.99
    error(run(d, Move(node_id=NodeId("a"), dx=1, dy=0)), "dedup_capacity_exceeded")
    assert d.dispatch(req, client_id="c") is first
    now[0] = 1800
    ok(d, Move(node_id=NodeId("a"), dx=1, dy=0))
    d.close()
    error(d.dispatch(req, client_id="c"), "session_closed")
    reopened = Dispatcher(DocumentSession(project=d.snapshot.project))
    error(reopened.dispatch(req, client_id="c"), "session_closed")
    with pytest.raises(ValueError):
        engine(retention_seconds=1799)


def test_inflight_retry_joins_future_and_timeout_cannot_cancel() -> None:
    joined: list[Future[Result]] = []

    def layout(project: Project) -> Project:
        joined.append(d.submit(req, client_id="c"))
        assert not joined[0].done()
        assert not joined[0].cancel()
        error(d.dispatch(replace(req, request_id="nested"), client_id="c"), "queue_full")
        return project

    d = engine(layout=layout)
    req = request(d, Create(node=node(d, "a")))
    completed = d.submit(req, client_id="c")
    assert completed is joined[0]
    assert completed.result().ok and d.snapshot.revision == 1


def test_listener_failure_and_reentrancy_do_not_reclassify_commit() -> None:
    d = engine()
    observed: list[int] = []

    def bad(event: ChangeEvent) -> None:
        error(run(d, Move(node_id=NodeId("a"), dx=1, dy=0)), "queue_full")
        raise RuntimeError("listener error")

    unsubscribe = d.subscribe(bad)
    d.subscribe(lambda event: observed.append(event.snapshot.revision))
    ok(d, Create(node=node(d, "a")))
    unsubscribe()
    ok(d, Move(node_id=NodeId("a"), dx=1, dy=0))
    assert observed == [1, 2]


def test_delete_subtree_and_undo_restore_hierarchy_style_and_bindings() -> None:
    d = engine()
    frame, a, b = node(d, "f", "frame"), node(d, "a"), node(d, "b")
    a = replace(a, parent_id=frame.id, style=Style(fill=Fill(color="#FF0000FF")))
    b = replace(b, parent_id=frame.id)
    tokens = Tokens(
        tokens=(NumberToken(id=TokenId("t"), name="Alpha", value=1),),
        bindings=(Binding(node_id=a.id, property="opacity", token_id=TokenId("t")),),
    )
    ok(d, Create(node=frame), Create(node=a), Create(node=b), SetTokens(tokens=tokens))
    before = d.snapshot.project
    ok(d, Delete(node_id=frame.id))
    assert not d.snapshot.project.document.nodes and not d.snapshot.project.tokens.bindings
    ok(d, action="undo")
    assert d.snapshot.project == before
    assert load_project(dump_project(d.snapshot.project, {})).document == before.document


def test_duplicate_subtree_remaps_children_parent_and_bindings() -> None:
    d = engine()
    frame, a = node(d, "f", "frame"), node(d, "a", parent_id=NodeId("f"))
    tokens = Tokens(
        tokens=(NumberToken(id=TokenId("t"), name="Alpha", value=1),),
        bindings=(Binding(node_id=a.id, property="opacity", token_id=TokenId("t")),),
    )
    ok(d, Create(node=frame), Create(node=a), SetTokens(tokens=tokens))
    result = ok(d, Duplicate(node_id=frame.id, dx=20))
    mapping = dict(result.id_map)
    assert set(mapping) == {frame.id, a.id} and not set(mapping) & set(mapping.values())
    nodes = d.snapshot.project.document.nodes
    assert nodes[mapping[frame.id]].children == (mapping[a.id],)
    assert nodes[mapping[a.id]].parent_id == mapping[frame.id]
    assert nodes[mapping[frame.id]].x == 20
    assert d.snapshot.project.tokens.bindings[-1].node_id == mapping[a.id]
    ok(d, action="undo")
    assert set(d.snapshot.project.document.nodes) == {frame.id, a.id}
    ok(d, action="redo")
    assert mapping[a.id] in d.snapshot.project.document.nodes


def test_group_reparent_ungroup_world_matrices_and_history() -> None:
    d = engine()
    f = node(d, "f", "frame", rotation=35, scale=1.5, x=30, y=-20)
    a = node(d, "a", x=60, rotation=-23, parent_id=f.id)
    b = node(d, "b", x=220, y=80, parent_id=f.id)
    target = node(d, "target", "frame", x=-120, rotation=-45, scale=0.7)
    ok(d, Create(node=f), Create(node=a), Create(node=b), Create(node=target))
    before = d.snapshot.project
    matrices = {k: world_matrix(before.document, k) for k in (a.id, b.id)}
    ok(d, Group(node_ids=(b.id, a.id), group_id=NodeId("g")))
    grouped = d.snapshot.project
    assert grouped.document.nodes[NodeId("g")].children == (a.id, b.id)
    for k, matrix in matrices.items():
        same_matrix(world_matrix(grouped.document, k), matrix)
    ok(d, Reparent(node_id=NodeId("g"), page_id=f.page_id, parent_id=target.id))
    for k, matrix in matrices.items():
        same_matrix(world_matrix(d.snapshot.project.document, k), matrix)
    ok(d, Ungroup(node_id=NodeId("g")))
    for k, matrix in matrices.items():
        same_matrix(world_matrix(d.snapshot.project.document, k), matrix)
    ok(d, action="undo")
    ok(d, action="undo")
    assert d.snapshot.project == grouped
    ok(d, action="undo")
    assert d.snapshot.project == before


def test_group_normalizes_after_child_move_delete_and_empty_group() -> None:
    d = engine()
    a, b = node(d, "a", x=10), node(d, "b", x=110)
    ok(d, Create(node=a), Create(node=b), Group(node_ids=(a.id, b.id), group_id=NodeId("g")))
    old_b = world_matrix(d.snapshot.project.document, b.id)
    ok(d, Move(node_id=a.id, dx=-50, dy=-20))
    same_matrix(world_matrix(d.snapshot.project.document, b.id), old_b)
    ok(d, Delete(node_id=a.id))
    same_matrix(world_matrix(d.snapshot.project.document, b.id), old_b)
    ok(d, Delete(node_id=b.id))
    g = d.snapshot.project.document.nodes[NodeId("g")]
    assert (g.width, g.height, g.pivot, g.children) == (0, 0, Point(), ())
    ok(d, Create(node=node(d, "c", parent_id=g.id)))
    assert d.snapshot.project.document.nodes[g.id].width == 100


def test_visual_preservation_guards_and_explicit_context_change() -> None:
    d = engine()
    a, b, c = node(d, "a"), node(d, "b"), node(d, "c")
    f = node(d, "f", "frame", clip_content=True)
    ok(d, Create(node=a), Create(node=b), Create(node=c), Create(node=f))
    error(
        run(d, Group(node_ids=(a.id, c.id), group_id=NodeId("g"))),
        "unsupported_visual_preservation",
    )
    ok(
        d,
        Group(node_ids=(a.id, c.id), group_id=NodeId("g"), preserve_appearance=False),
        request_id="explicit-group",
    )
    assert d.snapshot.project.document.pages[0].root_ids == (b.id, NodeId("g"), f.id)
    error(
        run(d, Reparent(node_id=b.id, parent_id=f.id, page_id=f.page_id)),
        "unsupported_visual_preservation",
    )
    ok(
        d,
        Reparent(node_id=b.id, parent_id=f.id, page_id=f.page_id, preserve_appearance=False),
        request_id="explicit-reparent",
    )
    g = d.snapshot.project.document.nodes[NodeId("g")]
    ok(d, Update(node=replace(g, opacity=0.5)))
    error(run(d, Ungroup(node_id=g.id)), "unsupported_visual_preservation")


def test_cross_page_reparent_cycle_rejection_and_reorder() -> None:
    project = create_project()
    page = Page()
    project = replace(
        project, document=replace(project.document, pages=project.document.pages + (page,))
    )
    d = Dispatcher(DocumentSession(project=project))
    f, a, b = node(d, "f", "frame"), node(d, "a", "frame", parent_id=NodeId("f")), node(d, "b")
    ok(d, Create(node=f), Create(node=a), Create(node=b))
    error(run(d, Reparent(node_id=f.id, parent_id=a.id, page_id=f.page_id)), "validation_error")
    ok(d, Reorder(node_id=b.id, index=0), request_id="reorder")
    assert d.snapshot.project.document.pages[0].root_ids == (b.id, f.id)
    ok(d, Reparent(node_id=f.id, page_id=page.id))
    assert d.snapshot.project.document.nodes[a.id].page_id == page.id


def test_text_style_font_and_serialization_share_dispatcher() -> None:
    d = engine()
    font = Font(id=FontId("font"), family="Abel")
    text = create_node(
        "text",
        d.snapshot.project.document.pages[0].id,
        data=TextData(typography=Typography(font_id=font.id), text="Before"),
    )
    ok(d, SetFont(font=font), Create(node=text))
    before = d.snapshot.project
    assert isinstance(text.data, TextData)
    ok(
        d,
        SetText(node_id=text.id, data=replace(text.data, text="After\nMultiline")),
        SetStyle(node_id=text.id, style=Style(fill=Fill(color="#003366FF"))),
    )
    after = d.snapshot.project
    loaded = load_project(dump_project(after, {}))
    assert loaded.document == after.document and loaded.fonts == after.fonts
    ok(d, action="undo")
    assert d.snapshot.project == before


def test_history_budget_whole_entries_and_explicit_cleanup() -> None:
    d = engine()
    ok(d, Create(node=node(d, "a")))
    budget = d.history_bytes
    assert budget >= retained_size(d.snapshot.project)
    limited = Dispatcher(DocumentSession(project=d.snapshot.project), history_budget=budget)
    events: list[ChangeEvent] = []
    limited.subscribe(events.append)
    for _ in range(5):
        ok(limited, Move(node_id=NodeId("a"), dx=1, dy=0))
        assert limited.history_bytes <= budget
    assert any(e.history_evicted for e in events)
    snapshot = limited.snapshot
    limited.clear_history()
    assert limited.snapshot is snapshot and limited.history_bytes == 0
    tiny = engine(history_budget=0)
    result = ok(tiny, Create(node=node(tiny, "a")))
    assert result.history_evicted == 1 and not tiny.undo_history


def test_layout_failure_rolls_back_and_layout_output_is_same_history_entry() -> None:
    def layout(project: Project) -> Project:
        a = project.document.nodes[NodeId("a")]
        nodes = dict(project.document.nodes)
        nodes[a.id] = replace(a, y=42)
        return replace(project, document=replace(project.document, nodes=nodes))

    d = engine(layout=layout)
    ok(d, Create(node=node(d, "a")))
    assert d.snapshot.project.document.nodes[NodeId("a")].y == 42
    ok(d, action="undo")
    assert not d.snapshot.project.document.nodes

    def broken(project: Project) -> Project:
        fail("layout_failed")

    failing = engine(layout=broken)
    before = failing.snapshot
    error(run(failing, Create(node=node(failing, "a"))), "validation_error")
    assert failing.snapshot is before and not failing.undo_history
    unsupported = engine()
    error(
        run(unsupported, Create(node=node(unsupported, "f", "frame", layout=Layout()))),
        "unsupported_capability",
    )


@pytest.mark.parametrize("operation", ["save", "export", "selection", "viewport"])
def test_side_effect_and_session_operations_are_not_content(operation: str) -> None:
    d = engine()
    with pytest.raises(ValueError):
        request(d, operation)  # type: ignore[arg-type]
    assert d.snapshot.revision == 0 and not d.undo_history


def test_limits_readonly_structural_updates_and_wrong_thread() -> None:
    d = engine()
    a = node(d, "a")
    error(run(d, *(Create(node=a) for _ in range(101))), "limit_exceeded")
    error(run(d, Create(node=replace(a, name="x" * (4 * 1024 * 1024)))), "limit_exceeded")
    ok(d, Create(node=a))
    error(run(d, Update(node=replace(a, parent_id=NodeId("missing")))), "validation_error")
    ro = engine(read_only=True)
    error(run(ro, Create(node=node(ro, "a"))), "read_only")
    failures: list[str] = []

    def worker() -> None:
        try:
            run(d, Move(node_id=a.id, dx=1, dy=0))
        except RuntimeError as exc:
            failures.append(str(exc))

    thread = Thread(target=worker)
    thread.start()
    thread.join()
    assert failures and d.snapshot.revision == 1


class Store:
    """Executable conformance double for the port; not a production blob store."""

    def __init__(self) -> None:
        self.roots: dict[AssetId, Asset] = {}
        self.staging: dict[str, Asset] = {}
        self.external: set[AssetId] = set()
        self.blobs: set[AssetId] = set()
        self.fail_prepare = False

    def prepare(
        self, roots: Mapping[AssetId, Asset], staged: Mapping[str, Asset]
    ) -> PreparedAssets:
        if self.fail_prepare:
            fail("prepare_failure")
        assert all(self.staging.get(k) == v for k, v in staged.items())
        assert set(roots) <= self.blobs | {a.id for a in staged.values()}
        store = self

        class Lease:
            def commit(self) -> None:
                store.blobs.update(a.id for a in staged.values())
                store.roots = dict(roots)
                store.discard(staged)

            def abort(self) -> None:
                store.discard(staged)

        return Lease()

    def discard(self, staged: Mapping[str, Asset]) -> None:
        for key in staged:
            self.staging.pop(key, None)

    def gc(self) -> None:
        self.blobs.intersection_update(set(self.roots) | self.external)


def asset() -> Asset:
    import hashlib

    digest = hashlib.sha256(b"image bytes").hexdigest()
    return Asset(
        id=AssetId("asset"),
        path="assets/data/" + digest,
        media_type="image/png",
        byte_length=len(b"image bytes"),
        sha256=digest,
    )


def test_staged_asset_batch_rollback_retention_gc_and_serialization() -> None:
    store = Store()
    d = engine(assets=store)
    image_asset = asset()
    store.staging["stage"] = image_asset
    image = create_node(
        "image", d.snapshot.project.document.pages[0].id, data=MediaData(asset_id=image_asset.id)
    )
    error(
        run(
            d,
            RegisterAsset(asset=image_asset, staging_id="stage"),
            Create(node=image),
            Delete(node_id=NodeId("missing")),
        ),
        "validation_error",
    )
    assert not store.staging and not store.roots and not store.blobs
    store.staging["stage2"] = image_asset
    ok(
        d,
        RegisterAsset(asset=image_asset, staging_id="stage2"),
        Create(node=image),
        request_id="import",
    )
    assert not store.staging and image_asset.id in store.roots
    assert (
        load_project(dump_project(d.snapshot.project, {image_asset.path: b"image bytes"})).assets
        == d.snapshot.project.assets
    )
    ok(d, Delete(node_id=image.id), RemoveAsset(asset_id=image_asset.id))
    store.gc()
    assert image_asset.id in store.blobs  # Undo pins bytes even with no live registration.
    ok(d, action="undo")
    assert image.id in d.snapshot.project.document.nodes
    ok(d, action="redo")
    store.external.add(image_asset.id)  # Job/recovery/snapshot lease, independent of history.
    d.clear_history()
    store.gc()
    assert image_asset.id in store.blobs
    store.external.clear()
    store.gc()
    assert not store.blobs


def test_asset_prepare_failure_and_live_reference_removal_are_atomic() -> None:
    store = Store()
    d = engine(assets=store)
    image_asset = asset()
    store.staging["stage"] = image_asset
    store.fail_prepare = True
    before = d.snapshot
    error(run(d, RegisterAsset(asset=image_asset, staging_id="stage")), "validation_error")
    assert d.snapshot is before and not store.staging and not d.undo_history
    store.fail_prepare = False
    store.staging["next"] = image_asset
    image = create_node(
        "image", d.snapshot.project.document.pages[0].id, data=MediaData(asset_id=image_asset.id)
    )
    ok(
        d,
        RegisterAsset(asset=image_asset, staging_id="next"),
        Create(node=image),
        request_id="import",
    )
    before = d.snapshot
    error(run(d, RemoveAsset(asset_id=image_asset.id)), "validation_error")
    assert d.snapshot is before and image_asset.id in store.roots


def test_no_store_does_not_claim_asset_registration_or_qt_integration() -> None:
    d = engine()
    error(run(d, RegisterAsset(asset=asset(), staging_id="stage")), "unsupported_capability")
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import sys; import ltechdesign.commands; "
            "assert not any(k.startswith(('PySide', 'PyQt')) for k in sys.modules)",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("cancel_at", [1, 2])
def test_cancel_before_and_after_asset_prepare_leaves_no_commit(cancel_at: int) -> None:
    store = Store()
    d = engine(assets=store)
    staged_asset = asset()
    store.staging["stage"] = staged_asset
    events: list[ChangeEvent] = []
    d.subscribe(events.append)
    calls = 0

    def cancelled() -> bool:
        nonlocal calls
        calls += 1
        return calls == cancel_at

    req = request(d, RegisterAsset(asset=staged_asset, staging_id="stage"))
    before = d.snapshot
    result = d.dispatch(req, client_id="c", cancelled=cancelled)
    error(result, "cancelled")
    assert not events and not d.undo_history and d.snapshot is before
    assert not store.staging and not store.roots and not store.blobs
    assert d.dispatch(req, client_id="c") is result


def test_cancel_after_barrier_cannot_relabel_success() -> None:
    d = engine()
    cancelled = [False]
    d.subscribe(lambda event: cancelled.__setitem__(0, True))
    req = request(d, Create(node=node(d, "a")))
    result = d.dispatch(req, client_id="c", cancelled=lambda: cancelled[0])
    assert result.ok and cancelled[0]
    assert d.dispatch(req, client_id="c", cancelled=lambda: True) is result


def test_unchanged_rotated_groups_do_not_drift_on_unrelated_edit() -> None:
    d = engine()
    a, b = node(d, "a", rotation=27, x=40), node(d, "b", rotation=-14, y=90)
    ok(d, Create(node=a), Create(node=b), Group(node_ids=(a.id, b.id), group_id=NodeId("g")))
    g = d.snapshot.project.document.nodes[NodeId("g")]
    ok(d, Update(node=replace(g, rotation=39, scale=1.3)))
    nodes = dict(d.snapshot.project.document.nodes)
    ok(d, Create(node=node(d, "other")))
    for _ in range(5):
        ok(d, Move(node_id=NodeId("other"), dx=1, dy=0))
        for key, original in nodes.items():
            assert d.snapshot.project.document.nodes[key] == original


def test_failed_final_token_validation_is_atomic_and_fixable_within_batch() -> None:
    d = engine()
    a = node(d, "a")
    tokens = Tokens(
        tokens=(NumberToken(id=TokenId("t"), name="Alpha", value=0.5),),
        bindings=(Binding(node_id=a.id, property="opacity", token_id=TokenId("t")),),
    )
    error(run(d, Create(node=a), SetTokens(tokens=tokens)), "validation_error")
    assert not d.snapshot.project.document.nodes
    ok(
        d,
        Create(node=a),
        SetTokens(tokens=tokens),
        Update(node=replace(a, opacity=0.5)),
        request_id="valid-token-batch",
    )
    assert d.snapshot.project.tokens == tokens


def test_redo_invalidation_releases_assets_only_when_unreferenced() -> None:
    store = Store()
    d = engine(assets=store)
    staged_asset = asset()
    store.staging["stage"] = staged_asset
    ok(d, RegisterAsset(asset=staged_asset, staging_id="stage"))
    ok(d, action="undo")
    store.gc()
    assert staged_asset.id in store.blobs  # Redo is a retention root too.
    ok(d, Create(node=node(d, "a")))
    store.gc()
    assert not store.blobs and not d.redo_history


@pytest.mark.parametrize(
    "operation",
    [
        Create(node=create_node("rectangle", create_project().document.pages[0].id)),
        Reorder(node_id=NodeId("a"), index=-1),
        Reparent(node_id=NodeId("a"), page_id=Page().id, parent_id=NodeId("a")),
    ],
)
def test_invalid_hierarchy_operations_preserve_existing_content(operation: Operation) -> None:
    d = engine()
    ok(d, Create(node=node(d, "a")))
    before = d.snapshot
    error(run(d, operation), "validation_error")
    assert d.snapshot is before


def test_revision_overflow_and_unexpected_planner_failure_do_not_publish() -> None:
    from ltechdesign.domain.models import MAX_REVISION

    d = Dispatcher(DocumentSession(project=create_project(), revision=MAX_REVISION))
    error(run(d, Create(node=node(d, "a"))), "limit_exceeded")

    def broken(project: Project) -> Project:
        raise RuntimeError("private implementation detail")

    d = engine(layout=broken)
    events: list[ChangeEvent] = []
    d.subscribe(events.append)
    error(run(d, Create(node=node(d, "a"))), "internal_error")
    assert not events and not d.undo_history and d.snapshot.revision == 0


def test_self_parent_create_is_rejected_before_later_subtree_traversal() -> None:
    d = engine()
    cyclic = node(d, "cycle", "frame", parent_id=NodeId("cycle"))
    error(run(d, Create(node=cyclic), Delete(node_id=cyclic.id)), "validation_error")
    assert d.snapshot.revision == 0 and not d.snapshot.project.document.nodes
