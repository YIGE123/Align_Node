# Align_Node

Blender node editor alignment add-on for Geometry Nodes, shader/material nodes, compositor nodes, and other node trees.

## Features

- Align selected nodes to the left, right, top, or bottom edge.
- PureRef-style keyboard workflow.
- macOS default shortcut: `Command + Shift + Left/Right/Up/Down`.
- Windows/Linux default shortcut: `Ctrl + Left/Right/Up/Down`.
- Customizable keys and modifiers in the add-on preferences.
- Configurable node gap for keeping links readable.
- Preserves the non-alignment axis. Up/Down never shifts nodes sideways, and Left/Right never shifts nodes vertically.
- Avoids visual overlap while keeping the layout as close as possible to the requested alignment.

## Installation

1. Download `Align_Node.zip`.
2. In Blender, open `Edit > Preferences > Add-ons`.
3. Click `Install...` and choose `Align_Node.zip`.
4. Enable `Align_Node`.

You can also install from source by copying the `Align_Node` folder into Blender's add-ons directory.

## Usage

Select two or more nodes in a node editor, then press:

- macOS: `Command + Shift + Arrow`
- Windows/Linux: `Ctrl + Arrow`

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

This is useful for reporting alignment edge cases.

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
