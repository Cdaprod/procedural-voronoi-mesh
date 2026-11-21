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
