# Doesbot CNC controller enclosure: engineering case study

The procedural Voronoi Mesh project grew out of a real enclosure problem. This page collects the hardware, reference geometry, saved enclosure views, and software work in one place. I’m David Cannan (Cdaprod), a self-taught software and systems engineer; I used programming and repeatable geometry experiments to work through the mechanical design.

The enclosure images below are computational review artifacts from the saved engineering history. They are not evidence of a successful physical fit or print.

## Hardware and component references

The actual controller board supplied the connector arrangement and the interfaces the enclosure needed to preserve.

![Full top-side photograph of the Doesbot controller PCB](../assets/images/hardware/doesbot-board-top.jpeg)

*Physical board overview used as a placement reference. Visible component positions are not a substitute for measured envelope dimensions.*

![Real Doesbot CNC controller terminal blocks on the PCB](../assets/images/hardware/doesbot-terminal-blocks.jpg)

*User-supplied hardware photograph. It is a close-up reference, not a dimensioned drawing.*

The stepper-drive headers and adapter hardware are useful supplementary references because a component's usable envelope includes connectors, installed accessories, and access space—not just the board outline.

![Stepper-drive header hardware on the Doesbot board](../assets/images/hardware/doesbot-stepper-drive-headers.jpeg)

![MKS driver adapter hardware documented during the project](../assets/images/hardware/mks-driver-adapters.jpeg)

*Physical reference images only. Connector compatibility, installed orientation, dimensions, and clearances must be established independently.*

The FreeCAD reference assembly let me inspect the PCB, connector bodies, terminal groups, headers, and mounting locations together.

![FreeCAD-derived PCB component reference with connector bodies and headers](../assets/images/assembly/v005-pcb-component-reference.png)

*Saved V005 native component reference view. Some solids are simplified reference geometry; they are not all verified manufacturer models.*

The header detail shows why the 8×2 and 10×2 pin components needed to remain visible in assembly views.

![V005 FreeCAD assembly with the male header pins visible](../assets/images/details/v005-header-pin-visibility.png)

## Master references and access geometry

I used the constrained PCB master as the positional authority. The recovered R08 dependency chain links the terminal housing placement to each screw axis, then links the axis to native access features.

![FreeCAD Sketcher master geometry for the controller board layout](../assets/images/freecad/doesbot-freecad-master-sketch.jpeg)

*The saved sketch records construction geometry and reference constraints used during PCB layout modeling.*

![R08 housing to screw axes to native access tools](../assets/images/freecad/r08-master-linked-references.png)

*Geometry-derived review diagram from the FreeCAD recovery work. The source FCStd remains in the local engineering archive and is not included here.*

## V23 cover and V24 assembly views

V23 carries the organic faceted exterior and the original functional opening layout. The oblique and top views show different aspects of the same saved cover render set.

![V23 plus R07 cover, oblique view](../assets/images/revisions/v23-r07-cover-oblique.png)

*Saved V23 + R07 cover render. It is a mesh-based computational artifact, not a parametric reconstruction of every exterior surface.*

![V23 plus R07 cover, top view with functional openings](../assets/images/revisions/v23-r07-cover-top.png)

The current Blender renders use the V24 lid and base STL files with the saved PCB/component OBJ. The OBJ import is explicitly Z-up; its saved assembly positions, rotations, scale, and X/Y registration are preserved.

![Blender Cycles render of the V24 cover, base, PCB and components in the saved closed pose](../assets/images/showcase/closed.jpg)

*Computational review candidate rendered from saved exported geometry. Lid/base seating and component fit still need physical verification.*

![Blender Cycles exploded render of the V24 cover, PCB/components and lower enclosure](../assets/images/showcase/exploded.jpg)

*Display translations are along Z only; all component rotations and X/Y registrations are preserved.*

![Blender Cycles render of the V24 lid exterior](../assets/images/showcase/lid-exterior.jpg)

![Blender Cycles render of the V24 lid interior](../assets/images/showcase/lid-underside.jpg)

![Blender Cycles render of the V24 base interior](../assets/images/showcase/base.jpg)

The previously saved V24 computational closed/exploded PNGs remain available as [closed assembly reference](../assets/images/revisions/v24-computational-candidate.png) and [exploded assembly reference](../assets/images/revisions/v24-exploded-reference.png); the current renders use the same saved input geometry with higher-quality local lighting.

## R07 support integration

R07 was treated as a local support and access problem around the real header placement and neighboring reference regions. The saved section shows the cover and support geometry at a cut through that area.

![Section through the V23 cover and R07 support integration](../assets/images/validation/v23-r07-cover-section.png)

The native support geometry and the mesh integration were separate engineering stages. A mesh Boolean can preserve the surface outside a local region while still leaving physical clearances unresolved. I therefore describe these results as computational review, not manufacturing acceptance.

## What the enclosure work changed in the software

The design work led me to build a reusable generator rather than leave the procedural operation embedded in one project. Its public API and CLI make seeds and settings explicit, its manifests record provenance, and its validators reload exported files before checking mesh topology.

The recovered historical values are seed `20261110`, 55 cells, and 1.8 mm relief. The public Doesbot example applies those settings to a sanitized slab; it does not reproduce V23. Enclosure supports, openings, reinforcements, and mating features remain CAD operations outside this repository.

![Sanitized generated example using the recovered Doesbot configuration](../../examples/doesbot/generated/preview.png)

## What remains unverified

The saved views document engineering intent and computational geometry. They do not prove the simplified component bodies match vendor models, that every connector has physical clearance, that the cover fits the base after printing, or that the enclosure will survive use. Those require authoritative component geometry, physical measurements, and fit/print checks.

For the reusable software, see the [generator README](../../README.md), [technical guide](../engineering/guide.md), [full preset gallery](../gallery/README.md), and [engineering story](../story/from-hardware-to-procedural-geometry.md).
