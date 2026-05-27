bl_info = {
    "name": "Align_Node",
    "author": "Anthem",
    "maintainer": "Anthem",
    "version": (1, 10, 18),
    "blender": (5, 1, 1),
    "location": "Node Editor > Command/Ctrl + Arrow Keys",
    "description": "Align selected nodes with configurable PureRef style shortcuts.",
    "category": "Node",
}

import bpy
import platform
from bpy.types import AddonPreferences, Operator
from bpy.props import BoolProperty, EnumProperty, FloatProperty


BASE_GAP = 24.0
SAFETY_GAP = 5.0
FRAME_INNER_MARGIN = 40.0
FALLBACK_HEIGHT = 120.0
COMPACT_NODE_HEIGHT = 76.0
DIMENSIONS_SCALE = 0.5
MAX_STABILIZE_PASSES = 12
POSITION_EPSILON = 0.001

ADDON_ID = __package__ or __name__
addon_keymaps = []
debug_alignment_lines = []


def vector_xy(value):
    if value is None:
        return None
    return (float(getattr(value, "x", 0.0)), float(getattr(value, "y", 0.0)))


def node_location_absolute(node):
    absolute = getattr(node, "location_absolute", None)
    if absolute is None:
        return None
    return vector_xy(absolute)


def format_xy(value):
    if value is None:
        return "None"
    return f"x={value[0]:.3f}, y={value[1]:.3f}"


def append_alignment_debug(lines):
    debug_alignment_lines.clear()
    debug_alignment_lines.extend(lines)


def use_command_key():
    return platform.system() == "Darwin"


def default_ctrl():
    return not use_command_key()


def default_shift():
    return True


def key_items():
    return (
        ("LEFT_ARROW", "Left Arrow", ""),
        ("RIGHT_ARROW", "Right Arrow", ""),
        ("UP_ARROW", "Up Arrow", ""),
        ("DOWN_ARROW", "Down Arrow", ""),
        ("A", "A", ""),
        ("D", "D", ""),
        ("W", "W", ""),
        ("S", "S", ""),
        ("H", "H", ""),
        ("J", "J", ""),
        ("K", "K", ""),
        ("L", "L", ""),
        ("NUMPAD_4", "Numpad 4", ""),
        ("NUMPAD_6", "Numpad 6", ""),
        ("NUMPAD_8", "Numpad 8", ""),
        ("NUMPAD_2", "Numpad 2", ""),
    )


def gap_size():
    preferences = get_preferences()
    if preferences is None:
        return BASE_GAP + SAFETY_GAP
    return max(0.0, float(preferences.gap)) + SAFETY_GAP


def frame_inner_margin():
    return max(gap_size(), FRAME_INNER_MARGIN)


def node_width(node):
    dimensions = getattr(node, "dimensions", None)
    dimension_width = getattr(dimensions, "x", 0.0) if dimensions else 0.0
    width = getattr(node, "width", 0.0)
    fallback_width = float(width) if width else 140.0
    if is_frame_node(node):
        return fallback_width
    if dimension_width and dimension_width > 1.0:
        if dimension_width <= fallback_width * 1.25:
            return float(dimension_width)
        return float(dimension_width) * DIMENSIONS_SCALE
    return fallback_width


def node_height(node):
    dimensions = getattr(node, "dimensions", None)
    dimension_height = getattr(dimensions, "y", 0.0) if dimensions else 0.0
    height = getattr(node, "height", 0.0)
    fallback_height = float(height) if height and height > 1.0 else FALLBACK_HEIGHT
    if is_frame_node(node):
        return fallback_height
    if dimension_height and dimension_height > 1.0:
        if is_compact_header_node(node, dimension_height):
            return COMPACT_NODE_HEIGHT
        if dimension_height <= FALLBACK_HEIGHT:
            return float(dimension_height)
        return float(dimension_height) * DIMENSIONS_SCALE
    return fallback_height


def is_compact_header_node(node, dimension_height):
    return (
        dimension_height <= 100.0
        and getattr(node, "bl_idname", "") in {"GeometryNodeInputPosition"}
    )


def is_frame_node(node):
    return getattr(node, "bl_idname", "") == "NodeFrame" or getattr(node, "type", "") == "FRAME"


def edges(node):
    return box_at(node)


def box_at(node, x=None, y=None):
    left = float(node.location.x if x is None else x)
    top = float(node.location.y if y is None else y)
    width = node_width(node)
    height = node_height(node)
    return {
        "left": left,
        "right": left + width,
        "top": top,
        "bottom": top - height,
        "width": width,
        "height": height,
    }


def boxes_too_close(a, b, gap=0.0):
    separated_x = a["right"] + gap <= b["left"] or b["right"] + gap <= a["left"]
    separated_y = a["bottom"] >= b["top"] + gap or b["bottom"] >= a["top"] + gap
    return not (separated_x or separated_y)


def vertical_ranges_overlap(a, b):
    return not (a["bottom"] >= b["top"] or b["bottom"] >= a["top"])


def horizontal_ranges_overlap(a, b):
    return not (a["right"] <= b["left"] or b["right"] <= a["left"])


def boxes_conflict_for_axis(candidate_box, other_box, axis, gap):
    if axis == "X" and not vertical_ranges_overlap(candidate_box, other_box):
        return False
    if axis == "Y" and not horizontal_ranges_overlap(candidate_box, other_box):
        return False
    return boxes_too_close(candidate_box, other_box, gap)


def boxes_conflict_for_axis_with_frames(candidate_box, other_node, other_box, axis, gap):
    if axis == "X" and is_frame_node(other_node):
        separated_x = (
            candidate_box["right"] + gap <= other_box["left"]
            or other_box["right"] + gap <= candidate_box["left"]
        )
        return not separated_x
    return boxes_conflict_for_axis(candidate_box, other_box, axis, gap)


def first_non_overlapping_position(node, box, placed, candidates, axis, gap, conflict_function=boxes_conflict_for_axis):
    for candidate in candidates:
        candidate_box = box_at(
            node,
            x=candidate if axis == "X" else box["left"],
            y=candidate if axis == "Y" else box["top"],
        )
        if not any(conflict_function(candidate_box, edges(other), axis, gap) for other in placed):
            return candidate
    return candidates[-1]


def align_left(nodes, target_left=None):
    if target_left is None:
        target_left = min(edges(node)["left"] for node in nodes)
    original = {node: edges(node) for node in nodes}
    ordered = sorted(nodes, key=lambda node: (original[node]["left"], -original[node]["top"]))
    placed = []

    for node in ordered:
        box = original[node]
        gap = gap_size()
        path_limit = target_left
        for other, other_box in original.items():
            if other is node:
                continue
            if original[other]["left"] < box["left"] and vertical_ranges_overlap(box, other_box):
                path_limit = max(path_limit, original[other]["right"] + gap)
        candidates = sorted({path_limit, *(edges(other)["right"] + gap for other in placed)})
        while True:
            candidate = first_non_overlapping_position(node, box, placed, candidates, "X", gap)
            candidate_box = box_at(node, x=candidate, y=box["top"])
            blockers = [edges(other) for other in placed if boxes_conflict_for_axis(candidate_box, edges(other), "X", gap)]
            if not blockers:
                node.location.x = candidate
                break
            candidates.append(max(other["right"] + gap for other in blockers))
            candidates = sorted(set(candidates))
        placed.append(node)


def align_right(nodes, target_right=None):
    if target_right is None:
        target_right = max(edges(node)["right"] for node in nodes)
    original = {node: edges(node) for node in nodes}
    ordered = sorted(nodes, key=lambda node: (-original[node]["right"], -original[node]["top"]))
    placed = []

    for node in ordered:
        box = original[node]
        gap = gap_size()
        path_limit = target_right - box["width"]
        for other in placed:
            other_box = original[other]
            if other_box["right"] > box["right"] and vertical_ranges_overlap(box, other_box):
                path_limit = min(path_limit, edges(other)["left"] - gap - box["width"])

        candidates = sorted(
            {
                candidate
                for candidate in {path_limit, *(edges(other)["left"] - gap - box["width"] for other in placed)}
                if candidate <= path_limit
            },
            reverse=True,
        )
        while True:
            candidate = first_non_overlapping_position(node, box, placed, candidates, "X", gap)
            candidate_box = box_at(node, x=candidate, y=box["top"])
            blockers = [edges(other) for other in placed if boxes_conflict_for_axis(candidate_box, edges(other), "X", gap)]
            if not blockers:
                node.location.x = candidate
                break
            candidates.append(min(other["left"] - gap - box["width"] for other in blockers))
            candidates = sorted(set(candidates), reverse=True)
        placed.append(node)


def align_up(nodes, target_top=None):
    if target_top is None:
        target_top = max(edges(node)["top"] for node in nodes)
    original = {node: edges(node) for node in nodes}
    ordered = sorted(nodes, key=lambda node: (-original[node]["top"], original[node]["left"]))
    placed = []

    for node in ordered:
        box = original[node]
        gap = gap_size()
        path_limit = target_top
        for other in placed:
            other_box = original[other]
            if other_box["top"] > box["top"] and horizontal_ranges_overlap(box, other_box):
                path_limit = min(path_limit, edges(other)["bottom"] - gap)
        candidates = sorted({path_limit, *(edges(other)["bottom"] - gap for other in placed)}, reverse=True)
        while True:
            candidate = first_non_overlapping_position(node, box, placed, candidates, "Y", gap)
            candidate_box = box_at(node, x=box["left"], y=candidate)
            blockers = [edges(other) for other in placed if boxes_conflict_for_axis(candidate_box, edges(other), "Y", gap)]
            if not blockers:
                node.location.y = candidate
                break
            candidates.append(min(other["bottom"] - gap for other in blockers))
            candidates = sorted(set(candidates), reverse=True)
        placed.append(node)


def align_down(nodes, target_bottom=None):
    if target_bottom is None:
        target_bottom = min(edges(node)["bottom"] for node in nodes)
    original = {node: edges(node) for node in nodes}
    ordered = sorted(nodes, key=lambda node: (original[node]["bottom"], original[node]["left"]))
    placed = []

    for node in ordered:
        box = original[node]
        gap = gap_size()
        path_limit = target_bottom + box["height"]
        for other in placed:
            other_box = original[other]
            if other_box["bottom"] < box["bottom"] and horizontal_ranges_overlap(box, other_box):
                path_limit = max(path_limit, edges(other)["top"] + gap + box["height"])
        candidates = sorted({path_limit, *(edges(other)["top"] + gap + box["height"] for other in placed)})
        while True:
            candidate = first_non_overlapping_position(node, box, placed, candidates, "Y", gap)
            candidate_box = box_at(node, x=box["left"], y=candidate)
            blockers = [edges(other) for other in placed if boxes_conflict_for_axis(candidate_box, edges(other), "Y", gap)]
            if not blockers:
                node.location.y = candidate
                break
            candidates.append(max(other["top"] + gap + box["height"] for other in blockers))
            candidates = sorted(set(candidates))
        placed.append(node)


def first_non_overlapping_position_with_anchors(node, box, placed, candidates, axis, gap):
    for candidate in candidates:
        candidate_box = box_at(
            node,
            x=candidate if axis == "X" else box["left"],
            y=candidate if axis == "Y" else box["top"],
        )
        if not any(
            boxes_conflict_for_axis_with_frames(candidate_box, other, edges(other), axis, gap)
            for other in placed
        ):
            return candidate
    return candidates[-1]


def align_left_with_anchors(nodes, anchor_nodes, target_left):
    original = {node: edges(node) for node in [*anchor_nodes, *nodes]}
    ordered = sorted(nodes, key=lambda node: (original[node]["left"], -original[node]["top"]))
    placed = list(anchor_nodes)

    for node in ordered:
        box = original[node]
        gap = gap_size()
        path_limit = target_left
        for other, other_box in original.items():
            if other is node:
                continue
            if original[other]["left"] < box["left"] and (
                vertical_ranges_overlap(box, other_box) or is_frame_node(other)
            ):
                path_limit = max(path_limit, edges(other)["right"] + gap)
        candidates = {path_limit, *(edges(other)["right"] + gap for other in placed)}
        for other in anchor_nodes:
            other_box = original[other]
            if box["right"] <= other_box["left"]:
                candidates.add(other_box["left"] - gap - box["width"])
        candidates = sorted(candidates)
        while True:
            candidate = first_non_overlapping_position_with_anchors(node, box, placed, candidates, "X", gap)
            candidate_box = box_at(node, x=candidate, y=box["top"])
            blockers = [
                other
                for other in placed
                if boxes_conflict_for_axis_with_frames(candidate_box, other, edges(other), "X", gap)
            ]
            if not blockers:
                node.location.x = candidate
                break
            candidates.append(max(edges(other)["right"] + gap for other in blockers))
            candidates = sorted(set(candidates))
        placed.append(node)


def align_right_with_anchors(nodes, anchor_nodes, target_right):
    original = {node: edges(node) for node in [*anchor_nodes, *nodes]}
    ordered = sorted(nodes, key=lambda node: (-original[node]["right"], -original[node]["top"]))
    placed = list(anchor_nodes)

    for node in ordered:
        box = original[node]
        gap = gap_size()
        path_limit = target_right - box["width"]
        for other in placed:
            other_box = original[other]
            if other_box["right"] > box["right"] and (
                vertical_ranges_overlap(box, other_box) or is_frame_node(other)
            ):
                path_limit = min(path_limit, edges(other)["left"] - gap - box["width"])
        candidates = {path_limit, *(edges(other)["left"] - gap - box["width"] for other in placed)}
        for other in anchor_nodes:
            other_box = original[other]
            if box["left"] >= other_box["right"]:
                candidates.add(other_box["right"] + gap)
        candidates = sorted(candidates, reverse=True)
        while True:
            candidate = first_non_overlapping_position_with_anchors(node, box, placed, candidates, "X", gap)
            candidate_box = box_at(node, x=candidate, y=box["top"])
            blockers = [
                other
                for other in placed
                if boxes_conflict_for_axis_with_frames(candidate_box, other, edges(other), "X", gap)
            ]
            if not blockers:
                node.location.x = candidate
                break
            candidates.append(min(edges(other)["left"] - gap - box["width"] for other in blockers))
            candidates = sorted(set(candidates), reverse=True)
        placed.append(node)


def align_up_with_anchors(nodes, anchor_nodes, target_top):
    original = {node: edges(node) for node in [*anchor_nodes, *nodes]}
    ordered = sorted(nodes, key=lambda node: (-original[node]["top"], original[node]["left"]))
    placed = list(anchor_nodes)

    for node in ordered:
        box = original[node]
        gap = gap_size()
        path_limit = target_top
        for other in placed:
            other_box = original[other]
            if other_box["top"] > box["top"] and horizontal_ranges_overlap(box, other_box):
                path_limit = min(path_limit, edges(other)["bottom"] - gap)
        candidates = sorted({path_limit, *(edges(other)["bottom"] - gap for other in placed)}, reverse=True)
        while True:
            candidate = first_non_overlapping_position_with_anchors(node, box, placed, candidates, "Y", gap)
            candidate_box = box_at(node, x=box["left"], y=candidate)
            blockers = [
                other
                for other in placed
                if boxes_conflict_for_axis_with_frames(candidate_box, other, edges(other), "Y", gap)
            ]
            if not blockers:
                node.location.y = candidate
                break
            candidates.append(min(edges(other)["bottom"] - gap for other in blockers))
            candidates = sorted(set(candidates), reverse=True)
        placed.append(node)


def align_down_with_anchors(nodes, anchor_nodes, target_bottom):
    original = {node: edges(node) for node in [*anchor_nodes, *nodes]}
    ordered = sorted(nodes, key=lambda node: (original[node]["bottom"], original[node]["left"]))
    placed = list(anchor_nodes)

    for node in ordered:
        box = original[node]
        gap = gap_size()
        path_limit = target_bottom + box["height"]
        for other in placed:
            other_box = original[other]
            if other_box["bottom"] < box["bottom"] and horizontal_ranges_overlap(box, other_box):
                path_limit = max(path_limit, edges(other)["top"] + gap + box["height"])
        candidates = sorted({path_limit, *(edges(other)["top"] + gap + box["height"] for other in placed)})
        while True:
            candidate = first_non_overlapping_position_with_anchors(node, box, placed, candidates, "Y", gap)
            candidate_box = box_at(node, x=box["left"], y=candidate)
            blockers = [
                other
                for other in placed
                if boxes_conflict_for_axis_with_frames(candidate_box, other, edges(other), "Y", gap)
            ]
            if not blockers:
                node.location.y = candidate
                break
            candidates.append(max(edges(other)["top"] + gap + box["height"] for other in blockers))
            candidates = sorted(set(candidates))
        placed.append(node)


def stabilize_frame_anchored_alignment(nodes, frame_nodes, direction):
    movable_nodes = [node for node in nodes if node not in frame_nodes]
    if not movable_nodes or not frame_nodes:
        return

    if direction == "LEFT":
        target = min(edges(frame)["left"] for frame in frame_nodes)
        align_once = lambda: align_left_with_anchors(movable_nodes, frame_nodes, target)
    elif direction == "RIGHT":
        target = max(edges(frame)["right"] for frame in frame_nodes)
        align_once = lambda: align_right_with_anchors(movable_nodes, frame_nodes, target)
    elif direction == "UP":
        target = max(edges(frame)["top"] for frame in frame_nodes)
        align_once = lambda: align_up_with_anchors(movable_nodes, frame_nodes, target)
    elif direction == "DOWN":
        target = min(edges(frame)["bottom"] for frame in frame_nodes)
        align_once = lambda: align_down_with_anchors(movable_nodes, frame_nodes, target)
    else:
        return

    for _ in range(MAX_STABILIZE_PASSES):
        before = snapshot_locations(movable_nodes)
        align_once()
        if not locations_changed(before, movable_nodes):
            break


def snapshot_locations(nodes):
    return {node: (float(node.location.x), float(node.location.y)) for node in nodes}


def restore_locations(locations):
    for node, (x, y) in locations.items():
        node.location.x = x
        node.location.y = y


def snapshot_frame_state(frame):
    return (
        float(frame.location.x),
        float(frame.location.y),
        float(getattr(frame, "width", 0.0)),
        float(getattr(frame, "height", 0.0)),
    )


def restore_frame_state(frame, state):
    x, y, width, height = state
    frame.location.x = x
    frame.location.y = y
    if width > 0.0:
        frame.width = width
    if height > 0.0:
        frame.height = height


def locations_changed(before, nodes):
    for node in nodes:
        old_x, old_y = before[node]
        if abs(float(node.location.x) - old_x) > POSITION_EPSILON:
            return True
        if abs(float(node.location.y) - old_y) > POSITION_EPSILON:
            return True
    return False


def stabilize_alignment(nodes, align_function):
    if align_function is align_left:
        fixed_target = min(edges(node)["left"] for node in nodes)
        stabilize_alignment_with_target(nodes, align_function, target_left=fixed_target)
    elif align_function is align_right:
        fixed_target = max(edges(node)["right"] for node in nodes)
        stabilize_alignment_with_target(nodes, align_function, target_right=fixed_target)
    elif align_function is align_up:
        fixed_target = max(edges(node)["top"] for node in nodes)
        stabilize_alignment_with_target(nodes, align_function, target_top=fixed_target)
    elif align_function is align_down:
        fixed_target = min(edges(node)["bottom"] for node in nodes)
        stabilize_alignment_with_target(nodes, align_function, target_bottom=fixed_target)
    else:
        stabilize_alignment_with_target(nodes, align_function)


def stabilize_alignment_with_target(nodes, align_function, **target_kwargs):
    align_once = lambda: align_function(nodes, **target_kwargs)

    for _ in range(MAX_STABILIZE_PASSES):
        before = snapshot_locations(nodes)
        align_once()
        if not locations_changed(before, nodes):
            break


def get_preferences():
    addon = bpy.context.preferences.addons.get(ADDON_ID)
    if addon is None:
        return None
    return addon.preferences


class PureRefNodeAlignPreferences(AddonPreferences):
    bl_idname = ADDON_ID

    left_key: EnumProperty(name="Left", items=key_items(), default="LEFT_ARROW")
    right_key: EnumProperty(name="Right", items=key_items(), default="RIGHT_ARROW")
    up_key: EnumProperty(name="Up", items=key_items(), default="UP_ARROW")
    down_key: EnumProperty(name="Down", items=key_items(), default="DOWN_ARROW")

    use_ctrl: BoolProperty(name="Ctrl", default=default_ctrl())
    use_shift: BoolProperty(name="Shift", default=default_shift())
    use_alt: BoolProperty(name="Alt", default=False)
    use_command: BoolProperty(name="Command", default=use_command_key())
    gap: FloatProperty(
        name="Node Gap",
        description="Extra spacing between nodes after alignment in node editor units",
        default=BASE_GAP,
        min=0.0,
        soft_max=300.0,
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Shortcut Keys")

        row = layout.row(align=True)
        row.prop(self, "use_ctrl")
        row.prop(self, "use_shift")
        row.prop(self, "use_alt")
        row.prop(self, "use_command")

        col = layout.column(align=True)
        col.prop(self, "left_key")
        col.prop(self, "right_key")
        col.prop(self, "up_key")
        col.prop(self, "down_key")

        layout.separator()
        layout.prop(self, "gap")

        layout.separator()
        layout.operator("align_node.apply_shortcuts", icon="FILE_REFRESH")
        layout.operator("align_node.debug_bounds", icon="INFO")


class NODE_OT_pureref_apply_shortcuts(Operator):
    bl_idname = "align_node.apply_shortcuts"
    bl_label = "Apply Node Align Shortcuts"
    bl_description = "Rebuild this add-on's node editor shortcuts from the settings above"

    def execute(self, context):
        unregister_keymaps()
        register_keymaps()
        self.report({"INFO"}, "PureRef Style Node Align shortcuts updated.")
        return {"FINISHED"}


class NODE_OT_pureref_debug_bounds(Operator):
    bl_idname = "align_node.debug_bounds"
    bl_label = "Debug Selected Node Bounds"
    bl_description = "Write selected node locations, sizes, dimensions, and calculated bounds to a Blender text block"

    def execute(self, context):
        nodes = selected_nodes_from_any_node_editor(context)
        if not nodes:
            self.report({"INFO"}, "Select at least one node in an open Node Editor to debug.")
            return {"CANCELLED"}

        lines = [
            "--- Align_Node: Selected Node Bounds ---",
            f"add-on version: {bl_info['version']}",
            f"align operator: {NODE_OT_pureref_align.bl_idname}",
            f"node gap: {gap_size()}",
            "",
        ]
        for index, node in enumerate(nodes, 1):
            dimensions = getattr(node, "dimensions", None)
            dimensions_x = getattr(dimensions, "x", None) if dimensions else None
            dimensions_y = getattr(dimensions, "y", None) if dimensions else None
            box = edges(node)
            absolute = node_location_absolute(node)

            lines.extend(
                (
                    f"[{index}] {node.name!r} ({node.bl_idname})",
                    f"    location: x={node.location.x:.3f}, y={node.location.y:.3f}",
                    f"    location_absolute: {format_xy(absolute)}",
                    f"    width/height: width={getattr(node, 'width', None)}, height={getattr(node, 'height', None)}",
                    f"    dimensions: x={dimensions_x}, y={dimensions_y}",
                    "    bounds: "
                    f"left={box['left']:.3f}, right={box['right']:.3f}, "
                    f"top={box['top']:.3f}, bottom={box['bottom']:.3f}",
                    "",
                )
            )
        lines.append("--- Pair Overlap Diagnostics ---")
        for first_index, first in enumerate(nodes):
            first_box = edges(first)
            for second in nodes[first_index + 1:]:
                second_box = edges(second)
                lines.append(
                    f"{first.name!r} <-> {second.name!r}: "
                    f"x_overlap={horizontal_ranges_overlap(first_box, second_box)}, "
                    f"y_overlap={vertical_ranges_overlap(first_box, second_box)}, "
                    f"box_overlap={boxes_too_close(first_box, second_box, 0.0)}"
                )
        lines.append("--- End Node Bounds ---")
        if debug_alignment_lines:
            lines.append("")
            lines.extend(debug_alignment_lines)

        debug_text = "\n".join(lines)
        text_name = "PureRef_Node_Bounds_Debug"
        text = bpy.data.texts.get(text_name) or bpy.data.texts.new(text_name)
        text.clear()
        text.write(debug_text)

        try:
            context.window_manager.clipboard = debug_text
            clipboard_message = " Also copied to clipboard."
        except Exception:
            clipboard_message = ""

        self.report({"INFO"}, f"Wrote bounds for {len(nodes)} node(s) to Text: {text_name}.{clipboard_message}")
        return {"FINISHED"}


def selected_nodes(context):
    tree = getattr(context.space_data, "edit_tree", None)
    if tree is None:
        return []
    return [node for node in tree.nodes if node.select]


def has_selected_frame_parent(node, selected_frames):
    parent = getattr(node, "parent", None)
    while parent is not None:
        if parent in selected_frames:
            return True
        parent = getattr(parent, "parent", None)
    return False


def selected_frame_parent(node, selected_frames):
    parent = getattr(node, "parent", None)
    while parent is not None:
        if parent in selected_frames:
            return parent
        parent = getattr(parent, "parent", None)
    return None


def alignment_nodes_from_selection(nodes):
    selected_frames = {node for node in nodes if is_frame_node(node)}
    if not selected_frames:
        return nodes

    top_level_nodes = [
        node
        for node in nodes
        if not has_selected_frame_parent(node, selected_frames)
    ]

    if len(top_level_nodes) >= 2:
        return top_level_nodes

    return [node for node in nodes if node not in selected_frames]


def split_alignment_selection(nodes):
    selected_frames = {node for node in nodes if is_frame_node(node)}
    if not selected_frames:
        return nodes, []

    top_level_nodes = [
        node
        for node in nodes
        if not has_selected_frame_parent(node, selected_frames)
    ]
    outside_nodes = [node for node in top_level_nodes if node not in selected_frames]
    internal_groups = []
    groups_by_frame = {}
    for node in nodes:
        if node in selected_frames:
            continue
        frame = selected_frame_parent(node, selected_frames)
        if frame is not None:
            groups_by_frame.setdefault(frame, []).append(node)
    internal_groups = list(groups_by_frame.items())

    if outside_nodes:
        return top_level_nodes, internal_groups

    if len(selected_frames) > 1:
        return top_level_nodes, internal_groups

    return [], internal_groups


def align_internal_nodes_to_frame(frame, nodes, direction):
    if not nodes:
        return

    frame_state = snapshot_frame_state(frame)
    margin = frame_inner_margin()
    before_frame_box = edges(frame)
    before_frame_absolute = node_location_absolute(frame)
    before_node_locations = snapshot_locations(nodes)
    before_node_absolute = {node: node_location_absolute(node) for node in nodes}

    if direction == "LEFT":
        natural_target = min(edges(node)["left"] for node in nodes)
        stabilize_alignment_with_target(nodes, align_left, target_left=min(natural_target, margin))
    elif direction == "RIGHT":
        natural_target = max(edges(node)["right"] for node in nodes)
        stabilize_alignment_with_target(nodes, align_right, target_right=max(natural_target, node_width(frame) - margin))
    elif direction == "UP":
        natural_target = max(edges(node)["top"] for node in nodes)
        stabilize_alignment_with_target(nodes, align_up, target_top=max(natural_target, -margin))
    elif direction == "DOWN":
        natural_target = min(edges(node)["bottom"] for node in nodes)
        stabilize_alignment_with_target(nodes, align_down, target_bottom=min(natural_target, -node_height(frame) + margin))

    node_locations = snapshot_locations(nodes)
    after_align_frame_state = snapshot_frame_state(frame)
    after_align_frame_box = edges(frame)
    after_align_frame_absolute = node_location_absolute(frame)
    after_align_node_absolute = {node: node_location_absolute(node) for node in nodes}

    restore_frame_state(frame, frame_state)
    restore_locations(node_locations)
    restore_frame_state(frame, frame_state)

    final_frame_box = edges(frame)
    final_frame_absolute = node_location_absolute(frame)
    final_node_absolute = {node: node_location_absolute(node) for node in nodes}
    lines = [
        "--- Align_Node: Last Internal Frame Align Debug ---",
        f"direction: {direction}",
        f"frame: {getattr(frame, 'name', '<unnamed>')!r}",
        f"frame inner margin: {margin:.3f}",
        "frame before: "
        f"state={frame_state}, abs={format_xy(before_frame_absolute)}, "
        f"bounds=left={before_frame_box['left']:.3f}, right={before_frame_box['right']:.3f}, "
        f"top={before_frame_box['top']:.3f}, bottom={before_frame_box['bottom']:.3f}",
        "frame after align before restore: "
        f"state={after_align_frame_state}, abs={format_xy(after_align_frame_absolute)}, "
        f"bounds=left={after_align_frame_box['left']:.3f}, right={after_align_frame_box['right']:.3f}, "
        f"top={after_align_frame_box['top']:.3f}, bottom={after_align_frame_box['bottom']:.3f}",
        "frame final after restore: "
        f"state={snapshot_frame_state(frame)}, abs={format_xy(final_frame_absolute)}, "
        f"bounds=left={final_frame_box['left']:.3f}, right={final_frame_box['right']:.3f}, "
        f"top={final_frame_box['top']:.3f}, bottom={final_frame_box['bottom']:.3f}",
        "nodes:",
    ]
    for node in nodes:
        before_x, before_y = before_node_locations[node]
        target_x, target_y = node_locations[node]
        final_x, final_y = float(node.location.x), float(node.location.y)
        lines.extend(
            (
                f"  {getattr(node, 'name', '<unnamed>')!r}:",
                f"    local before: x={before_x:.3f}, y={before_y:.3f}",
                f"    local target after align: x={target_x:.3f}, y={target_y:.3f}",
                f"    local final: x={final_x:.3f}, y={final_y:.3f}",
                f"    abs before: {format_xy(before_node_absolute[node])}",
                f"    abs after align before restore: {format_xy(after_align_node_absolute[node])}",
                f"    abs final: {format_xy(final_node_absolute[node])}",
                f"    delta local final-before: dx={final_x - before_x:.3f}, dy={final_y - before_y:.3f}",
            )
        )
    lines.append("--- End Internal Frame Align Debug ---")
    append_alignment_debug(lines)


def find_node_editor_tree(context):
    space_data = getattr(context, "space_data", None)
    tree = getattr(space_data, "edit_tree", None)
    if tree is not None:
        return tree

    window = getattr(context, "window", None)
    screen = getattr(window, "screen", None) if window else None
    if screen is None:
        return None

    for area in screen.areas:
        if area.type != "NODE_EDITOR":
            continue
        for space in area.spaces:
            if space.type == "NODE_EDITOR" and getattr(space, "edit_tree", None) is not None:
                return space.edit_tree
    return None


def find_selected_nodes_from_open_node_editors():
    window_manager = bpy.context.window_manager
    if window_manager is None:
        return []

    for window in window_manager.windows:
        screen = getattr(window, "screen", None)
        if screen is None:
            continue
        for area in screen.areas:
            if area.type != "NODE_EDITOR":
                continue
            for space in area.spaces:
                if space.type != "NODE_EDITOR":
                    continue
                tree = getattr(space, "edit_tree", None)
                if tree is None:
                    continue
                nodes = [node for node in tree.nodes if node.select]
                if nodes:
                    return nodes
    return []


def selected_nodes_from_any_node_editor(context):
    tree = find_node_editor_tree(context)
    if tree is not None:
        nodes = [node for node in tree.nodes if node.select]
        if nodes:
            return nodes
    return find_selected_nodes_from_open_node_editors()


class NODE_OT_pureref_align(Operator):
    bl_idname = "align_node.align"
    bl_label = "PureRef Style Align Nodes"
    bl_description = "Align selected nodes and spread them so they do not overlap"
    bl_options = {"REGISTER", "UNDO"}

    direction: EnumProperty(
        name="Direction",
        items=(
            ("LEFT", "Left", "Align left edges"),
            ("RIGHT", "Right", "Align right edges"),
            ("UP", "Up", "Align top edges"),
            ("DOWN", "Down", "Align bottom edges"),
        ),
    )

    @classmethod
    def poll(cls, context):
        return (
            context.area is not None
            and context.area.type == "NODE_EDITOR"
            and getattr(context.space_data, "edit_tree", None) is not None
        )

    def execute(self, context):
        nodes, internal_groups = split_alignment_selection(selected_nodes(context))
        if len(nodes) < 2 and not internal_groups:
            self.report({"INFO"}, "Select at least two nodes to align.")
            return {"CANCELLED"}

        if len(nodes) >= 2:
            if self.direction == "LEFT":
                stabilize_alignment(nodes, align_left)

            elif self.direction == "RIGHT":
                stabilize_alignment(nodes, align_right)

            elif self.direction == "UP":
                stabilize_alignment(nodes, align_up)

            elif self.direction == "DOWN":
                stabilize_alignment(nodes, align_down)

        for frame, internal_nodes in internal_groups:
            align_internal_nodes_to_frame(frame, internal_nodes, self.direction)

        return {"FINISHED"}


classes = (
    PureRefNodeAlignPreferences,
    NODE_OT_pureref_apply_shortcuts,
    NODE_OT_pureref_debug_bounds,
    NODE_OT_pureref_align,
)


def node_editor_menu(self, context):
    self.layout.separator()
    self.layout.operator(NODE_OT_pureref_debug_bounds.bl_idname, icon="INFO")


def register_keymaps():
    window_manager = bpy.context.window_manager
    keyconfig = window_manager.keyconfigs.addon
    if keyconfig is None:
        return

    keymap = keyconfig.keymaps.new(name="Node Editor", space_type="NODE_EDITOR")
    remove_legacy_keymap_items(keymap)
    preferences = get_preferences()
    ctrl = preferences.use_ctrl if preferences else default_ctrl()
    shift = preferences.use_shift if preferences else default_shift()
    alt = preferences.use_alt if preferences else False
    oskey = preferences.use_command if preferences else use_command_key()

    shortcuts = (
        (preferences.left_key if preferences else "LEFT_ARROW", "LEFT"),
        (preferences.right_key if preferences else "RIGHT_ARROW", "RIGHT"),
        (preferences.up_key if preferences else "UP_ARROW", "UP"),
        (preferences.down_key if preferences else "DOWN_ARROW", "DOWN"),
    )

    for key, direction in shortcuts:
        item = keymap.keymap_items.new(
            NODE_OT_pureref_align.bl_idname,
            key,
            "PRESS",
            ctrl=ctrl,
            shift=shift,
            alt=alt,
            oskey=oskey,
        )
        item.properties.direction = direction
        addon_keymaps.append((keymap, item))


def remove_legacy_keymap_items(keymap):
    for item in list(keymap.keymap_items):
        if item.idname == "node.pureref_align":
            keymap.keymap_items.remove(item)


def unregister_keymaps():
    for keymap, item in addon_keymaps:
        keymap.keymap_items.remove(item)
    addon_keymaps.clear()


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.NODE_MT_node.append(node_editor_menu)
    register_keymaps()


def unregister():
    unregister_keymaps()
    bpy.types.NODE_MT_node.remove(node_editor_menu)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
