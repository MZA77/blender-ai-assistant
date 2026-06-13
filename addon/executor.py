"""Execution layer — a Scene Edit Language (SEL) dispatcher.

Every action is `{action, target, params}`. The executor stays dumb: it knows
primitives, transforms, materials, and lights — never high-level concepts. All
interpretation lives in the planning layer (`llm.py`).

Create actions   (target = the NEW name to assign):
  create_cube / create_cylinder / create_cone / create_sphere / create_plane
  add_light
Edit actions     (target = an EXISTING object name):
  set_material      params: base_color, roughness, metallic, emission_strength,
                            emission_color
  transform_object  params: location ([x,y,z] or "behind:name" etc.), rotation
                            ([deg x,y,z]), scale

`scene_state(context)` reads the current scene (incl. material values) so the
planner can target and modify what already exists.
"""

import json
import math

import bpy

# Named colors -> RGBA. Unknown names fall back to grey.
COLORS = {
    "red": (1.0, 0.0, 0.0, 1.0),
    "green": (0.0, 1.0, 0.0, 1.0),
    "blue": (0.0, 0.0, 1.0, 1.0),
    "yellow": (1.0, 1.0, 0.0, 1.0),
    "orange": (1.0, 0.5, 0.0, 1.0),
    "purple": (0.5, 0.0, 0.5, 1.0),
    "pink": (1.0, 0.4, 0.7, 1.0),
    "cyan": (0.0, 1.0, 1.0, 1.0),
    "brown": (0.4, 0.26, 0.13, 1.0),
    "white": (1.0, 1.0, 1.0, 1.0),
    "black": (0.05, 0.05, 0.05, 1.0),
    "grey": (0.5, 0.5, 0.5, 1.0),
    "gray": (0.5, 0.5, 0.5, 1.0),
}

# Fallback spacing when a create action provides no explicit location.
SPACING = 3.0

# Principled BSDF emission-color socket name varies by Blender version.
_EMISSION_COLOR_NAMES = ("Emission Color", "Emission")


# --- parameter helpers --------------------------------------------------------

def _num(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _xyz(value, default=(0.0, 0.0, 0.0)):
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        try:
            return (float(value[0]), float(value[1]), float(value[2]))
        except (TypeError, ValueError):
            return default
    return default


def _euler(value):
    """Rotation given in degrees -> radians tuple for Blender."""
    return tuple(math.radians(a) for a in _xyz(value))


def _rgba(value):
    """Accept [r,g,b], [r,g,b,a], or a named color -> RGBA tuple."""
    if isinstance(value, str):
        return COLORS.get(value.lower(), COLORS["grey"])
    if isinstance(value, (list, tuple)):
        vals = [float(c) for c in value]
        if len(vals) == 3:
            return (vals[0], vals[1], vals[2], 1.0)
        if len(vals) >= 4:
            return (vals[0], vals[1], vals[2], vals[3])
    return COLORS["grey"]


# --- material helpers ---------------------------------------------------------

def _principled(mat):
    if mat.use_nodes and mat.node_tree:
        return mat.node_tree.nodes.get("Principled BSDF")
    return None


def _set_input(bsdf, names, value):
    for name in names:
        if name in bsdf.inputs:
            bsdf.inputs[name].default_value = value
            return True
    return False


def _get_or_create_material(obj):
    if obj.data and getattr(obj.data, "materials", None) and obj.data.materials:
        mat = obj.data.materials[0]
        if mat:
            mat.use_nodes = True
            return mat
    mat = bpy.data.materials.new(name=f"{obj.name}_material")
    mat.use_nodes = True
    if obj.data and hasattr(obj.data, "materials"):
        obj.data.materials.append(mat)
    return mat


def _assign_simple_color(obj, color):
    """Quick named/RGB color used by create actions."""
    rgba = _rgba(color)
    mat = _get_or_create_material(obj)
    mat.diffuse_color = rgba
    bsdf = _principled(mat)
    if bsdf:
        _set_input(bsdf, ["Base Color"], rgba)


def read_material(obj):
    """Summarize an object's first material for the scene state, or None."""
    if not (obj.data and getattr(obj.data, "materials", None) and obj.data.materials):
        return None
    mat = obj.data.materials[0]
    bsdf = _principled(mat) if mat else None
    if not bsdf:
        return None

    def get(names):
        for name in names:
            if name in bsdf.inputs:
                v = bsdf.inputs[name].default_value
                try:
                    return [round(float(x), 3) for x in v]
                except TypeError:
                    return round(float(v), 3)
        return None

    return {
        "base_color": get(["Base Color"]),
        "roughness": get(["Roughness"]),
        "metallic": get(["Metallic"]),
        "emission_strength": get(["Emission Strength"]),
    }


def scene_state(context):
    """A JSON-serializable snapshot of the scene for the planner."""
    out = []
    for obj in context.scene.objects:
        entry = {
            "name": obj.name,
            "type": obj.type,
            "location": [round(c, 2) for c in obj.location],
        }
        material = read_material(obj)
        if material:
            entry["material"] = material
        out.append(entry)
    return out


# --- create handlers ----------------------------------------------------------

def _finish(obj, params):
    scale = params.get("scale")
    if isinstance(scale, (int, float)):
        obj.scale = (float(scale),) * 3
    elif isinstance(scale, (list, tuple)):
        obj.scale = _xyz(scale, (1.0, 1.0, 1.0))
    color = params.get("color")
    if color:
        _assign_simple_color(obj, color)


def _create_cube(params):
    size = _num(params.get("size"), 2.0)
    bpy.ops.mesh.primitive_cube_add(
        size=size, location=_xyz(params.get("location")),
        rotation=_euler(params.get("rotation")),
    )
    _finish(bpy.context.active_object, params)
    return f"cube size={size}"


def _create_cylinder(params):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=_num(params.get("radius"), 1.0),
        depth=_num(params.get("depth"), 2.0),
        location=_xyz(params.get("location")),
        rotation=_euler(params.get("rotation")),
    )
    _finish(bpy.context.active_object, params)
    return "cylinder"


def _create_cone(params):
    bpy.ops.mesh.primitive_cone_add(
        radius1=_num(params.get("radius"), 1.0),
        depth=_num(params.get("depth"), 2.0),
        location=_xyz(params.get("location")),
        rotation=_euler(params.get("rotation")),
    )
    _finish(bpy.context.active_object, params)
    return "cone"


def _create_sphere(params):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=_num(params.get("radius"), 1.0),
        location=_xyz(params.get("location")),
    )
    _finish(bpy.context.active_object, params)
    return "sphere"


def _create_plane(params):
    size = _num(params.get("size"), 10.0)
    bpy.ops.mesh.primitive_plane_add(
        size=size, location=_xyz(params.get("location")),
        rotation=_euler(params.get("rotation")),
    )
    _finish(bpy.context.active_object, params)
    return f"plane size={size}"


def _add_light(params):
    light_type = str(params.get("light_type", "POINT")).upper()
    if light_type not in {"POINT", "SUN", "SPOT", "AREA"}:
        light_type = "POINT"
    bpy.ops.object.light_add(
        type=light_type, location=_xyz(params.get("location"), (0.0, 0.0, 5.0))
    )
    obj = bpy.context.active_object
    energy = params.get("energy")
    if energy is not None:
        obj.data.energy = _num(energy, obj.data.energy)
    color = params.get("color")
    if color:
        obj.data.color = _rgba(color)[:3]
    return f"{light_type.lower()} light"


CREATE_HANDLERS = {
    "create_cube": _create_cube,
    "create_cylinder": _create_cylinder,
    "create_cone": _create_cone,
    "create_sphere": _create_sphere,
    "create_plane": _create_plane,
    "add_light": _add_light,
}


# --- edit handlers ------------------------------------------------------------

def _set_material(obj, params):
    mat = _get_or_create_material(obj)
    bsdf = _principled(mat)
    if bsdf is None:
        return f"no Principled BSDF on {obj.name}"

    base = params.get("base_color")
    if base is not None:
        rgba = _rgba(base)
        _set_input(bsdf, ["Base Color"], rgba)
        mat.diffuse_color = rgba
    if "roughness" in params:
        _set_input(bsdf, ["Roughness"], _num(params["roughness"], 0.5))
    if "metallic" in params:
        _set_input(bsdf, ["Metallic"], _num(params["metallic"], 0.0))

    emission_color = params.get("emission_color")
    if emission_color is not None:
        _set_input(bsdf, list(_EMISSION_COLOR_NAMES), _rgba(emission_color))
    if "emission_strength" in params:
        _set_input(bsdf, ["Emission Strength"], _num(params["emission_strength"], 0.0))

    return f"material on {obj.name}"


def _resolve_relative(spec, obj):
    """Resolve 'keyword:target_name' to a coordinate near the named object."""
    try:
        keyword, ref_name = spec.split(":", 1)
    except ValueError:
        return None
    ref = bpy.data.objects.get(ref_name.strip())
    if ref is None:
        return None

    keyword = keyword.strip().lower()
    base = list(ref.location)
    gap = 1.0
    rd = ref.dimensions
    od = obj.dimensions

    if keyword in ("behind", "back"):
        base[1] += rd.y / 2 + od.y / 2 + gap
    elif keyword in ("front", "infront"):
        base[1] -= rd.y / 2 + od.y / 2 + gap
    elif keyword == "right":
        base[0] += rd.x / 2 + od.x / 2 + gap
    elif keyword == "left":
        base[0] -= rd.x / 2 + od.x / 2 + gap
    elif keyword in ("above", "over"):
        base[2] += rd.z / 2 + od.z / 2 + gap
    elif keyword == "on":
        base[2] += rd.z / 2 + od.z / 2
    elif keyword in ("below", "under"):
        base[2] -= rd.z / 2 + od.z / 2 + gap
    else:
        return None
    return tuple(base)


def _transform_object(obj, params):
    location = params.get("location")
    if isinstance(location, str):
        resolved = _resolve_relative(location, obj)
        if resolved is not None:
            obj.location = resolved
    elif isinstance(location, (list, tuple)):
        obj.location = _xyz(location, tuple(obj.location))

    rotation = params.get("rotation")
    if rotation is not None:
        obj.rotation_euler = _euler(rotation)

    scale = params.get("scale")
    if isinstance(scale, (int, float)):
        obj.scale = (float(scale),) * 3
    elif isinstance(scale, (list, tuple)):
        obj.scale = _xyz(scale, tuple(obj.scale))

    return f"transformed {obj.name}"


EDIT_HANDLERS = {
    "set_material": _set_material,
    "transform_object": _transform_object,
}


# --- dispatcher ---------------------------------------------------------------

def execute(actions):
    """Run each SEL action in order.

    Returns a list of (action, ok, detail) tuples describing what happened.
    """
    results = []
    for i, action in enumerate(actions):
        name = action.get("action")
        target = action.get("target")

        raw = action.get("params")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                raw = {}
        params = dict(raw) if isinstance(raw, dict) else {}

        try:
            if name in CREATE_HANDLERS:
                if name.startswith("create_") and "location" not in params:
                    params["location"] = [i * SPACING, 0.0, 0.0]
                detail = CREATE_HANDLERS[name](params)
                obj = bpy.context.active_object
                if target and obj:
                    obj.name = target
                    detail = f"{detail} -> {obj.name}"
                results.append((name, True, detail))
            elif name in EDIT_HANDLERS:
                obj = bpy.data.objects.get(target) if target else None
                if obj is None:
                    results.append((name, False, f"object not found: {target}"))
                    continue
                detail = EDIT_HANDLERS[name](obj, params)
                results.append((name, True, detail))
            else:
                results.append((name, False, "unsupported action"))
        except Exception as exc:  # keep going even if one step fails
            results.append((name, False, str(exc)))

    return results
