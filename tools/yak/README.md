# TopOptLab for Rhino 8 / Grasshopper — Windows Yak alpha

Requires Rhino 8 SR37 or later, Python 3.13 x64 with the Python Launcher,
and internet access for the first CPU setup. Python itself is not installed by
this package. No downloads occur merely by loading the GHA.

## Installation

1. Save work and close Rhino before changing an existing installation.
2. If a manual TopOptLab GHA is already in Grasshopper/Libraries, back up its
   entire folder outside Grasshopper search paths before installing Yak. Do not
   load both copies of this plugin; they share component GUIDs.
3. In Rhino run `_PackageManager`, choose Online, enable **Include pre-releases**, search **topoptlab-rhino**, select **0.4.0-alpha.4** and click **Install**. Restart Rhino.
4. Run SETUP-PYTHON.cmd from the package folder. In Grasshopper, right-click a
   TopOptLab component and choose **TopOptLab Python setup folder** to find it.
5. Restart Rhino. Open source/tool/examples/engineering_workflow_2d.gh and run
   baseline, optimisation and verification in sequence using a CPU backend.

The runtime is in `%LOCALAPPDATA%/TopOptLab/Rhino8/runtimes/` and survives Yak
package upgrades/uninstall. Settings are stored separately in
`%LOCALAPPDATA%/TopOptLab/Rhino8/settings.json`. The source and licence accompany
each persistent runtime. Re-running setup reuses a validated identical runtime;
changed worker/dependency inputs produce a separate runtime. Old runtimes are
kept for rollback rather than silently deleted. A setup.lock prevents concurrent
setup. After an interrupted setup, confirm no setup is running before removing
a stale lock and retrying.

Manual: source/docs/manual/index.html. Existing manual installs retain their
local-settings.json priority; the persistent Yak settings are a fallback.
Uninstall via Yak removes the plugin, not shared runtime data or job reports.

This is an experimental alpha with small-strain linear elasticity. A numerical
result is not engineering certification. Mac is outside this Windows package.

Original TopOptLab: Stefan Hiemer. Integration: Andrea Detry. GPL licence and
upstream provenance: source/LICENSE and source/THIRD_PARTY_NOTICES.md.
ARCHIBIOFOAM funding acknowledgement and EU disclaimer: source/README.md.

## Numerical examples

The shelf-bracket classroom example starts with CPU AMG, 5 mm voxels, threshold 0.35 and 60 iterations over all four load cases. Its former 2.5 mm CUDA default was unsuitable for the CPU-only Yak setup. Finer grids remain optional advanced studies and are not qualified by the default-example acceptance; the historical fine surface has a documented automatic-meshing limitation. No GPU fallback or numerical tolerance relaxation is introduced.

Run tools/yak/native_calculations.py inside a separate Rhino 8 session to exercise every canonical example and lesson. Progress and stage results are written under tool/build/yak-calculations. Student geometry references and deliberate starter wiring gaps are completed only in memory.
