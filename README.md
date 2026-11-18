# TopOptLab for Rhino 8 / Grasshopper

<img src="docs/assets/topoptlab-icon.png" alt="TopOptLab icon: a turquoise topology-inspired structure on a navy background" width="120" height="120">

**Experimental alpha releases: Windows `0.4.0-alpha.4`; Mac `0.4.0-alpha.5`.** Native Grasshopper components for
2D/3D linear-elastic FEM and topology optimization using Stefan Hiemer's topoptlab.
Numerical regression tests do not replace application-specific engineering qualification.
The Windows default examples passed native Rhino/Grasshopper calculation acceptance;
see the [full acceptance matrix](docs/YAK_NUMERICAL_ACCEPTANCE.md).

[![Numerical validation](https://github.com/andrea199/TopOptLab-Rhino-Grasshopper/actions/workflows/numerics.yml/badge.svg)](https://github.com/andrea199/TopOptLab-Rhino-Grasshopper/actions/workflows/numerics.yml)

CPU tests and repository integrity run on pushes and pull requests. A green badge
does not validate the Rhino UI, CUDA, or a physical design. Actions results are linked above.

![Actual TopOptLab topology optimization iterations](docs/assets/topoptlab-optimization.gif)

*Real 2D solver iterations: an 80 × 40 grid, 45% volume fraction and 100 SIMP iterations,
sampled every five steps and played back faster than real time. The animation shows
the density field evolving; it does not establish convergence or qualify a physical design.*
See the [animation provenance](docs/assets/README.md) for the source example and numerical evidence.

## Install from Rhino Package Manager (Windows)

**Package:** `topoptlab-rhino` · **Version:** `0.4.0-alpha.4` · **Platform:** Windows x64, Rhino 8 SR37 or later.

1. Install **Python 3.13 (64 bit)** with the **Python Launcher** if it is not already installed. Python itself is not bundled; the first setup needs internet access. Official Python installers are available from [python.org](https://www.python.org/downloads/windows/).
2. In Rhino, run **`_PackageManager`** and select the **Online** tab.
3. Enable **Include pre-releases**, search for **`topoptlab-rhino`**, select **`0.4.0-alpha.4`**, then click **Install**. Restart Rhino.
4. Run **`_Grasshopper`**, place any component from the **TopOptLab** tab, right-click it and choose **TopOptLab Python setup folder**.
5. In that folder, double-click **`SETUP-PYTHON.cmd`** and wait for the CPU runtime validation to finish. This prepares an isolated persistent Python environment; it does not compile the plugin. Restart Rhino after setup.
6. Open **`source/docs/manual/index.html`** from the same package folder to read the complete offline English manual, Component Guide and lessons.
7. Open **`source/tool/examples/engineering_workflow_2d.gh`**. Run **BASELINE FEM → OPTIMIZATION → FINAL VERIFICATION**, waiting for each stage to finish. Use the CPU defaults first.

The package folder is normally `%APPDATA%\McNeel\Rhinoceros\packages\8.0\topoptlab-rhino\0.4.0-alpha.4`.
The numerical environment is stored separately under `%LOCALAPPDATA%\TopOptLab\Rhino8\runtimes` and survives package upgrades. Loading a Grasshopper component does not start downloads or calculations.

**Upgrading from a manual installation:** save your work and close Rhino. Back up the old TopOptLab plugin folder outside Grasshopper's library/search paths before installing the Yak package. Both copies share component IDs and must not be loaded together. See [setup, migration and acceptance](docs/YAK_WINDOWS.md).

If the package does not appear, check **Include pre-releases**, your Windows x64 platform and Rhino service release. The [official Package Manager help](https://docs.mcneel.com/rhino/8/help/en-us/commands/packagemanager.htm) describes the installation dialog.

## Course manual and platform support

The Yak package contains the complete English HTML manual, HTML lesson slides and all example/exercise files under `source/`. Keep that folder intact so its relative links and images work offline. PowerPoint files are not included.

## Install from Rhino Package Manager (Mac — experimental)

> **EXPERIMENTAL MAC ALPHA — NOT YET TESTED INSIDE RHINO OR GRASSHOPPER FOR MAC.**
> Native CPU-worker tests pass on Apple Silicon and Intel; this does not validate GHA loading, menus/icons, preview, Run/Stop/Reset, save/reopen or Bake/Undo in Rhino. The Windows native acceptance results do not qualify the Mac application integration.

**Package:** `topoptlab-rhino` · **Mac version:** `0.4.0-alpha.5` · **Requirements:** macOS 15+, Rhino 8 SR37+, native 64-bit Python 3.13. One Mac package serves both Apple Silicon (arm64) and Intel (x86_64). Rosetta Python is rejected.

1. Save your work. If an older manual TopOptLab GHA is installed, close Rhino and back up that plugin folder outside Grasshopper search paths before installing Yak.
2. Run **`_PackageManager`** in Rhino → **Online** → enable **Include pre-releases** → search **`topoptlab-rhino`** → select **`0.4.0-alpha.5`** → **Install**. Restart Rhino.
3. In Grasshopper, right-click a TopOptLab component → **TopOptLab Python setup folder**. Run **`SETUP-PYTHON.command`** to prepare the native CPU runtime. Python itself must already be installed; first setup needs internet access.
4. Restart Rhino. The package includes the English manual at **`source/docs/manual/index.html`** and examples under **`source/tool/examples/`**.

If the untested component/menu integration does not load, the package folder is normally `~/Library/Application Support/McNeel/Rhinoceros/packages/8.0/topoptlab-rhino/0.4.0-alpha.5`. Run its setup launcher from Terminal with `bash "/full/path/to/SETUP-PYTHON.command"`. Setting up Python does not prove the plugin works inside Rhino.

See [Mac installation and untested application checks](docs/YAK_MACOS.md) and [the exact test evidence](docs/YAK_MACOS_EVIDENCE.json). This Mac release is for experimental use; native Rhino/Grasshopper qualification is still pending. CUDA is not included on Mac.

The historical 26 October classroom ZIP release remains a draft and is not the current public installation route. There is no verified installer for Linux, Windows ARM or macOS below 15. The Windows Package Manager release remains `0.4.0-alpha.4` and is unchanged.

## Start here

| Goal | Guide |
| --- | --- |
| Install on Windows | [Rhino Package Manager](#install-from-rhino-package-manager-windows) |
| Run your first FEM and optimization | [Quick start](docs/QUICKSTART.md) |
| Choose a ready-made model | [20-example gallery](docs/EXAMPLES.md) |
| Learn or teach TopOptLab in English | [Unified manual: components and lessons](docs/manual/index.html) |
| Find technical documentation | [Documentation index](docs/README.md) |
| Build, test or contribute | [Contributing](CONTRIBUTING.md) |

The repository includes the integration source, the complete upstream snapshot,
editable examples, icons, tests and a roof-rib teaching kit. The Windows source
installer creates the local Python environment and compiles the plugin. The
published English teaching material includes the HTML manual, 56 HTML lesson
slides, illustrated installation, component explanations and exercise files.
PowerPoint files are maintained separately by the instructor and are not included
in the repository or its release packages.

![Shelf bracket development preview](docs/shelf-bracket-preview.png)

*Shelf-bracket development preview. See the [current numerical acceptance](docs/YAK_NUMERICAL_ACCEPTANCE.md) for tested defaults, results and limitations.*

## Teaching manual

The canonical English teaching manual is in [`docs/manual/`](docs/manual/index.html).
Open its `index.html` locally to browse the Component Guide and the sequential
Learnings section from one navigation. All eight lessons are available, with 56
HTML lesson slides, teacher guides, student worksheets and linked exercise files.
The manual includes an [illustrated installation guide](docs/manual/getting-started/installation/index.html),
a [component and port introduction](docs/manual/learnings/component-primer/index.html),
and [wiring walkthroughs](docs/manual/learnings/connections/index.html).
PowerPoint presentations are distributed separately by the instructor; use the
HTML lesson slides and illustrated setup guide included here.
See [authoring instructions](docs/manual/AUTHORING.md) before adding new material.
The [documentation hosting guide](docs/DOCUMENTATION_HOSTING.md) explains the
Read the Docs build; it serves this same manual without maintaining another site.
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
The CPU classroom default uses CPU AMG, 5 mm cells, threshold 0.35 and 60 optimization steps over all four cases. Baseline, optimization, voxel verification, CAD extraction and conforming final FEM passed native acceptance. The former 2.5 mm refinement remains unqualified and has a documented automatic-meshing limitation. See [current acceptance](docs/YAK_NUMERICAL_ACCEPTANCE.md) and [resolution scope](docs/RESOLUTION_VALIDATION.md).

## Implemented

These are the **integration's exposed workflows**, not an upstream feature
catalogue. See [TopOptLab upstream](https://github.com/stefanhiemer/topoptlab)
and the [bundled snapshot README](vendor/topoptlab/README.md) for upstream
documentation, and [third-party notices](THIRD_PARTY_NOTICES.md)
for snapshot provenance. New upstream features are not automatically available here.

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

## Install from source on Windows

For a developer build or an optional CUDA environment, use the source route below.
The Package Manager route above installs the precompiled Windows plugin.

- Prerequisites: **Rhino 8 and Python 3.13 (64 bit)**, plus internet access.
- Download/clone the complete repository into a permanent folder.
- Save and close Rhino, then run `INSTALL.cmd`.
- Optional NVIDIA CUDA: run `INSTALL.cmd --cuda`; CPU is the default.
- See [Installation](docs/INSTALLATION.md) for nonstandard paths, preparation,
  backups, updates and troubleshooting.

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

- Linear isotropic small-strain elasticity only. Stress screening is not code compliance.
- Default 3D Domain limit: 8,000 cells. The shelf example uses a 250,000-cell
  user limit and 5 mm default cells (7,500 bounding cells); finer grids are advanced studies.
- Memory admission and absolute guards (2,000,000 bounding cells; 2,048 per axis)
  are not tested-capacity or accuracy claims. See [resolution evidence](docs/RESOLUTION_VALIDATION.md).
- Stage 2 checks the original voxel grid; Stages 3/4 extract a smoothed surface
  and remesh with TET4. Keep/envelope regions remain authoritative.
- The shelf CAD contract restores nominal plates/clearances and rechecks load regions.
  Final supports require complete boundary-face patches; removed load interfaces are rejected.
- TET4 needs bending/stress refinement studies. No evolving-surface pressure,
  buckling, fatigue, plasticity or contact.
- Self-weight optimization uses a fixed material budget and projected-gradient updates
  (or MMA when design limits are enforced). Stress-constrained and low-density
  behavior remains experimental and must be checked on the final shape.
- Process notes and feature-size erosion are diagnostic; only symmetry,
  extrusion and Keep are enforced manufacturing-related controls today.

## Development and attribution

- Run `.venv/Scripts/python -m pytest` for integration regressions.
- Run `.venv/Scripts/python tool/tools/benchmark_engineering.py` for full-solid FEM measurements.
- Run `.venv/Scripts/python tool/tools/benchmark_final_workflows.py --cuda` for short
  constrained workloads; add `--surface PATH/TO/surface/result.json` for final FEM.
- See [0.4 performance evidence](docs/PERFORMANCE_04.md) for scope and measured data.
- Native SDK/bridge acceptance requires Rhino; CPU and archive regressions run in CI.
- See [LICENSE](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md).
- The transferred upstream source is included unchanged with a SHA-256 manifest.
  No upstream Git revision is claimed.
- See [Contributing](CONTRIBUTING.md) for upstream updates and release gates.

<!-- FUNDING ACKNOWLEDGEMENT START -->
## Funding acknowledgements

[![European Innovation Council. Funded by the European Union.](docs/manual/assets/funding/eic-funded-by-eu.png)](https://cordis.europa.eu/project/id/101161052)

The authors acknowledge support from the ARCHIBIOFOAM project, which received funding from the European Union’s Horizon Europe research and innovation programme under grant agreement No 101161052.

Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or European Innovation Council and SMEs Executive Agency (EISMEA). Neither the European Union nor the granting authority can be held responsible for them.

[ARCHIBIOFOAM — project and grant information](https://cordis.europa.eu/project/id/101161052).
<!-- FUNDING ACKNOWLEDGEMENT END -->
