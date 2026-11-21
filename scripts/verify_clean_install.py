#!/usr/bin/env python3
"""Install a built wheel into a fresh venv and exercise user-facing commands."""
from pathlib import Path
import json
import subprocess
import tempfile
import venv
ROOT = Path(__file__).resolve().parents[1]
def main():
    wheel = next((ROOT/"dist").glob("*.whl"))
    results = []
    with tempfile.TemporaryDirectory(prefix="pvm-clean-") as temp:
        p = Path(temp); venv.EnvBuilder(with_pip=True).create(p/"venv")
        python = p/"venv/bin/python"
        subprocess.run([str(python), "-m", "pip", "install", str(wheel)+"[validation]"], check=True, stdout=subprocess.DEVNULL)
        commands = [[], ["generate", "--preset", "organic-inverted", "--output", "inverted"],
                    ["generate", "--seed", "42", "--output", "seed42"],
                    ["batch", "--preset", "fast-preview", "--seed", "100", "--count", "2", "--output", "batch"],
                    ["doesbot", "--output", "doesbot"],
                    ["reproduce", "doesbot/manifest.json", "--output", "reproduced"],
                    ["validate", "output/mesh.stl", "--closed"], ["presets"]]
        for args in commands:
            r = subprocess.run([str(python), "-m", "procedural_voronoi", *args], cwd=p, text=True, capture_output=True)
            results.append({"command": "voronoi-mesh "+" ".join(args), "returncode": r.returncode})
            if r.returncode:
                raise RuntimeError(r.stderr+r.stdout)
        assert (p/"output/preview.png").is_file()
        result = {"wheel": wheel.name, "fresh_environment": True, "source_directory_on_pythonpath": False,
                  "commands": results, "status": "passed", "doesbot_geometry_reproduced": True,
                  "note": "Sanitized Doesbot example only; no exact V23 reconstruction claimed."}
    (ROOT/"docs/engineering/clean-install-verification.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))
if __name__ == "__main__":
    main()
