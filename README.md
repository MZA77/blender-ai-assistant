# Blender AI Assistant

A minimal Blender add-on that adds an AI assistant panel to the 3D viewport.

## Features

- Sidebar panel in the 3D View (`N` panel → **AI Assistant** tab)
- Text input field
- **Run Command** button that prints the input to the system console

## Install

1. Open Blender → **Edit → Preferences → Add-ons → Install...**
2. Select the `addon` folder (or a zip of it).
3. Enable **Blender AI Assistant** in the list.

> Tip: To see printed output, open **Window → Toggle System Console** (Windows)
> or launch Blender from a terminal (macOS/Linux).

## Usage

1. In the 3D viewport press `N` to open the sidebar.
2. Switch to the **AI Assistant** tab.
3. Type a command and click **Run Command**.

## Project structure

```
blender-ai-assistant/
└── addon/
    ├── __init__.py   # add-on registration
    ├── ui.py         # sidebar panel
    ├── operator.py   # "Run Command" operator
    └── llm.py        # command handling (LLM hook point)
```
