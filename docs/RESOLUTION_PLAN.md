# Resolution and CAD interface increment

ECC workflow: orch-change-feature / orch-pipeline and benchmark-optimization-loop.
User authorization: implement the proposed larger-grid, performance and CAD-interface plan. No publication or commit requested.

## Acceptance tasks

1. Replace 8k/32k backend admission limits by conservative host/GPU memory estimates, retaining explicit absolute input guards (2M bounding cells, 2048/axis). Show selected limit and resource explanations in Grasshopper.
2. Bound matrix/filter/projection memory. Preserve equations, cone-filter normalization and exact transpose gradients. Preserve a physical filter radius across mesh refinements.
3. Keep CPU/CUDA selection explicit, unchanged residual/force/moment/energy checks. Record same-input repeated assembly and solver microbenchmarks, then actual shelf jobs at 60k/122k bounding cells.
4. Restore the shelf nominal attachment plates and circular screw/tool clearances with a declared independent chord tolerance. Validate geometry/specification provenance; transfer the four physical load regions with unchanged total force and explicit moment differences from the raster model.
5. Verify final conforming FEM on the CAD-restored surface, correct closure/connectivity/clearances, usable preview and sample archives. Do not equate one solved mesh or an iteration limit with convergence.
6. Run regression/native tests, prepare examples and English docs plus Italian quickstart; install only when Rhino is closed, with rollback.

## Initial evidence

- Baseline 207 tests passed in 25.18 seconds; one pre-existing upstream small-Jacobian warning.
- Initial test invocation failed only because Windows temporary pytest directory was inaccessible; all subsequent tests use fresh project-local basetemp folders.
- Baseline sources and assembly: tool/build/resolution-baseline-20260921-174549.
- Hardware: ~64 GiB RAM, RTX 5070 Laptop 8 GiB. Available memory is checked at each job, not assumed from this snapshot.

## Bounded performance search

Two solver hypotheses: cached block assembly; rigid-body AMG candidate modes. Same-input baseline/winner, two repeats. Larger jobs: 2.5 mm full FEM and 60-update constrained optimization; 2 mm full FEM and constrained workload, followed by actual geometry/FEM where completed. Measurements report what finished without extrapolating a universal supported size or speedup.

## Numerical boundaries

Voxel geometry remains center sampled. CAD restoration is explicitly shelf-specific; arbitrary imported CAD still uses the generic extraction path. STL is a triangulation with a tolerance, not exact NURBS. Final FEM and printing/anchors/material qualification remain distinct checks.

## Delivered scope and open acceptance

Items 1–4 are implemented and tested. Actual shelf FEM completed at 60k/122k bounding
cells; the 60k constrained run completed 60 updates (iteration limit), and 122k completed
two constrained updates. The latter timing is invalidated by confirmed host standby.
Item 5 passes on the earlier 5 mm source shape; the new 2.5 mm candidate extracts with
correct CAD interfaces, but automatic conforming tetrahedral FEM remains blocked by
parameterization/meshing. This is recorded explicitly, not marked complete. Voxel
reanalysis at threshold 0.32 passes all four displacement checks. Native interactive
Rhino acceptance and final fine-surface FEM/refinement remain open after installation.
