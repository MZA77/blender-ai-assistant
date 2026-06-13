"""Planning layer.

Interprets intent and emits a Scene Edit Language (SEL) plan: a list of
`{action, target, params}` edits — creating primitives, setting materials, and
transforming objects. The intelligence (spatial + material reasoning) lives
here; the executor (`executor.py`) is deliberately dumb.

Flow:  text + scene state  ->  Claude  ->  {summary, actions: [...]}

Requires the official Anthropic SDK installed into Blender's bundled Python:
    <blender>/python/bin/python -m pip install anthropic
"""

import json
import os

MODEL = "claude-opus-4-8"

# Conversation memory for the current Blender session. Lets references like
# "it" / "the sphere" / "make it brighter" resolve across messages. Holds
# alternating user/assistant turns, trimmed to the last MAX_HISTORY_MESSAGES.
_history = []
MAX_HISTORY_MESSAGES = 12


def reset_history():
    """Forget the conversation so far."""
    _history.clear()

SYSTEM_PROMPT = (
    "You are a Blender Scene Editor AI. You do NOT write Python. You output a "
    "structured plan; a dumb executor runs it. You do all the spatial and "
    "material reasoning yourself.\n\n"
    "Each action is {action, target, params}, where params is a JSON OBJECT "
    "ENCODED AS A STRING.\n\n"
    "CREATE actions — `target` is a NEW, unique name you assign (e.g. "
    "'tower_1', 'sphere_1'):\n"
    "  - create_cube     {\"size\": n, \"location\": [x,y,z], \"scale\": [x,y,z], "
    "\"rotation\": [rx,ry,rz], \"color\": \"name\"}\n"
    "  - create_cylinder {\"radius\": n, \"depth\": n, \"location\": [..], "
    "\"rotation\": [..], \"color\": \"name\"}\n"
    "  - create_cone     {\"radius\": n, \"depth\": n, \"location\": [..], "
    "\"rotation\": [..], \"color\": \"name\"}  (roofs/spikes)\n"
    "  - create_sphere   {\"radius\": n, \"location\": [..], \"color\": \"name\"}\n"
    "  - create_plane    {\"size\": n, \"location\": [..], \"color\": \"name\"}  (ground)\n"
    "  - add_light       {\"light_type\": \"POINT|SUN|SPOT|AREA\", \"energy\": n, "
    "\"location\": [..], \"color\": \"name\"}\n\n"
    "EDIT actions — `target` is the EXACT name of an existing object from the "
    "scene state:\n"
    "  - set_material {\"base_color\": [r,g,b], \"roughness\": 0-1, "
    "\"metallic\": 0-1, \"emission_strength\": 0-10, \"emission_color\": [r,g,b]}\n"
    "  - transform_object {\"location\": [x,y,z] OR \"behind:name\" / \"front:name\" "
    "/ \"left:name\" / \"right:name\" / \"above:name\" / \"on:name\" / "
    "\"below:name\", \"rotation\": [rx,ry,rz], \"scale\": [x,y,z]}\n\n"
    "Conventions: colors as [r,g,b] floats 0-1 (or a name: red, green, blue, "
    "yellow, orange, purple, pink, cyan, brown, white, black, grey). +Z is up. "
    "rotation in DEGREES. An object of size S spans S/2 each side of its location "
    "— rest things on the ground/each other.\n\n"
    "Material intelligence — translate description into PBR params:\n"
    "  - bright / glowing / neon  -> emission_strength 2-10 (+ emission_color)\n"
    "  - soft / matte             -> roughness 0.7-1.0\n"
    "  - shiny / glossy           -> roughness 0.0-0.3\n"
    "  - metallic / metal         -> metallic 0.8-1.0\n"
    "  - plastic                  -> roughness ~0.4, metallic 0\n"
    "  - dark                     -> low base_color values\n\n"
    "Use the prior conversation AND the scene state for context. When the user "
    "refers to something by pronoun or description ('it', 'the sphere', 'make it "
    "brighter', 'move them up'), resolve it to the right existing object — match "
    "it to an exact name in the scene state — and EDIT that object rather than "
    "creating a new one. Create only what doesn't "
    "exist yet. To build a structure, place concrete primitives at real "
    "coordinates (e.g. castle = ground plane + corner cylinder towers + stretched "
    "cube walls + cone roofs).\n\n"
    "Keep it recognizable: roughly 1-30 actions. Also return a short 'summary' "
    "(one or two sentences) of your plan. If the request is impossible with these "
    "actions, return an empty list and say why in the summary."
)

# Structured-output schema for a SEL plan.
PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "target": {"type": "string"},
                    "params": {"type": "string"},
                },
                "required": ["action", "target", "params"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "actions"],
    "additionalProperties": False,
}


def run(text, api_key=None, scene_state=None):
    """Plan scene edits from `text` and return a result dict.

    Returns a dict with keys:
        ok      (bool)        — whether the call succeeded
        summary (str)         — the plan the editor chose
        actions (list[dict])  — SEL edits (each: {action, target, params})
        error   (str | None)  — a human-readable message when ok is False
    """
    text = (text or "").strip()
    if not text:
        return {"ok": False, "summary": "", "actions": [], "error": "No command entered."}

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return {
            "ok": False,
            "summary": "",
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
            "summary": "",
            "actions": [],
            "error": (
                "The 'anthropic' package is not installed in Blender's Python. "
                "Install it with: <blender>/python/bin/python -m pip install anthropic"
            ),
        }

    user_content = f"User request:\n{text}\n\nScene state:\n{scene_state or 'empty'}"

    try:
        client = anthropic.Anthropic(api_key=key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=8192,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            messages=_history + [{"role": "user", "content": user_content}],
            output_config={"format": {"type": "json_schema", "schema": PLAN_SCHEMA}},
        )
    except anthropic.APIError as exc:
        return {"ok": False, "summary": "", "actions": [], "error": f"API error: {exc}"}
    except Exception as exc:  # network failure, bad key, etc.
        return {"ok": False, "summary": "", "actions": [], "error": f"Request failed: {exc}"}

    if response.stop_reason == "refusal":
        return {
            "ok": False,
            "summary": "",
            "actions": [],
            "error": "Claude declined this request.",
        }

    # output_config.format guarantees the first text block is valid JSON.
    raw = next((b.text for b in response.content if b.type == "text"), "")
    try:
        plan = json.loads(raw)
        actions = plan.get("actions", [])
        summary = plan.get("summary", "")
    except (json.JSONDecodeError, AttributeError):
        return {
            "ok": False,
            "summary": "",
            "actions": [],
            "error": f"Could not parse response: {raw}",
        }

    # Decode each action's params (stored as a JSON string) into a dict.
    for action in actions:
        params = action.get("params")
        if isinstance(params, str):
            try:
                action["params"] = json.loads(params) if params else {}
            except json.JSONDecodeError:
                pass  # leave the raw string; the executor tolerates it

    # Record this turn so later messages can resolve references like "it".
    # We store the plain request (not the scene state, which is sent fresh each
    # call) and a compact note of what was done, including affected object names.
    _history.append({"role": "user", "content": text})
    targets = list(dict.fromkeys(a.get("target") for a in actions if a.get("target")))
    note = summary or "(done)"
    if targets:
        note += " | objects: " + ", ".join(targets)
    _history.append({"role": "assistant", "content": note})
    if len(_history) > MAX_HISTORY_MESSAGES:
        del _history[: len(_history) - MAX_HISTORY_MESSAGES]

    return {"ok": True, "summary": summary, "actions": actions, "error": None}
