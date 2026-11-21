#!/usr/bin/env python3
"""Validate Markdown/HTML local images and required visual narratives."""
import re
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
def check(root=ROOT):
    errors = []; counts = {}
    for md in root.rglob("*.md"):
        if any(x in md.parts for x in [".venv", ".git", "build", "dist"]):
            continue
        text = md.read_text()
        refs = re.findall(r'!\[([^\]]*)\]\(([^\s)]+)(?:\s+"[^"]*")?\)', text)
        for tag in re.findall(r'<img\b[^>]*>', text, re.I):
            src = re.search(r'\bsrc=[\'"]([^\'"]+)', tag, re.I)
            alt = re.search(r'\balt=[\'"]([^\'"]*)', tag, re.I)
            if src:
                refs.append((alt.group(1) if alt else "", src.group(1)))
        counts[str(md.relative_to(root))] = len(refs)
        for alt, src in refs:
            if len(alt.strip()) < 8 or alt.lower().strip() in ["image", "photo", "screenshot", "preview.png"]:
                errors.append(f"{md}: non-descriptive alt text {alt!r}")
            if src.startswith(("https://", "http://", "data:")):
                errors.append(f"{md}: required image must be a portable local asset: {src}")
                continue
            p = (md.parent/src).resolve()
            if not p.is_file():
                errors.append(f"{md}: missing {src}"); continue
            try:
                with Image.open(p) as im:
                    im.verify()
            except Exception as e:
                errors.append(f"{md}: invalid image {src}: {e}")
    for name, minimum in [("README.md", 4), ("docs/story/from-hardware-to-procedural-geometry.md", 4)]:
        if counts.get(name, 0) < minimum:
            errors.append(f"{name}: expected at least {minimum} embedded images")
    return errors
if __name__ == "__main__":
    failures = check()
    print("\n".join(failures) if failures else "Documentation image paths, decoding and alt text pass")
    raise SystemExit(bool(failures))
