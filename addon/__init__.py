bl_info = {
    "name": "Blender AI Assistant",
    "author": "Zia Ahmed",
    "version": (0, 1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > AI Assistant",
    "description": "Minimal AI assistant panel for the 3D viewport.",
    "category": "3D View",
}

from . import operator, ui

# Property holding the user's text input, attached to the Scene so the
# panel and operator can share it.
import bpy


classes = (
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
