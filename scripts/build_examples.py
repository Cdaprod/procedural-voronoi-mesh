#!/usr/bin/env python3
"""Build every shipped preset and portable examples from the installed library."""
from pathlib import Path
import json
import shutil
import trimesh
import yaml
from PIL import Image, ImageDraw
from procedural_voronoi import generate
from procedural_voronoi.config import presets, resolve
ROOT = Path(__file__).resolve().parents[1]

def main():
    rows = []
    for name, p in presets().items():
        dest = ROOT/"examples"/"presets"/name
        manifest = generate(dest, name)
        if not manifest["validation_pass"]:
            raise RuntimeError(f"Preset {name} validation failed")
        category = "functional" if name in ["protected-boundary", "constant-thickness", "reinforced", "manufacturing"] else ("geometric" if name in ["crystalline", "low-poly", "fractured"] else "organic")
        config = ROOT/"presets"/category/(name+".yaml")
        config.write_text(yaml.safe_dump(resolve(name), sort_keys=True))
        image = ROOT/"docs/assets/images/presets"/(name+".png")
        shutil.copyfile(dest/"preview.png", image)
        readme = f"# {name}\n\n{p['description']}\n\n![Actual generated {name} geometry](preview.png)\n\nSeed {manifest['seed']}; actual configuration in resolved.yaml and validation in validation.json.\n\n```sh\nvoronoi-mesh generate --preset {name} --output generated/{name}\n```\n"
        (dest/"README.md").write_text(readme)
        rows.append({"preset": name, "geometry_sha256": manifest["geometry_sha256"], "pass": manifest["validation_pass"]})
        print(name, "PASS", flush=True)
    generate(ROOT/"examples/plane/generated", "organic-raised")
    generate(ROOT/"examples/box/generated", "organic-inverted", overrides={"input": "box", "thickness": 12})
    source = ROOT/"examples/imported-mesh/input.obj"
    trimesh.creation.icosphere(subdivisions=2, radius=20).export(source)
    generate(ROOT/"examples/imported-mesh/generated", "organic-raised", overrides={"input": str(source), "relief": .5})
    generate(ROOT/"examples/doesbot/generated", "doesbot-original")
    for folder, title in [("plane", "Procedural plane"), ("box", "Procedural box"), ("imported-mesh", "Imported OBJ sphere")]:
        (ROOT/"examples"/folder/"README.md").write_text(f"# {title}\n\n![Actual generated {title.lower()} example](generated/preview.png)\n\nResolved configuration, exported geometry and validation are in generated/. Imported geometry uses a +Z directional displacement; it is not a conformal remesher.\n")
    # Comparison uses actual rendered preset images at identical camera conventions.
    names = ["organic-raised", "organic-inverted", "crystalline", "protected-boundary"]
    canvas = Image.new("RGB", (1200, 840), "#101b28")
    for i, name in enumerate(names):
        im = Image.open(ROOT/"docs/assets/images/presets"/(name+".png")).convert("RGB").resize((600, 420))
        canvas.paste(im, ((i % 2)*600, (i//2)*420))
    canvas.save(ROOT/"docs/assets/images/presets/comparison.png")
    (ROOT/"examples/preset-inventory.json").write_text(json.dumps(rows, indent=2)+"\n")
if __name__ == "__main__":
    main()
