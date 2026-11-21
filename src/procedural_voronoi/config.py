"""Configuration authority and deterministic precedence."""
from copy import deepcopy
from pathlib import Path
import yaml
DEFAULT = {
    "seed": 20261110, "cells": 55, "relief": 1.8, "mode": "raised", "style": "organic",
    "distribution": "uniform", "relaxation": 0, "width": 130.0, "height": 90.0,
    "resolution": 65, "thickness": 2.5, "solidify": True, "constant_thickness": False,
    "boundary": 4.0, "border": 7.0, "protected": [], "input": "plane", "scale": 1.0,
    "formats": ["stl", "obj", "glb", "3mf"], "quality": "preview", "validation": "decorative",
    "near_area": 1e-10, "minimum_thickness": 1.0,
}
def presets():
    return yaml.safe_load(Path(__file__).with_name("presets.yaml").read_text())
def merge(a, b):
    out = deepcopy(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out
def resolve(preset=None, user=None, overrides=None):
    c = deepcopy(DEFAULT)
    if preset:
        ps = presets()
        if preset not in ps:
            raise ValueError(f"Unknown preset {preset!r}; use 'voronoi-mesh presets'.")
        c = merge(c, ps[preset]["config"])
    if user:
        data = yaml.safe_load(Path(user).read_text())
        if not isinstance(data, dict):
            raise ValueError("Configuration must be a YAML mapping.")
        c = merge(c, data)
    c = merge(c, overrides or {})
    unknown = set(c) - set(DEFAULT)
    if unknown:
        raise ValueError(f"Unknown configuration keys: {sorted(unknown)}")
    if c["mode"] not in ["raised", "inverted", "flat"]:
        raise ValueError("mode must be raised, inverted, or flat")
    if c["style"] not in ["organic", "flowing", "crystalline", "angular", "fractured"]:
        raise ValueError("Unknown relief style")
    if c["distribution"] not in ["uniform", "jittered", "clustered"]:
        raise ValueError("distribution must be uniform, jittered, or clustered")
    for k, lo, hi in [("cells", 2, 1000), ("resolution", 8, 257), ("relaxation", 0, 10)]:
        if not isinstance(c[k], int) or isinstance(c[k], bool) or not lo <= c[k] <= hi:
            raise ValueError(f"{k} must be an integer in [{lo}, {hi}]")
    for k in ["width", "height", "thickness", "scale"]:
        if not isinstance(c[k], (int, float)) or not 0 < c[k] < 1e5:
            raise ValueError(f"{k} must be positive and finite")
    for k in ["relief", "boundary", "border", "near_area", "minimum_thickness"]:
        if not isinstance(c[k], (int, float)) or not 0 <= c[k] < 1e5:
            raise ValueError(f"{k} must be nonnegative and finite")
    if c["border"] * 2 >= min(c["width"], c["height"]):
        raise ValueError("border must be smaller than half the surface size")
    if c["validation"] not in ["decorative", "manufacturing"]:
        raise ValueError("validation must be decorative or manufacturing")
    if not c["formats"] or set(c["formats"]) - {"stl", "obj", "glb", "3mf"}:
        raise ValueError("formats must contain stl, obj, glb, or 3mf")
    for r in c["protected"]:
        if not isinstance(r, dict) or set(r) != {"xmin", "xmax", "ymin", "ymax"}:
            raise ValueError("Each protected rectangle requires xmin,xmax,ymin,ymax in mm")
        if r["xmin"] >= r["xmax"] or r["ymin"] >= r["ymax"]:
            raise ValueError("Protected rectangle bounds must increase")
    return c
