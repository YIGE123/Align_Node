# Align_Node

Blender node editor alignment add-on for Geometry Nodes, shader/material nodes, compositor nodes, and other node trees.

## Features

- Align selected nodes to the left, right, top, or bottom edge.
- PureRef-style keyboard workflow.
- macOS default shortcut: `Command + Shift + Left/Right/Up/Down`.
- Windows/Linux default shortcut: `Ctrl + Shift + Left/Right/Up/Down`.
- Customizable keys and modifiers in the add-on preferences.
- Configurable node gap for keeping links readable.
- Preserves the non-alignment axis. Up/Down never shifts nodes sideways, and Left/Right never shifts nodes vertically.
- Avoids visual overlap while keeping the layout as close as possible to the requested alignment.
- Treats selected Frames as top-level nodes when they are aligned with outside nodes.
- Aligns selected nodes inside a selected Frame to the Frame's inner boundary while preserving the configured gap.
- Multiple selected Frames follow the same alignment and spacing rules as regular nodes, including when selected child nodes are also included.
- Repeated Frame-internal alignment restores Frame and child-node positions to avoid accumulated drift.
- Frame-internal boundary alignment uses a separate `40` unit safe margin only as a movement limit, so shortcuts do not push already-stable child nodes in the opposite direction.
- Uses compact visual bounds for the Geometry Nodes Position input so bottom alignment matches what is visible in Blender.

## Installation

1. Download `Align_Node.zip`.
2. In Blender, open `Edit > Preferences > Add-ons`.
3. Click `Install...` and choose `Align_Node.zip`.
4. Enable `Align_Node`.

You can also install from source by copying the `Align_Node` folder into Blender's add-ons directory.

## Usage

Select two or more nodes in a node editor, then press:

- macOS: `Command + Shift + Arrow`
- Windows/Linux: `Ctrl + Shift + Arrow`

The add-on aligns the selected edge and only spreads nodes along the movement axis when their visual bounds would collide.

## Preferences

Open `Edit > Preferences > Add-ons > Align_Node`.

Available settings:

- Shortcut keys for Left, Right, Up, and Down.
- Modifier keys: Ctrl, Shift, Alt, Command.
- `Node Gap`: extra spacing between nodes after collision avoidance. The default value is `24`.

After changing shortcuts, click `Apply Node Align Shortcuts`.

## Debugging Bounds

Use `Debug Selected Node Bounds` in the add-on preferences or the node editor menu. The add-on writes the selected nodes' calculated bounds to a Blender text block named `PureRef_Node_Bounds_Debug` and also copies the output to the clipboard when Blender allows it.

The debug output includes `location_absolute` when Blender exposes it. After a Frame-internal alignment, it also includes the last internal Frame alignment diagnostics so boundary and drift behavior can be compared before and after the operation.

## Development

Run the unit tests from the repository root:

```bash
python3 -m unittest tests/test_alignment_logic.py
```

Build the installable zip:

```bash
zip -r Align_Node.zip Align_Node -x 'Align_Node/__pycache__/*'
```

## Maintainer

Anthem
