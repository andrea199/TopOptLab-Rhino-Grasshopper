# Resolution increment: measured scope and acceptance

Development snapshot, 21 September 2026. ECC: scoped plan, red/green regressions,
repeated performance experiments and independent code/security review.
No publication or engineering certification. Completed numerical runs and remaining acceptance are distinguished below.

## Implementation and resource policy

The earlier 5 mm shelf had 7,500 bounding / 7,328 active cells. Raising its old
8k/32,768 guards alone would leave expensive stiffness indices, neighbor filters,
extrusion projections, preview construction and repeated JSON parsing.

The increment adds cached block assembly, elasticity AMG modes, FFT cone filtering
with exact transpose, linear-storage group projection, boundary-only preview and
cached unchanged snapshots. Large outputs preserve Gauss stress tensors in per-case
NPZ archives instead of duplicating them in JSON. Keep the entire job folder.

Domain keeps its generic 8,000-cell user default; the shelf explicitly selects
250,000. Admission checks reserve 40% of currently free RAM and 30% of free CUDA
memory. An explicit host budget can lower admission, never override free memory.
Absolute 2,000,000-cell / 2,048-per-axis input guards are NOT validated capacities.
Estimates are conservative heuristics, not peak-memory/time/accuracy guarantees.
No backend or residual tolerance is silently changed.

Keep Physical filter radius fixed across refinements: the shelf uses 9 mm.
CAD radial clearance tolerance (0.05 mm) and initial final tetrahedral size (4 mm) are
independent of Cell size. Smooth display is not evidence of stress convergence.

## Repeated controlled measurements

[Solver scaling evidence](SOLVER_SCALING_EVIDENCE.md) records exact inputs and repeats.
The 27,000-cell assembly trial fell from about 973 to 459 MiB peak process RSS.
The measured 8,000-cell changing-density AMG sequence improved 2.16–4.94 times across
two comparisons. These are workload-specific results, not universal speedups.

## Actual shelf: four independent loads

Native RhinoCore geometry/condition construction passed at 5, 2.5 and 2 mm.
At 2.5 mm: 60,000 bounding / 58,552 active cells.
At 2 mm: 121,875 bounding / 119,155 active cells.
Construction alone does not establish a solved or accurate engineering model.

On the development PC (Core Ultra 9 285H, about 64 GiB RAM, RTX 5070 Laptop 8 GiB),
2.5 mm full-solid FEM completed all four cases:

| Backend | End-to-end seconds | Peak host RSS MiB | Maximum displacement mm |
|---|---:|---:|---:|
| CPU AMG | 63.17 | 1010.58 | 0.031088731474 |
| CUDA CG | 40.40 | 1360.15 | 0.031088731474 |

These are single fresh-process runs including fields/reports, not repeated speedup
benchmarks. Same geometry, material, load cases and tolerance; case compliance and
displacement agree to about 1e-10 relative or better. RSS is host memory, not VRAM.
See [machine-readable evidence](resolution-evidence.json).

The initial CPU AMG optimization trial was deliberately cancelled after its initial
feasible iterate (210 seconds), and is not a completed optimization. The full 60-update CUDA trial completed in 2,595.67 s (43.26 min), with peak host RSS 1,759.02 MiB. It terminated at the iteration limit, not convergence. Four-case constrained feasibility passed; weighted compliance fell 39.46%, and the worst case displacement of the relaxed design was 0.32535 mm. This actual workflow ran alongside some CPU work and started before the later stable RHS warm-start keys were added, so it is not a controlled timing for that last change. The 2 mm full-solid FEM has completed all four cases: 119,155 active cells, 144.06 s and 1,956.90 MiB host RSS. This run overlapped other work, so its time is a capacity observation, not a controlled speed comparison. Maximum displacement was 0.02975464 mm; residuals were below 5.6e-10 and force equilibrium errors below 1.4e-8. The raster geometry/patches also change with cell size (25 mm width does not divide evenly by 2 mm), so this is not a formal mesh-convergence result. The 2 mm constrained workload also completed two updates on all four cases, including adjoints, with peak host RSS 2,930.29 MiB and strict residual checks. Its 2,278.35 s raw duration is EXCLUDED from performance evidence: Windows Kernel-Power events 506/507 confirmed Modern Standby during the job. It is a capacity/numerical test only, not a converged design.

## Tests and integration

- Baseline: 207 tests passed before changes.
- Targeted radius/resource/2D tests: 41 passed. New tests first reproduced silent 2D
  radius omission, ignored positive 2D RAM budget and nonfinite FEM metadata.
- Native boundary harness: exposed faces, cavity, truncated mask, outward orientation,
  volume/colors; accepted 60k/122k guards, rejected low memory, overflow and bad dimensions.
- Native snapshot harness: unchanged/changed/replaced files, completion priority,
  parse recovery, deletion, folder and job-identity invalidation.
- Legacy native shelf: four dimensional/load variants passed.
- C#/external Python bridge: constrained 2D/3D and saved-case selection passed.
- Full regression at the first integrated checkpoint: 262 tests passed (one pre-existing upstream near-zero-Jacobian warning in the unit-conversion test). After the final CAD mesher revision, 261 tests passed; a discarded meshing-route test accounts for the count change. The final shelf threshold/archive checks also passed (11 tests).
- Updated GH/GHX archive readback and C#/Python generic final-geometry/TET4 bridge passed. The installed DLL and configured Python worker passed that bridge again. Receipt: tool/build/resolution-ready.json; rollback: tool/build/installation-backups/resolution-20260921-200144. Assembly SHA-256 was checked against the compiled build.

## Scope still requiring acceptance

The optional CAD reconstruction is shelf-specific, not arbitrary-BRep reconstruction.
[CAD interfaces](CAD_INTERFACES.md) explains nominal plates, clearance tolerances,
source contracts and physical loads. A closed surface is not a completed final FEM;
tetrahedral quality checks and refinement criteria remain enforced.

Interactive Rhino preview/Stop/Reset/Bake/Undo for this build requires acceptance.
Printed ABS properties, creep, contact/fasteners, load-patch/stress convergence and
fabrication tolerances remain application-specific engineering work.

## Threshold is a design decision, not display smoothing

The old threshold 0.35 on the new fine design removed too much material: all-case
voxel reanalysis reached 45.50 mm, exceeding the chosen 1 mm limit. It was rejected
as the example setting. A bounded three-candidate comparison kept identical physics:

| Threshold | Retained cells | Mass g | Worst displacement mm |
|---|---:|---:|---:|
| 0.25 | 40,098 | 651.59 | 0.05638 |
| 0.30 | 26,252 | 426.60 | 0.19300 |
| 0.32 | 21,084 | 342.62 | 0.24291 |

All four cases at 0.32 passed the chosen voxel-model displacement limit, with linear
residuals below 9e-10. The example now starts at 0.32. See
[threshold evidence](threshold-calibration-25mm.json). This is not a guarantee for
other geometries or meshes, and extraction changes the shape again.

## CAD integration reference

The actual earlier 5 mm design completed the entire new CAD extraction/remeshing/FEM
pipeline: 136,749 tetrahedra, 36,396 nodes, mass 255.44 g, worst displacement 0.26421 mm
and four residuals below 1e-9. Source/exported geometry hashes match; CAD voids and
protected interfaces passed checks again on the tetrahedral boundary. Eighteen
elements are below the advisory quality 0.05 and only one mesh level was run;
structurally_verified remains false. See [CAD validation](cad-interface-validation.json).
The newer 2.5 mm surface at threshold 0.32 passes the CAD geometry checks but its automatic conforming FEM remains INCOMPLETE. The default partition fails Gmsh parameterization. A bounded alternative partition of the unchanged surface passed parameterization but timed out after 210 s without an accepted mesh; it was not integrated. No geometric, solver or mesh-quality checks were weakened. This candidate is not final-shape verified. See [fine CAD evidence](cad-fine-interface-validation.json).

The continuous CAD-derived candidate weighs 309.70 g, distinct from the 342.62 g binary voxel model. Geometry changes after thresholding/extraction, which is exactly why its final FEM is still required. A precomputed STL in declared mm is included as tool/examples/shelf_bracket_25mm_candidate_mm.stl with a provenance JSON; it is a preliminary geometry study.

## Installation

Installed locally on 21 September 2026 with Rhino closed. Native interactive UI acceptance remains open. No repository publication or commit was performed. Open the newly generated engineering_shelf_bracket_3d.gh; previously saved copies retain their own slider values.
