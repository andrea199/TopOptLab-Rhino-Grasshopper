# Latest resolution increment — 2026-09-21

See [resolution validation](RESOLUTION_VALIDATION.md) for larger-grid, solver, CAD-interface
and installation evidence. The records below describe earlier development snapshots;
their measured workloads and test counts are retained as history.

# Validation record — 2026-09-19

## Final geometry increment — 0.4.0-dev

- Full regression: 196 tests passed in 16.54 seconds. After tightening final-verification
  metadata, all 19 final-geometry tests passed again, including a stable three-level
  tension case and rejected final verification without a mesh study or with failed limits.
- One unchanged upstream small-Jacobian warning remains in the metre-unit HEX8 test.
- Continuous closed surface extraction, exact voxel Keep retention and envelope clipping;
  disconnected/open surfaces and edited meshes removing interfaces are rejected.
- TET4 exact tension on direct/CG/AMG/matrix-free/real CUDA, independent scikit-fem
  assembly and bending response, mm/N versus m/kN invariance, force/moment/energy balance.
- Point-force barycentric mapping, partial pressure patch integration, gravity and full-face
  support transfer. Missing loads and point-only supports are explicitly rejected.
- Print-direction/bed/overhang and sampled normal thickness tests; no global wall guarantee.
- Cancellation before final work and during the isolated mesher; stale source signatures
  and edited surface hashes rejected. Saved independent cases and HTML/STL outputs checked.
- 19 English GH/GHX pairs passed native SDK property/object readback. Four new components
  have code-native icons; 3D geometry/FEM icons carry a 3D badge. Review output indices
  for the original stages/case/field are preserved, with two new visibility outputs appended.
- Real C#/external-Python CUDA probe completed baseline, design, surface extraction, final
  TET4 FEM, saved-case selection and matched-baseline comparison. Native UI is not tested
  by this harness. The source installer preparation and dependency consistency check passed.
- The 401-file upstream snapshot SHA-256 manifest still matches; no upstream source edits.

### Real final-part mesh study

The default 120 x 60 x 30 mm constrained 3D cantilever was extracted at threshold 0.4
with 0.5-cell smoothing. One connected solid with an enclosed cavity: 1,490 vertices,
2,972 surface triangles, volume 148,932.246 mm3. All 144 protected interface voxels
were retained with zero measured volume loss. Original density-weighted volume was
129,599.876 mm3; extraction does not preserve that optimization volume exactly.

| Mesh size, mm | Tetrahedra | Max U Case 1, mm | Max VM Case 1, MPa | Max VM Case 2, MPa |
|---:|---:|---:|---:|---:|
| 6.000 | 8,886 | 0.00234161 | 1.877120 | 1.050332 |
| 4.500 | 14,553 | 0.00241367 | 1.886759 | 0.989792 |
| 3.375 | 25,174 | 0.00246713 | 1.938351 | 1.052842 |

All tested per-mesh displacement/stress limits passed. Mesh accuracy is **not established**
at the selected 5% tolerance: Case 2 peak stress changes by approximately 6% on both
refinements. There are also a small number of poor tetrahedra near the boundary (minimum
mean-ratio quality approximately 0.00079 on the finest level); these are reported.
The final shape is therefore not labelled numerically verified. This is a useful
qualification finding, not a reason to relabel the result converged.

Final force transfer error <= 3e-16, moment transfer error < 1e-15; maximum linear
relative residual < 1e-9 and equilibrium error < 5e-10 across these levels/cases.
Surface-to-volume mesh volume difference decreases from 0.412% to 0.156%.
See [final-geometry-reference.json](final-geometry-reference.json) for geometry,
printing review, material, complete case values, quality and refinement data.

### Performance and remaining acceptance

[PERFORMANCE_04.md](PERFORMANCE_04.md) records 1,728/13,824-voxel short constrained
workloads and 14,553-TET4 final FEM. CPU/CUDA response differences were < 5e-11 relative.
Recorded memory distinguishes host RSS from CuPy pool storage; total VRAM is not measured.
Single samples are not speedup guarantees or large-design qualification.

The owner confirmed the previous installed 3D workflow and smaller cell sizes working.
The new 0.4 native stages, printing flags, edited-mesh input, Stop and Bake/Undo still
require the acceptance sequence in FINAL_GEOMETRY.md. Higher-quality boundary meshes,
extended refinement/independent-solver studies, repeated performance measurements,
process-enforced manufacturing constraints and a second-PC installer test remain open.
Publication remains deferred.


## Previous engineering preview — 0.3.0-dev

- 176 project tests passed in 24.69 seconds for 0.3.0-dev, including design-limit tests.
- The independent Python 3.13 environment was prepared and tested during 0.2.0-dev.
- CPU direct/CG/AMG/matrix-free and real NVIDIA CUDA parity tests passed in 2D/3D.
- Unit conversion invariance, independent opposite load cases, matrix reuse, cancellation,
  failed linear convergence, manufacturing projection derivatives and threshold reanalysis tested.
- All 18 English examples pass native SDK document-property and object readback in GH/GHX.
- Engineering C#/external-Python bridge passed with two cases, CUDA and report generation.
- Source installer --prepare-only --cuda successfully built an independent environment from
  the included upstream source and Python wheels on the development machine.
- This is not a second-PC or native Rhino interactive acceptance test.

Existing tests also cover analytical tension, affine strain/shear, rigid modes,
Gauss energy, compliance sensitivities, equilibrium, bending refinement, invalid domains,
volume/Keep budgets, archive dates and persistent-default regressions.

## Full engineering reference run

3D cantilever, 1728 voxels, independent downward and sideways loads, volume target 0.5,
CUDA CG, maximum 40 iterations: optimization terminated as converged in approximately
13.8 seconds. Binary threshold FEM succeeded at 0.5, 0.3 and 0.2. This is same-grid
voxel verification; it does not validate a smoothed or independently remeshed solid.
The 0.5 reference has weighted compliance 0.403456; see reference-validation.json
for case-specific values, units, material and convergence data.

## Performance evidence

Raw timings and peak host RSS: benchmarks.json. Each backend/grid ran in a separate
process. GPU kernel caches may be warm even when the process/context is new.
Single samples do not establish robust speedups or worst-case performance.

At 13,824 voxels (47,775 DOF):
- CPU CG, 4-thread limit: 2.37 s, about 415 MB host RSS.
- CPU matrix-free, 1 thread: 1.34 s, about 87 MB host RSS.
- CPU matrix-free, 8-thread limit: 1.31 s, about 90 MB host RSS.
- CUDA CG: 1.81 s, about 623 MB host RSS (not a GPU VRAM measurement).

Compliance agrees at approximately 0.212912206482; relative equilibrium error <1e-8.
The thread-limit comparison shows little scaling for this case. GPU can reduce
iterative solve time while still losing end-to-end to matrix-free CPU.

## Outstanding qualification

Native Rhino open/resize/select/run/stop/reset/save/reopen/preview/Bake/Undo;
clean second PC; repeated cold/warm benchmarks and VRAM telemetry; large optimized
high-contrast designs; independent-solver comparison; conforming remesh studies;
extended stress-constraint mesh studies; evolving-boundary pressure; verified manufacturing checks.

## Distributed loading increment — 0.2.1-dev

- Exact axial pressure/tension response and consistent edge/face nodal loads in 2D/3D,
  on two resolutions; traction force and moment resultants.
- Gravity resultant = mass * acceleration, reaction balance including fixed-node loads,
  and exact axial body-force nodal displacement reference.
- Finite-difference derivatives with mixed pressure/gravity, filters, Keep and symmetry;
  an analytical positive self-weight derivative at low density.
- Monotone self-weight projected updates with fixed-volume feasibility in reference tests.
- Units invariant between mm/N and m/kN, including 2D thickness and gravity.
- Preserved pressure and attachment interfaces; removed/internal/duplicate faces rejected.
- Direct/CG/matrix-free/real CUDA response parity for the distributed loading path.
- Real C# boundary enumeration, vector mapping and external Python/CUDA bridge passed
  in both dimensions. Out-of-plane 2D acceleration is rejected.
- Loaded curve/surface selection, native preview and Bake/Undo still require Rhino UI tests.

The full default-size reference uses 1,152 Q4 cells and 1,728 HEX8 voxels, pressure
0.1 on the top boundary, steel and gravity, with two independent cases. Baseline,
40 optimization updates and threshold-0.5 binary verification completed in both
cases. Both optimizations ended at iteration_limit, not converged. Reference
optimization times were approximately 5.1 s and 29.3 s with CPU CG; these are single
samples and are not scaling or speedup claims. See distributed-loads-reference.json.

The unit-invariance test triggers an upstream absolute-Jacobian warning for small
physical cells expressed in metres. The cells are regular and the tested responses
agree across units; the unchanged upstream warning is recorded, not suppressed.

Self-weight optimization is experimental. The exact discrete derivative does not
remove low-density SIMP parasitic effects or establish mesh-independent designs.
Use final-shape FEM, further mesh studies and engineering constraints before relying
on a design. No online publication was performed in this increment.

## Design-limit and review increment — 0.3.0-dev

- Finite-difference displacement/stress adjoints in 2D/3D, with/without gravity and
  symmetry, including filter-transpose and explicit relaxed-stress derivatives.
- Exact FEM stress checks and MPa/model-unit conversion, material-allowable validation,
  conservative/stable KS bound, independent case checks regardless of objective weight.
- Constrained feasible designs in both dimensions, impossible-limit diagnostics,
  controlled MMA failure, unchanged check-only optimization and full-material final checks.
- Fixed-budget gravity with multiple cases; real CUDA/direct adjoint parity.
- Saved optimization case fields, opposite-case displacement and compliance accounting.
- New SDK C# tests verify case selection and identity/path guards, matching-baseline
  comparison, exclusion of inappropriate relaxed/physical stress ratios and legend metadata.
- All six engineering graphs contain review controls; two new graphs include enabled
  limits. Eighteen GH/GHX pairs passed SDK serialization/readback, including idle buttons.
- Real C#/external Python bridge with MMA, two cases and NVIDIA CUDA passed in
  both dimensions. The harness confirms the exact assembly path and selected backend.
- Compilation uses the installed Rhino 8 SDK. Legend drawing and native control/preview
  behavior cannot be certified by these SDK tests and still require interactive Rhino.

Default-example numerical reference (CPU CG, 4-thread limit, steel mm/N, independent cases):

| Model | Cells | Optimization | Final threshold FEM | Final mass vs baseline | Max final displacement |
|---|---:|---|---|---|---:|
| 2D, two load positions | 1152 | Feasible; iteration_limit at 80 | Both limits passed | 0.000702575 / 0.0011304 kg | 0.000149051 mm |
| 3D, down and side | 1728 | Feasible; converged at 46 | Both limits passed | 1.126475 / 1.6956 kg | 0.00253229 mm |

The 2D displacement limit is 0.0002 mm; 3D is 0.03 mm; both stress limits are
10 MPa. Final peak von Mises: approximately 4.11712 MPa (2D) and 1.36390 MPa (3D).
Both use 60% density-design volume and threshold 0.4. Extracted binary mass differs
from the density-design mass. Approximate optimization times 38.2 s and 57.8 s are
single reference runs, not performance guarantees. The same-grid verification is
not an independent remesh or code-compliance check.

Reproduce with tool/tools/validate_design_limits.py. Numerical records and history:
design-limits-reference.json. Review C# harness: tool/tools/test_review.py. External
worker/real CUDA/MMA bridge: tool/tools/test_constrained_bridge.py --cuda.

The owner reported the installed 0.2.1-dev 3D workflow working and supplied a Rhino
preview screenshot. This supports that specific run only. It does not establish
complete native Run/Stop/Reset/selection/Bake/Undo acceptance, or acceptance of the
new 0.3 controls. Publication remains deferred.

## Installation verification — 2026-09-19

Version 0.3.0-dev installed with CUDA support after confirming Rhino was closed.
The installed assembly matches the rebuilt assembly; runtime paths point to the
project Python and worker. An isolated C# harness loaded the installed GHA and
completed 2D/3D MMA runs through external Python with real CUDA, two load cases
and saved-case selection. No native viewport/Run/Stop/Reset/Bake/Undo acceptance
is claimed by this bridge check. Previous GHA/settings and verification record
were backed up under tool/build/installation-backups/20260919-142112-838007.

## Installed 0.4 verification — 2026-09-19

Rhino was confirmed closed. The source installer installed 0.4.0-dev with CUDA;
installed and built assembly hashes match, and the configuration points to the
project Python/worker. The exact installed GHA passed the complete C#/Python
baseline/design/extraction/STL/final-TET4/case-selection/comparison probe on CUDA.
Native Rhino controls, viewport and Bake/Undo were not exercised by this probe.
Previous assembly, settings and verification record are backed up in
`tool/build/installation-backups/20260919-161556-356654`.
Current machine records: `tool/build/installation-verification.json` and
`tool/build/readiness-0.4.json`. Open `engineering_final_geometry_3d.gh` in Rhino.

## Parametric shelf bracket — 2026-09-21

See [Shelf bracket validation](SHELF_BRACKET_VALIDATION.md) and [reference data](shelf-bracket-reference.json). The new example adds four alternative mass-normalized cases, nominal screw holes/tool clearances, native dataflow variants and independent force/moment/raster checks. The full suite passed 207 tests, with the existing upstream small-Jacobian warning; 54 affected tests passed again after calibrated defaults.
