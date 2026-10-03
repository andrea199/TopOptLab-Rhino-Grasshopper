# Nominal CAD interfaces for the shelf bracket

## Current validation status

CAD interface extraction, physical load/support transfer and their provenance checks are covered by automated tests. A holed-solid case also checks the CAD mesher at two element sizes. On the reference 5 mm shelf design, a mesh generated from the cleaned CAD surface passed the existing FEM quality rejection threshold and all four CPU AMG cases solved with relative residuals below 1e-9. The mesh still contains elements below the advisory quality threshold of 0.05 and only one mesh level was analysed, so this is **not a converged or structurally qualified final design**.

The software rejects poor automatic meshes explicitly. It does not silently revert to voxel holes, reduce the FEM quality threshold or present earlier voxel results as final-CAD verification. Thin grooves at web/plate intersections may require explicit cleanup or a better surface/volume mesh. Changing a cleanup tolerance changes geometry and must be reviewed.

The optional CAD path in **Final Geometry 3D** rebuilds the wall and shelf attachment plates from their nominal dimensions. It subtracts all four screw holes and the four tool-access volumes before exporting the final triangle surface. These interface dimensions are independent of the optimization cell size.

## Grasshopper connections

Connect the **Shelf Bracket 3D → Spec** output and the **Bracket Cases 3D → Summary** output to the optional CAD inputs of Final Geometry 3D. Set **CAD chord tolerance** in millimetres (initially 0.05 mm). **Web cleanup** is a separate geometric simplification tolerance, initially 0.01 mm; set it to 0 to disable simplification. **Envelope cleanup** is optional snapping to outer envelope planes, initially 0 (disabled). The existing Source, Threshold, Smoothing, Edited mesh, Run, Stop and Reset inputs keep their previous positions.

Without the CAD contract, extraction follows the existing generic path and preserves the original voxel Keep/envelope. The CAD path currently supports the parametric shelf bracket, in mm and N. It does not claim to preserve arbitrary Rhino Breps.

## What is reconstructed

1. Extract the smooth density isosurface from the optimization result.
2. Add the nominal wall plate and top plate, minus screw/tool voids.
3. Preserve any additional protected source voxels inside the nominal allowed CAD volume.
4. Clip to the nominal envelope and remove all nominal forbidden volumes.
5. Simplify the density web within the explicitly selected Web cleanup tolerance (0.01 mm initially), reconstruct nominal interfaces and subtract all voids again. The report records this tolerance. This happens before STL export and surface hashing; Final FEM always receives that same extracted surface.
6. If Envelope cleanup is enabled, snap surface vertices within that distance of an outer envelope plane onto that plane, then reconstruct nominal plates and subtract voids again. The report records moved vertices and maximum displacement (bounded by √3 times the per-axis tolerance).
7. Remove numerical collinear facets at a maximum tolerance of 0.0000001 mm and check protected volume loss, forbidden-volume intrusion and material outside the envelope; reject failed geometry.


The source domain must match a fresh analytical centre-sampling of the supplied CAD specification. The original four load cases, force values, gravity and rigid wall-pad supports must also match the physical loading contract. Connecting an unrelated bracket specification or changed payload does not silently alter an old optimization.

The core web still comes from the density grid. Restoring the interfaces cannot recover optimized web details that were never resolved by that grid. Refining the optimization remains necessary for those features.

## Circular surface tolerance

STL stores triangles, not exact cylindrical CAD surfaces. Each cylindrical void is represented by a **circumscribed polygon**. Its minimum radius is the nominal circle radius, and its maximum radius exceeds nominal by at most the requested chord tolerance. Thus a nominal screw clearance is not narrowed by inscribed polygon chords. The actual radial overcut bound and number of segments are recorded in the extraction report.

At the default 0.05 mm tolerance, an 8 mm diameter nominal hole can locally be up to 0.10 mm wider in diameter. This is a geometric tessellation bound, **not** a print tolerance, shrinkage allowance, fit specification, or validated minimum wall. Tool access remains reserved space, not a proof that a screwdriver can reach every fastener.

Planar plate positions and thicknesses use their nominal coordinates. This output is a closed triangle surface, not an exact BRep.

## Loads and supports on the final surface

The generic final-FEM mapper requires every original loaded voxel face to survive. That condition cannot be used for nominal circular holes: replacing raster holes changes their neighbouring contact areas.

The CAD path therefore uses the physical regions stated by Bracket Cases 3D:

- Full top contact surface for the distributed payload and the separately entered share of shelf mass.
- Front strip of the chosen physical depth for the front case.
- Right and left portions of that strip for the two separate torsion cases.
- Nominal wall-face pads around the two wall holes, fixed in X, Y and Z.

Holes are excluded from these contact areas. Uniform traction is normalized by the actual surface area so that each total payload remains `mass × 9.80665 N`. Self-weight is recomputed from the final tetrahedral solid.

The physical CAD patch centroid may differ from the old raster patch centroid, especially when dimensions are not multiples of cell size. The report records the new centroid, its moment about the wall origin, the old raster resultant and **the moment difference**. This is an explicit change from an approximate contact area to its nominal CAD definition; total payload force is preserved.

Force and moment are checked against the integrated nominal-patch load. A missing contact patch, area discrepancy above 0.5%, or centroid movement above max(0.01 mm, 0.005 × source cell size) after tetrahedral remeshing is rejected. These checks detect transfer failures; they are not a stress-accuracy certificate. The nominal reference is the same bounded polygonal CAD surface.

## Provenance and edited meshes

The extracted result stores the full CAD and loading contract plus its separate SHA-256 signature. Final FEM validates that record and the original physical inputs again. Geometry has its existing independent surface hash.

An optional edited mesh must also retain nominal attachment material and any additional protected source material inside the allowed CAD envelope. It must not fill screw/tool voids or extend beyond the envelope. A failed edit is rejected rather than repaired without notice.

## Engineering limits

The wall pads are an idealized rigid connection. Wall strength, anchors, screws, preload, friction and contact opening are not simulated. The ABS reference remains a linear isotropic material model; printed orientation, creep and failure allowables require separate validation. A visually smooth shape and clear circular holes do not establish a safe shelf rating.

Run Final FEM and its mesh-refinement study after CAD reconstruction. Optimized-density and voxel-verification results describe the earlier geometry and cannot substitute for this analysis.

## CAD tetrahedral meshing

The CAD route separates planar surface patches at a 0.5 degree classification angle, then uses Gmsh's conforming tetrahedral mesher and Netgen mesh optimizer. The generic voxel route keeps its previous 40 degree classification. The selected method and angle are recorded for each mesh-study level; there is no silent switch to the original voxel geometry.

Unlike the failed boundary-preserving development trial, this route remeshes surface patches to improve triangle quality. It retains the nominal circular polygons and planar interface constraints through **post-mesh CAD checks**, not by assuming that any remeshed surface is acceptable. The actual tetrahedral boundary is tested again for missing protected plate material, forbidden hole/tool intrusion and material outside the envelope. Loaded contact areas and centroids are checked independently during transfer. Volume must also agree with the extracted surface within the existing 2% limit; this volume screen alone is not a geometric distance guarantee or mesh-convergence proof.

No web simplification occurs secretly inside the mesher. Web and optional envelope cleanup belong to extraction, are recorded there, and are included in the geometry written to STL and hashed for Final FEM. An imported edited mesh is checked as supplied; it is not silently simplified.

Budgets are checked before CAD meshing and the existing maximum of 250,000 tetrahedra remains enforced. The CAD source surface has a separate 200,000-triangle budget. These limits are separate from optimization-grid resource planning. Poor tetrahedra remain subject to the existing rejection threshold of 0.0001 and the advisory threshold of 0.05.

Mesh-refinement studies examine the extracted geometry. They do not establish that density optimization, exact cylindrical geometry, material behaviour or wall anchorage is converged.

## Reproducible full-workflow reference

The production extraction → meshing → four-case FEM workflow completed in `tool/build/cad-shelf-runs/8a95f82891d34c968a4dffe05b5fc14e/`. Its source optimization used 5 mm voxels, while the final interfaces were reconstructed from nominal CAD, with 0.05 mm circular chord tolerance, 0.01 mm web cleanup and envelope snapping disabled.

- Exported and hashed surface: 2,474 vertices, 4,964 triangles.
- Source surface hash: `b76283b027b7c96c7fa15fe623ecbbdd59b578a347b6bd4dc3397f217252fd92`.
- Final conforming mesh: 136,749 tetrahedra; mass 0.25544 kg.
- Maximum displacement over the four independent cases: 0.26421 mm.
- Relative solver residuals: below 1e-9; load force and moment transfer errors below 4e-15.
- Nominal CAD invariants were checked both before STL export and on the actual tetrahedral boundary.

Only one mesh level was analysed and some tetrahedra remain below the advisory quality level of 0.05. The result therefore correctly reports `accuracy: not_studied`, `mesh_quality: poor_elements_present` and `structurally_verified: false`. No load rating or mesh convergence is claimed. The full machine-readable record is [cad-interface-validation.json](cad-interface-validation.json). Timing is included for traceability only; other development jobs ran concurrently.

## Fine-grid limitation observed on 21 September 2026

The 2.5 mm shelf-bracket optimization was also extracted at density thresholds 0.30 and 0.32. Both passed the CAD extraction invariants, but automatic Final FEM stopped during Gmsh surface parametrization (`Wrong topology of boundary mesh for parametrization`). A successful density-grid verification therefore cannot be described as a successful final-shape analysis.

The selected 0.32 surface has 7,506 vertices and 15,028 triangles, with geometry hash `824fcac2ce8692d412b950adbf8a81b6c2591cd54dbcb78d718d903de98d4821`. A bounded, isolated diagnostic using a 0.1 degree surface classification and 45 degree curve splitting passed parametrization on exactly those vertices, but tetrahedral meshing did not complete within its 210 second trial budget. No alternative path was added to production, no CAD or quality check was relaxed, and no different geometry was substituted. This is a limitation of the current automatic meshing path on that extracted surface; it is not evidence that its final stress or deformation is acceptable.

For this fine candidate, the exported surface is available for inspection and further remeshing work, while **Final FEM remains incomplete**. Any geometric repair must be exported and hashed as the actual shape being analysed, retain the nominal protected plates and empty screw/tool spaces, and pass the same load-transfer and tetrahedron-quality checks. The successful 5 mm reference above remains a separate development case. See [cad-fine-interface-validation.json](cad-fine-interface-validation.json) for the failed fine-candidate record.
