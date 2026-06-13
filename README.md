# Blender AI Assistant

A minimal Blender add-on that adds an AI assistant panel to the 3D viewport.

## Features

- Sidebar panel in the 3D View (`N` panel → **AI Assistant** tab)
- Text input field
- **Run Command** button that sends the text to Claude and **executes the
  resulting scene plan** in the viewport

### Architecture — a small text-to-3D compiler

```
your words → planning layer (Claude) → scene plan (concrete primitives) → executor (bpy.ops) → 3D
```

The intelligence lives in the **planning layer**: Claude interprets intent,
chooses a construction strategy, and emits a list of primitive placements with
real coordinates (it does the spatial reasoning). The **executor is deliberately
dumb** — it only knows primitives, transforms, colors, and lights, and has no
concept of a "castle" or "tower". That's what makes it open-ended: new kinds of
scenes need no new executor code, only better planning by the AI.

### Scene Edit Language (SEL)

Every action is `{action, target, params}`. The planner can **create** geometry
and **edit existing objects** (materials, transforms). Because each request also
receives a snapshot of the scene (object names, locations, and material values),
follow-ups like *"make the sphere brighter"* resolve against what's already
there.

**Create actions** (`target` = a new name the planner assigns, e.g. `tower_1`):

| Action | Key params |
| --- | --- |
| `create_cube` | `size`, `location`, `scale`, `rotation`, `color` |
| `create_cylinder` | `radius`, `depth`, `location`, `rotation`, `color` |
| `create_cone` | `radius`, `depth`, `location`, `rotation`, `color` |
| `create_sphere` | `radius`, `location`, `color` |
| `create_plane` | `size`, `location`, `color` |
| `add_light` | `light_type`, `energy`, `location`, `color` |

**Edit actions** (`target` = an existing object's name):

| Action | Key params |
| --- | --- |
| `set_material` | `base_color`, `roughness`, `metallic`, `emission_strength`, `emission_color` |
| `transform_object` | `location` (`[x,y,z]` or `"behind:name"`, `"above:name"`, …), `rotation`, `scale` |

`location`/`scale`/`rotation` are `[x, y, z]`; rotation is in **degrees**, +Z up.
Colors are `[r,g,b]` (0–1) or names. `transform_object` accepts relative
positions like `behind:`, `front:`, `left:`, `right:`, `above:`, `on:`,
`below:` followed by an object name, resolved from that object's live position
and size.

**Material intelligence** — the planner maps language to PBR params: bright /
glowing → emission, matte → high roughness, shiny → low roughness, metallic →
high metallic, dark → low base color.

Examples:
- `create 2 cubes and a red sphere`
- `build a small medieval castle with stone walls, corner towers, and moody lighting`
- `make the sphere bright glowing red and move it behind the castle base`

## Install

1. Open Blender → **Edit → Preferences → Add-ons → Install...**
2. Select the `addon` folder (or a zip of it).
3. Enable **Blender AI Assistant** in the list.

> Tip: To see printed output, open **Window → Toggle System Console** (Windows)
> or launch Blender from a terminal (macOS/Linux).

## Setup (required for the AI stage)

1. **Install the Anthropic SDK into Blender's bundled Python.** Find Blender's
   Python and run:
   ```
   <blender-install>/python/bin/python -m pip install anthropic
   ```
   (On Windows the path looks like
   `C:\Program Files\Blender Foundation\Blender X.X\X.X\python\bin\python.exe`.)
2. **Add your API key.** In the add-on's preferences (the row you enabled it on,
   expanded), paste your key into **Anthropic API Key**. Get one at
   [console.anthropic.com](https://console.anthropic.com). Alternatively set the
   `ANTHROPIC_API_KEY` environment variable before launching Blender.

## Usage

1. In the 3D viewport press `N` to open the sidebar.
2. Switch to the **AI Assistant** tab.
3. Type a command (e.g. *"add a cube at the origin and a sphere above it"*) and
   click **Run Command**.
4. Open the system console — the planned actions are printed there as a numbered
   list. Nothing is executed in the scene yet.

## Project structure

```
blender-ai-assistant/
└── addon/
    ├── __init__.py   # add-on registration
    ├── ui.py         # sidebar panel
    ├── operator.py   # "Run Command" operator — orchestrates plan → execute
    ├── llm.py        # planning layer: intent → scene plan (concrete primitives)
    └── executor.py   # execution layer: primitives → bpy.ops calls
```
