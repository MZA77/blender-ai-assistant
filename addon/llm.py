"""Claude API integration.

Sends the user's natural-language command to Claude and asks for a JSON list
of actions. This stage only RETURNS and logs the actions — it deliberately does
NOT execute anything in Blender yet.

Flow:  text  ->  Claude  ->  JSON {actions: [...]}  ->  returned to caller

Requires the official Anthropic SDK installed into Blender's bundled Python:
    <blender>/python/bin/python -m pip install anthropic
"""

import json
import os

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = (
    "You are an assistant embedded in Blender. The user describes what they want "
    "to do in the 3D scene in natural language. Translate their request into a "
    "list of discrete actions.\n\n"
    "You are only PLANNING — do not assume anything has been executed. Each action "
    "has:\n"
    "  - type: a short verb-like identifier (e.g. 'add_object', 'delete', 'move', "
    "'scale', 'rename').\n"
    "  - params: a JSON object, encoded as a string, holding that action's "
    "arguments, e.g. '{\"object_type\": \"cube\", \"location\": [0, 0, 0]}'.\n\n"
    "If the request is empty or unclear, return an empty action list."
)

# Structured-output schema. The API guarantees the response is valid JSON
# matching this shape. `params` is a JSON-encoded string so each action can
# carry arbitrary arguments (strict structured outputs disallow free-form
# objects, so we nest the flexible part as a string and decode it ourselves).
ACTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "params": {"type": "string"},
                },
                "required": ["type", "params"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["actions"],
    "additionalProperties": False,
}


def run(text, api_key=None):
    """Send `text` to Claude and return a result dict.

    Returns a dict with keys:
        ok      (bool)        — whether the call succeeded
        actions (list[dict])  — the planned actions (each: {type, params})
        error   (str | None)  — a human-readable message when ok is False
    """
    text = (text or "").strip()
    if not text:
        return {"ok": False, "actions": [], "error": "No command entered."}

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {
            "ok": False,
            "actions": [],
            "error": (
                "No API key. Set it in the add-on preferences (Edit > Preferences "
                "> Add-ons > Blender AI Assistant) or the ANTHROPIC_API_KEY "
                "environment variable."
            ),
        }

    try:
        import anthropic
    except ImportError:
        return {
            "ok": False,
            "actions": [],
            "error": (
                "The 'anthropic' package is not installed in Blender's Python. "
                "Install it with: <blender>/python/bin/python -m pip install anthropic"
            ),
        }

    try:
        client = anthropic.Anthropic(api_key=key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
            output_config={
                "format": {"type": "json_schema", "schema": ACTIONS_SCHEMA}
            },
        )
    except anthropic.APIError as exc:
        return {"ok": False, "actions": [], "error": f"API error: {exc}"}
    except Exception as exc:  # network failure, bad key, etc.
        return {"ok": False, "actions": [], "error": f"Request failed: {exc}"}

    if response.stop_reason == "refusal":
        return {"ok": False, "actions": [], "error": "Claude declined this request."}

    # output_config.format guarantees the first text block is valid JSON.
    raw = next((b.text for b in response.content if b.type == "text"), "")
    try:
        actions = json.loads(raw).get("actions", [])
    except (json.JSONDecodeError, AttributeError):
        return {"ok": False, "actions": [], "error": f"Could not parse response: {raw}"}

    # Decode each action's params (stored as a JSON string) for convenience.
    for action in actions:
        params = action.get("params")
        if isinstance(params, str):
            try:
                action["params"] = json.loads(params) if params else {}
            except json.JSONDecodeError:
                pass  # leave the raw string if it isn't valid JSON

    return {"ok": True, "actions": actions, "error": None}
