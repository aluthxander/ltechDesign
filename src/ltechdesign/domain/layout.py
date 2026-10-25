"""Deterministic stack/parent constraints. No scene, fonts, widgets or I/O.

Dimensions form a directed graph (including wrapped text height -> width).
Resolve that graph once, then place children in stored order. See ADR 0025.
"""

from collections.abc import Callable, Mapping
from dataclasses import replace

from .editing import MIN_SIZE, resized
from .errors import fail
from .models import Node, NodeId, Point, Project, Sizing, TextData

Axis = int
Dimension = tuple[NodeId, Axis]


def mode(node: Node, axis: Axis) -> Sizing:
    source = node.layout or node.constraints
    if source is None:
        return "fixed"
    return source.sizing_x if axis == 0 else source.sizing_y


def extent(node: Node, axis: Axis) -> float:
    return node.width if axis == 0 else node.height


def main_axis(node: Node) -> Axis:
    assert node.layout is not None
    return 0 if node.layout.direction == "horizontal" else 1


def padding(node: Node, axis: Axis) -> tuple[float, float]:
    assert node.layout is not None
    top, right, bottom, left = node.layout.padding
    return (left, right) if axis == 0 else (top, bottom)


def fills(nodes: Mapping[NodeId, Node], node: Node, axis: Axis) -> bool:
    parent = nodes.get(node.parent_id) if node.parent_id else None
    if parent and parent.layout:
        return mode(node, axis) == "fill" or (
            axis != main_axis(parent) and parent.layout.align_cross == "stretch"
        )
    constraints = node.constraints
    anchor = (
        (constraints.horizontal if axis == 0 else constraints.vertical) if constraints else "start"
    )
    return mode(node, axis) == "fill" or anchor == "stretch"


def dependencies(nodes: Mapping[NodeId, Node], node: Node, axis: Axis) -> list[Dimension]:
    if fills(nodes, node, axis):
        if node.parent_id is None:
            fail("layout_fill_requires_parent", node_id=node.id)
        parent = nodes[node.parent_id]
        if parent.layout and main_axis(parent) == axis:
            # One shared remaining-space dependency for all fill siblings.
            return [(parent.id, axis + 2)]
        return [(parent.id, axis)]
    if node.layout and mode(node, axis) == "hug":
        return [(key, axis) for key in node.children]
    if isinstance(node.data, TextData) and axis == 1:
        if node.data.typography.sizing == "auto_height":
            return [(node.id, 0)]
    return []


def validate_configuration(nodes: Mapping[NodeId, Node]) -> None:
    """Validate the supported subset and graph also on native-file admission."""
    for node in nodes.values():
        parent = nodes.get(node.parent_id) if node.parent_id else None
        managed = bool((parent and parent.layout) or node.constraints)
        if managed and node.type == "group":
            fail("layout_group_unsupported", code="unsupported_capability", node_id=node.id)
        if managed and (node.rotation % 360 != 0 or node.scale != 1):
            fail(
                "layout_child_transform_unsupported", code="unsupported_capability", node_id=node.id
            )
        if (
            node.layout
            and node.constraints
            and (node.constraints.sizing_x != "fixed" or node.constraints.sizing_y != "fixed")
        ):
            fail("layout_sizing_belongs_to_stack", node_id=node.id)
        for axis in (0, 1):
            sizing = mode(node, axis)
            fill = fills(nodes, node, axis)
            if fill and sizing == "hug":
                fail("layout_hug_stretch_conflict", node_id=node.id)
            if (fill or sizing == "hug") and node.type in ("group", "line", "polygon"):
                fail("layout_intrinsic_geometry_unsupported", code="unsupported_capability")
            if sizing == "hug" and not node.layout:
                if (
                    not isinstance(node.data, TextData)
                    or (axis == 0 and node.data.typography.sizing != "auto_width")
                    or (axis == 1 and node.data.typography.sizing == "fixed")
                ):
                    fail("layout_hug_requires_stack_or_auto_text", node_id=node.id)
            if isinstance(node.data, TextData) and fill:
                text_mode = node.data.typography.sizing
                if text_mode == "auto_width" or (axis == 1 and text_mode == "auto_height"):
                    fail("layout_text_sizing_conflict", node_id=node.id)
            if fill and parent and not parent.layout and parent.type not in ("frame", "artboard"):
                fail("layout_constraints_require_frame", node_id=node.id)
        if node.constraints and (parent is None or parent.type not in ("frame", "artboard")):
            fail("layout_constraints_require_frame", node_id=node.id)

    done: set[Dimension] = set()
    active: set[Dimension] = set()

    def visit(key: Dimension) -> None:
        if key in active:
            fail("layout_dependency_cycle", node_id=key[0], axis=key[1])
        if key in done:
            return
        active.add(key)
        node, axis = nodes[key[0]], key[1]
        deps = (
            [(node.id, axis - 2)]
            + [
                (child, axis - 2)
                for child in node.children
                if not fills(nodes, nodes[child], axis - 2)
            ]
            if axis >= 2
            else dependencies(nodes, node, axis)
        )
        for dep in deps:
            visit(dep)
        active.remove(key)
        done.add(key)

    for key in nodes:
        for axis in (0, 1):
            visit((key, axis))


def recalculate(
    before: Project,
    planned: Project,
    measure: Callable[[Node], Node] | None = None,
) -> Mapping[NodeId, Node]:
    nodes = planned.document.nodes
    if not any(n.layout or n.constraints for n in nodes.values()):
        return nodes
    validate_configuration(nodes)
    values: dict[Dimension, float] = {}
    measured: dict[NodeId, Node] = {}
    budgets: dict[Dimension, float] = {}

    def parent_delta(node: Node, axis: Axis) -> float:
        assert node.parent_id is not None
        old = before.document.nodes.get(node.id)
        old_parent = before.document.nodes.get(node.parent_id)
        baseline = (
            extent(old_parent, axis)
            if old and old.parent_id == node.parent_id and old_parent
            else extent(nodes[node.parent_id], axis)
        )
        return dimension(node.parent_id, axis) - baseline

    def dimension(key: NodeId, axis: Axis) -> float:
        pair = (key, axis)
        if pair in values:
            return values[pair]
        node = nodes[key]
        parent = nodes.get(node.parent_id) if node.parent_id else None
        if fills(nodes, node, axis):
            assert parent is not None
            if parent.layout:
                start, end = padding(parent, axis)
                available = dimension(parent.id, axis) - start - end
                if axis == main_axis(parent):
                    budget_key = (parent.id, axis)
                    if budget_key not in budgets:
                        fixed = sum(
                            dimension(k, axis)
                            for k in parent.children
                            if not fills(nodes, nodes[k], axis)
                        )
                        count = sum(fills(nodes, nodes[k], axis) for k in parent.children)
                        budgets[budget_key] = (
                            available - fixed - parent.layout.gap * (len(parent.children) - 1)
                        ) / count
                    available = budgets[budget_key]
                result = max(MIN_SIZE, available)
            else:
                result = max(MIN_SIZE, extent(node, axis) + parent_delta(node, axis))
        elif node.layout and mode(node, axis) == "hug":
            start, end = padding(node, axis)
            sizes = [dimension(k, axis) for k in node.children]
            content = (
                sum(sizes) + node.layout.gap * max(0, len(sizes) - 1)
                if axis == main_axis(node)
                else max(sizes, default=0)
            )
            result = max(MIN_SIZE, start + content + end)
        elif (
            isinstance(node.data, TextData)
            and axis == 1
            and node.data.typography.sizing == "auto_height"
        ):
            width = dimension(key, 0)
            if width != node.width:
                if measure is None:
                    fail("text_metrics_required", code="unsupported_capability")
                measured[key] = measure(replace(node, width=width))
            result = measured[key].height if key in measured else node.height
        else:
            result = extent(node, axis)
        values[pair] = result
        return result

    # Resolve all sizes before position; axis iteration/order cannot change results.
    for key in nodes:
        dimension(key, 0)
        dimension(key, 1)
    changed = dict(nodes)
    for key, node in nodes.items():
        width, height = values[key, 0], values[key, 1]
        if (width, height) != (node.width, node.height):
            # Preserve auto typography: resizing here is evaluation, not user resize intent.
            changed[key] = replace(resized(node, width, height, Point()), data=node.data)
        parent = nodes.get(node.parent_id) if node.parent_id else None
        if node.constraints and parent and not parent.layout:
            c = node.constraints
            dx, dy = parent_delta(node, 0), parent_delta(node, 1)
            changed[key] = replace(
                changed[key],
                x=node.x
                + (dx if c.horizontal == "end" else dx / 2 if c.horizontal == "center" else 0),
                y=node.y + (dy if c.vertical == "end" else dy / 2 if c.vertical == "center" else 0),
            )
    for key, parent in nodes.items():
        layout = parent.layout
        if layout is None:
            continue
        main = main_axis(parent)
        cross = 1 - main
        lead, trail = padding(parent, main)
        cross_lead, cross_trail = padding(parent, cross)
        occupied = sum(values[k, main] for k in parent.children) + layout.gap * max(
            0, len(parent.children) - 1
        )
        spare = max(0, values[key, main] - lead - trail - occupied)
        cursor = lead + (
            spare
            if layout.align_main == "end"
            else spare / 2
            if layout.align_main == "center"
            else 0
        )
        for child_key in parent.children:
            child = changed[child_key]
            spare_cross = max(
                0, values[key, cross] - cross_lead - cross_trail - values[child_key, cross]
            )
            position = cross_lead + (
                spare_cross
                if layout.align_cross == "end"
                else spare_cross / 2
                if layout.align_cross == "center"
                else 0
            )
            changed[child_key] = replace(
                child, x=cursor if main == 0 else position, y=position if main == 0 else cursor
            )
            cursor += values[child_key, main] + layout.gap
    return changed
