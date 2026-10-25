"""Private mutable transaction draft; never exposed as a live document."""

from dataclasses import replace

from ltechdesign.domain.arrangement import translations
from ltechdesign.domain.editing import around, resized, selection_roots
from ltechdesign.domain.errors import fail
from ltechdesign.domain.geometry import (
    Bounds,
    Matrix,
    close,
    local_matrix,
    normalize_group,
    primitive_bounds,
    translation,
    with_matrix,
    world_matrix,
)
from ltechdesign.domain.inspector import inspected
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
from ltechdesign.domain.typography import changed as typography_changed
from ltechdesign.domain.validation import CONTAINERS

from .contracts import (
    ArrangeNodes,
    Create,
    CreatePage,
    Delete,
    DeletePage,
    Duplicate,
    DuplicatePage,
    EditNodes,
    Group,
    Move,
    Operation,
    PasteNodes,
    RegisterAsset,
    RelocateNodes,
    RemoveAsset,
    Reorder,
    Reparent,
    ReparentNodes,
    ResizeNode,
    ScaleNodes,
    SetFont,
    SetLayerState,
    SetProperties,
    SetStyle,
    SetText,
    SetTokens,
    SetTypography,
    TransformNodes,
    Ungroup,
    Update,
    UpdatePage,
)


class Draft:
    def __init__(self, project: Project) -> None:
        self.base = project
        self.nodes = dict(project.document.nodes)
        self.pages = {p.id: p for p in project.document.pages}
        self.tokens = project.tokens
        self.fonts = project.fonts
        self.assets = {a.id: a for a in project.assets.assets}
        self.workspace = project.workspace
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
        if isinstance(op, CreatePage):
            if op.page.id in self.pages or str(op.page.id) in self.nodes:
                fail("duplicate_id")
            if op.page.root_ids:
                fail("create_page_requires_empty_roots")
            pages = list(self.pages.items())
            index = len(pages) if op.index is None else op.index
            if not 0 <= index <= len(pages):
                fail("invalid_index")
            pages.insert(index, (op.page.id, op.page))
            self.pages = dict(pages)
        elif isinstance(op, UpdatePage):
            if op.page_id not in self.pages:
                fail("missing_page")
            self.pages[op.page_id] = replace(self.pages[op.page_id], name=op.name)
        elif isinstance(op, DuplicatePage):
            self.duplicate_page(op)
        elif isinstance(op, DeletePage):
            if op.page_id not in self.pages:
                fail("missing_page")
            if len(self.pages) == 1:
                fail("cannot_delete_last_page")
            deleted_page = self.pages[op.page_id]
            if deleted_page.root_ids and not op.delete_contents:
                fail("page_contents_require_explicit_delete")
            previous_index = list(self.pages).index(deleted_page.id)
            for key in deleted_page.root_ids:
                self.apply(Delete(node_id=key))
            del self.pages[deleted_page.id]
            if self.workspace:
                active = self.workspace.active_page_id
                if active == deleted_page.id:
                    active = list(self.pages)[min(previous_index, len(self.pages) - 1)]
                self.workspace = replace(
                    self.workspace,
                    active_page_id=active,
                    views=tuple(v for v in self.workspace.views if v.page_id != deleted_page.id),
                )
        elif isinstance(op, SetLayerState):
            self.selected_roots(
                op.node_ids
            )  # validates IDs/budget; flags apply to each explicit ID
            if op.visible is None and op.locked is None:
                fail("empty_layer_state")
            for key in op.node_ids:
                node = self.node(key)
                self.nodes[key] = replace(
                    node,
                    visible=node.visible if op.visible is None else op.visible,
                    locked=node.locked if op.locked is None else op.locked,
                )
        elif isinstance(op, RelocateNodes):
            self.relocate(op)
        elif isinstance(op, ScaleNodes):
            matrix = around(op.center, factor=op.factor)
            for key in self.selected_roots(op.node_ids):
                node = self.node(key)
                old_world = self.world(key)
                desired = matrix @ old_world
                if node.type in ("frame", "artboard"):
                    if any(
                        self.node(k).layout or self.node(k).constraints for k in self.subtree(key)
                    ):
                        fail("layout_evaluator_unavailable", code="unsupported_capability")
                    node = resized(node, node.width * op.factor, node.height * op.factor, Point())
                    desired = Matrix(
                        old_world.a, old_world.b, old_world.c, old_world.d, desired.tx, desired.ty
                    )
                self.nodes[key] = with_matrix(node, self.world(node.parent_id).inverse() @ desired)
        elif isinstance(op, ArrangeNodes):
            self.normalize()
            document = replace(
                self.base.document, nodes=self.nodes, pages=tuple(self.pages.values())
            )
            for key, delta in translations(document, op.node_ids, op.mode):
                node = self.node(key)
                self.nodes[key] = with_matrix(
                    node,
                    self.world(node.parent_id).inverse()
                    @ translation(delta.x, delta.y)
                    @ world_matrix(document, key),
                )
        elif isinstance(op, TransformNodes):
            op.matrix.similarity_scale()
            for key in self.selected_roots(op.node_ids):
                node = self.node(key)
                self.nodes[key] = with_matrix(
                    node, self.world(node.parent_id).inverse() @ op.matrix @ self.world(key)
                )
        elif isinstance(op, ResizeNode):
            node = self.node(op.node_id)
            if any(self.node(k).layout or self.node(k).constraints for k in self.subtree(node.id)):
                fail("layout_evaluator_unavailable", code="unsupported_capability")
            self.nodes[node.id] = resized(node, op.width, op.height, op.anchor)
        elif isinstance(op, EditNodes):
            keys = self.selected_roots(op.node_ids)
            if op.edit in ("forward", "backward"):
                selected = set(keys)
                parents = {(self.node(k).page_id, self.node(k).parent_id) for k in keys}
                for page, parent in parents:
                    ids = list(self.siblings(page, parent))
                    indices = (
                        range(len(ids) - 2, -1, -1) if op.edit == "forward" else range(1, len(ids))
                    )
                    for i in indices:
                        j = i + 1 if op.edit == "forward" else i - 1
                        if ids[i] in selected and ids[j] not in selected:
                            ids[i], ids[j] = ids[j], ids[i]
                    self.set_siblings(page, parent, tuple(ids))
            else:
                for key in keys:
                    if op.edit == "delete":
                        self.apply(Delete(node_id=key))
                    elif op.edit == "ungroup":
                        self.apply(Ungroup(node_id=key))
                    else:
                        node = self.node(key)
                        parent_world = self.world(node.parent_id)
                        delta = parent_world.inverse().point(
                            Point(x=parent_world.tx + 10, y=parent_world.ty + 10)
                        )
                        self.apply(Duplicate(node_id=key, dx=delta.x, dy=delta.y))
        elif isinstance(op, ReparentNodes):
            for key in self.selected_roots(op.node_ids):
                self.apply(Reparent(node_id=key, page_id=op.page_id, parent_id=op.parent_id))
        elif isinstance(op, PasteNodes):
            incoming = op.project
            if incoming.manifest.extensions or len(incoming.document.pages) != 1:
                fail("unsupported_clipboard_project")
            self.siblings(op.page_id, op.parent_id)
            for asset in incoming.assets.assets:
                if self.assets.get(asset.id) != asset:
                    fail("missing_staged_asset")
            for font in incoming.fonts.fonts:
                if any(f.id == font.id for f in self.fonts.fonts):
                    fail("duplicate_id")
            self.fonts = replace(self.fonts, fonts=self.fonts.fonts + incoming.fonts.fonts)
            if {t.id for t in self.tokens.tokens} & {t.id for t in incoming.tokens.tokens}:
                fail("duplicate_id")
            self.tokens = replace(
                self.tokens,
                tokens=self.tokens.tokens + incoming.tokens.tokens,
                bindings=self.tokens.bindings + incoming.tokens.bindings,
            )
            for key, node in incoming.document.nodes.items():
                self.fresh(key)
                self.nodes[key] = replace(node, page_id=op.page_id)
            for key in incoming.document.pages[0].root_ids:
                node = self.node(key)
                moved = with_matrix(
                    node,
                    self.world(op.parent_id).inverse()
                    @ translation(op.offset.x, op.offset.y)
                    @ local_matrix(node),
                )
                moved = replace(moved, parent_id=op.parent_id)
                self.nodes[key] = moved
                self.insert(moved, None)
        elif isinstance(op, Create):
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
            for field in ("type", "page_id", "parent_id", "children"):
                if getattr(old, field) != getattr(op.node, field):
                    fail("structural_update_forbidden", field=field)
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
        elif isinstance(op, SetProperties):
            self.selected_roots(op.node_ids)  # validates explicit targets and selection budget
            for key in op.node_ids:
                node = self.node(key)
                if op.property in ("width", "height") and any(
                    self.node(k).layout or self.node(k).constraints for k in self.subtree(key)
                ):
                    fail("layout_evaluator_unavailable", code="unsupported_capability")
                self.nodes[key] = inspected(node, op.property, op.value)
        elif isinstance(op, SetStyle):
            self.nodes[op.node_id] = replace(self.node(op.node_id), style=op.style)
        elif isinstance(op, SetText):
            self.nodes[op.node_id] = replace(self.node(op.node_id), data=op.data)
        elif isinstance(op, SetTypography):
            self.selected_roots(op.node_ids)
            for key in op.node_ids:
                self.nodes[key] = typography_changed(self.node(key), op.property, op.value)
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

    def selected_roots(self, keys: tuple[NodeId, ...]) -> tuple[NodeId, ...]:
        # Use the current draft graph (also valid after prior operations in the batch).
        return selection_roots(self.nodes, keys)

    def duplicate_page(self, op: DuplicatePage) -> None:
        if op.page_id not in self.pages:
            fail("missing_page")
        if self.base.manifest.extensions:
            fail("extension_remap_unavailable", code="unsupported_capability")
        source = self.pages[op.page_id]
        page = replace(
            source,
            id=op.new_page_id,
            name=op.name if op.name is not None else source.name + " copy",
            root_ids=(),
        )
        self.apply(CreatePage(page=page, index=list(self.pages).index(source.id) + 1))
        keys = tuple(k for root in source.root_ids for k in self.subtree(root))
        mapping = {key: NodeId(new_id()) for key in keys}
        for key, new_key in mapping.items():
            self.fresh(new_key)
            original = self.node(key)
            self.nodes[new_key] = replace(
                original,
                id=new_key,
                page_id=page.id,
                parent_id=mapping[original.parent_id] if original.parent_id is not None else None,
                children=tuple(mapping[k] for k in original.children),
            )
        self.pages[page.id] = replace(page, root_ids=tuple(mapping[k] for k in source.root_ids))
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

    def relocate(self, op: RelocateNodes) -> None:
        roots = self.selected_roots(op.node_ids)
        order = {
            key: i
            for i, key in enumerate(
                k for p in self.pages.values() for root in p.root_ids for k in self.subtree(root)
            )
        }
        keys = tuple(sorted(roots, key=lambda k: order[k]))
        destination = self.siblings(op.page_id, op.parent_id)
        remaining = tuple(k for k in destination if k not in keys)
        index = len(remaining) if op.index is None else op.index
        if not 0 <= index <= len(remaining):
            fail("invalid_index")
        matrices = {k: self.world(k) for k in keys}
        for key in keys:
            node = self.node(key)
            if op.parent_id in self.subtree(key):
                fail("hierarchy_cycle")
            if node.type == "artboard" and op.parent_id is not None:
                fail("nested_artboard")
            if op.preserve_appearance and self.context(node.parent_id) != self.context(
                op.parent_id
            ):
                fail("ancestor_compositing_changes", code="unsupported_visual_preservation")
        for key in keys:
            self.detach(self.node(key))
        inverse = self.world(op.parent_id).inverse()
        for offset, key in enumerate(keys):
            node = with_matrix(self.node(key), inverse @ matrices[key])
            for descendant in self.subtree(key):
                self.nodes[descendant] = replace(self.node(descendant), page_id=op.page_id)
            node = replace(node, page_id=op.page_id, parent_id=op.parent_id)
            self.nodes[key] = node
            self.insert(node, index + offset)

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
            workspace=self.workspace,
        )
