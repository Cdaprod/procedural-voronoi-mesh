from pathlib import Path
import importlib.util
from PIL import Image
spec = importlib.util.spec_from_file_location("docs", Path(__file__).parents[1]/"scripts/check_docs.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
def test_broken_and_html_images(tmp_path):
    story = tmp_path/"docs/story"; story.mkdir(parents=True)
    (tmp_path/"README.md").write_text('![x](missing.png)\n<img src="bad.png" alt="">')
    (story/"from-hardware-to-procedural-geometry.md").write_text("no images")
    errors = mod.check(tmp_path)
    assert any("missing" in e for e in errors) and any("alt text" in e for e in errors)
    assert any("expected at least" in e for e in errors)

def test_repeated_embedded_images_are_reported(tmp_path):
    story = tmp_path/"docs/story"; story.mkdir(parents=True)
    (story/"same.png").write_bytes(b"not a real image")
    (tmp_path/"README.md").write_text('![First descriptive image](docs/story/same.png)\n![Second descriptive image](docs/story/same.png)')
    errors = mod.check(tmp_path)
    assert any("repeated image reference" in error for error in errors)

def test_manifest_rejects_checksum_and_untracked_assets(tmp_path):
    import json
    images = tmp_path/"docs/assets/images/showcase"; images.mkdir(parents=True)
    image = images/"sample.png"
    Image.new("RGB", (4, 4), "red").save(image)
    manifest = tmp_path/"docs/assets/manifest.json"
    manifest.write_text(json.dumps([{"file":"docs/assets/images/showcase/sample.png", "sha256":"bad", "public_url":"bad", "source":"test", "status":"test", "caption":"sample"}]))
    errors=[]
    mod._check_asset_manifest(tmp_path, errors)
    assert any("checksum mismatch" in error for error in errors)
    assert any("public URL" in error for error in errors)
