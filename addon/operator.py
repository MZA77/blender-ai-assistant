import json

import bpy

from . import executor, llm


class AIASSISTANT_OT_run_command(bpy.types.Operator):
    """Send the panel's text to Claude and execute the returned actions."""

    bl_idname = "aiassistant.run_command"
    bl_label = "Run Command"

    def execute(self, context):
        text = context.scene.ai_assistant_input
        prefs = context.preferences.addons[__package__].preferences

        # Structured snapshot of the scene (names, types, locations, materials)
        # so the planner can target and modify what already exists.
        state = executor.scene_state(context)
        scene_state = json.dumps(state) if state else "empty"

        result = llm.run(text, api_key=prefs.api_key, scene_state=scene_state)

        if not result["ok"]:
            print(f"[AI Assistant] Error: {result['error']}")
            self.report({"ERROR"}, result["error"])
            return {"CANCELLED"}

        actions = result["actions"]
        print(f"[AI Assistant] Command: {text}")
        print(f"[AI Assistant] Plan: {result['summary']}")
        print(f"[AI Assistant] {len(actions)} step(s) — executing:")

        # Turn the concrete primitive steps into real Blender objects.
        outcomes = executor.execute(actions)
        created = 0
        for action_type, ok, detail in outcomes:
            status = "ok" if ok else "FAILED"
            if ok:
                created += 1
            print(f"  [{status}] {action_type}: {detail}")

        self.report({"INFO"}, f"Created {created}/{len(actions)} object(s).")
        return {"FINISHED"}
