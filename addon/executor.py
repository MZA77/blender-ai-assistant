"""Action executor.

Takes the JSON actions produced by `llm.py` and turns them into real Blender
operations via `bpy.ops`. Actions run sequentially.

Supported actions:
  - create_cube   params: {"size": <number>}        default size 2.0
  - create_sphere params: {"color": "<name>"}        default color grey
"""

import bpy

# Named colors -> RGBA. Falls back to grey for anything unknown.
COLORS = {
    "red": (1.0, 0.0, 0.0, 1.0),
    "green": (0.0, 1.0, 0.0, 1.0),
    "blue": (0.0, 0.0, 1.0, 1.0),
    "yellow": (1.0, 1.0, 0.0, 1.0),
    "orange": (1.0, 0.5, 0.0, 1.0),
    "purple": (0.5, 0.0, 0.5, 1.0),
    "pink": (1.0, 0.4, 0.7, 1.0),
    "cyan": (0.0, 1.0, 1.0, 1.0),
    "white": (1.0, 1.0, 1.0, 1.0),
    "black": (0.0, 0.0, 0.0, 1.0),
    "grey": (0.8, 0.8, 0.8, 1.0),
    "gray": (0.8, 0.8, 0.8, 1.0),
}

# Spacing between successive objects so they don't all stack at the origin.
SPACING = 3.0


def _create_cube(params, location):
    size = params.get("size", 2.0)
    try:
        size = float(size)
    except (TypeError, ValueError):
        size = 2.0
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    return f"cube (size={size})"


def _create_sphere(params, location):
    color = str(params.get("color", "grey")).lower()
    rgba = COLORS.get(color, COLORS["grey"])

    bpy.ops.mesh.primitive_uv_sphere_add(location=location)
    obj = bpy.context.active_object

    # Build a material and set the color in both the viewport-display slot and
    # the Principled BSDF base color so it shows in every shading mode.
    mat = bpy.data.materials.new(name=f"{color}_material")
    mat.diffuse_color = rgba  # Solid-mode viewport display
    if mat.use_nodes and mat.node_tree:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = rgba
    obj.data.materials.append(mat)

    return f"sphere (color={color})"


HANDLERS = {
    "create_cube": _create_cube,
    "create_sphere": _create_sphere,
}


def execute(actions):
    """Run each action in order.

    Returns a list of (type, ok, detail) tuples describing what happened.
    """
    results = []
    for i, action in enumerate(actions):
        action_type = action.get("type")
        params = action.get("params")
        if not isinstance(params, dict):
            params = {}

        handler = HANDLERS.get(action_type)
        if handler is None:
            results.append((action_type, False, "unsupported action"))
            continue

        location = (i * SPACING, 0.0, 0.0)
        try:
            detail = handler(params, location)
            results.append((action_type, True, detail))
        except Exception as exc:  # keep going even if one action fails
            results.append((action_type, False, str(exc)))

    return results
