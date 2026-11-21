#!/usr/bin/env python3
"""Refresh visual provenance/checksums and build the versioned example archive."""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def inferred_metadata(rel: str) -> dict[str, str]:
    path = Path(rel)
    if "hardware" in path.parts:
        return {"source": "User-supplied real Doesbot PCB photograph; EXIF stripped.", "status": "physical hardware reference", "media_type": "photograph"}
    if "freecad" in path.parts:
        return {"source": "Saved native FreeCAD geometry-derived dependency preview.", "status": "computational review reference", "media_type": "CAD-derived image"}
    if "assembly" in path.parts or "details" in path.parts:
        return {"source": "Saved V005 FreeCAD assembly reference image.", "status": "historical component-layout reference", "media_type": "CAD-derived render"}
    if "validation" in path.parts:
        return {"source": "Saved V23/R07 computational section render.", "status": "local integration review; physical fit unverified", "media_type": "CAD-derived render"}
    if path.name.startswith("v23-"):
        return {"source": "Saved V23 + R07 engineering render.", "status": "computational review candidate", "media_type": "CAD-derived render"}
    if path.name.startswith("v24-"):
        return {"source": "Saved V24 mechanical reconciliation render.", "status": "computational review candidate; physical fit unverified", "media_type": "CAD-derived render"}
    if "showcase" in path.parts:
        return {"source": "Blender Cycles render from saved V24 lid/base STL and assembly reference OBJ; see render configuration and local output manifest.", "status": "computational review visualization; physical fit and print testing unverified", "media_type": "Blender Cycles render"}
    return {"source": "Generated from the named repository preset and saved example manifest.", "status": "generated software example; not Doesbot enclosure geometry", "media_type": "generated mesh render"}


def main() -> None:
    manifest_path = ROOT / "docs/assets/manifest.json"
    existing = json.loads(manifest_path.read_text())
    old = {row.get("file"): row for row in existing if isinstance(row, dict)}
    assets = []
    for path in sorted((ROOT / "docs/assets/images").rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        rel = str(path.relative_to(ROOT))
        prior = old.get(rel, {})
        inferred = inferred_metadata(rel)
        row = dict(prior)
        row.update({
            "file": rel,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "attribution": prior.get("attribution", "David Cannan (Cdaprod)"),
            "source": prior.get("source", prior.get("provenance", inferred["source"])),
            "status": prior.get("status", inferred["status"]),
            "media_type": prior.get("media_type", inferred["media_type"]),
            "caption": prior.get("caption", path.stem.replace("-", " ")),
            "public_url": "https://raw.githubusercontent.com/Cdaprod/procedural-voronoi-mesh/main/" + rel,
        })
        assets.append(row)
    manifest_path.write_text(json.dumps(assets, indent=2) + "\n")

    with (ROOT / "pyproject.toml").open("rb") as stream:
        version = tomllib.load(stream)["project"]["version"]
    dest = ROOT / "dist"
    dest.mkdir(exist_ok=True)
    archive = dest / f"procedural-voronoi-mesh-{version}-examples.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for folder in ("examples", "presets", "configs", "docs"):
            for path in sorted((ROOT / folder).rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    bundle.write(path, path.relative_to(ROOT))
        for name in ("README.md", "LICENSE", "CHANGELOG.md"):
            bundle.write(ROOT / name, name)
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise RuntimeError(f"Archive validation failed: {archive}")
    sums = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(dest.iterdir())
        if path.is_file() and path.name != "checksums.sha256"
    }
    (dest / "checksums.sha256").write_text("".join(f"{digest}  {name}\n" for name, digest in sums.items()))
    print(json.dumps({"visual_assets": len(assets), "release_files": sums,
                      "preserved_provenance_records": sum(row.get("file") in old for row in assets)}, indent=2))


if __name__ == "__main__":
    main()
