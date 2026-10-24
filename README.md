# TopOptLab for Rhino 8 / Grasshopper

**0.4.0-dev — final geometry and engineering workflow preview.** Native Grasshopper components for
2D/3D linear-elastic FEM and topology optimization using Stefan Hiemer's topoptlab.
Numerical regression tests do not replace application-specific engineering qualification.
The newest UI still requires interactive Rhino acceptance.

## Start here

| Goal | Guide |
| --- | --- |
| Install on a new Windows PC | [Installation](docs/INSTALLATION.md) |
| Run your first FEM and optimization | [Quick start](docs/QUICKSTART.md) |
| Choose a ready-made model | [20-example gallery](docs/EXAMPLES.md) |
| Learn or teach TopOptLab in English | [Unified manual: components and lessons](docs/manual/index.html) |
| Find technical documentation | [Documentation index](docs/README.md) |
| Build, test or contribute | [Contributing](CONTRIBUTING.md) |

The repository includes the integration source, the complete upstream snapshot,
editable examples, icons, tests and a roof-rib teaching kit. Installation creates
the local Python environment and compiles the plugin. The original 40-slide
course deck is in Italian, with English instructor and student companion guides.

![Computed shelf bracket study](docs/shelf-bracket-fine-preview.png)

*Computed fine-grid shelf study; final conforming FEM of this candidate remains
incomplete. See the validation scope below.*

## Teaching manual

The canonical English teaching manual is in [`docs/manual/`](docs/manual/index.html).
Open its `index.html` locally to browse the Component Guide and the sequential
Learnings section from one navigation. Lesson01 includes its slides, teacher
notes, student sheet and starter files; later blocks are clearly marked Planned.
See [authoring instructions](docs/manual/AUTHORING.md) before adding new material.
The original Italian roof-rib course remains in `teaching/roof_2d/` as reference
material. New English lessons are developed inside the unified manual.

## Workflow

Geometry → Material and Units → Supports → Load Cases → Baseline FEM → Optimization
→ Voxel Verification → Final Surface → Conforming Final FEM → Engineering Report.

Start with tool/examples/engineering_workflow_2d.gh or engineering_workflow_3d.gh.
Twenty English example documents are included. Run the three stages in order.
Use each stage's Report output to locate report.html.
For pressure and self-weight, start with engineering_distributed_loads_2d.gh or
engineering_distributed_loads_3d.gh and read [distributed loads](docs/DISTRIBUTED_LOADS.md).

For design limits and the new review controls, use engineering_design_limits_2d.gh or
engineering_design_limits_3d.gh and read [design limits](docs/DESIGN_LIMITS.md).
Both are teaching examples with explicit limits, not a material design code.

For a complete 3D workflow through extracted surface and conforming FEM, use
**tool/examples/engineering_final_geometry_3d.gh** and read [Final Geometry](docs/FINAL_GEOMETRY.md)
and [3D Printing Review](docs/PRINT_REVIEW.md). Stage 3 shows the surface and print
flags; Stage 4 shows the new tetrahedral FEM response.

For a real-size 250 mm ABS-reference shelf bracket with four independent 4 kg load cases,
open **tool/examples/engineering_shelf_bracket_3d.gh**. Parametric holes, protected plates
and tool-clearance voids are included. See [Shelf Bracket](docs/SHELF_BRACKET.md).
The updated 2.5 mm example passes voxel reanalysis at threshold 0.32; automatic
tetrahedral meshing of its final CAD surface remains incomplete. The previous 5 mm
shape completed the separate CAD/FEM workflow. See the exact [validation scope](docs/RESOLUTION_VALIDATION.md).

## Implemented

- Q4 plane-stress 2D and HEX8 solid 3D FEM, stress/displacement/reaction results.
- SIMP compliance minimization with volume budget and preserved material regions.
- Optional all-case displacement/stress constraints using MMA and checked adjoint derivatives.
- Explicit relaxed design stress, numerical feasibility and distinct optimizer-failure status.
- Review controls: one visible stage, saved case selection, viewport legend and baseline comparison.
- Integrated fixed-boundary pressure/traction loads and density-dependent self-weight in 2D/3D.
- Optional preservation of support/point-load attachments; surface-load interfaces always preserved.
- Independent named load cases with positive objective weights; forces within a case act together.
- Explicit mm/m and N/kN units; documented structural-steel and ABS reference presets.
- CPU direct, CPU CG, CPU AMG, CPU matrix-free, and optional CUDA CG backends.
- Shared matrix/preconditioner across load cases and warm starts between iterations.
- Cached block assembly, elasticity AMG modes, linear-storage symmetry/extrusion projection,
  FFT cone filtering, explicit physical filter radius and 3D memory admission estimates.
- Boundary-only grid preview and cached unchanged result snapshots.
- Shelf-specific nominal CAD plate/clearance reconstruction with a recorded chord tolerance
  and physical load-patch transfer; see [CAD interfaces](docs/CAD_INTERFACES.md).
- Objective/design convergence window, distinct iteration-limit status and cancellation.
- Symmetry and 3D extrusion density constraints with derivative checks.
- Binary voxel threshold reanalysis, connected-domain and selected-node validation.
- Continuous 3D isosurface extraction, exact voxel Keep preservation, closure/connectivity
  checks, edited-mesh validation and STL export.
- Gmsh conforming TET4 remesh and full-material FEM, with explicit support/load transfer,
  force/moment/energy checks, independent case responses and one-to-three-level mesh studies.
- 3D printing geometry review: build direction, overhangs and sampled normal wall thickness.
  These print checks flag geometry; they are not optimization-enforced printability constraints.
- Saved project JSON, per-case FEM/optimization JSON, history, mass and HTML report.
- Parametric dimensions and XYZ position in the examples.

## Install on Windows

Prerequisites: **Rhino 8 and Python 3.13 (64 bit)**. Save and close Rhino, then run
INSTALL.cmd. It creates a project .venv, installs pinned top-level dependencies
and the included upstream source, compiles the plugin and configures Grasshopper.
The source installer uses internet access for Python wheels. Keep this project folder
in place after installation; rerun setup if it moves. A standalone EXE/bootstrapper
with uninstall support is a later release milestone.

For NVIDIA CUDA support, run INSTALL.cmd --cuda from a terminal. CUDA is optional;
CPU installation does not download NVIDIA runtime packages. A compatible NVIDIA driver
is required. No driver is installed or changed by this project.

Prepare dependencies and compile while Rhino remains open with:
py -3.13 setup.py --prepare-only --cuda
This does not replace the plugin loaded by Rhino. Installation saves rollback files
under tool/build/installation-backups.

## Validation and performance

See [validation](docs/VALIDATION.md), [raw benchmarks](docs/benchmarks.json),
[reference run](docs/reference-validation.json), [user guide](docs/USER_GUIDE.md),
and the [development plan](docs/DEVELOPMENT_PLAN.md).

On the development PC (Core Ultra 9 285H, 64 GB RAM, RTX 5070 Laptop 8 GB), a
13,824-voxel FEM benchmark took approximately 1.31 s with CPU matrix-free and 1.81 s
with CUDA, including model/backend setup. These are single-run timings, not promised
speedups. GPU context startup matters. CPU thread settings limit BLAS threads;
they do not mean every solver stage is parallel.

## Scope and limits

Linear isotropic small-strain elasticity only. Stress screening is not code compliance.
The generic 3D Domain defaults to an 8,000-cell user limit for compatibility; the updated
shelf example uses a 250,000-cell user limit and 2.5 mm cells (60,000 bounding cells).
Host/GPU memory estimates govern admission, with separate absolute input guards of
2,000,000 bounding cells and 2,048 cells per axis. These guards are not tested-capacity
or accuracy claims. See [resolution evidence](docs/RESOLUTION_VALIDATION.md) for completed trials.

The Stage 2 threshold check uses the original voxel grid. The separate Stage 3/4
workflow extracts a smoothed triangle surface and remeshes it with TET4. Original
voxel Keep/envelope regions remain authoritative in the generic path; the shelf CAD
contract explicitly restores nominal plates/clearances and rechecks physical load regions. Final supports currently require
complete boundary-face patches; removed load interfaces are rejected. TET4 requires
bending/stress refinement studies. No evolving-surface pressure, buckling, fatigue,
plasticity or contact.
Self-weight optimization uses a fixed material budget and projected-gradient updates
(or MMA when design limits are enforced);
stress-constrained and low-density behavior remains experimental and must be checked on the final shape. Process notes and feature-size erosion are diagnostic; only symmetry,
extrusion and Keep are enforced manufacturing-related controls today.

## Development and attribution

Run .venv/Scripts/python -m pytest tool/tests -q for regressions.
Run .venv/Scripts/python tool/tools/benchmark_engineering.py for full-solid FEM measurements.
Run .venv/Scripts/python tool/tools/benchmark_final_workflows.py --cuda for short
constrained workloads; add --surface PATH/TO/surface/result.json for final FEM.
See [0.4 performance evidence](docs/PERFORMANCE_04.md) for scope and measured data.
SDK/archive and bridge tests require Rhino. See LICENSE and THIRD_PARTY_NOTICES.md.
The transferred upstream source is included unchanged with a SHA-256 manifest.
No upstream Git revision is claimed.
