"""Reloaded mesh checks; independent CGAL optional, required by strict presets."""
from pathlib import Path
import numpy as np
import trimesh

def read(path):
    path = Path(path)
    if path.suffix.lower() == ".3mf":
        from .export import read_3mf
        return read_3mf(path)
    m = trimesh.load(path, force="mesh", process=False)
    # Exact-coordinate welding only, required for STL triangle soup.
    v, inv = np.unique(np.asarray(m.vertices, dtype=np.float64), axis=0, return_inverse=True)
    return trimesh.Trimesh(v, inv[m.faces], process=False)

def validate(path, closed=None, near_area=1e-10, independent=True):
    m = read(path)
    if not len(m.faces):
        raise ValueError("Mesh has no triangles")
    incidence = np.bincount(m.edges_unique_inverse, minlength=len(m.edges_unique))
    area = m.area_faces
    duplicate = len(m.faces)-len(np.unique(np.sort(m.faces, axis=1), axis=0))
    from scipy.sparse.csgraph import connected_components
    from scipy.sparse import coo_matrix
    e = m.edges_unique
    g = coo_matrix((np.ones(len(e)*2), (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])), shape=(len(m.vertices), len(m.vertices)))
    count = connected_components(g, directed=False)[0]
    r = {"vertices": len(m.vertices), "faces": len(m.faces), "components": int(count),
         "watertight": bool(m.is_watertight), "winding_consistent": bool(m.is_winding_consistent),
         "volume_mm3": float(m.volume), "positive_volume": bool(m.volume > 0),
         "boundary_edges": int((incidence == 1).sum()), "nonmanifold_edges": int((incidence > 2).sum()),
         "duplicate_faces": int(duplicate), "degenerate_faces": int((area == 0).sum()),
         "near_zero_faces": int((area <= near_area).sum()), "minimum_area_mm2": float(area.min()),
         "finite": bool(np.isfinite(m.vertices).all()), "self_intersections": None,
         "self_intersection_checker": "unavailable", "physical_fit": "not assessed"}
    if independent:
        try:
            import igl.copyleft.cgal as cgal
            _, _, pairs, _, _ = cgal.remesh_self_intersections(np.asarray(m.vertices, dtype=np.float64), np.asarray(m.faces, dtype=np.int64), detect_only=True)
            r["self_intersections"] = len(pairs)
            r["self_intersection_checker"] = "libigl/CGAL"
        except ImportError:
            pass
    if closed is None:
        closed = bool(m.is_watertight)
    r["expected_closed"] = bool(closed)
    r["pass"] = bool(r["finite"] and r["components"] == 1 and r["winding_consistent"] and
                     not any(r[k] for k in ["duplicate_faces", "degenerate_faces", "nonmanifold_edges"]) and
                     r["self_intersections"] in [None, 0] and
                     (not closed or (r["watertight"] and r["positive_volume"])))
    return r
