import bpy

from . import llm


class AIASSISTANT_OT_run_command(bpy.types.Operator):
    """Run the command typed into the panel."""

    bl_idname = "aiassistant.run_command"
    bl_label = "Run Command"

    def execute(self, context):
        text = context.scene.ai_assistant_input
        result = llm.run(text)
        print(result)
        self.report({"INFO"}, result)
        return {"FINISHED"}
