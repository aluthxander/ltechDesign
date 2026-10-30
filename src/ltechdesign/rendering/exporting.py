"""Snapshot render plans for artboards and selected subtrees, with ancestor context."""

from dataclasses import dataclass, replace

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainterPath, QPainterPathStroker

from ltechdesign.domain.editing import selection_roots
from ltechdesign.domain.errors import fail
from ltechdesign.domain.geometry import Matrix, local_matrix, with_matrix
from ltechdesign.domain.models import Document, NodeId, Project
from ltechdesign.exports.contracts import ExportOptions, dimensions, filename

from .drawing import path, transform
from .text import Resources


@dataclass(frozen=True)
class RenderPlan:
    document: Document
    roots: tuple[NodeId, ...]
    bounds: QRectF
    width: int
    height: int
    name: str
    painted: frozenset[NodeId] | None
    context: frozenset[NodeId]

    def resources(self, base: Resources | None = None) -> Resources:
        return replace(
            base or Resources({}), render_nodes=self.painted, render_context=self.context
        )


def visual_envelope(
    document: Document, key: NodeId, painted: frozenset[NodeId], context: frozenset[NodeId]
) -> QPainterPath:
    """Conservative shadow envelope; real rounded ancestor clips, no screen hit padding."""
    from PySide6.QtCore import Qt

    node = document.nodes[key]
    result = QPainterPath()
    if (key not in painted and key not in context) or not node.visible or node.opacity == 0:
        return result
    if key in painted and node.type != "group":
        result = path(node)
        if node.style.stroke:
            stroke = QPainterPathStroker()
            stroke.setWidth(node.style.stroke.width)
            stroke.setCapStyle(Qt.PenCapStyle.SquareCap)
            stroke.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
            stroke.setMiterLimit(2)
            result = result.united(stroke.createStroke(result))
    for child in node.children:
        envelope = transform(local_matrix(document.nodes[child])).map(
            visual_envelope(document, child, painted, context)
        )
        if node.clip_content:
            envelope = envelope.intersected(path(node))
        result = result.united(envelope)
    source = result.boundingRect()
    if key in painted and not source.isEmpty():
        for shadow in node.style.shadows:
            pad = shadow.spread + 3 * shadow.blur
            envelope = QPainterPath()
            envelope.addRect(
                source.adjusted(-pad, -pad, pad, pad).translated(shadow.offset_x, shadow.offset_y)
            )
            result = result.united(envelope)
    return result


def plans(
    project: Project, options: ExportOptions, maximum: int = 64_000_000, max_outputs: int = 256
) -> tuple[RenderPlan, ...]:
    options.validate()
    document = project.document
    targets = options.target
    painted: frozenset[NodeId] | None = None
    context: frozenset[NodeId] = frozenset()
    entries: list[tuple[Document, tuple[NodeId, ...], QRectF, str, str, str]] = []
    if targets.kind == "selection":
        selected = selection_roots(document.nodes, targets.node_ids)
        if len({document.nodes[k].page_id for k in selected}) != 1:
            fail("selection_requires_one_page", code="validation_error")
        included: set[NodeId] = set()

        def visit(key: NodeId) -> None:
            included.add(key)
            for child in document.nodes[key].children:
                visit(child)

        for key in selected:
            visit(key)
        ancestors: set[NodeId] = set()
        for key in selected:
            parent = document.nodes[key].parent_id
            while parent is not None:
                ancestors.add(parent)
                parent = document.nodes[parent].parent_id
        kept = included | ancestors
        painted, context = frozenset(included), frozenset(ancestors)
        page = next(p for p in document.pages if p.id == document.nodes[selected[0]].page_id)
        roots = tuple(k for k in page.root_ids if k in kept)
        pruned = document
        envelope = QPainterPath()
        for key in roots:
            envelope = envelope.united(
                transform(local_matrix(document.nodes[key])).map(
                    visual_envelope(pruned, key, painted, context)
                )
            )
        entries.append(
            (pruned, roots, envelope.boundingRect(), page.name, "selection", "selection")
        )
    else:
        keys = [
            k
            for page in document.pages
            for k in page.root_ids
            if document.nodes[k].type == "artboard"
            and (
                targets.kind == "artboard"
                and k == targets.artboard_id
                or targets.kind == "all_artboards"
                and document.nodes[k].visible
            )
        ]
        if not keys:
            fail("artboard_not_found", code="validation_error")
        for key in keys:
            node = document.nodes[key]
            root = with_matrix(node, Matrix())
            page = next(p for p in document.pages if p.id == node.page_id)
            isolated = replace(document, nodes={**document.nodes, key: root})
            entries.append(
                (isolated, (key,), QRectF(0, 0, node.width, node.height), page.name, node.name, key)
            )
    if len(entries) > max_outputs:
        fail("export_output_count", code="limit_exceeded", maximum=max_outputs)
    result = []
    names = set()
    for index, (doc, roots, bounds, page_name, name, identifier) in enumerate(entries, 1):
        if targets.kind != "selection":
            included = set()
            pending = list(roots)
            while pending:
                key = pending.pop()
                included.add(key)
                pending.extend(doc.nodes[key].children)
            painted = frozenset(included)
        w, h = dimensions(bounds.width(), bounds.height(), options, maximum)
        output = filename(
            options,
            project=document.name,
            page=page_name,
            artboard=name,
            index=index,
            id=identifier,
        )
        if output.casefold() in names:
            fail("duplicate_output_name", code="validation_error", name=output)
        names.add(output.casefold())
        result.append(RenderPlan(doc, roots, bounds, w, h, output, painted, context))
    return tuple(result)
