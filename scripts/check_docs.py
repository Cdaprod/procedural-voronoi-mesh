#!/usr/bin/env python3
"""Validate Markdown images, links, visual requirements, and published asset provenance."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _without_code(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`]*`", "", text)


def _image_references(text: str) -> list[tuple[str, str]]:
    refs = re.findall(r'!\[([^\]]*)\]\(([^\s)]+)(?:\s+"[^"]*")?\)', text)
    for tag in re.findall(r"<img\b[^>]*>", text, re.I):
        src = re.search(r"\bsrc=['\"]([^'\"]+)", tag, re.I)
        alt = re.search(r"\balt=['\"]([^'\"]*)", tag, re.I)
        if src:
            refs.append((alt.group(1) if alt else "", src.group(1)))
    return refs


def _slug(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text.lower())
    text = re.sub(r"[^\w\- ]", "", text)
    return re.sub(r"\s+", "-", text.strip())


def _heading_slugs(path: Path) -> set[str]:
    slugs: set[str] = set()
    counts: dict[str, int] = {}
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", path.read_text(), re.M):
        base = _slug(heading)
        n = counts.get(base, 0)
        counts[base] = n + 1
        slugs.add(base if n == 0 else f"{base}-{n}")
    return slugs


def _local_target(md: Path, target: str, errors: list[str]) -> None:
    target = target.strip().strip("<>")
    if target.startswith(("https://", "http://", "mailto:", "tel:", "data:")):
        return
    path_text, _, fragment = target.partition("#")
    if not path_text:
        dest = md
    else:
        dest = (md.parent / path_text.split("?", 1)[0]).resolve()
    if not dest.exists():
        errors.append(f"{md}: broken local link {target}")
        return
    if fragment and dest.is_file() and dest.suffix.lower() == ".md":
        if _slug(fragment) not in _heading_slugs(dest):
            errors.append(f"{md}: missing heading anchor in {target}")


def _check_asset_manifest(root: Path, errors: list[str]) -> None:
    manifest = root / "docs/assets/manifest.json"
    if not manifest.exists():
        return
    try:
        records = json.loads(manifest.read_text())
    except Exception as exc:
        errors.append(f"{manifest}: cannot parse manifest: {exc}")
        return
    if not isinstance(records, list):
        errors.append(f"{manifest}: expected an array of asset records")
        return
    listed: set[str] = set()
    for record in records:
        rel = record.get("file", "")
        if not rel or rel in listed:
            errors.append(f"{manifest}: missing or duplicate asset path {rel!r}")
            continue
        listed.add(rel)
        asset = root / rel
        if not asset.is_file():
            errors.append(f"{manifest}: listed image is missing: {rel}")
            continue
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        if record.get("sha256") != digest:
            errors.append(f"{manifest}: checksum mismatch for {rel}")
        expected_url = "https://raw.githubusercontent.com/Cdaprod/procedural-voronoi-mesh/main/" + rel
        if record.get("public_url") != expected_url:
            errors.append(f"{manifest}: public URL does not match path for {rel}")
        if not record.get("source") or not record.get("status") or not record.get("caption"):
            errors.append(f"{manifest}: provenance/status/caption missing for {rel}")
    actual = {
        str(p.relative_to(root))
        for p in (root / "docs/assets/images").rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    }
    for rel in sorted(actual - listed):
        errors.append(f"{manifest}: image is not inventoried: {rel}")
    for rel in sorted(listed - actual):
        errors.append(f"{manifest}: non-image or untracked asset entry: {rel}")


def check(root: Path = ROOT) -> list[str]:
    root = Path(root).resolve()
    errors: list[str] = []
    counts: dict[str, int] = {}
    refs_by_doc: dict[str, list[tuple[str, str]]] = {}
    for md in root.rglob("*.md"):
        if any(part in md.parts for part in (".venv", ".git", "build", "dist")):
            continue
        text = _without_code(md.read_text())
        refs = _image_references(text)
        name = str(md.relative_to(root))
        counts[name] = len(refs)
        refs_by_doc[name] = refs
        seen: set[str] = set()
        for alt, src in refs:
            if len(alt.strip()) < 8 or alt.lower().strip() in {"image", "photo", "screenshot", "preview.png"}:
                errors.append(f"{md}: non-descriptive alt text {alt!r}")
            if src in seen:
                errors.append(f"{md}: repeated image reference {src}")
            seen.add(src)
            if src.startswith(("https://", "http://", "data:")):
                errors.append(f"{md}: required image must be a portable local asset: {src}")
                continue
            p = (md.parent / src).resolve()
            if not p.is_file():
                errors.append(f"{md}: missing image {src}")
                continue
            try:
                with Image.open(p) as im:
                    im.verify()
            except Exception as exc:
                errors.append(f"{md}: invalid image {src}: {exc}")
        link_text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
        for target in re.findall(r"(?<!!)\[[^\]]+\]\((<[^>]+>|[^)\s]+)(?:\s+\"[^\"]*\")?\)", link_text):
            _local_target(md, target, errors)

    minimums = {
        "README.md": 10,
        "docs/story/from-hardware-to-procedural-geometry.md": 10,
        "docs/showcase/doesbot-cnc-enclosure.md": 10,
        "docs/rendering/README.md": 5,
    }
    for name, minimum in minimums.items():
        if counts.get(name, 0) < minimum:
            errors.append(f"{name}: expected at least {minimum} embedded images")

    required_readme = {
        "docs/assets/images/revisions/v23-r07-cover-oblique.png",
        "docs/assets/images/hardware/doesbot-terminal-blocks.jpg",
        "docs/assets/images/assembly/v005-pcb-component-reference.png",
        "docs/assets/images/freecad/r08-master-linked-references.png",
        "docs/assets/images/showcase/closed.jpg",
        "docs/assets/images/showcase/exploded.jpg",
        "docs/assets/images/showcase/lid-exterior.jpg",
        "docs/assets/images/showcase/lid-underside.jpg",
        "docs/assets/images/showcase/base.jpg",
        "docs/assets/images/validation/v23-r07-cover-section.png",
    }
    readme_refs = {src for _, src in refs_by_doc.get("README.md", [])}
    for required in sorted(required_readme - readme_refs):
        errors.append(f"README.md: required engineering image is not embedded: {required}")
    first_readme_image = refs_by_doc.get("README.md", [("", "")])[0][1] if refs_by_doc.get("README.md") else ""
    if first_readme_image != "docs/assets/images/showcase/closed.jpg":
        errors.append("README.md: the first image must be the Blender-rendered V24 enclosure hero")

    _check_asset_manifest(root, errors)
    return errors


if __name__ == "__main__":
    failures = check()
    print("\n".join(failures) if failures else "Documentation images, local links, asset manifest, and visual requirements pass")
    raise SystemExit(bool(failures))
