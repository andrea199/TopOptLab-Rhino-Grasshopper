# TopOptLab Mac Yak candidate — Apple Silicon and Intel

This is a **local preparation candidate**, not a public Package Manager release.
It contains one AnyCPU managed plugin for both Mac architectures. Python dependencies
are installed natively for the current Mac, in a separate persistent environment.

## Requirements

- Rhino 8 SR37 or later on **macOS 15 or later**.
- Native **Python 3.13, 64 bit**, from python.org or a matching native Homebrew installation.
- Internet access for the first setup. Run the official Python certificate installer if required by that Python distribution.
- Apple Silicon: native arm64 Python and Terminal. Intel: x86_64 Python. Rosetta Python is rejected.

## Local pilot installation

1. Save work and close Rhino. Move any previous manual TopOptLab GHA folder outside Grasshopper library/search paths. Keep a backup; do not load duplicate component GUIDs.
2. Put the Mac `.yak` in a folder, then use the bundled Rhino CLI from Terminal:

   ```sh
   "/Applications/Rhino 8.app/Contents/Resources/bin/yak" install --source "/path/to/candidate/folder" topoptlab-rhino 0.4.0-alpha.5
   ```

3. Restart Rhino, open Grasshopper and place any TopOptLab component. Right-click it → **TopOptLab Python setup folder**.
4. Run **SETUP-PYTHON.command**. If it is not executable, run `bash "/full/path/to/SETUP-PYTHON.command"` from Terminal. Do not disable Gatekeeper or remove quarantine from unrelated files.
5. Restart Rhino. Open **source/docs/manual/index.html** for the complete English manual and **source/tool/examples/engineering_workflow_2d.gh** for the first three-stage calculation.

The runtime and active settings live under `~/Library/Application Support/TopOptLab/Rhino8/`.
Runtime folders include the native CPU architecture. Settings are activated only after validation; a failed setup preserves the old configuration. Old runtimes remain available for rollback.

## Acceptance still required before public Mac publication

Native CPU worker tests are separate from **loading the GHA in Rhino for Mac**.
Test all 33 component types, icons/context menu, the 3D memory preflight, geometry
selection, Python process launch, preview/legends, Run/Stop/Reset, save/reopen and
Bake/Undo on Apple Silicon and Intel. The included `source/tools/yak/native_calculations.py`
can exercise the canonical examples in a separate Rhino session. It writes its report
under `source/tool/build/yak-calculations/` and supplies only intentional lesson inputs/wires in memory.

The Windows release remains a separate `win` distribution. CUDA is not offered by
this Mac CPU setup. Shelf classroom defaults are CPU AMG, 5 mm, threshold .35 and
60 iterations; the historical 2.5 mm refinement is not qualified.

Licences, upstream provenance, ARCHIBIOFOAM acknowledgement and EU disclaimer are
included in source/LICENSE, source/THIRD_PARTY_NOTICES.md and source/README.md.
