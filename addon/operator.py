import bpy

from . import executor, llm


class AIASSISTANT_OT_run_command(bpy.types.Operator):
    """Send the panel's text to Claude and execute the returned actions."""

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

        actions = result["actions"]
        print(f"[AI Assistant] Command: {text}")
        print(f"[AI Assistant] {len(actions)} action(s) returned — executing:")

        # Turn the JSON actions into real Blender objects.
        outcomes = executor.execute(actions)
        created = 0
        for action_type, ok, detail in outcomes:
            status = "ok" if ok else "FAILED"
            if ok:
                created += 1
            print(f"  [{status}] {action_type}: {detail}")

        self.report({"INFO"}, f"Created {created}/{len(actions)} object(s).")
        return {"FINISHED"}
