# Shelf bracket validation — 2026-09-21

## Delivered default workflow

Actual 250 × 150 × 25 mm model, 7,328 active 5 mm cells, four independent cases; 4 kg payload per bracket, assumed 0.5 kg shelf share, ABS reference, self-weight. CPU direct, 35% density-design volume, threshold 0.35, 60 MMA updates and 1 mm displacement target.

| Stage | Mass, kg | Maximum displacement over four cases, mm | Termination |
|---|---:|---:|---|
| Full-solid baseline | 0.952640 | 0.028922 | fem_completed |
| Density design | 0.333424 | 0.283098 | iteration_limit |
| Thresholded voxel shape | 0.314730 | 0.223027 | voxel_reanalysis_completed |
| Conforming TET4 FEM | 0.254450 | 0.233279 | conforming_fem_completed |

The optimiser reached its iteration limit; it is not labelled converged. The density-design and binary/surface masses differ. Stress is not constrained in this example; printed-material allowable is unknown.

## Numerical and native checks

- 207 regression tests passed (one existing upstream small-Jacobian warning). After calibration, all 54 affected geometry/archive/load tests passed again.
- Native RhinoCore/Grasshopper dataflow passed for default, resized, translated and finer-grid variants. Generated fixtures match analytical cylinders, attachment plates and force/moment integration.
- Missing/invalid units, zero payload, negative shelf share, inconsistent domain/specification, invalid patches, invalid geometry and an unresolved hole are rejected.
- GH and GHX passed native SDK readback: document properties and all 116 objects.
- Forces remain mass-normalized across sizes and grids. Opposite eccentric cases are evaluated independently.
- Baseline CPU-CG, CUDA-CG and CPU-direct displacements agreed at the shown precision. These runs are not controlled performance benchmarks.

## Findings that changed the delivered example

- Threshold 0.40 on the 60-step density design produced 0.18915 kg and approximately 37.45 mm maximum displacement, exceeding the chosen 1 mm limit. It is not the delivered default.
- Threshold 0.30 added disconnected voxel material and was rejected. Lower thresholds are not automatically better.
- Threshold 0.35 passed voxel reanalysis and is the delivered value; changing it requires another verification.
- CUDA-CG did not satisfy the strict residual criterion on the discarded 0.40 final surface. It was not silently accepted. CPU direct is selected explicitly for the delivered modest grid.
- A CPU-CG optimisation trial was intentionally cancelled; no converged result is claimed for that trial.

## Remaining acceptance and qualification

- Final FEM mesh quality: **no_poor_elements**. Accuracy study: **not_studied**. One mesh does not establish convergence.
- The extracted surface retains original protected voxels, but its holes remain approximations of nominal CAD geometry.
- Test native Rhino preview, selection, Run/Stop/Reset, save/reopen and Bake/Undo interactively. SDK/headless checks do not exercise these UI operations.
- Rigid wall pads do not validate bolts, wall anchors, contact, printed layer strength or creep. This is not a certified 4 kg load rating.

Machine-readable evidence: **shelf-bracket-reference.json**. Full job files remain in the local run folder. Reproduce with tool/tools/validate_shelf_bracket.py --final-fem.
