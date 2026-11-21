"""Render saved Doesbot V24 meshes in Blender; run with Blender's --python argument.

This is a visualization pipeline, not a geometry generator. It imports the saved
lid/base STL files and the positioned assembly OBJ without scaling or rotating
them. Only the exploded view applies presentation-only Z translations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lid", type=Path, required=True, help="V24 lid STL")
    parser.add_argument("--base", type=Path, required=True, help="V24 base STL")
    parser.add_argument("--assembly", type=Path, required=True, help="saved PCB and component placement OBJ")
    parser.add_argument("--config", type=Path, required=True, help="render settings JSON")
    parser.add_argument("--output-dir", type=Path, required=True, help="directory for 4K or preview PNGs")
    parser.add_argument("--preset", choices=("draft", "web", "master"), default="master")
    parser.add_argument("--device", choices=("auto", "metal", "cpu"), help="override the device in the render config")
    parser.add_argument("--views", nargs="+", help="view names; defaults to all views in config")
    return parser.parse_args(argv)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights, bpy.data.materials):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def material(name: str, settings: dict) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = tuple(settings["color"])
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = tuple(settings["color"])
    shader.inputs["Roughness"].default_value = float(settings.get("roughness", 0.5))
    shader.inputs["Metallic"].default_value = float(settings.get("metallic", 0.0))
    return mat


def assign(obj: bpy.types.Object, mat: bpy.types.Material, kind: str) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    obj["showcase_part"] = kind


def imported_meshes(before: set[bpy.types.Object]) -> list[bpy.types.Object]:
    return [obj for obj in bpy.context.scene.objects if obj not in before and obj.type == "MESH"]


def import_stl(path: Path, part: str, mat: bpy.types.Material) -> list[bpy.types.Object]:
    before = set(bpy.context.scene.objects)
    bpy.ops.wm.stl_import(filepath=str(path))
    objects = imported_meshes(before)
    if not objects:
        raise RuntimeError(f"Blender did not import a mesh from {path}")
    for obj in objects:
        assign(obj, mat, part)
    return objects


def classify_component(name: str) -> str:
    folded = name.casefold()
    if "r07" in folded:
        return "r07"
    if "r08" in folded:
        return "r08"
    if any(token in folded for token in ("contact", "pin", "header")):
        return "pins"
    return "components"


def import_assembly(path: Path, mats: dict[str, bpy.types.Material]) -> dict[str, list[bpy.types.Object]]:
    before = set(bpy.context.scene.objects)
    # The exported OBJ is already in the shared CAD frame: X/Y plan, Z up.
    # Explicit axes prevent Blender's Y-up default from rotating the PCB.
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis="Y", up_axis="Z")
    objects = imported_meshes(before)
    if not objects:
        raise RuntimeError(f"Blender did not import a mesh from {path}")
    groups: dict[str, list[bpy.types.Object]] = {key: [] for key in ("base", "pcb", "components", "r07", "r08", "pins")}
    for obj in objects:
        name = obj.name.casefold()
        # The V24 base STL is the printable base. Avoid rendering the duplicate
        # lower shell contained in the assembly-reference OBJ.
        if "scaled_bottom" in name or "enclosure_bottom" in name:
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        if "pcb" in name:
            kind = "pcb"
        else:
            kind = classify_component(obj.name)
        assign(obj, mats[kind], kind)
        groups[kind].append(obj)
    groups["base"] = []
    return groups


def bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    if not points:
        raise RuntimeError("No geometry selected for this view")
    return Vector(tuple(min(p[i] for p in points) for i in range(3))), Vector(
        tuple(max(p[i] for p in points) for i in range(3))
    )


def add_lighting(config: dict, center: Vector, span: float) -> list[bpy.types.Object]:
    scene = bpy.context.scene
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (*config["scene"]["world_color"], 1.0)
    background.inputs["Strength"].default_value = float(config["scene"]["world_strength"])
    created = []
    for row in config["lighting"]["area_lights"]:
        data = bpy.data.lights.new(row["name"], type="AREA")
        data.energy = float(row["watts"])
        data.shape = "DISK"
        data.size = max(span * float(row["size_fraction"]), 1.0)
        data.color = tuple(row.get("color", [1.0, 1.0, 1.0]))
        obj = bpy.data.objects.new(row["name"], data)
        scene.collection.objects.link(obj)
        offset = Vector(row["offset"]) * span
        obj.location = center + offset
        obj.rotation_euler = (center - obj.location).to_track_quat("-Z", "Y").to_euler()
        created.append(obj)
    return created


def add_floor(config: dict, center: Vector, low: Vector, span: float) -> bpy.types.Object:
    margin = float(config["lighting"].get("floor_margin_fraction", 0.12))
    z = low.z - span * margin
    bpy.ops.mesh.primitive_plane_add(size=span * 18.0, location=(center.x, center.y, z))
    floor = bpy.context.object
    floor.name = "Render-only studio floor"
    floor.data.materials.append(material("Studio floor", config["materials"]["floor"]))
    floor["render_stage_only"] = True
    return floor


def create_camera(view: dict, center: Vector, span: float, multiplier: float) -> bpy.types.Object:
    data = bpy.data.cameras.new("Showcase camera")
    data.type = "ORTHO"
    data.ortho_scale = max(span * float(view["scale_fraction"]) * multiplier, 1.0)
    obj = bpy.data.objects.new("Showcase camera", data)
    bpy.context.scene.collection.objects.link(obj)
    direction = Vector(view["direction"]).normalized()
    distance = span * 3.0
    obj.location = center + direction * distance
    obj.rotation_euler = (center - obj.location).to_track_quat("-Z", "Y").to_euler()
    data.clip_start = 0.01
    data.clip_end = span * 30.0
    bpy.context.scene.camera = obj
    return obj


def configure_scene(config: dict, profile: dict, device: str) -> str:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = float(config["scene"].get("unit_scale_meters_per_blender_unit", 0.001))
    scene.view_settings.view_transform = config["scene"].get("view_transform", "AgX")
    scene.view_settings.look = config["scene"].get("look", "AgX - Medium High Contrast")
    scene.view_settings.exposure = float(config["scene"].get("exposure", 0.0))
    scene.render.resolution_x, scene.render.resolution_y = map(int, profile["resolution"])
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.compression = 18
    scene.render.film_transparent = bool(config["scene"].get("film_transparent", False))
    scene.cycles.samples = int(profile["samples"])
    scene.cycles.use_denoising = bool(profile.get("denoise", True))
    scene.cycles.device = "CPU"
    selected_device = "CPU"
    if device != "cpu":
        try:
            preferences = bpy.context.preferences.addons["cycles"].preferences
            preferences.compute_device_type = "METAL"
            preferences.get_devices()
            metal_devices = [item for item in preferences.devices if item.type == "METAL"]
            for item in preferences.devices:
                item.use = item.type == "METAL"
            if metal_devices:
                scene.cycles.device = "GPU"
                selected_device = "METAL: " + ", ".join(item.name for item in metal_devices)
            elif device == "metal":
                raise RuntimeError("Metal was requested but Blender did not expose a Metal device")
        except Exception as exc:
            if device == "metal":
                raise
            print(f"Metal unavailable; using CPU: {exc}")
    if device == "metal" and selected_device == "CPU":
        raise RuntimeError("Metal device selection failed")
    return selected_device


def render_view(
    name: str,
    view: dict,
    groups: dict[str, list[bpy.types.Object]],
    config: dict,
    profile: dict,
    output_dir: Path,
    quality: str,
) -> dict:
    scene = bpy.context.scene
    included = set(view["include"])
    all_parts = {obj for objects in groups.values() for obj in objects}
    stored_locations = {obj: obj.location.copy() for obj in all_parts}
    explode = view.get("explode_mm", {})
    for kind, offset in explode.items():
        delta = Vector((0.0, 0.0, float(offset))) if isinstance(offset, (int, float)) else Vector(offset)
        for obj in groups.get(kind, []):
            obj.location += delta
    bpy.context.view_layer.update()
    for obj in all_parts:
        obj.hide_render = obj.get("showcase_part") not in included
    visible = [obj for obj in all_parts if not obj.hide_render]
    low, high = bounds(visible)
    center = (low + high) * 0.5
    span = max(*(high - low), 1.0)
    lights = add_lighting(config, center, span)
    floor = add_floor(config, center, low, span) if view.get("floor", True) else None
    camera = create_camera(view, center, span, float(profile.get("framing_multiplier", 1.0)))
    scene.render.filepath = str((output_dir / f"{name}.png").resolve())
    print(f"Rendering {name}: {quality}, {profile['resolution'][0]}x{profile['resolution'][1]}, "
          f"{profile['samples']} samples; geometry bbox {list(low)} .. {list(high)}")
    bpy.ops.render.render(write_still=True)
    for obj, location in stored_locations.items():
        obj.location = location
    bpy.context.view_layer.update()
    for obj in lights + [camera] + ([floor] if floor else []):
        bpy.data.objects.remove(obj, do_unlink=True)
    return {"view": name, "bounds_mm": [list(low), list(high)], "output": f"{name}.png"}


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text())
    for path in (args.lid, args.base, args.assembly, config_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required input does not exist: {path}")
    profile = dict(config["render_profiles"][args.preset])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    clear_scene()
    scene = bpy.context.scene
    scene.render.engine = config["scene"].get("engine", "CYCLES")
    scene.world.use_nodes = True
    scene.render.film_transparent = bool(config["scene"].get("film_transparent", False))
    mats = {name: material(f"Doesbot {name}", row) for name, row in config["materials"].items()}

    groups: dict[str, list[bpy.types.Object]] = {key: [] for key in ("cover", "base", "pcb", "components", "r07", "r08", "pins")}
    groups["cover"] = import_stl(args.lid, "cover", mats["cover"])
    groups["base"] = import_stl(args.base, "base", mats["base"])
    assembly_groups = import_assembly(args.assembly, mats)
    for kind, objects in assembly_groups.items():
        groups[kind].extend(objects)

    device = configure_scene(config, profile, args.device or config["scene"].get("device", "auto").lower())
    requested = args.views or list(config["views"])
    unknown = sorted(set(requested) - set(config["views"]))
    if unknown:
        raise ValueError(f"Unknown view(s): {', '.join(unknown)}. Available: {', '.join(config['views'])}")
    outputs = [render_view(name, config["views"][name], groups, config, profile, args.output_dir, args.preset)
               for name in requested]
    input_paths = {"lid": args.lid.resolve(), "base": args.base.resolve(), "assembly": args.assembly.resolve(), "config": config_path}
    manifest = {
        "renderer": "Blender",
        "blender_version": bpy.app.version_string,
        "blender_build_hash": str(bpy.app.build_hash),
        "render_engine": "Cycles",
        "device": device,
        "preset": args.preset,
        "resolution": profile["resolution"],
        "samples": profile["samples"],
        "denoise": profile.get("denoise", True),
        "coordinate_system": "saved native assembly frame; mm; Z up; imported meshes are not rescaled or rotated",
        "exploded_view_transforms": config["views"].get("exploded", {}).get("explode_mm", {}),
        "inputs": {key: {"filename": path.name, "sha256": sha256(path)} for key, path in input_paths.items()},
        "mesh_object_counts": {kind: len(objects) for kind, objects in groups.items()},
        "renders": outputs,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    (args.output_dir / "render-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Render complete. Metal/CPU backend: {device}")


if __name__ == "__main__":
    main()
