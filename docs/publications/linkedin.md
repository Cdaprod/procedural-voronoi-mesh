# LinkedIn announcement

I’ve been turning lessons from my Doesbot CNC enclosure work into a reusable Python geometry tool.

procedural-voronoi-mesh generates seeded Voronoi relief, protects boundaries and rectangular exclusion regions, exports STL/OBJ/GLB/3MF, and saves the configuration and validation with each build. It has a CLI, Python API, and local browser interface.

![Blender Cycles render of the actual V24 CNC enclosure assembly](../assets/images/showcase/closed.jpg)

The work reinforced a practical lesson for me: native CAD relationships, mesh integration, visualization, and physical fit are different things. A successful render or Boolean does not settle all four.

I’m self-taught, and I like software that leaves enough evidence to reproduce an experiment and understand its limits. That is what I’m aiming for here.

Code, examples, and engineering story: https://github.com/Cdaprod/procedural-voronoi-mesh

The [enclosure case study](../showcase/doesbot-cnc-enclosure.md) shows the saved mechanical references and review renders behind the project.

David Cannan (Cdaprod)
