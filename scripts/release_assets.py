#!/usr/bin/env python3
"""Generate public asset attribution and a versioned example archive."""
from pathlib import Path
import hashlib
import json
import zipfile
ROOT = Path(__file__).resolve().parents[1]

def main():
    assets = []
    for p in sorted((ROOT/"docs/assets/images").rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(ROOT))
        kind = "actual generated preset mesh render"
        if "hardware" in p.parts:
            kind = "user-supplied real Doesbot PCB photograph; EXIF stripped"
        elif "freecad" in p.parts:
            kind = "saved native FreeCAD geometry-derived dependency preview"
        elif "revisions" in p.parts:
            kind = "actual V24 computational review-candidate render; physical fit unverified"
        assets.append({"file": rel, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                       "attribution": "David Cannan (Cdaprod)", "provenance": kind,
                       "caption": p.stem.replace("-", " "),
                       "public_url": "https://raw.githubusercontent.com/Cdaprod/procedural-voronoi-mesh/main/"+rel})
    (ROOT/"docs/assets/manifest.json").write_text(json.dumps(assets, indent=2)+"\n")
    dest = ROOT/"dist"; dest.mkdir(exist_ok=True)
    archive = dest/"procedural-voronoi-mesh-1.0.0-examples.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for folder in ["examples", "presets", "configs", "docs"]:
            for f in sorted((ROOT/folder).rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts:
                    z.write(f, f.relative_to(ROOT))
        for name in ["README.md", "LICENSE", "CHANGELOG.md"]:
            z.write(ROOT/name, name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    sums = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir()) if p.is_file() and p.name != "checksums.sha256"}
    (dest/"checksums.sha256").write_text("".join(f"{h}  {n}\n" for n, h in sums.items()))
    print(json.dumps({"visual_assets": len(assets), "release_files": sums}, indent=2))
if __name__ == "__main__":
    main()
