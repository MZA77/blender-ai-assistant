import bpy


class AIASSISTANT_PT_panel(bpy.types.Panel):
    """Sidebar panel in the 3D viewport."""

    bl_label = "AI Assistant"
    bl_idname = "AIASSISTANT_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AI Assistant"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "ai_assistant_input", text="")

        row = layout.row(align=True)
        row.operator("aiassistant.run_command", text="Run Command", icon="PLAY")
        row.operator("aiassistant.voice_input", text="", icon="REC")

        layout.operator("aiassistant.clear_memory", text="Clear Memory", icon="TRASH")
