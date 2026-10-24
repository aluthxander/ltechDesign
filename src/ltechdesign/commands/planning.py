"""Private mutable transaction draft; never exposed as a live document."""

from dataclasses import replace

from ltechdesign.domain.errors import fail
from ltechdesign.domain.geometry import (
    Bounds,
    Matrix,
    close,
    local_matrix,
    normalize_group,
    primitive_bounds,
    with_matrix,
)
from ltechdesign.domain.models import (
    AssetsIndex,
    Document,
    Fonts,
    InventoryEntry,
    Node,
    NodeId,
    PageId,
    Point,
    Project,
    create_node,
    new_id,
)
from ltechdesign.domain.validation import CONTAINERS

from .contracts import (
    Create,
    Delete,
    Duplicate,
    Group,
    Move,
    Operation,
    RegisterAsset,
    RemoveAsset,
    Reorder,
    Reparent,
    SetFont,
    SetStyle,
    SetText,
    SetTokens,
    Ungroup,
    Update,
)


class Draft:
    def __init__(self, project: Project) -> None:
        self.base = project
        self.nodes = dict(project.document.nodes)
        self.pages = {p.id: p for p in project.document.pages}
        self.tokens = project.tokens
        self.fonts = project.fonts
        self.assets = {a.id: a for a in project.assets.assets}
        self.id_map: list[tuple[NodeId, NodeId]] = []

    def node(self, key: NodeId) -> Node:
        if key not in self.nodes:
            fail("missing_node", node_id=key)
        return self.nodes[key]

    def siblings(self, page: PageId, parent: NodeId | None) -> tuple[NodeId, ...]:
        if page not in self.pages:
            fail("missing_page")
        if parent is None:
            return self.pages[page].root_ids
        node = self.node(parent)
        if node.page_id != page or node.type not in CONTAINERS:
            fail("invalid_parent")
        return node.children

    def set_siblings(self, page: PageId, parent: NodeId | None, ids: tuple[NodeId, ...]) -> None:
        if parent is None:
            self.pages[page] = replace(self.pages[page], root_ids=ids)
        else:
            node = self.node(parent)
            if node.type == "group" and not ids:
                # An empty group has canonical zero geometry; its world matrix is retained.
                node = with_matrix(
                    replace(node, children=(), width=0, height=0, pivot=Point()),
                    local_matrix(node),
                )
            self.nodes[parent] = replace(node, children=ids)

    def insert(self, node: Node, index: int | None) -> None:
        ids = self.siblings(node.page_id, node.parent_id)
        position = len(ids) if index is None else index
        if not 0 <= position <= len(ids):
            fail("invalid_index")
        self.set_siblings(
            node.page_id, node.parent_id, ids[:position] + (node.id,) + ids[position:]
        )

    def detach(self, node: Node) -> None:
        ids = self.siblings(node.page_id, node.parent_id)
        self.set_siblings(node.page_id, node.parent_id, tuple(k for k in ids if k != node.id))

    def subtree(self, key: NodeId) -> tuple[NodeId, ...]:
        result: list[NodeId] = []
        stack = [key]
        while stack:
            current = stack.pop()
            result.append(current)
            stack.extend(reversed(self.node(current).children))
        return tuple(result)

    def ancestors(self, key: NodeId | None) -> tuple[NodeId, ...]:
        chain: list[NodeId] = []
        while key is not None:
            if key in chain:
                fail("hierarchy_cycle")
            chain.append(key)
            key = self.node(key).parent_id
        return tuple(reversed(chain))

    def world(self, key: NodeId | None) -> Matrix:
        result = Matrix()
        for ancestor in self.ancestors(key):
            result = result @ local_matrix(self.node(ancestor))
        return result

    def context(self, key: NodeId | None) -> tuple[NodeId, ...]:
        return tuple(k for k in self.ancestors(key) if self.nontrivial(self.node(k)))

    @staticmethod
    def nontrivial(node: Node) -> bool:
        return (
            node.clip_content or node.opacity != 1 or not node.visible or bool(node.style.shadows)
        )

    def fresh(self, key: NodeId) -> None:
        if key in self.nodes or str(key) in self.pages:
            fail("duplicate_id")

    def apply(self, op: Operation) -> None:
        if isinstance(op, Create):
            self.fresh(op.node.id)
            if op.node.children:
                fail("create_requires_empty_children")
            # Resolve the destination BEFORE adding the node: self-parent must not
            # create a cyclic draft that a later subtree operation could traverse.
            self.siblings(op.node.page_id, op.node.parent_id)
            self.nodes[op.node.id] = op.node
            self.insert(op.node, op.index)
        elif isinstance(op, Update):
            old = self.node(op.node.id)
            for key in ("type", "page_id", "parent_id", "children"):
                if getattr(old, key) != getattr(op.node, key):
                    fail("structural_update_forbidden", field=key)
            if old.type == "group" and (old.width, old.height, old.pivot) != (
                op.node.width,
                op.node.height,
                op.node.pivot,
            ):
                fail("group_resize_requires_uniform_scale")
            self.nodes[old.id] = op.node
        elif isinstance(op, Delete):
            node = self.node(op.node_id)
            removed = set(self.subtree(node.id))
            self.detach(node)
            for key in removed:
                del self.nodes[key]
            self.tokens = replace(
                self.tokens,
                bindings=tuple(b for b in self.tokens.bindings if b.node_id not in removed),
            )
        elif isinstance(op, Move):
            node = self.node(op.node_id)
            self.nodes[node.id] = replace(node, x=node.x + op.dx, y=node.y + op.dy)
        elif isinstance(op, Reorder):
            node = self.node(op.node_id)
            self.detach(node)
            self.insert(node, op.index)
        elif isinstance(op, Reparent):
            node = self.node(op.node_id)
            self.siblings(op.page_id, op.parent_id)
            if op.parent_id in self.subtree(node.id):
                fail("hierarchy_cycle")
            if op.preserve_appearance and self.context(node.parent_id) != self.context(
                op.parent_id
            ):
                fail("ancestor_compositing_changes", code="unsupported_visual_preservation")
            moved = with_matrix(node, self.world(op.parent_id).inverse() @ self.world(node.id))
            self.detach(node)
            for key in self.subtree(node.id):
                self.nodes[key] = replace(self.nodes[key], page_id=op.page_id)
            moved = replace(moved, parent_id=op.parent_id, page_id=op.page_id)
            self.nodes[node.id] = moved
            self.insert(moved, op.index)
        elif isinstance(op, Group):
            self.group(op)
        elif isinstance(op, Ungroup):
            self.ungroup(op)
        elif isinstance(op, Duplicate):
            self.duplicate(op)
        elif isinstance(op, SetStyle):
            self.nodes[op.node_id] = replace(self.node(op.node_id), style=op.style)
        elif isinstance(op, SetText):
            self.nodes[op.node_id] = replace(self.node(op.node_id), data=op.data)
        elif isinstance(op, SetTokens):
            self.tokens = op.tokens
        elif isinstance(op, SetFont):
            fonts = {f.id: f for f in self.fonts.fonts}
            fonts[op.font.id] = op.font
            self.fonts = Fonts(fonts=tuple(fonts.values()))
        elif isinstance(op, RegisterAsset):
            if op.asset.id in self.assets:
                fail("duplicate_id")
            self.assets[op.asset.id] = op.asset
        elif isinstance(op, RemoveAsset):
            if op.asset_id not in self.assets:
                fail("missing_asset")
            del self.assets[op.asset_id]
        else:
            fail("unsupported_operation")

    def group(self, op: Group) -> None:
        self.fresh(op.group_id)
        if not op.node_ids or len(set(op.node_ids)) != len(op.node_ids):
            fail("invalid_group_membership")
        first = self.node(op.node_ids[0])
        ids = self.siblings(first.page_id, first.parent_id)
        selected = set(op.node_ids)
        if not selected <= set(ids) or any(self.node(k).type == "artboard" for k in selected):
            fail("group_requires_siblings")
        positions = [i for i, key in enumerate(ids) if key in selected]
        if op.preserve_appearance and positions[-1] - positions[0] + 1 != len(selected):
            fail("noncontiguous_stacking", code="unsupported_visual_preservation")
        children = tuple(k for k in ids if k in selected)
        group = replace(
            create_node("group", first.page_id, node_id=op.group_id),
            parent_id=first.parent_id,
            children=children,
            name=op.name,
        )
        self.nodes[group.id] = group
        for key in children:
            self.nodes[key] = replace(self.node(key), parent_id=group.id)
        remaining = tuple(k for k in ids[: positions[-1]] if k not in selected)
        remaining += (group.id,) + ids[positions[-1] + 1 :]
        self.set_siblings(first.page_id, first.parent_id, remaining)

    def ungroup(self, op: Ungroup) -> None:
        node = self.node(op.node_id)
        if node.type != "group":
            fail("not_a_group")
        if op.preserve_appearance and self.nontrivial(node):
            fail("group_compositing_changes", code="unsupported_visual_preservation")
        if any(b.node_id == node.id for b in self.tokens.bindings):
            fail("bound_group_ungroup_unsupported", code="unsupported_visual_preservation")
        for key in node.children:
            child = self.node(key)
            self.nodes[key] = replace(
                with_matrix(child, local_matrix(node) @ local_matrix(child)),
                parent_id=node.parent_id,
            )
        ids = self.siblings(node.page_id, node.parent_id)
        index = ids.index(node.id)
        self.set_siblings(
            node.page_id, node.parent_id, ids[:index] + node.children + ids[index + 1 :]
        )
        del self.nodes[node.id]

    def duplicate(self, op: Duplicate) -> None:
        if self.base.manifest.extensions:
            fail("extension_remap_unavailable", code="unsupported_capability")
        node = self.node(op.node_id)
        mapping = {key: NodeId(new_id()) for key in self.subtree(node.id)}
        for old, new in mapping.items():
            self.fresh(new)
            original = self.node(old)
            self.nodes[new] = replace(
                original,
                id=new,
                parent_id=(
                    mapping.get(original.parent_id, original.parent_id)
                    if original.parent_id is not None
                    else None
                ),
                children=tuple(mapping[k] for k in original.children),
            )
        root = self.nodes[mapping[node.id]]
        root = replace(root, x=root.x + op.dx, y=root.y + op.dy)
        self.nodes[root.id] = root
        self.insert(root, self.siblings(node.page_id, node.parent_id).index(node.id) + 1)
        self.tokens = replace(
            self.tokens,
            bindings=self.tokens.bindings
            + tuple(
                replace(b, node_id=mapping[b.node_id])
                for b in self.tokens.bindings
                if b.node_id in mapping
            ),
        )
        self.id_map.extend(mapping.items())

    def normalize(self) -> None:
        def visit(key: NodeId, depth: int) -> None:
            if depth > 64:
                fail("hierarchy_depth", code="limit_exceeded")
            node = self.node(key)
            for child_key in node.children:
                visit(child_key, depth + 1)
            node = self.node(key)
            if node.type == "group" and node.children:
                bounds: Bounds | None = None
                stack = [(k, local_matrix(self.node(k))) for k in node.children]
                while stack:
                    child_id, matrix = stack.pop()
                    child = self.node(child_id)
                    if child.type != "group" or not child.children:
                        current = primitive_bounds(child, matrix)
                        bounds = current if bounds is None else bounds.union(current)
                    stack.extend((k, matrix @ local_matrix(self.node(k))) for k in child.children)
                assert bounds is not None
                if all(
                    close(a, b)
                    for a, b in zip(bounds.extents, (0, 0, node.width, node.height), strict=True)
                ):
                    return
                normalized, children = normalize_group(
                    node, tuple(self.node(k) for k in node.children), bounds
                )
                self.nodes[key] = normalized
                self.nodes.update((c.id, c) for c in children)

        for page in self.pages.values():
            for key in page.root_ids:
                visit(key, 1)

    def finish(self) -> Project:
        self.normalize()
        document = Document(
            document_id=self.base.document.document_id,
            name=self.base.document.name,
            pages=tuple(self.pages.values()),
            nodes=self.nodes,
        )
        assets = AssetsIndex(assets=tuple(self.assets.values()))
        # Content inventory digests are regenerated by dump_project at serialization.
        inventory = {
            e.path: e for e in self.base.manifest.files if not e.path.startswith("assets/data/")
        }
        for asset in assets.assets:
            inventory[asset.path] = InventoryEntry(
                path=asset.path,
                media_type=asset.media_type,
                byte_length=asset.byte_length,
                sha256=asset.sha256,
            )
        # Declare the supported feature set, consistently for every committed snapshot.
        capabilities = set(self.base.manifest.required_capabilities)
        if self.tokens.bindings:
            capabilities.add("tokens.bindings/1")
        if any(a.media_type == "image/svg+xml" for a in assets.assets):
            capabilities.add("assets.svg/1")
        if any(f.source == "embedded" for f in self.fonts.fonts):
            capabilities.add("fonts.embedded/1")
        for node in self.nodes.values():
            if node.layout is not None or node.constraints is not None:
                fail("layout_evaluator_unavailable", code="unsupported_capability")
            if node.clip_content or (node.type in ("image", "svg") and any(node.style.radius)):
                capabilities.add("render.clipping/1")
            if node.type == "group" and node.opacity != 1:
                capabilities.add("render.isolated-opacity/1")
            if node.type == "svg":
                capabilities.add("assets.svg/1")
        manifest = replace(
            self.base.manifest,
            files=tuple(inventory.values()),
            required_capabilities=tuple(sorted(capabilities)),
            optional_capabilities=tuple(
                c for c in self.base.manifest.optional_capabilities if c not in capabilities
            ),
        )
        return replace(
            self.base,
            document=document,
            tokens=self.tokens,
            fonts=self.fonts,
            assets=assets,
            manifest=manifest,
        )
