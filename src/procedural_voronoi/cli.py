"""Command-line interface."""
import argparse
import json
import sys
from pathlib import Path
from .config import presets, resolve
from .pipeline import generate, reproduce
from .validation import validate

def parser():
    p = argparse.ArgumentParser(prog="voronoi-mesh", description="Seeded Voronoi relief in millimetres; no CAD GUI required")
    sub = p.add_subparsers(dest="command")
    g = sub.add_parser("generate", help="Generate with built-in defaults or a preset")
    g.add_argument("--preset"); g.add_argument("--config", type=Path); g.add_argument("--seed", type=int)
    g.add_argument("--cells", type=int); g.add_argument("--relief", type=float)
    g.add_argument("--mode", choices=["raised", "inverted", "flat"])
    g.add_argument("--input"); g.add_argument("--output", default="output"); g.add_argument("--formats", nargs="+", choices=["stl", "obj", "glb", "3mf"])
    ps = sub.add_parser("presets", help="List presets or inspect a resolved preset")
    ps.add_argument("name", nargs="?")
    v = sub.add_parser("validate", help="Reload and validate an existing mesh")
    v.add_argument("mesh"); v.add_argument("--closed", action="store_true", default=None)
    b = sub.add_parser("batch", help="Generate successive seed variations")
    b.add_argument("--seed", type=int, default=20261110); b.add_argument("--count", type=int, default=3)
    b.add_argument("--preset", default="organic-raised"); b.add_argument("--output", default="batch")
    r = sub.add_parser("reproduce", help="Reproduce geometry from a saved manifest")
    r.add_argument("manifest"); r.add_argument("--output", required=True)
    d = sub.add_parser("doesbot", help="Generate sanitized historical-parameter reference; not V23")
    d.add_argument("--output", default="doesbot-reference")
    w = sub.add_parser("serve", help="Launch local browser parameter explorer")
    w.add_argument("--port", type=int, default=8765); w.add_argument("--output", default="browser-output")
    return p

def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        args = ["generate"]
    a = parser().parse_args(args)
    try:
        if a.command == "generate":
            keys = ["seed", "cells", "relief", "mode", "input", "formats"]
            result = generate(a.output, a.preset, a.config, {k: getattr(a, k) for k in keys if getattr(a, k) is not None})
        elif a.command == "presets":
            result = resolve(a.name) if a.name else {k: v["description"] for k, v in presets().items()}
        elif a.command == "validate":
            result = validate(a.mesh, a.closed)
        elif a.command == "reproduce":
            result = reproduce(a.manifest, a.output)
        elif a.command == "doesbot":
            result = generate(a.output, "doesbot-original")
        elif a.command == "batch":
            if not 1 <= a.count <= 100:
                raise ValueError("count must be between 1 and 100")
            result = [generate(Path(a.output)/str(a.seed+i), a.preset, overrides={"seed": a.seed+i}) for i in range(a.count)]
        elif a.command == "serve":
            from .web import serve
            serve(a.port, a.output)
            return 0
        else:
            parser().print_help(); return 0
        print(json.dumps(result, indent=2))
        if isinstance(result, dict) and (result.get("validation_pass") is False or result.get("pass") is False):
            return 2
        return 0
    except (ValueError, OSError, KeyError, TypeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
