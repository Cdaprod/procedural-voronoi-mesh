"""Stable geometry and portable 3MF exports."""
from pathlib import Path
import zipfile
import xml.etree.ElementTree as E
import numpy as np
import trimesh
NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
def canonical(mesh):
    v, inv = np.unique(np.asarray(mesh.vertices, dtype=np.float64), axis=0, return_inverse=True)
    f = inv[mesh.faces]
    f = np.array([np.roll(x, -int(np.argmin(x))) for x in f])
    f = f[np.lexsort((f[:, 2], f[:, 1], f[:, 0]))]
    return trimesh.Trimesh(v, f, process=False)
def export(mesh, path):
    path = Path(path)
    if path.suffix == ".3mf":
        write_3mf(mesh, path)
    else:
        mesh.export(path)
def write_3mf(m, path):
    E.register_namespace("", NS)
    root = E.Element("{"+NS+"}model", unit="millimeter")
    ob = E.SubElement(E.SubElement(root, "resources"), "object", id="1", type="model")
    me = E.SubElement(ob, "mesh"); ve = E.SubElement(me, "vertices"); tr = E.SubElement(me, "triangles")
    for x in m.vertices:
        E.SubElement(ve, "vertex", **dict(zip(["x", "y", "z"], [repr(float(t)) for t in x])))
    for f in m.faces:
        E.SubElement(tr, "triangle", **dict(zip(["v1", "v2", "v3"], map(str, f))))
    E.SubElement(E.SubElement(root, "build"), "item", objectid="1")
    data = {
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>',
        "_rels/.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="r0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>',
        "3D/3dmodel.model": E.tostring(root, encoding="utf-8", xml_declaration=True),
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in data.items():
            zi = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, body)
def read_3mf(path):
    with zipfile.ZipFile(path) as z:
        r = E.fromstring(z.read("3D/3dmodel.model"))
    v = [[float(e.attrib[k]) for k in ["x", "y", "z"]] for e in r.iter() if e.tag.split("}")[-1] == "vertex"]
    f = [[int(e.attrib[k]) for k in ["v1", "v2", "v3"]] for e in r.iter() if e.tag.split("}")[-1] == "triangle"]
    return trimesh.Trimesh(v, f, process=False)
