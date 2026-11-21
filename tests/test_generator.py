import json
from pathlib import Path
import subprocess
import sys
import threading
import urllib.request
from http.server import HTTPServer
import numpy as np
import pytest
import trimesh
from procedural_voronoi import generate
from procedural_voronoi.config import resolve, presets
from procedural_voronoi.geometry import construct, sites
from procedural_voronoi.pipeline import reproduce
from procedural_voronoi.validation import read, validate
from procedural_voronoi.web import handler

SMALL = {"resolution": 17, "cells": 8, "formats": ["stl", "obj", "glb", "3mf"]}

def test_library_default_and_formats(tmp_path):
    m = generate(tmp_path/"a", overrides=SMALL)
    assert m["validation_pass"]
    for fmt in SMALL["formats"]:
        r = validate(tmp_path/"a"/f"mesh.{fmt}", closed=True)
        assert r["pass"] and r["watertight"] and r["self_intersections"] == 0
    assert (tmp_path/"a/preview.png").read_bytes().startswith(b"\x89PNG")

def test_determinism_manifest_reproduce(tmp_path):
    a = generate(tmp_path/"a", "organic-raised", overrides=SMALL)
    b = generate(tmp_path/"b", "organic-raised", overrides=SMALL)
    assert a["geometry_sha256"] == b["geometry_sha256"]
    for fmt in SMALL["formats"]:
        assert (tmp_path/"a"/f"mesh.{fmt}").read_bytes() == (tmp_path/"b"/f"mesh.{fmt}").read_bytes()
    c = reproduce(tmp_path/"a/manifest.json", tmp_path/"c")
    assert a["geometry_sha256"] == c["geometry_sha256"]
    d = generate(tmp_path/"d", overrides={**SMALL, "seed": 4})
    assert d["geometry_sha256"] != a["geometry_sha256"]

def test_config_precedence(tmp_path):
    p = tmp_path/"custom.yaml"; p.write_text("cells: 13\nrelief: 0.7\n")
    c = resolve("coarse-facets", p, {"seed": 12, "cells": 14})
    assert (c["seed"], c["cells"], c["relief"]) == (12, 14, .7)
    with pytest.raises(ValueError):
        resolve(overrides={"unknown": 1})
    with pytest.raises(ValueError):
        resolve(overrides={"cells": 0})

@pytest.mark.parametrize("preset", list(presets()))
def test_every_preset(tmp_path, preset):
    c = resolve(preset, overrides={"resolution": 17, "cells": 8, "formats": ["stl"]})
    m = generate(tmp_path/preset, preset, overrides={"resolution": 17, "cells": 8, "formats": ["stl"]})
    assert m["validation_pass"], c

def test_boundary_protected_flat_open(tmp_path):
    c = resolve("protected-boundary", overrides={"resolution": 17})
    m, info = construct(c)
    assert info["protected_displacement_mm"] == 0
    assert np.allclose(m.vertices[np.abs(m.vertices[:, 0]) == c["width"]/2, 2].max(), c["thickness"])
    a = generate(tmp_path/"open", overrides={**SMALL, "solidify": False, "mode": "flat"})
    assert a["validation_pass"]
    r = validate(tmp_path/"open/mesh.stl", closed=False)
    assert r["boundary_edges"] > 0 and not r["watertight"]

@pytest.mark.parametrize("fmt", ["stl", "obj", "glb"])
def test_import_and_manifest(tmp_path, fmt):
    src = tmp_path/f"source.{fmt}"
    trimesh.creation.box([40, 30, 4]).export(src)
    # Flat mode validates real import/export without implying sparse imported boxes are richly sampled.
    a = generate(tmp_path/fmt, overrides={**SMALL, "input": str(src), "mode": "flat"})
    assert a["validation_pass"] and a["input"]["sha256"]
    b = reproduce(tmp_path/fmt/"manifest.json", tmp_path/(fmt+"-repro"))
    assert a["geometry_sha256"] == b["geometry_sha256"]

def test_validation_reports_bad_geometry(tmp_path):
    m = trimesh.creation.box(); m.faces = np.r_[m.faces, m.faces[:1]]
    p = tmp_path/"bad.obj"; m.export(p)
    r = validate(p, closed=True)
    assert not r["pass"] and r["duplicate_faces"] == 1 and r["nonmanifold_edges"] > 0

def test_cli_commands(tmp_path):
    def run(*args):
        return subprocess.run([sys.executable, "-m", "procedural_voronoi", *args], capture_output=True, text=True)
    assert run("--help").returncode == 0
    assert "organic-raised" in run("presets").stdout
    assert run("presets", "doesbot-original").returncode == 0
    p = tmp_path/"c.yaml"; p.write_text("resolution: 17\ncells: 8\nformats: [stl]\n")
    assert run("generate", "--config", str(p), "--output", str(tmp_path/"out")).returncode == 0
    assert run("validate", str(tmp_path/"out/mesh.stl"), "--closed").returncode == 0
    assert run("reproduce", str(tmp_path/"out/manifest.json"), "--output", str(tmp_path/"copy")).returncode == 0
    assert run("generate", "--cells", "0").returncode == 2

def test_web_real_generation(tmp_path):
    server = HTTPServer(("127.0.0.1", 0), handler(tmp_path))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    try:
        assert b"Voronoi mesh studio" in urllib.request.urlopen(url).read()
        assert "organic-raised" in json.load(urllib.request.urlopen(url+"/api/presets"))
        req = urllib.request.Request(url+"/api/generate", data=json.dumps({"preset": "fast-preview", "seed": 2, "cells": 8, "relief": 1, "input": "plane", "mode": "raised", "quality": "preview", "format": "stl"}).encode(), headers={"Content-Type": "application/json"})
        out = json.load(urllib.request.urlopen(req))
        assert out["pass"]
        assert urllib.request.urlopen(url+out["preview"]).read().startswith(b"\x89PNG")
        assert len(urllib.request.urlopen(url+out["mesh"]).read()) > 100
    finally:
        server.shutdown(); server.server_close(); thread.join()

def test_docs():
    import importlib.util
    path = Path(__file__).parents[1]/"scripts/check_docs.py"
    spec = importlib.util.spec_from_file_location("docs", path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    assert mod.check() == []
