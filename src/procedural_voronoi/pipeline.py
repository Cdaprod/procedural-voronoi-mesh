"""Library build: resolved configuration → geometry → reload validation → artifacts."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import shutil
import numpy as np
import yaml
from . import __version__
from .config import resolve
from .geometry import construct
from .export import canonical, export
from .validation import validate, read
from .render import render

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def geometry_hash(mesh):
    m = canonical(mesh)
    return hashlib.sha256(m.vertices.astype("<f8").tobytes()+m.faces.astype("<i8").tobytes()).hexdigest()
def generate(output="output", preset=None, config=None, overrides=None):
    c = resolve(preset, config, overrides)
    out = Path(output).resolve(); out.mkdir(parents=True, exist_ok=True)
    # Never overwrite an existing unrelated output or a build with differing configuration.
    saved_c = c.copy()
    if c["input"] not in ["plane", "box"]:
        saved_c["input"] = "input"+Path(c["input"]).suffix.lower()
    old = out/"resolved.yaml"
    if old.exists() and yaml.safe_load(old.read_text()) != saved_c:
        raise ValueError(f"{out} contains a different build; select a new output directory")
    mesh, metrics = construct(c)
    mesh = canonical(mesh)
    inp = None
    if c["input"] not in ["plane", "box"]:
        path = Path(c["input"]).resolve()
        if path.parent == out:
            raise ValueError("Input must be outside the output directory")
        dest = out/("input"+path.suffix.lower())
        shutil.copyfile(path, dest)
        inp = {"file": dest.name, "sha256": sha(dest), "original_name": path.name}
    (out/"resolved.yaml").write_text(yaml.safe_dump(saved_c, sort_keys=True))
    results = {}
    for fmt in c["formats"]:
        path = out/("mesh."+fmt)
        export(mesh, path)
        r = validate(path, closed=c["solidify"], near_area=c["near_area"])
        r["geometry_sha256"] = geometry_hash(read(path))
        if c["validation"] == "manufacturing":
            thick = metrics["thickness"]
            r["strict_pass"] = bool(r["pass"] and r["self_intersections"] == 0 and r["near_zero_faces"] == 0 and
                                     thick and thick["minimum_vertical_mm"] >= c["minimum_thickness"] and
                                     not c["constant_thickness"] and c["solidify"])
        results[fmt] = r
    render(mesh, out/"preview.png", f"{preset or 'custom'} · seed {c['seed']} · {c['cells']} cells", c["quality"])
    (out/"validation.json").write_text(json.dumps({"exports": results, "geometry": metrics, "limitations": ["Vertical thickness is not shortest normal thickness.", "Topology does not prove physical printability or fit.", "Imports displace existing +Z-facing vertices and are not remeshed."]}, indent=2)+"\n")
    versions = {}
    for name in ["numpy", "scipy", "trimesh", "manifold3d", "matplotlib", "PyYAML", "libigl"]:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    passed = all(r.get("strict_pass", r["pass"]) for r in results.values())
    manifest = {"schema": 1, "generator_version": __version__, "seed": c["seed"], "preset": preset,
                "configuration": saved_c, "input": inp, "dependencies": versions,
                "geometry_sha256": geometry_hash(mesh), "validation_pass": passed,
                "files": {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name != "manifest.json"}}
    (out/"manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True)+"\n")
    return manifest

def reproduce(manifest_path, output):
    p = Path(manifest_path).resolve(); m = json.loads(p.read_text())
    if m["generator_version"] != __version__:
        raise ValueError(f"Requires generator {m['generator_version']}; installed {__version__}")
    c = m["configuration"].copy()
    if m["input"]:
        inp = p.parent/m["input"]["file"]
        if sha(inp) != m["input"]["sha256"]:
            raise ValueError("Manifest input hash mismatch")
        c["input"] = str(inp)
    result = generate(output, preset=m["preset"], overrides=c)
    if result["geometry_sha256"] != m["geometry_sha256"]:
        raise ValueError("Reproduction geometry mismatch; compare dependency versions")
    return result
