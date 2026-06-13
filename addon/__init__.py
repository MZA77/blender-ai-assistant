bl_info = {
    "name": "Blender AI Assistant",
    "author": "Zia Ahmed",
    "version": (0, 5, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > AI Assistant",
    "description": "Minimal AI assistant panel for the 3D viewport (Claude-powered).",
    "category": "3D View",
}

import bpy

from . import operator, ui


class AIASSISTANT_AddonPreferences(bpy.types.AddonPreferences):
    """Add-on preferences — holds the Claude API key."""

    bl_idname = __package__

    api_key: bpy.props.StringProperty(
        name="Anthropic API Key",
        description="Your Claude API key (or set the ANTHROPIC_API_KEY env var)",
        default="",
        subtype="PASSWORD",
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "api_key")
        layout.label(text="Get a key at console.anthropic.com")
        layout.label(text="Requires the 'anthropic' package in Blender's Python.")


classes = (
    AIASSISTANT_AddonPreferences,
    operator.AIASSISTANT_OT_run_command,
    ui.AIASSISTANT_PT_panel,
)


def register():
    bpy.types.Scene.ai_assistant_input = bpy.props.StringProperty(
        name="Command",
        description="Text to send to the assistant",
        default="",
    )
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.ai_assistant_input


if __name__ == "__main__":
    register()
