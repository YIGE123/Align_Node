# Changelog

## 1.10.25

- Fixed GitHub Actions/Linux test runs by using the same default `0.5` dimensions scale as macOS for non-Windows platforms.
- Kept Windows dimensions scaling unchanged at `2/3` for both axes.

## 1.10.24

- Increased Windows vertical dimensions scaling to `2/3` so Up alignment has enough visual height to stack overlapping columns without vertical overlap.
- Kept macOS dimensions scaling unchanged.
- Added Windows regression coverage for repeated Separate XYZ and Color Ramp columns aligned upward.

## 1.10.23

- Refined Windows visual bounds scaling: horizontal dimensions now use `2/3` of `dimensions.x`, while vertical dimensions use `0.5` of `dimensions.y`.
- Kept macOS dimensions scaling unchanged.
- Added Windows regression coverage for Color Ramp spacing and bottom alignment with scaled visual bounds.

## 1.10.22

- Fixed Windows node spacing by using raw `node.dimensions` for visual bounds on Windows while keeping macOS on the existing `0.5` dimensions scale.
- Added regression coverage for Windows left alignment so horizontal gap spacing is preserved with Windows-reported dimensions.

## 1.10.21

- Changed compact Position and Boolean input nodes to use `dimensions.y * 0.5` instead of a fixed `76` unit override, matching the same visual-height scale used by Normal and taller Geometry Nodes.

## 1.10.20

- Expanded `Debug Selected Node Bounds` with height-rule diagnostics, alternative height candidates, parent/collapse state, and socket metadata so compact node visual bounds can be calibrated from Blender output instead of guessed.

## 1.10.19

- Added compact visual-height handling for `FunctionNodeInputBool` so Boolean and Position input nodes use the same visual bounds during Up/Down alignment.
- Added regression coverage for aligning compact Position, Boolean, and Normal nodes to the same visual bottom edge.

## 1.10.18

- Changed single Frame plus outside-node selections to use the normal node alignment rules, so the topmost/rightmost/bottommost/leftmost selected item becomes the target instead of treating the Frame as a fixed anchor.
- Added compact visual-height handling for `GeometryNodeInputPosition`, fixing bottom-edge alignment against taller Geometry Nodes such as Set Position.

## 1.10.17

- Fixed selections containing multiple Frames so the Frames are returned as primary alignment nodes and align like regular nodes.
- Kept selected child nodes grouped by their selected Frame so internal Frame boundary alignment still runs after multi-Frame alignment.

## 1.10.16

- Made Frame-internal alignment directional: pressing Up/Down/Left/Right will no longer push already-stable child nodes in the opposite direction just to satisfy the safe inner margin.
- Kept the safe Frame inner margin as a limit for moving toward the Frame boundary, while preserving closer existing stable margins.

## 1.10.15

- Added `location_absolute` to selected-node bounds debug output when Blender exposes it.
- Added last internal Frame alignment diagnostics showing before/after Frame bounds, Frame state, child-node local positions, and child-node absolute positions.

## 1.10.14

- Added a separate `40` unit safe inner margin for aligning selected nodes to a selected Frame boundary.
- Kept regular node spacing controlled by the user-configured node gap.

## 1.10.13

- Fixed repeated Frame-internal alignment drift by restoring both the Frame state and the aligned child-node local positions after Blender's automatic Frame adjustment runs.
- Added regression coverage for repeated internal alignment in all four directions.

## 1.10.12

- Restored Frame position and size after internal child-node alignment to prevent Blender's Frame auto-adjustment from causing repeated one-pixel drift.
- Kept single selected Frame as an anchor when aligning it with outside nodes, while allowing multiple selected Frames to align with the normal node rules.
- Added regression coverage for Frame inner-bottom alignment, Frame state restoration, and multi-Frame alignment.

## 1.10.11

- Restored Frame-only internal alignment: selected nodes inside a selected Frame now align to the Frame's inner boundary while keeping the configured gap.
- Fixed the false "Select at least two nodes to align" report for selections that contain a Frame and multiple selected child nodes.
- Prevented outside nodes from crossing to the opposite side of a selected Frame during left/right Frame alignment.
- Added regression coverage for repeated mixed Frame/internal/outside alignment so repeated shortcuts stay stable.

## 1.10.10

- Fixed Frame-only selections so selecting a Frame and only its contained nodes no longer moves anything.
- Treat selected Frames as fixed anchors when outside nodes are also selected.
- Added Frame-aware horizontal gap handling so outside nodes keep the same spacing rule from Frames as they do from regular nodes.

## 1.10.9

- Reworked mixed Frame selections into strict two-pass alignment.
- Frame and outside nodes are aligned first.
- Selected nodes inside the Frame are then aligned to the Frame's local boundary.
- Fixed large offsets caused by applying global Frame coordinates to child nodes.

## 1.10.8

- Added a second Frame selection pass for selections that include a Frame, outside nodes, and selected nodes inside the Frame.
- Frame and outside nodes align first; then selected internal nodes align to the selected Frame boundary in the same direction.
- Kept selected Frame children moving with the Frame when the children themselves are not selected.

## 1.10.7

- Added Frame-aware selection handling.
- Selected child nodes inside a selected Frame are aligned without moving the Frame when no outside nodes are selected.
- When a selected Frame is grouped with selected outside nodes, the Frame is aligned as a top-level node and its children are not moved independently.
- Changed Windows/Linux default shortcut to `Ctrl + Shift + Arrow`.
- Improved width handling for platforms that report `node.dimensions.x` at actual visual scale.
- Updated Blender compatibility metadata to `5.1.1`.

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
