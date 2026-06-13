# Blender AI Assistant

A minimal Blender add-on that adds an AI assistant panel to the 3D viewport.

## Features

- Sidebar panel in the 3D View (`N` panel → **AI Assistant** tab)
- Text input field
- **Run Command** button that sends the text to Claude and **logs the returned
  actions** to the system console

The text → AI → JSON → console pipeline is wired up. The add-on sends your
command to Claude (`claude-opus-4-8`), which returns a JSON list of actions.
Those actions are printed to the console — they are **not executed in Blender
yet** (that's a later stage).

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
    ├── operator.py   # "Run Command" operator — logs the returned actions
    └── llm.py        # Claude API call → JSON list of actions
```
