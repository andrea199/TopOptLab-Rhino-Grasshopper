# Windows Yak alpha acceptance

Candidate: `topoptlab-rhino-0.4.0-alpha.3-rh8_37-win.yak`.
Minimum target: Rhino 8 SR37, Windows x64. Python 3.13 x64 must already be
installed; the first CPU setup downloads dependencies. This candidate has not
been published to the public Yak server.

## Changes

- Correct package name and prerelease version; Yak build has no metadata warnings.
- A persistent CPU runtime under LocalAppData, outside versioned Yak folders.
- Atomic settings updates, a setup lock, runtime identity checks and preserved
  previous settings/runtime versions for rollback.
- Right-click a TopOptLab component to open its Python setup folder.
- Existing manual-install local settings keep priority for backward compatibility.
- No silent downloads when Rhino loads a component.

## Acceptance on 17 November 2026

- Actual Yak install, uninstall and reinstall on the development Windows PC.
- Fresh CPU runtime creation and successful reuse after package reinstall.
- 33 component types loaded by real Rhino/Grasshopper from the Yak package GHA,
  with the legacy manual GHA backed up outside Grasshopper search paths.
- Native 2D engineering example, CPU direct backend, cell size 0.5, volume fraction
  0.45 and verification threshold 0.2: baseline, optimisation and voxel
  verification all completed. Optimisation reached its 40-iteration limit;
  this is explicitly not a claim of convergence.
- Native single-stage preview and valid preview bounds, setup menu, actual button
  Run/Stop/Reset, cancellation marker with worker exit, mesh Bake/Undo (0→1→0
  active objects), and GH save/reopen without automatic worker starts passed.
- Full regression suite: 270 passed, one existing near-zero determinant warning.
- C# worker bridge 2D and 3D: launch, completion, cancellation, isolation,
  fingerprints and rejection of a foreign result passed.

The reproducible in-Rhino harness is `tools/yak/native_acceptance.py`. Run it with
Rhino's `RunPythonScript` after loading Grasshopper, in a **separate empty test
Rhino instance**: it creates a GH document and performs Bake/Undo in that test
model. It writes `tool/build/yak-native/native-acceptance.json`. Keep automation's
Rhino.Application COM reference alive until its asynchronous timers finish.

This is API-driven acceptance in the actual Rhino/Grasshopper process, not a
claim of manual mouse testing. Optional screenshot capture is diagnostic only;
the solver and lifecycle checks use native component data and assertions.

## Scope still unverified

No second Windows computer or native Mac acceptance was performed. The Windows
Yak release is experimental alpha. A model's engineering qualification remains
application-specific. No Rhino SDK binaries, machine settings, Python virtual
environments or instructor PowerPoints belong in the distribution source.

## Build and setup

Run `python tools/yak/build.py --output <new-directory>` from a source checkout
with the Rhino SDK installed. Never reuse a setup/test directory as the package
staging folder. See [setup and migration](../tools/yak/README.md).

Public Yak publication requires Rhino Account authorization and is a separate
step. Check the package on the official test server before the first public push.

## Example archive repair (alpha.3)

A native GH_IO audit reproduced missing parameter chunks in 40 of 106 repository GH/GHX archives. These archives predated appended ports in Engineering Settings, Domain 3D and Final Geometry 3D. They were re-saved by Rhino 8 Grasshopper with the current component schema. Component IDs, types, input/output parameter IDs, persistent values and wire source IDs were compared before and after migration. All 106 archives must now read without errors or warnings. This is archive compatibility acceptance, not a claim that every numerical example was rerun.

Run python tools/yak/check_example_archives.py for the portable GHX/port/wire check (also in CI). Run tools/yak/native_archive_audit.py with Rhino RunPythonScript for binary and XML archive acceptance.
