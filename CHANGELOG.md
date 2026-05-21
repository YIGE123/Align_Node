# Changelog

## 1.10.5

- Fixed an Up/Down alignment case where nodes that were visually separate but closer than the configured gap were treated as colliding.
- Collision avoidance is now axis-aware: Up/Down only stacks nodes when their X ranges visually overlap, and Left/Right only stacks nodes when their Y ranges visually overlap.
- Kept stable iterative alignment behavior for Geometry Nodes edge cases.

## 1.10.4

- Improved collision candidate checks for configurable node gaps.
- Added regression coverage for Geometry Nodes layouts that could drift during repeated Up/Down alignment.

## 1.10.3

- Renamed the add-on to `Align_Node`.
- Updated maintainer metadata to `Anthem`.
- Added selected-node bounds debugging output.

## Earlier

- Added customizable shortcuts.
- Added macOS default shortcut `Command + Shift + Arrow`.
- Added configurable node gap.
- Added PureRef-style node alignment for left, right, up, and down directions.
