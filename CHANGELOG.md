# Resolution increment — 2026-09-21 (development)

- Replaced fixed 3D backend cell caps with conservative host/GPU memory admission and
  separate absolute input guards. Added Domain Resources, optional RAM budget and
  physical filter length. The 2D filter also consumes the physical length explicitly.
- Added cached nodal block assembly, rigid-body AMG candidates, FFT density filtering
  with exact adjoint, linear-storage group projections and compact stress NPZ output.
- Reduced Rhino preview to boundary faces and cached unchanged worker snapshots.
- Updated the shelf example to 2.5 mm cells / 60,000 bounding cells, 250,000 user limit,
  9 mm physical filter, explicit CUDA backend (CPU AMG alternative), and CAD interface inputs.
- Added shelf-specific nominal plate/circular clearance reconstruction, source/spec checks
  and physical load patches for final FEM. Final-mesh quality guards remain enforced.
- Recorded repeated numerical/performance evidence and native component/archive checks.
  See docs/RESOLUTION_VALIDATION.md for exact completed coverage and outstanding checks.
  No publication or general engineering qualification is implied.

# 0.4.0-dev — final geometry, conforming FEM and print review

- Added Final Geometry 3D, Final FEM 3D, Final Results 3D and Print Review, with dedicated
  icons and 3D badges on the geometric/FEM components. Added one complete English
  five-stage example; 19 GH/GHX pairs total. Review preserves original output indices.
- Extracted continuous triangle surfaces from density, restored exact protected voxel
  regions, clipped to the original design envelope, checked closure/components and
  supported validated user-edited meshes. Added STL export with explicit unit guidance.
- Added cancellable isolated Gmsh remeshing, first-order tetrahedral FEM, preserved
  boundary-face supports, barycentric point loads, clipped pressure/traction integration
  and actual-volume gravity. Rejected missing interfaces instead of moving them silently.
- Added per-case full-material limits, baseline comparison and up to three mesh levels.
  Recorded geometry hashes, transfer errors, quality, force/moment/work checks and reports.
- Added 3D-print build direction, overhang flags and sampled normal thickness checks;
  these are geometric reviews, not optimizer-enforced manufacturing guarantees.
- Added independent scikit-fem TET assembly/solution comparison, backend/unit/cancellation
  tests, C#/Python final-workflow probe and constrained CPU/CUDA memory/time benchmarks.
- Native Rhino UI and broader engineering qualification remain explicit acceptance steps.
  Publication remains deferred.

# 0.3.0-dev — design limits and result review

- Added Design Limits, Case Result, Compare Results and Review Controls components,
  with dedicated code-native icons. All interface text and examples are in English.
- Added optional displacement/stress checks for every independent case and MMA
  constraints with exact density-filter, stiffness, self-weight and stress adjoints.
- Marked optimization stress as a sqrt-density relaxed surrogate. Final verification
  checks full-material stress on the retained voxel grid. No certification implied.
- Separated feasibility, convergence, iteration limit and numerical optimizer failure.
  Preserve the best valid diagnostic result; never convert a failed solve into convergence.
- Added saved optimization case responses, viewport legends with units, fixed color
  scales, exclusive stage previews, and matched-baseline mass/displacement comparisons.
- Added two design-limit examples; updated all six engineering documents with review
  controls and optional limits. The complete gallery now contains 18 .gh/.ghx pairs.
- Numerical and SDK checks are recorded in docs/VALIDATION.md. New native Rhino
  viewport/control acceptance remains to be completed. Publication remains deferred.

# 0.2.1-dev — distributed loads and self-weight

- Added Surface Load (2D/3D) and Gravity components, with code-native icons.
- Integrated pressure/traction on grid facets and consistent mass-based nodal loads.
- Added exact self-weight load sensitivities, projected-gradient updates, fixed-volume
  budget and explicit line-search failure status; bounded warm-start memory.
- Preserved surface-load interfaces and added optional support/point-load Keep.
- Added two parametric three-stage examples, force/reaction summaries and loading guide.
- Publication remains deferred. Native Rhino UI acceptance is still required.

# Changelog

## 0.2.0-dev

English parametric gallery; sourced materials/units; independent load cases;
verified CPU/CUDA backends; convergence; symmetry/extrusion; same-grid threshold
FEM; reports; source installer and local repository. Native UI acceptance pending.

## Earlier prototype

2D/3D FEM/SIMP, preview, Bake/Undo and numerical tests. Fixed missing archive dates
and duplicated persistent defaults in the generated examples.

## Shelf bracket example — 2026-09-21

- Add parametric 200–300 mm wall shelf bracket, circular holes/tool clearances and protected plates.
- Add four mass-normalized surface-load cases, shelf share and self-weight; rigid wall pads.
- Add five-stage GH/GHX workflow, nominal CAD interfaces and Italian quick-start.
- Add native RhinoCore dataflow checks and independent raster/force/moment regressions.
- Printed-material qualification, anchorage and exact-CAD reconstruction remain open.
