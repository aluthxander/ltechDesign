import base64
import hashlib
import json
import subprocess
import sys
from collections.abc import Callable
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import Any

import pytest

from ltechdesign.domain import (
    Document,
    DocumentSession,
    ModelError,
    create_node,
    dump_project,
    dumps,
    from_data,
    load_project,
    loads,
    semantic_content,
    to_data,
)
from ltechdesign.domain.codec import MEMBER_TYPES, json_bytes, parse_json
from ltechdesign.domain.geometry import (
    Bounds,
    Matrix,
    hit_test_bounds,
    local_matrix,
    normalize_group,
    primitive_bounds,
    relative_node,
    scale_group,
    subtree_geometry_bounds,
    visual_bounds,
    with_matrix,
    world_matrix,
)
from ltechdesign.domain.migrations import MigrationRegistry, document_migrations
from ltechdesign.domain.models import (
    AssetId,
    ColorToken,
    Constraints,
    Crop,
    Fill,
    FontId,
    Layout,
    LineHeight,
    MediaData,
    NodeData,
    NodeId,
    Page,
    PageId,
    Point,
    Project,
    Shadow,
    Stroke,
    Style,
    TextData,
    TokenId,
    Typography,
)
from ltechdesign.domain.schema import schemas

pytestmark = pytest.mark.core
ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/schema"


def fixture(name: str = "nested-v1.json") -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8-sig"))  # type: ignore[no-any-return]


def payloads(wrapper: dict[str, Any], *, rehash: bool = False) -> dict[str, bytes]:
    result = {p: json_bytes(v) for p, v in wrapper["members"].items()}
    result.update(
        {b["path"]: base64.b64decode(b["base64"], validate=True) for b in wrapper["asset_blobs"]}
    )
    if rehash:
        manifest = deepcopy(wrapper["members"]["manifest.json"])
        for entry in manifest["files"]:
            if entry["path"] in result:
                data = result[entry["path"]]
                entry.update(byte_length=len(data), sha256=hashlib.sha256(data).hexdigest())
        result["manifest.json"] = json_bytes(manifest)
    return result


@pytest.fixture
def project() -> Project:
    return load_project(payloads(fixture()))


def assert_matrix(actual: Matrix, expected: Matrix) -> None:
    for attr in ("a", "b", "c", "d", "tx", "ty"):
        assert getattr(actual, attr) == pytest.approx(getattr(expected, attr), abs=1e-9)


def test_model_without_qt_even_when_qt_imports_are_blocked() -> None:
    code = """
import sys
class BlockQt:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('PySide', 'PyQt', 'qtpy')):
            raise AssertionError(fullname)
sys.meta_path.insert(0, BlockQt())
from ltechdesign.domain import Document, dumps, loads
from ltechdesign.domain import geometry, migrations, schema
assert loads(Document, dumps(Document())).pages
assert not any(k.startswith(('PySide', 'PyQt', 'qtpy')) for k in sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("name", ["nested-v1.json", "legacy-00b.json"])
def test_repeated_roundtrip_preserves_semantics_and_stable_ids(name: str) -> None:
    original_payloads = payloads(fixture(name))
    original = current = load_project(original_payloads)
    blobs = {a.path: original_payloads[a.path] for a in original.assets.assets}
    for _ in range(3):
        encoded = dump_project(current, blobs)
        current = load_project(encoded)
        assert semantic_content(current) == semantic_content(original)
        assert current.document == original.document
        for key in current.document.nodes:
            assert_matrix(world_matrix(current.document, key), world_matrix(original.document, key))
        assert {p: encoded[p] for p in blobs} == blobs
    assert current.document.document_id == "doc-example"


def test_runtime_session_revision_and_immutable_snapshot(project: Project) -> None:
    first, second = DocumentSession(project=project), DocumentSession(project=project)
    assert first.session_id != second.session_id
    assert first.revision == second.revision == 0
    assert project.manifest.saved_revision == 12
    assert replace(first, revision=1).session_id == first.session_id
    with pytest.raises(ModelError, match="not_a_file_member"):
        dumps(first)
    with pytest.raises(ModelError, match="out_of_range"):
        replace(first, revision=-1)
    with pytest.raises(ModelError, match="out_of_range"):
        replace(first, revision=9007199254740992)
    with pytest.raises(FrozenInstanceError):
        project.document.name = "changed"  # type: ignore[misc]
    caller_nodes = dict(project.document.nodes)
    snapshot = replace(project.document, nodes=caller_nodes)
    caller_nodes.clear()
    assert snapshot.nodes == project.document.nodes
    with pytest.raises(TypeError):
        snapshot.nodes[NodeId("foo")] = next(iter(snapshot.nodes.values()))  # type: ignore[index]


@pytest.mark.parametrize(
    "kind",
    [
        "artboard",
        "frame",
        "group",
        "rectangle",
        "ellipse",
        "line",
        "polygon",
        "text",
        "image",
        "svg",
    ],
)
def test_create_defaults_and_typed_payloads(kind: Any) -> None:
    data: NodeData | None = None
    if kind == "text":
        data = TextData(typography=Typography(font_id=FontId("font-1")))
    elif kind in ("image", "svg"):
        data = MediaData(asset_id=AssetId("asset-1"))
    node = create_node(kind, PageId("page-1"), data=data)
    assert node.rotation == 0 and node.scale == 1 and node.opacity == 1
    assert node.visible and not node.locked
    assert node.clip_content == (kind == "artboard")
    assert node.pivot == Point(x=node.width / 2, y=node.height / 2)
    assert create_node(kind, PageId("page-1"), data=data).id != node.id
    assert len(node.id) == 36 and node.id == node.id.lower()


def test_typography_defaults_and_units() -> None:
    font = Typography(font_id=FontId("font-1"))
    assert font.font_size == 16 and font.letter_spacing == 0
    assert font.line_height == LineHeight(unit="multiplier", value=1.2)
    assert replace(font, line_height=LineHeight(unit="px", value=24)).line_height.value == 24
    assert font.sizing == "fixed"


@pytest.mark.parametrize(
    "field,value",
    [
        ("scale", 0),
        ("scale", -1),
        ("scale", [1, 2]),
        ("scale", True),
        ("x", float("nan")),
        ("y", float("inf")),
        ("rotation", float("-inf")),
        ("width", -1),
        ("width", 0),
        ("height", 0),
        ("opacity", -0.01),
        ("opacity", 1.01),
        ("x", "4"),
        ("x", 10**400),
        ("visible", 1),
        ("locked", "false"),
    ],
)
def test_numeric_and_boolean_invariants(field: str, value: Any) -> None:
    node = create_node("rectangle", PageId("page-1"))
    with pytest.raises(ModelError) as caught:
        replace(node, **{field: value})
    assert caught.value.code == "invalid_project"
    assert caught.value.path == "$." + field


@pytest.mark.parametrize("color", ["#fff", "#ffffffff", "#FFFFFF", "red", "#ZZZZZZFF", 2, None])
def test_color_invariants(color: Any) -> None:
    with pytest.raises(ModelError):
        Fill(color=color)


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (lambda d: d.update(session_id="runtime"), "unknown_property"),
        (lambda d: d.update(revision=1), "unknown_property"),
        (lambda d: d.update(schema_version="1.1"), "unsupported_version"),
        (lambda d: d.update(schema_version="2.0"), "unsupported_version"),
        (lambda d: d["pages"].append(deepcopy(d["pages"][0])), "duplicate_id"),
        (lambda d: d["pages"][0]["root_ids"].append("artboard-poster"), "duplicate_id"),
        (lambda d: d["pages"][0]["root_ids"].append("missing"), "missing_node"),
        (lambda d: d["pages"][0].update(root_ids=[]), "invalid_membership"),
        (lambda d: d["pages"][0]["root_ids"].append("text-title"), "root_ownership_mismatch"),
        (lambda d: d["nodes"]["text-title"].update(parent_id="artboard-web"), "parent_mismatch"),
        (lambda d: d["nodes"]["text-title"].update(parent_id="missing"), "missing_node"),
        (lambda d: d["nodes"]["text-title"].update(page_id="page-web"), "parent_mismatch"),
        (lambda d: d["nodes"]["text-title"].update(page_id="missing"), "missing_page"),
        (lambda d: d["nodes"]["text-title"].update(id="another"), "id_mismatch"),
        (lambda d: d["nodes"]["group-content"]["children"].append("missing"), "missing_node"),
        (lambda d: d["nodes"]["group-content"]["children"].append("text-title"), "duplicate_id"),
        (lambda d: d["nodes"]["group-content"].update(parent_id="frame-nested"), "hierarchy_cycle"),
        (
            lambda d: d["nodes"]["rectangle-card"].update(children=["text-title"]),
            "leaf_has_children",
        ),
        (lambda d: d["nodes"]["artboard-web"].update(parent_id="group-content"), "nested_artboard"),
        (lambda d: d["nodes"]["rectangle-card"].update(shear=0.2), "unknown_property"),
        (lambda d: d["nodes"]["group-content"].update(scale_x=2), "unknown_property"),
        (lambda d: d["nodes"]["group-content"].update(width=301), "group_geometry_mismatch"),
        (
            lambda d: d["nodes"]["group-content"]["style"].update(
                fill={"type": "solid", "color": "#FFFFFFFF"}
            ),
            "invalid_group_style",
        ),
        (
            lambda d: d["nodes"]["ellipse-overlap"]["style"].update(radius=[1, 1, 1, 1]),
            "invalid_radius_target",
        ),
        (lambda d: d["nodes"]["ellipse-overlap"].update(clip_content=True), "leaf_clip_content"),
        (
            lambda d: d["nodes"]["group-empty"].update(pivot={"x": 1, "y": 0}),
            "empty_group_geometry",
        ),
        (lambda d: d["nodes"]["line-horizontal"].update(width=99), "geometry_extent_mismatch"),
        (
            lambda d: d["nodes"]["line-horizontal"]["data"].update(end={"x": 0, "y": 0}),
            "degenerate_line",
        ),
        (
            lambda d: d["nodes"]["polygon-triangle"]["data"].update(points=[{"x": 0, "y": 0}]),
            "out_of_range",
        ),
        (
            lambda d: d["nodes"]["rectangle-card"].update(
                data={
                    "text": "wrong",
                    "typography": deepcopy(d["nodes"]["text-title"]["data"]["typography"]),
                }
            ),
            "invalid_node_payload",
        ),
    ],
)
def test_corrupt_document_rejected(mutation: Callable[[Any], None], reason: str) -> None:
    data = fixture()["members"]["document.json"]
    mutation(data)
    with pytest.raises(ModelError) as caught:
        from_data(Document, data)
    assert caught.value.reason == reason
    result = caught.value.to_dict()
    assert result["path"].startswith("$")
    assert set(result) == {"code", "reason", "path", "details"}


@pytest.mark.parametrize("member", list(MEMBER_TYPES))
def test_all_members_strict_fields_versions_and_roundtrip(member: str) -> None:
    data = fixture()["members"][member]
    cls = MEMBER_TYPES[member]
    assert loads(cls, dumps(from_data(cls, data))) == from_data(cls, data)
    unknown = deepcopy(data)
    unknown["future"] = True
    with pytest.raises(ModelError, match="unknown_property"):
        from_data(cls, unknown)
    missing = deepcopy(data)
    missing.pop(next(iter(data)))
    with pytest.raises(ModelError, match="missing_property"):
        from_data(cls, missing)
    version_key = "format_version" if member == "manifest.json" else "schema_version"
    data[version_key] = "9.9"
    with pytest.raises(ModelError) as caught:
        from_data(cls, data)
    assert caught.value.code == "unsupported_version"
    assert caught.value.details == {"actual": "9.9", "supported": ["1.0"]}


@pytest.mark.parametrize(
    "text,reason",
    [
        ('{"x":1,"x":2}', "duplicate_key"),
        ('{"x":{"y":1,"y":2}}', "duplicate_key"),
        ('{"x":NaN}', "nonfinite_number"),
        ('{"x":Infinity}', "nonfinite_number"),
        ('{"x":-Infinity}', "nonfinite_number"),
        ("\ufeff{}", "invalid_json"),
        ('{"x":1,}', "invalid_json"),
        ("/*comment*/{}", "invalid_json"),
    ],
)
def test_strict_json(text: str, reason: str) -> None:
    with pytest.raises(ModelError, match=reason):
        parse_json(text)


def test_json_limits_and_invalid_utf8() -> None:
    with pytest.raises(ModelError, match="json_bytes"):
        parse_json(b" " * (4 * 1024 * 1024 + 1))
    with pytest.raises(ModelError, match="json_depth"):
        parse_json("[" * 65 + "0" + "]" * 65)
    with pytest.raises(ModelError, match="invalid_json"):
        parse_json(b"\xff")
    with pytest.raises(ModelError, match="nonfinite_number"):
        parse_json('{"value":1e999}')
    with pytest.raises(ModelError, match="invalid_unicode"):
        Typography(font_id=FontId("f\ud800"))


def test_future_version_rejected_before_incompatible_shape() -> None:
    with pytest.raises(ModelError) as caught:
        from_data(Document, {"schema_version": "2.0", "new_representation": []})
    assert caught.value.code == "unsupported_version"
    assert caught.value.details["actual"] == "2.0"


def test_root_and_child_order_is_semantic_registry_order_is_not(project: Project) -> None:
    data = to_data(project.document)
    data["nodes"] = dict(reversed(list(data["nodes"].items())))
    assert from_data(Document, data) == project.document
    data["pages"][1]["root_ids"].reverse()
    reversed_roots = from_data(Document, data)
    assert reversed_roots != project.document
    assert loads(Document, dumps(reversed_roots)).pages[1].root_ids == (
        "root-foreground",
        "artboard-web",
    )
    data["nodes"]["frame-nested"]["children"].reverse()
    assert from_data(Document, data) != reversed_roots


def test_transform_order_pivot_and_relative_reparent(project: Project) -> None:
    node = replace(
        create_node("rectangle", PageId("p")),
        x=10,
        y=20,
        pivot=Point(x=3, y=4),
        rotation=90,
        scale=2,
    )
    matrix = local_matrix(node)
    assert matrix.point(node.pivot) == Point(x=13, y=24)
    assert matrix.point(Point(x=4, y=4)).x == pytest.approx(13)
    assert matrix.point(Point(x=4, y=4)).y == pytest.approx(26)
    child = project.document.nodes[NodeId("ellipse-overlap")]
    old_parent = world_matrix(project.document, NodeId("frame-nested"))
    new_parent = local_matrix(replace(node, rotation=-33, scale=0.7))
    moved = relative_node(child, old_parent, new_parent)
    assert_matrix(new_parent @ local_matrix(moved), old_parent @ local_matrix(child))
    assert_matrix(matrix.inverse() @ matrix, Matrix())


@pytest.mark.parametrize(
    "matrix",
    [
        Matrix(-1, 0, 0, 1),
        Matrix(1, 0, 0.3, 1),
        Matrix(2, 0, 0, 1),
        Matrix(0, 0, 0, 0),
        Matrix(1e-15, 0, 0, -1e-15),
    ],
)
def test_reject_affine_flip_shear_nonuniform_and_singular(matrix: Matrix) -> None:
    with pytest.raises(ModelError, match="unsupported_transform"):
        with_matrix(create_node("rectangle", PageId("p")), matrix)


def test_group_normalization_preserves_world_geometry(project: Project) -> None:
    group = project.document.nodes[NodeId("group-content")]
    children = tuple(project.document.nodes[key] for key in group.children)
    shifted = tuple(replace(child, x=child.x - 30, y=child.y + 17) for child in children)
    normalized, normalized_children = normalize_group(group, shifted, Bounds(-30, 17, 270, 137))
    for before, after in zip(shifted, normalized_children, strict=True):
        assert_matrix(
            local_matrix(group) @ local_matrix(before),
            local_matrix(normalized) @ local_matrix(after),
        )
    nodes = dict(project.document.nodes)
    nodes[normalized.id] = normalized
    nodes.update({n.id: n for n in normalized_children})
    document = replace(project.document, nodes=nodes)
    assert subtree_geometry_bounds(document, group.id) == Bounds(0, 0, 300, 120)


def test_group_resize_degenerate_line_and_hidden_geometry(project: Project) -> None:
    group = project.document.nodes[NodeId("group-line")]
    assert group.width == 0 and group.height == 50
    assert scale_group(group, 2).scale == 2
    assert scale_group(group, 2).children == group.children
    with pytest.raises(ModelError, match="unsupported_transform"):
        scale_group(group, 2, 3)
    with pytest.raises(ModelError, match="invalid_group_resize"):
        scale_group(project.document.nodes[NodeId("group-empty")], 2)
    nodes = dict(project.document.nodes)
    nodes[NodeId("rectangle-card")] = replace(nodes[NodeId("rectangle-card")], visible=False)
    hidden = replace(project.document, nodes=nodes)
    assert subtree_geometry_bounds(hidden, NodeId("group-content")) == Bounds(0, 0, 300, 120)
    assert visual_bounds(hidden, NodeId("rectangle-card")) is None


def test_geometry_visual_and_hit_bounds_are_distinct() -> None:
    line = create_node("line", PageId("p"), width=100, height=0, node_id=NodeId("line"))
    line = replace(line, style=Style(stroke=Stroke(width=2), shadows=(Shadow(offset_x=3, blur=2),)))
    doc = Document(pages=(Page(id=PageId("p"), root_ids=(line.id,)),), nodes={line.id: line})
    assert primitive_bounds(line) == Bounds(0, 0, 100, 0)
    assert visual_bounds(doc, line.id) == Bounds(-4, -7, 110, 7)
    assert hit_test_bounds(doc, line.id, tolerance_px=4, zoom=2, dpr=2) == Bounds(-5, -8, 111, 8)
    assert doc.nodes[line.id].height == 0
    with pytest.raises(ModelError):
        hit_test_bounds(doc, line.id, zoom=0)


def test_ellipse_uses_geometry_not_rotated_rectangle() -> None:
    ellipse = replace(create_node("ellipse", PageId("p"), width=100, height=100), rotation=45)
    bounds = primitive_bounds(ellipse, local_matrix(ellipse))
    assert bounds.width == pytest.approx(100)
    assert bounds.height == pytest.approx(100)


def test_ancestor_clipping_and_visibility(project: Project) -> None:
    child = NodeId("rectangle-overlap")
    frame = NodeId("frame-nested")
    bounds = visual_bounds(project.document, child)
    clip = primitive_bounds(project.document.nodes[frame], world_matrix(project.document, frame))
    assert bounds is not None and bounds.intersect(clip) == bounds
    nodes = dict(project.document.nodes)
    nodes[frame] = replace(nodes[frame], opacity=0)
    assert visual_bounds(replace(project.document, nodes=nodes), child) is None


def test_generated_fixture_schema_and_docs_do_not_drift() -> None:
    assert (FIXTURES / "nested-v1.json").read_bytes() == (
        ROOT / "docs/examples/ltechdesign-v1-contract.json"
    ).read_bytes()
    for name, schema in schemas().items():
        assert json.loads((ROOT / "docs/schemas" / name).read_text()) == schema
        assert json.loads((FIXTURES / "json-schema" / name).read_text()) == schema
        for definition in schema["$defs"].values():
            assert definition["additionalProperties"] is False
            assert set(definition["required"]) == set(definition["properties"])


def test_layout_configuration_is_validated_at_project_admission(project: Project) -> None:
    nodes = dict(project.document.nodes)
    key = NodeId("artboard-web")
    nodes[key] = replace(nodes[key], layout=Layout())
    doc = replace(project.document, nodes=nodes)
    assert loads(Document, dumps(doc)) == doc
    manifest = replace(
        project.manifest,
        required_capabilities=(*project.manifest.required_capabilities, "layout.stack/1"),
    )
    # Fixture contains transformed children: preserve the typed wire payload, but
    # reject this unsupported MVP layout rather than silently changing appearance.
    with pytest.raises(ModelError, match="layout_child_transform_unsupported"):
        replace(project, document=doc, manifest=manifest)
    nodes[key] = replace(nodes[key], layout=None, constraints=Constraints())
    with pytest.raises(ModelError, match="layout_constraints_require_frame"):
        replace(project, document=replace(doc, nodes=nodes))


def test_migration_registry_is_explicit_staged_and_validated() -> None:
    source = fixture()["members"]["document.json"]
    original = deepcopy(source)
    registry = document_migrations()
    result = registry.migrate(source, "1.0")
    assert not result.steps and result.payload == source and result.payload is not source
    with pytest.raises(ModelError, match="unsupported_version"):
        registry.migrate({"schema_version": "0.1"}, "1.0")
    with pytest.raises(ModelError, match="no_migration_path"):
        registry.migrate(source, "2.0")
    # Synthetic versions prove the registry; no native 0.x/2.x support is claimed.
    synthetic = MigrationRegistry()

    def validate(data: dict[str, Any]) -> None:
        if data["id"] != "stable-id":
            raise ModelError("lost_id")

    synthetic.register_version("old", validate)
    synthetic.register_version("new", validate)

    def upgrade(data: dict[str, Any]) -> dict[str, Any]:
        data["schema_version"] = "new"
        data["new_default"] = 0
        return data

    synthetic.register("old", "new", upgrade, description="Add explicit default")
    old = {"schema_version": "old", "id": "stable-id"}
    migrated = synthetic.migrate(old, "new")
    assert migrated.payload == {"schema_version": "new", "id": "stable-id", "new_default": 0}
    assert old == {"schema_version": "old", "id": "stable-id"}
    assert len(migrated.steps) == 1 and migrated.steps[0].description == "Add explicit default"
    with pytest.raises(ModelError, match="migration_cycle"):
        synthetic.register("new", "old", upgrade, description="Cycle")
    with pytest.raises(ModelError, match="invalid_migration_registration"):
        synthetic.register("old", "new", upgrade, description="Duplicate")
    assert source == original


def test_failed_migration_does_not_modify_source() -> None:
    registry = MigrationRegistry()
    registry.register_version("old", lambda _: None)
    registry.register_version("new", lambda _: (_ for _ in ()).throw(ModelError("invalid_result")))

    def broken(data: dict[str, Any]) -> dict[str, Any]:
        data["ids"].clear()
        data["schema_version"] = "new"
        return data

    registry.register("old", "new", broken, description="Fail validation")
    original = {"schema_version": "old", "ids": ["keep"]}
    with pytest.raises(ModelError, match="invalid_result"):
        registry.migrate(original, "new")
    assert original == {"schema_version": "old", "ids": ["keep"]}


def test_direct_nested_properties_are_validated() -> None:
    factories: list[Callable[[], object]] = [
        lambda: Crop(x=0.5, width=0.6),
        lambda: Stroke(width=0),
        lambda: Shadow(blur=-1),
        lambda: Style(radius=(0, 0, -1, 0)),
        lambda: Style(shadows=tuple(Shadow() for _ in range(9))),
        lambda: Typography(font_id=FontId("f"), font_weight=1001),
        lambda: Typography(font_id=FontId("f"), font_size=0),
        lambda: ColorToken(id=TokenId("bad/id"), name="", value="#FFFFFFFF"),
        lambda: Document(pages=()),
        lambda: replace(create_node("rectangle", PageId("p")), layout=Layout()),
        lambda: replace(
            create_node("rectangle", PageId("p")), data=MediaData(asset_id=AssetId("a"))
        ),
        lambda: LineHeight(value=0),
        lambda: Typography(font_id=FontId("f"), font_weight=0),
    ]
    for factory in factories:
        with pytest.raises(ModelError):
            factory()


def test_node_page_collision_and_disconnected_cycle() -> None:
    data = fixture()["members"]["document.json"]
    data["nodes"]["page-web"] = data["nodes"].pop("root-foreground")
    data["nodes"]["page-web"]["id"] = "page-web"
    data["pages"][1]["root_ids"][1] = "page-web"
    with pytest.raises(ModelError, match="id_mismatch"):
        from_data(Document, data)
    data = fixture()["members"]["document.json"]
    data["nodes"]["group-empty"].update(parent_id="group-empty", children=["group-empty"])
    data["nodes"]["artboard-web"]["children"].remove("group-empty")
    with pytest.raises(ModelError, match="hierarchy_cycle"):
        from_data(Document, data)


def test_all_fixture_core_objects_reject_unknown_properties() -> None:
    for member, source in fixture()["members"].items():
        paths: list[tuple[str | int, ...]] = []
        stack: list[tuple[Any, tuple[str | int, ...]]] = [(source, ())]
        while stack:
            value, path = stack.pop()
            if isinstance(value, dict):
                if path != ("nodes",):  # registry keys are NodeIds, not core property names
                    paths.append(path)
                stack.extend((child, (*path, key)) for key, child in value.items())
            elif isinstance(value, list):
                stack.extend((child, (*path, index)) for index, child in enumerate(value))
        for path in paths:
            broken = deepcopy(source)
            target = broken
            for key in path:
                target = target[key]
            target["unknown_future_property"] = 1
            with pytest.raises(ModelError, match="unknown_property"):
                from_data(MEMBER_TYPES[member], broken)
