#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

: "${DOESBOT_V24_DIR:?Set DOESBOT_V24_DIR to the directory containing V24 lid.stl, base.stl, and references/assembly.obj}"
BLENDER_BIN="${BLENDER_BIN:-$(command -v blender || true)}"
if [[ -z "$BLENDER_BIN" && -x /Applications/Blender.app/Contents/MacOS/Blender ]]; then
  BLENDER_BIN=/Applications/Blender.app/Contents/MacOS/Blender
fi
if [[ -z "$BLENDER_BIN" || ! -x "$BLENDER_BIN" ]]; then
  echo "Blender executable not found. Set BLENDER_BIN to Blender 4.2+ (Blender 5.2 tested)." >&2
  exit 2
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"
PRESET="${BLENDER_PRESET:-master}"
DEVICE="${BLENDER_DEVICE:-auto}"
OUTPUT_DIR="${BLENDER_OUTPUT_DIR:-rendered/doesbot-v24/masters}"

if [[ "${BLENDER_SKIP_RENDER:-0}" != "1" ]]; then
  "$BLENDER_BIN" --background --factory-startup --python scripts/render_blender_showcase.py -- \
    --lid "$DOESBOT_V24_DIR/exports/lid.stl" \
    --base "$DOESBOT_V24_DIR/exports/base.stl" \
    --assembly "$DOESBOT_V24_DIR/references/assembly.obj" \
    --config docs/rendering/doesbot-v24-blender.json \
    --output-dir "$OUTPUT_DIR" \
    --preset "$PRESET" --device "$DEVICE"
elif [[ ! -s "$OUTPUT_DIR/render-manifest.json" ]]; then
  echo "BLENDER_SKIP_RENDER=1 requires an existing render-manifest.json in $OUTPUT_DIR" >&2
  exit 2
fi

cp "$OUTPUT_DIR/render-manifest.json" docs/rendering/v24-render-manifest.json

"$PYTHON_BIN" - "$OUTPUT_DIR" docs/assets/images/showcase <<'PY'
from pathlib import Path
import sys
from PIL import Image

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
destination.mkdir(parents=True, exist_ok=True)
for master in sorted(source.glob("*.png")):
    if master.name == "render-manifest.json":
        continue
    image = Image.open(master).convert("RGB")
    original_size = image.size
    image.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
    target = destination / f"{master.stem}.jpg"
    image.save(target, "JPEG", quality=91, optimize=True, progressive=True, subsampling=0)
    print(f"{target}: {original_size[0]}x{original_size[1]} master -> {image.width}x{image.height}, {target.stat().st_size:,} bytes")
PY
