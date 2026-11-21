"""Recovered height-field algorithm, parameterized without private project paths.

Usage: python historical_replay.py historical-evidence.json BASE.npy OUTPUT.npy
The archival base height field is not shipped; use generated/ for the sanitized example.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter

def replay(base, config):
    c = config
    base = gaussian_filter(np.asarray(base, dtype=float), c["base_smooth_mm"]/c["xy_step_mm"], mode="nearest")
    ny, nx = base.shape
    x, y = np.meshgrid(np.linspace(-65, 65, nx), np.linspace(-45, 45, ny))
    rng = np.random.default_rng(c["seed"]); b = c["border_mm"]; n = c["cells"]
    s = np.c_[rng.uniform(-65+b, 65-b, n), rng.uniform(-45+b, 45-b, n)]
    d = np.stack([(x-a)**2+(y-b)**2 for a, b in s])
    i, j = np.argpartition(d, 1, axis=0)[:2]
    f, second = [np.take_along_axis(d, k[None], axis=0)[0] for k in (i, j)]
    sep = np.linalg.norm(s[i]-s[j], axis=-1)
    field = np.clip((second-f)/(2*sep*np.maximum(sep*.5, 2)), 0, 1)
    t = np.clip(np.minimum(65-abs(x), 45-abs(y))/c["perimeter_fade_mm"], 0, 1)
    return base+c["relief_mm"]*field*t*t*(3-2*t)
if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("evidence", type=Path); p.add_argument("base", type=Path); p.add_argument("output", type=Path)
    a = p.parse_args(); np.save(a.output, replay(np.load(a.base), json.loads(a.evidence.read_text())["config"]))
