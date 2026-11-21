# Historical Doesbot parameter reference

Recovered evidence: seed **20261110**, **55 cells**, **1.8 mm relief**, border 7 mm, perimeter fade 4 mm. `historical-evidence.json` preserves the numerical replay record; `provenance.json` identifies its source and SHA-256.

![Actual generated sanitized surface using recovered Doesbot parameters](generated/preview.png)

```sh
voronoi-mesh doesbot --output output/doesbot-reference
voronoi-mesh reproduce examples/doesbot/generated/manifest.json --output output/replayed
```

The distributed geometry is a new slab made from these recovered settings and the public algorithm. No unfinished hardware CAD or enclosure STL is redistributed. The recovered replay algorithm is in historical_replay.py and needs the original historical height arrays, which are not distributed here; its evidence records an extremely small height-field replay error. That evidence applies to its archived field, not to this new slab or V23.

Distinguish these artifacts:

1. Historical seeded field: the recovered configuration and archived numerical replay.
2. V23: an enclosure shell with earlier construction and later exterior reinforcement operations.
3. V23/R07: native support geometry integrated into that mesh by separate Boolean operations.
4. V24: later PCB keepout and mating reconciliation, still subject to physical and functional validation.
5. This public generator: a reusable engine producing new geometry from explicit configuration.

The seed is not proof of exact V23 reconstruction. The first-person engineering story and review imagery explain the development without shipping unfinished enclosure models.
