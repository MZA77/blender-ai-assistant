import bpy

from . import llm


class AIASSISTANT_OT_run_command(bpy.types.Operator):
    """Send the panel's text to Claude and log the returned actions."""

    bl_idname = "aiassistant.run_command"
    bl_label = "Run Command"

    def execute(self, context):
        text = context.scene.ai_assistant_input
        prefs = context.preferences.addons[__package__].preferences

        result = llm.run(text, api_key=prefs.api_key)

        if not result["ok"]:
            print(f"[AI Assistant] Error: {result['error']}")
            self.report({"ERROR"}, result["error"])
            return {"CANCELLED"}

        # This stage only logs the plan — actions are NOT executed yet.
        actions = result["actions"]
        print(f"[AI Assistant] Command: {text}")
        print(f"[AI Assistant] {len(actions)} action(s) returned (not executed):")
        for i, action in enumerate(actions, 1):
            print(f"  {i}. {action.get('type')}  params={action.get('params')}")

        self.report({"INFO"}, f"{len(actions)} action(s) logged to console.")
        return {"FINISHED"}
