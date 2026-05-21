import importlib
import sys
import types
import unittest


def install_bpy_stub():
    bpy = types.ModuleType("bpy")
    bpy.context = types.SimpleNamespace(
        preferences=types.SimpleNamespace(addons={}),
        window_manager=types.SimpleNamespace(keyconfigs=types.SimpleNamespace(addon=None)),
    )
    bpy.utils = types.SimpleNamespace(
        register_class=lambda cls: None,
        unregister_class=lambda cls: None,
    )

    bpy_types = types.ModuleType("bpy.types")
    bpy_types.AddonPreferences = object
    bpy_types.Operator = object

    bpy_props = types.ModuleType("bpy.props")
    bpy_props.BoolProperty = lambda **kwargs: kwargs.get("default")
    bpy_props.EnumProperty = lambda **kwargs: kwargs.get("default")
    bpy_props.FloatProperty = lambda **kwargs: kwargs.get("default")

    sys.modules["bpy"] = bpy
    sys.modules["bpy.types"] = bpy_types
    sys.modules["bpy.props"] = bpy_props


install_bpy_stub()
align = importlib.import_module("Align_Node")


class Location:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Dimensions:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Node:
    def __init__(self, x, y, width=100, height=80, reported_width=None, reported_height=None):
        self.location = Location(x, y)
        self.width = width
        self.height = height
        self.dimensions = Dimensions(
            reported_width if reported_width is not None else width,
            reported_height if reported_height is not None else height,
        )


def bottom(node):
    return align.edges(node)["bottom"]


def right(node):
    return align.edges(node)["right"]


def left(node):
    return align.edges(node)["left"]


class AlignmentLogicTest(unittest.TestCase):
    def test_gap_size_uses_preferences_when_available(self):
        original_context = align.bpy.context
        preferences = types.SimpleNamespace(gap=80)
        addon = types.SimpleNamespace(preferences=preferences)
        align.bpy.context = types.SimpleNamespace(preferences=types.SimpleNamespace(addons={align.ADDON_ID: addon}))

        try:
            self.assertEqual(align.gap_size(), 85)
        finally:
            align.bpy.context = original_context

    def test_gap_changes_spacing_linearly(self):
        original_context = align.bpy.context
        left_node = Node(0, 100, width=100, height=80)
        right_node = Node(500, 100, width=100, height=80)

        try:
            preferences = types.SimpleNamespace(gap=30)
            addon = types.SimpleNamespace(preferences=preferences)
            align.bpy.context = types.SimpleNamespace(preferences=types.SimpleNamespace(addons={align.ADDON_ID: addon}))
            align.align_left([left_node, right_node])
            gap_30_x = left(right_node)

            left_node = Node(0, 100, width=100, height=80)
            right_node = Node(500, 100, width=100, height=80)
            preferences.gap = 40
            align.align_left([left_node, right_node])
            gap_40_x = left(right_node)

            self.assertEqual(gap_40_x - gap_30_x, 10)
        finally:
            align.bpy.context = original_context

    def test_down_align_uses_lowest_bottom_for_non_overlapping_nodes(self):
        nodes = [
            Node(0, 100),
            Node(240, 40),
            Node(480, 20),
        ]
        target = min(bottom(node) for node in nodes)

        align.align_down(nodes)

        self.assertEqual([bottom(node) for node in nodes], [target, target, target])

    def test_stabilize_alignment_runs_until_up_alignment_stops_changing(self):
        nodes = [
            Node(-1010, -678, width=140, height=100, reported_width=280, reported_height=192),
            Node(-667, -394, width=200, height=100, reported_width=400, reported_height=564),
            Node(-841, -492, width=145, height=100, reported_width=290, reported_height=564),
            Node(-611, -803, width=145, height=100, reported_width=290, reported_height=564),
            Node(-954, -803, width=145, height=100, reported_width=290, reported_height=564),
            Node(-780, -989, width=140, height=100, reported_width=280, reported_height=192),
        ]

        align.stabilize_alignment(nodes, align.align_up)
        stabilized = [(node.location.x, node.location.y) for node in nodes]
        align.align_up(nodes)

        self.assertEqual([(node.location.x, node.location.y) for node in nodes], stabilized)

    def test_down_alignment_does_not_cross_original_lower_horizontal_blockers(self):
        warning_top = Node(-1165.469, -269.588, width=140, height=100, reported_width=280, reported_height=192)
        noise_mid = Node(-822.469, -394.588, width=200.8662109375, height=100, reported_width=401.732421875, reported_height=564)
        noise_left = Node(-996.469, -269.588, width=145, height=100, reported_width=290, reported_height=564)
        lower_blocker = Node(-766.603, -705.588, width=145, height=100, reported_width=290, reported_height=564)
        nodes = [
            warning_top,
            noise_mid,
            noise_left,
            lower_blocker,
            Node(-761.603, -269.588, width=140, height=100, reported_width=280, reported_height=192),
        ]

        align.stabilize_alignment(nodes, align.align_down)

        self.assertLessEqual(bottom(noise_mid), align.edges(lower_blocker)["top"] + align.gap_size())
        self.assertLessEqual(bottom(noise_left), align.edges(lower_blocker)["top"] + align.gap_size())

    def test_up_down_preserve_order_when_unrelated_left_node_is_added(self):
        unrelated = Node(-1200, 500, width=140, height=100, reported_width=280, reported_height=192)
        node_5 = Node(-700, 450, width=145, height=100, reported_width=290, reported_height=564)
        node_3 = Node(-350, 450, width=145, height=100, reported_width=290, reported_height=564)
        node_4 = Node(-350, 0, width=145, height=100, reported_width=290, reported_height=564)
        nodes = [unrelated, node_5, node_3, node_4]

        align.stabilize_alignment(nodes, align.align_up)
        self.assertGreaterEqual(align.edges(node_3)["bottom"], align.edges(node_4)["top"] + align.gap_size())

        align.stabilize_alignment(nodes, align.align_down)
        self.assertGreaterEqual(align.edges(node_3)["bottom"], align.edges(node_4)["top"] + align.gap_size())

    def test_geometry_node_up_down_does_not_drift_when_gap_is_required(self):
        set_position = Node(-123.544, 1006.826, width=140, height=100, reported_width=280, reported_height=352)
        separate_xyz = Node(-123.544, 801.826, width=140, height=100, reported_width=280, reported_height=362)
        compare = Node(45.456, 769.826, width=140, height=100, reported_width=280, reported_height=298)
        nodes = [set_position, separate_xyz, compare]

        align.stabilize_alignment(nodes, align.align_up)
        up_positions = [(node.location.x, node.location.y) for node in nodes]
        self.assertGreaterEqual(align.edges(set_position)["bottom"], align.edges(separate_xyz)["top"] + align.gap_size())

        align.stabilize_alignment(nodes, align.align_down)
        down_positions = [(node.location.x, node.location.y) for node in nodes]

        align.stabilize_alignment(nodes, align.align_up)
        self.assertEqual([(node.location.x, node.location.y) for node in nodes], up_positions)

        align.stabilize_alignment(nodes, align.align_down)
        self.assertEqual([(node.location.x, node.location.y) for node in nodes], down_positions)

    def test_up_align_does_not_stack_nodes_that_are_only_closer_than_gap(self):
        position = Node(199.578, 530.519, width=140, height=100, reported_width=280, reported_height=100)
        separate_xyz = Node(53.486, 650.504, width=140, height=100, reported_width=280, reported_height=362)
        nodes = [position, separate_xyz]

        align.stabilize_alignment(nodes, align.align_up)

        self.assertEqual(position.location.y, separate_xyz.location.y)
        self.assertFalse(align.horizontal_ranges_overlap(align.edges(position), align.edges(separate_xyz)))

    def test_up_down_keep_x_unchanged(self):
        nodes = [
            Node(0, 100),
            Node(40, 20),
            Node(320, 10),
        ]
        original_x = [node.location.x for node in nodes]

        align.align_up(nodes)
        self.assertEqual([node.location.x for node in nodes], original_x)

        align.align_down(nodes)
        self.assertEqual([node.location.x for node in nodes], original_x)

    def test_right_align_does_not_pass_through_blocking_node(self):
        blocker = Node(300, 100, width=100, height=80)
        moving = Node(0, 100, width=100, height=80)
        nodes = [moving, blocker]

        align.align_right(nodes)

        self.assertLessEqual(right(moving), blocker.location.x - align.gap_size())

    def test_right_align_evenly_packs_nodes_that_share_vertical_range(self):
        red_info = Node(0, 500, width=260, height=180)
        wide_a = Node(320, 500, width=360, height=500)
        wide_b = Node(720, 500, width=420, height=500)
        far_target = Node(1800, 500, width=260, height=500)
        nodes = [red_info, wide_a, wide_b, far_target]

        align.align_right(nodes)

        packed = sorted(nodes, key=left)
        for index in range(len(packed) - 1):
            self.assertEqual(left(packed[index + 1]) - right(packed[index]), align.gap_size())

    def test_right_align_preserves_original_order_for_vertical_lane(self):
        red_top = Node(0, 500, width=260, height=180)
        long_a = Node(430, 500, width=360, height=500)
        long_b = Node(850, 500, width=420, height=500)
        lower_free = Node(1800, -200, width=260, height=500)
        nodes = [red_top, long_a, long_b, lower_free]

        align.align_right(nodes)

        self.assertLessEqual(right(red_top), left(long_a) - align.gap_size())
        self.assertLessEqual(right(long_a), left(long_b) - align.gap_size())

    def test_left_align_does_not_pass_through_blocking_node(self):
        anchor = Node(0, -300, width=100, height=80)
        blocker = Node(300, 300, width=170, height=300)
        moving = Node(900, 240, width=160, height=90)
        nodes = [anchor, blocker, moving]

        align.align_left(nodes)

        self.assertEqual(left(anchor), 0)
        self.assertEqual(left(blocker), 0)
        self.assertGreaterEqual(left(moving), right(blocker) + align.gap_size())

    def test_left_align_fills_available_lane_without_vertical_blocker(self):
        anchor = Node(0, 260, width=100, height=100)
        middle = Node(300, 20, width=100, height=100)
        lower_right = Node(800, -260, width=100, height=100)
        nodes = [anchor, middle, lower_right]

        align.align_left(nodes)

        self.assertEqual(left(anchor), 0)
        self.assertEqual(left(middle), 0)
        self.assertEqual(left(lower_right), 0)

    def test_left_align_fills_independent_empty_slots(self):
        left_top = Node(0, 300, width=260, height=500)
        lower_mid = Node(360, -120, width=260, height=500)
        top_mid = Node(700, 850, width=260, height=500)
        info = Node(1620, 730, width=240, height=170)
        lower_right = Node(1620, -90, width=260, height=500)
        nodes = [left_top, lower_mid, top_mid, info, lower_right]

        align.align_left(nodes)

        self.assertEqual(left(left_top), 0)
        self.assertEqual(left(top_mid), 0)
        for index, node in enumerate(nodes):
            for other in nodes[index + 1:]:
                self.assertFalse(align.boxes_too_close(align.edges(node), align.edges(other)))

    def test_node_height_prefers_dimensions_when_available(self):
        node = Node(0, 0, height=100, reported_height=400)

        self.assertEqual(align.node_height(node), 200)

    def test_node_width_prefers_dimensions_when_available(self):
        node = Node(0, 0, width=100, reported_width=180)

        self.assertEqual(align.node_width(node), 90)

    def test_left_align_uses_dimensions_width_to_prevent_overlap(self):
        left_node = Node(0, 100, width=180, reported_width=400)
        right_node = Node(500, 100, width=180, reported_width=400)
        nodes = [left_node, right_node]

        align.align_left(nodes)

        self.assertGreaterEqual(left(right_node), right(left_node) + align.gap_size())

    def test_right_align_uses_dimensions_width_to_prevent_overlap(self):
        left_node = Node(0, 100, width=180, reported_width=400)
        right_node = Node(500, 100, width=180, reported_width=400)
        nodes = [left_node, right_node]

        align.align_right(nodes)

        self.assertLessEqual(right(left_node), left(right_node) - align.gap_size())

    def test_down_align_falls_back_until_left_column_does_not_overlap(self):
        upper = Node(0, 500, width=240, height=240, reported_height=600)
        middle = Node(0, 120, width=240, height=240, reported_height=600)
        lower = Node(0, -260, width=240, height=240, reported_height=600)
        nodes = [upper, middle, lower]

        align.align_down(nodes)

        ordered = sorted(nodes, key=bottom)
        self.assertGreaterEqual(bottom(ordered[1]), align.edges(ordered[0])["top"] + align.gap_size())
        self.assertGreaterEqual(bottom(ordered[2]), align.edges(ordered[1])["top"] + align.gap_size())

    def test_left_align_uses_dimensions_height_to_prevent_left_column_overlap(self):
        upper = Node(0, 500, width=240, height=240, reported_height=600)
        middle = Node(400, 120, width=240, height=240, reported_height=600)
        lower = Node(800, -260, width=240, height=240, reported_height=600)
        nodes = [upper, middle, lower]

        align.align_left(nodes)

        self.assertFalse(align.boxes_too_close(align.edges(upper), align.edges(middle)))
        self.assertFalse(align.boxes_too_close(align.edges(middle), align.edges(lower)))

    def test_left_right_keep_y_unchanged(self):
        nodes = [
            Node(0, 100),
            Node(260, 40),
            Node(520, -20),
        ]
        original_y = [node.location.y for node in nodes]

        align.align_left(nodes)
        self.assertEqual([node.location.y for node in nodes], original_y)

        align.align_right(nodes)
        self.assertEqual([node.location.y for node in nodes], original_y)


if __name__ == "__main__":
    unittest.main()
