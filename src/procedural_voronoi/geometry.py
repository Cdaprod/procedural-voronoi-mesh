"""Deterministic sites, relief fields, protected masks and mesh construction."""
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import trimesh

def sites(c):
    rng = np.random.default_rng(c["seed"])
    w, h, b, n = c["width"], c["height"], c["border"], c["cells"]
    lo, hi = np.array([-w/2+b, -h/2+b]), np.array([w/2-b, h/2-b])
    if c["distribution"] == "jittered":
        k = int(np.ceil(np.sqrt(n)))
        xy = np.array([(i, j) for j in range(k) for i in range(k)])[:n]
        s = lo + ((xy + rng.uniform(.15, .85, (n, 2))) / k) * (hi-lo)
    elif c["distribution"] == "clustered":
        centers = rng.uniform(lo, hi, (max(2, n//12), 2))
        s = np.clip(centers[rng.integers(0, len(centers), n)] + rng.normal(0, (hi-lo)/9, (n, 2)), lo, hi)
    else:
        # Preserve the historical independent X and Y random draw ordering.
        s = np.c_[rng.uniform(lo[0], hi[0], n), rng.uniform(lo[1], hi[1], n)]
    gx, gy = np.meshgrid(np.linspace(*[lo[0], hi[0]], 96), np.linspace(lo[1], hi[1], 72))
    samples = np.c_[gx.ravel(), gy.ravel()]
    for _ in range(c["relaxation"]):
        ids = cKDTree(s).query(samples)[1]
        for i in range(n):
            pts = samples[ids == i]
            if len(pts):
                s[i] = pts.mean(axis=0)
    return s

def mask(xy, c):
    distance = np.minimum(c["width"]/2-np.abs(xy[:, 0]), c["height"]/2-np.abs(xy[:, 1]))
    t = np.clip(distance / max(c["boundary"], 1e-12), 0, 1)
    fade = t*t*(3-2*t)
    for r in c["protected"]:
        dx = np.maximum.reduce([r["xmin"]-xy[:, 0], xy[:, 0]-r["xmax"], np.zeros(len(xy))])
        dy = np.maximum.reduce([r["ymin"]-xy[:, 1], xy[:, 1]-r["ymax"], np.zeros(len(xy))])
        fade *= np.clip(np.hypot(dx, dy)/max(c["boundary"], 1e-12), 0, 1)
    return fade

def field(xy, c, s):
    q = xy.copy()
    if c["style"] == "flowing":
        q[:, 0] += .035*c["width"]*np.sin(q[:, 1]/c["height"]*2*np.pi)
    dist, ids = cKDTree(s).query(q, k=2)
    sep = np.linalg.norm(s[ids[:, 0]]-s[ids[:, 1]], axis=1)
    f = np.clip((dist[:, 1]**2-dist[:, 0]**2)/(2*np.maximum(sep, 1e-9)*np.maximum(sep*.5, 2)), 0, 1)
    if c["style"] in ["organic", "flowing"]:
        f = f*f*(3-2*f)
    if c["style"] == "fractured":
        f *= np.random.default_rng(c["seed"]+1).uniform(.35, 1, len(s))[ids[:, 0]]
    if c["mode"] == "flat":
        f *= 0
    if c["mode"] == "inverted":
        f = -f
    return c["relief"]*f*mask(xy, c)

def construct(c):
    s = sites(c)
    if c["input"] not in ["plane", "box"]:
        path = Path(c["input"])
        if path.suffix.lower() not in [".stl", ".obj", ".glb"]:
            raise ValueError("Imported input must be STL, OBJ or GLB")
        source = trimesh.load(path, force="mesh", process=True)
        if not len(source.faces) or not np.isfinite(source.vertices).all():
            raise ValueError("Input has empty or non-finite geometry")
        source.apply_scale(c["scale"])
        # Preserve original topology and vertices; imports must already have adequate sampling.
        v = source.vertices.copy()
        before = v.copy()
        xy = v[:, :2]
        if np.ptp(v[:, 0]) > c["width"]+1e-7 or np.ptp(v[:, 1]) > c["height"]+1e-7:
            raise ValueError("Input XY bounds exceed configured width/height; center and size the input first")
        top = source.vertex_normals[:, 2] > .5
        v[top, 2] += field(xy[top], c, s)
        mesh = trimesh.Trimesh(v, source.faces.copy(), process=False)
        if c["solidify"] and not source.is_watertight:
            raise ValueError("Open imports cannot be solidified automatically; use a closed mesh or solidify: false")
        protected = mask(xy, c) == 0
        err = float(np.max(np.abs(v[protected]-before[protected]))) if protected.any() else 0.0
        return mesh, {"sites": s.tolist(), "protected_displacement_mm": err, "thickness": None,
                      "input_type": "imported", "import_note": "+Z-facing vertices displaced; sampling/topology retained"}
    nx = c["resolution"]
    ny = max(8, round(nx*c["height"]/c["width"]))
    x, y = np.meshgrid(np.linspace(-c["width"]/2, c["width"]/2, nx), np.linspace(-c["height"]/2, c["height"]/2, ny))
    xy = np.c_[x.ravel(), y.ravel()]
    relief = field(xy, c, s)
    # Inverted relief has a raised baseline so substrate never falls below thickness.
    baseline = c["thickness"] + (c["relief"] if c["mode"] == "inverted" else 0)
    z = baseline+relief
    top = np.c_[xy, z]
    n = len(top)
    faces = []
    for j in range(ny-1):
        for i in range(nx-1):
            a = j*nx+i; b = a+1; d = a+nx; e = d+1
            faces.extend([[a, b, e], [a, e, d]])
    if not c["solidify"]:
        return trimesh.Trimesh(top, np.array(faces), process=False), {"sites": s.tolist(), "protected_displacement_mm": 0.0, "thickness": None, "input_type": "plane"}
    bottom_z = z-c["thickness"] if c["constant_thickness"] else np.zeros(n)
    vertices = np.r_[top, np.c_[xy, bottom_z]]
    faces += [[a+n, d+n, b+n] for a, b, d in faces.copy()]
    ring = list(range(nx))+[j*nx+nx-1 for j in range(1, ny)]+list(range(n-2, n-nx-1, -1))+[j*nx for j in range(ny-2, 0, -1)]
    for a, b in zip(ring, ring[1:]+ring[:1]):
        faces.extend([[a, a+n, b+n], [a, b+n, b]])
    metric = {"axis": "+Z", "minimum_vertical_mm": float((z-bottom_z).min()),
              "normal_thickness_verified": False, "method": "known paired grid vertices; not shortest normal distance"}
    return trimesh.Trimesh(vertices, np.array(faces), process=False), {"sites": s.tolist(), "protected_displacement_mm": 0.0, "thickness": metric, "input_type": c["input"]}
