# Native numerical example acceptance

Windows Yak alpha.4, Rhino 8 Grasshopper, 17 November 2026.

**PASS: 32 graphs (21 canonical examples and 11 lesson files), 55 numerical stages across 27 graphs, plus 5 geometry/condition exercises.**

All saved default numerical stages were run through native Grasshopper components and their external Python workers. Each canonical GH graph is executed once; its duplicate GHX/manual copies are covered by archive and wiring checks. Lesson reference selections and intentional student wiring gaps were completed only in memory.

| Example | Stages | Result |
|---|---:|---|
| tool/examples/engineering_design_limits_2d.gh | 3 | PASS |
| tool/examples/engineering_design_limits_3d.gh | 3 | PASS |
| tool/examples/engineering_distributed_loads_2d.gh | 3 | PASS |
| tool/examples/engineering_distributed_loads_3d.gh | 3 | PASS |
| tool/examples/engineering_final_geometry_3d.gh | 5 | PASS |
| tool/examples/engineering_shelf_bracket_3d.gh | 5 | PASS |
| tool/examples/engineering_workflow_2d.gh | 3 | PASS |
| tool/examples/engineering_workflow_3d.gh | 3 | PASS |
| tool/examples/fem_cantilever.gh | 1 | PASS |
| tool/examples/fem_cantilever_3d.gh | 1 | PASS |
| tool/examples/fem_cantilever_two_loads.gh | 1 | PASS |
| tool/examples/fem_plate_two_holes.gh | 1 | PASS |
| tool/examples/fem_plate_with_hole.gh | 1 | PASS |
| tool/examples/fem_simply_supported_beam.gh | 1 | PASS |
| tool/examples/opt_cantilever.gh | 1 | PASS |
| tool/examples/opt_cantilever_3d.gh | 1 | PASS |
| tool/examples/opt_cantilever_two_loads.gh | 1 | PASS |
| tool/examples/opt_plate_two_holes.gh | 1 | PASS |
| tool/examples/opt_simply_supported_beam.gh | 1 | PASS |
| tool/examples/plate_with_hole.gh | 1 | PASS |
| teaching/roof_2d/output/case/roof_2d_classroom.gh | 3 | PASS |
| docs/manual/learnings/01-understand-the-problem/files/lesson01_starter.gh | 0 | PASS |
| docs/manual/learnings/02-build-the-domain/files/lesson02_solution.gh | 0 | PASS |
| docs/manual/learnings/02-build-the-domain/files/lesson02_starter.gh | 0 | PASS |
| docs/manual/learnings/03-supports-and-loads/files/lesson03_solution.gh | 0 | PASS |
| docs/manual/learnings/03-supports-and-loads/files/lesson03_starter.gh | 0 | PASS |
| docs/manual/learnings/04-first-fem-analysis/files/lesson04_solution.gh | 1 | PASS |
| docs/manual/learnings/04-first-fem-analysis/files/lesson04_starter.gh | 1 | PASS |
| docs/manual/learnings/05-optimise-the-structure/files/lesson05_solution.gh | 2 | PASS |
| docs/manual/learnings/05-optimise-the-structure/files/lesson05_starter.gh | 2 | PASS |
| docs/manual/learnings/06-extract-and-check/files/lesson06_solution.gh | 3 | PASS |
| docs/manual/learnings/06-extract-and-check/files/lesson06_starter.gh | 3 | PASS |

Checks include finite results, density and volume bounds, nonnegative response metrics, residual/equilibrium below 1e-5 and applied-force/reaction balance for every engineering load case. Constraint-optimizer numerical failures are rejected. Worst observed residual/equilibrium: 2.18e-08.

## Shelf-bracket correction

The former saved default selected CUDA although Yak installs a CPU runtime. The CPU classroom default is now AMG at 5 mm, threshold .35, with the complete 60-iteration budget and all four original load cases. Baseline, optimization, voxel verification, CAD surface extraction and conforming final FEM must all pass. Geometry dimensions, physical filter radius and nominal CAD interfaces are unchanged. The 2.5 mm advanced refinement is not qualified by this acceptance; its CPU optimization trial was stopped and its historical automatic-meshing limitation remains documented.

## Limits

These are API-driven calculations inside an actual Rhino GUI instance. They do not qualify every slider combination, Macs, a second Windows PC, printed material or anchorage. Completion, convergence, design-limit feasibility and mesh accuracy are recorded separately in the machine-readable report. One tetrahedral mesh can report not_studied and poor_elements_present advisory flags; it does not establish a safe load rating. No solver tolerance, geometry admission, force-transfer or element-quality rejection check was relaxed.

Machine-readable evidence: [YAK_NUMERICAL_ACCEPTANCE.json](YAK_NUMERICAL_ACCEPTANCE.json).
