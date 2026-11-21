# I turned a CNC enclosure experiment into a seeded mesh generator

I started with a practical problem: model an enclosure around a Doesbot controller without losing the relationship between its connectors, header pins, terminal screws, and mounting points. The organic Voronoi surface was the visible part, but the mechanical references were what made it useful.

![Physical top-side photograph of the Doesbot CNC controller PCB](../assets/images/hardware/doesbot-board-top.jpeg)

*The real hardware supplied the initial layout problem; connector dimensions were addressed through measured and modeled references rather than inferred solely from photographs.*

![Original FreeCAD Sketcher master reference for the controller PCB](../assets/images/freecad/doesbot-freecad-master-sketch.jpeg)

*The working Sketcher view captures the geometric reference stage that preceded the procedural enclosure roof.*

![Blender Cycles render of the V24 enclosure assembly that motivated the public geometry tool](../assets/images/showcase/closed.jpg)

*This is a computational enclosure review render. It is separate from the public generator’s planar sample outputs and does not establish physical fit.*

![Exploded Blender Cycles view of the saved V24 cover, PCB/component references, and base](../assets/images/showcase/exploded.jpg)

I learned that native CAD features and triangle meshes need different workflows. Converting hundreds of thousands of triangles into individual B-rep faces was not a useful shortcut to a parametric model. Native references could define mechanical supports, while mesh operations handled their integration into the organic exterior. Independent validation after export mattered because a successful Boolean was not a guarantee of clean topology or physical clearance.

The reusable result is procedural-voronoi-mesh: a Python library, CLI, and local browser with deterministic seeds, preset configurations, protected regions, portable mesh exports, actual triangle renders, and saved build manifests.

![Actual comparison of four generated preset surfaces](../assets/images/presets/comparison.png)

The project’s [enclosure case study](../showcase/doesbot-cnc-enclosure.md) shows the board references, lid, assembly, and local support reviews. The public package does not include unfinished enclosure CAD.

I preserved the historical Doesbot parameter evidence—seed 20261110, 55 cells, 1.8 mm relief—without claiming that those three numbers reproduce the final V23 enclosure. The public reference is a sanitized new slab. The enclosure’s later supports and mating corrections are separate operations.

You can generate a default example with `voronoi-mesh generate`, inspect its validation JSON, and reproduce it from the manifest. I’ve included working presets and examples because a library that leaves all the configuration work to its first user is not the tool I wanted to ship.

The limitations are explicit: vertical thickness is not normal thickness, imported meshes need appropriate tessellation and +Z orientation, and mesh topology does not prove physical printability. The software is an engineering tool, not a fit certificate.

Source and examples: https://github.com/Cdaprod/procedural-voronoi-mesh

— David Cannan (Cdaprod)
