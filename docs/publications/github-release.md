# Procedural Voronoi Mesh 1.0.0

I’m releasing the standalone generator developed from my CNC enclosure experiments. This release includes a Python API, installable CLI, local browser interface, fifteen built-in presets, generated examples, STL/OBJ/GLB/3MF exports, headless PNG rendering, configuration and manifest reproduction, and optional independent CGAL self-intersection validation.

![Actual raised Voronoi output included with the release](../assets/images/presets/organic-raised.png)

The Doesbot example preserves historical seed/configuration evidence on a sanitized new surface. It does not claim exact V23 reconstruction or publish unfinished enclosure CAD. Computational validation does not establish physical fit, print success, or manufacturing acceptance.

Install from source with `python -m pip install '.[validation]'`, then run `voronoi-mesh generate` or `voronoi-mesh serve`.

— David Cannan (Cdaprod)
