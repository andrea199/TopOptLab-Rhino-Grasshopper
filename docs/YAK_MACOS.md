# Mac Yak preparation — Apple Silicon and Intel

**Status: candidate prepared, CPU worker and host APIs tested; Rhino/Grasshopper Mac acceptance pending.**
Candidate: `topoptlab-rhino-0.4.0-alpha.5-rh8_37-mac.yak`. It has not been published to the public Yak server. The existing Windows `0.4.0-alpha.4` release is unchanged.

## One Mac package, native runtime per architecture

Yak uses the `mac` platform tag. One IL-only AnyCPU GHA serves Apple Silicon and Intel; Python creates a separate native arm64 or x86_64 environment. The setup rejects Rosetta Python, unsupported architectures and macOS below 15. It requires Python 3.13, 64 bit, and first-setup internet access. Native numerical libraries must have binary wheels; setup does not attempt to compile them on a student machine.

Requirements and setup instructions are in [the Mac package README](../tools/yak/README_MAC.md). The package includes the complete source, licences, English HTML manual, component guide, lesson files and funding acknowledgement. No PowerPoint or Rhino SDK binaries are included.

## Verified on actual macOS runners

| Check | Apple Silicon | Intel |
|---|---|---|
| Native CPU Python environment and imports | PASS | PASS |
| Persistent runtime reuse and paths with spaces | PASS | PASS |
| Integration regressions | 263 passed, 11 skipped | 263 passed, 11 skipped |
| Actual .NET Mac settings path and vm_stat memory preflight | PASS | PASS |
| GHA loaded inside Rhino for Mac | **Not tested** | **Not tested** |

The skipped tests are seven CUDA cases and four Windows source-installer cases. The Mac worker suite includes real CPU FEM/optimization and Gmsh/TET4 integration tests. The .NET probe compiles the actual RuntimePaths.cs source and executes it on native macOS; this does not load the full Grasshopper assembly or exercise Rhino UI.

Evidence: [workflow run](https://github.com/andrea199/TopOptLab-Rhino-Grasshopper/actions/runs/44107816967) and [machine-readable record](YAK_MACOS_EVIDENCE.json). Windows CPU regressions also pass (267 passed, seven optional CUDA skips), and the C# bridge passes real 2D/3D worker launch, completion, cancellation and result-isolation checks.

## Portability fixes

- Use `~/Library/Application Support/TopOptLab/Rhino8` and `venv/bin/python` on Mac; retain the released Windows path contract.
- Keep architecture-specific runtime folders, atomic settings activation, rollback copies and setup locking.
- Replace unconditional kernel32 memory access with macOS vm_stat free+inactive-page preflight. Existing allocation budgets and fail-closed checks remain unchanged.
- Use the Mac `.command` setup launcher and `/usr/bin/open` folder action; preserve executable archive permissions.
- Use Eto's UI timer for the native calculation harness on Mac. Rhino supplies its own drawing/forms compatibility implementations; they are not bundled.
- Keep CUDA outside this Mac CPU setup.

## What still prevents public Mac qualification

No licensed Rhino for Mac session is available here, and no Mac is available to the project owner for the final application test. Hosted CPU tests cannot replace the following checks on **both** architectures:

1. Load all 33 component types, icons and context menus without missing dependency/type errors.
2. Open the Python setup folder, configure/reuse the native runtime and launch a worker from a real GHA component.
3. Create 2D and 3D geometry, select support/load regions and verify the actual Rhino memory preflight.
4. Run baseline, optimization and verification; check results, preview clipping, legends and stage visibility.
5. Test Run/Stop/Reset, save/reopen without automatic workers, and Rhino Bake/Undo.
6. Run [native_calculations.py](../tools/yak/native_calculations.py) from the installed package inside a separate Rhino Mac session for all canonical examples/lessons. Source student gaps are completed only in memory; numerical jobs remain outside the plugin.

The Windows native matrix remains separate evidence. Neither the Mac GHA load path nor every slider combination is qualified by these tests. The shelf classroom example uses the already documented CPU 5 mm defaults; the historical 2.5 mm refinement remains unqualified. A one-level final FEM mesh does not establish convergence or a load rating.

## Build and local trial

On the prepared Windows development checkout with Rhino SDK, run:

```text
python tools/yak/build_macos.py --output NEW_OUTPUT_DIRECTORY
```

The builder checks AnyCPU IL flags, package CRC, runtime identity, absence of SDK/native binaries and executable `.command` mode. It never publishes or installs. Follow [local Mac installation](../tools/yak/README_MAC.md) using the single file in its `distribution` folder. Keep public publication pending the native Rhino checks above.

References: [Yak distribution tags](https://developer.rhino3d.com/en/guides/yak/the-anatomy-of-a-package/), [Rhino .NET compatibility](https://developer.rhino3d.com/guides/rhinocommon/moving-to-dotnet-core/), [McNeel on Mac drawing/forms compatibility](https://discourse.mcneel.com/t/cross-platform-support-and-menu-items-for-gh/201146), [GitHub native Mac runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
