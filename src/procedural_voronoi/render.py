"""Headless PNG rendering from actual triangles; no Blender runtime required."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

def render(mesh, output, title="Voronoi relief", quality="preview"):
    fig = plt.figure(figsize=(9, 6), facecolor="#101b28")
    ax = fig.add_subplot(111, projection="3d", computed_zorder=False)
    ax.set_facecolor("#101b28")
    xyz = mesh.triangles
    z = xyz.mean(axis=1)[:, 2]
    normals = mesh.face_normals
    light = np.clip(normals @ np.array([-.3, -.4, .85]), .1, 1)
    color = plt.cm.viridis((z-z.min())/max(np.ptp(z), 1e-9)*.7+.15)
    color[:, :3] *= (.4+.6*light[:, None])
    ax.add_collection3d(Poly3DCollection(xyz, facecolors=color, edgecolors="none", linewidths=0))
    lo, hi = mesh.bounds; center = (lo+hi)/2; extent = max(hi-lo)
    ax.set_xlim(center[0]-extent*.52, center[0]+extent*.52)
    ax.set_ylim(center[1]-extent*.42, center[1]+extent*.42)
    ax.set_zlim(lo[2]-extent*.02, hi[2]+extent*.02)
    ax.set_box_aspect([1, .82, max(.08, (hi[2]-lo[2])/extent+.04)], zoom=1.55)
    ax.view_init(elev=38, azim=-58); ax.set_axis_off()
    fig.text(.06, .91, title, color="white", fontsize=15, weight="bold")
    fig.text(.06, .07, f"Actual mesh · {len(mesh.faces):,} triangles · millimetres", color="#a9c0d5", fontsize=10)
    fig.savefig(output, dpi=160 if quality == "high" else 110, facecolor=fig.get_facecolor(), metadata={"Software": "procedural-voronoi-mesh"})
    plt.close(fig)
