# Contributing

This repository contains the Rhino/Grasshopper integration and a bundled upstream
snapshot. It is currently private and at **experimental alpha 0.4.0-dev**. Work in a feature branch
and describe the problem, resulting behavior, validation and remaining limitations.

## Development environment

Follow [Installation](docs/INSTALLATION.md). For Python-only development/CI, from
the repository root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c requirements-runtime-lock.txt -r tool/requirements-tested.txt threadpoolctl==3.7.0 psutil==7.2.2
.\.venv\Scripts\python.exe -m pip install --no-deps ./vendor/topoptlab
New-Item -ItemType Directory -Force tool/build | Out-Null
.\.venv\Scripts\python.exe -m pytest tool/tests -q --basetemp tool/build/dev-tests
.\.venv\Scripts\python.exe tool/tools/verify_repository.py
```

The last two commands do not require the Rhino UI. CUDA tests are optional and
skip if CuPy is absent. A CPU CI run does not validate CUDA.

To compile against the installed Rhino 8 SDK:

```powershell
.\.venv\Scripts\python.exe tool/build.py
```

Generate the main example gallery with:

```powershell
.\.venv\Scripts\python.exe tool/tools/generate_example.py
```

The generator currently assumes the standard Rhino installation path. Review
generated GH/GHX files and run archive/native probes before committing changes.
The teaching example has its own source in
[teaching/roof_2d/output/source](teaching/roof_2d/output/source/README.md).

## Validation expectations

See [repository review validation](docs/REVIEW_VALIDATION.md) for the latest
installer/documentation change checks; numerical history remains in docs/VALIDATION.md.

- Reproduce defects with relevant numerical or integration checks.
- State units, geometry, material, boundary conditions and load cases.
- Check solver residuals, reactions and force/moment/energy balance where applicable.
- Keep mesh refinement distinct from reoptimization on a changing geometry.
- Record benchmark inputs, backend, hardware, warm-up/repeats and memory definition.
- Describe native Rhino tests separately from Python, SDK and bridge tests.
- Preserve strict geometry and mesh-quality rejection; do not label iteration limits
  as convergence or a successful solve as engineering qualification.

Use the [native acceptance checklist](docs/USER_GUIDE.md) for preview, selection,
Run/Stop/Reset, save/reopen, Bake and Undo.

## Repository hygiene and attribution

Commit source, examples and concise reproducible evidence. Do not commit the
virtual environment, GHA/SDK binaries, local-settings.json, credentials, cache
folders or complete personal job histories. Course reference outputs are an
intentional exception: they let a class inspect solved results without rerunning.

Keep `vendor/topoptlab/` byte-for-byte consistent with `vendor/upstream-sha256.json`.
Some original CSV/log fixtures are ignored by the upstream .gitignore but are
intentionally tracked here. Do not edit the upstream snapshot to implement an
integration feature. Resolve the original revision before proposing upstream work.

The integration is GPL-3.0-or-later; retain [LICENSE](LICENSE) and
[third-party notices](THIRD_PARTY_NOTICES.md). Do not redistribute Rhino SDK binaries.
The editable teaching deck and reference figures are included with their existing
source/provenance notes.

GitHub Actions runs CPU numerical regressions and repository integrity checks.
A release also needs licensed Rhino/native and relevant CUDA acceptance; green
hosted CI alone is not that acceptance.

## Controlled upstream updates

- Identify the current snapshot with `vendor/upstream-sha256.json`; do not invent
  a Git revision for the transferred source.
- Update upstream only on a dedicated branch, recording the source revision when
  available, provenance, API changes and regenerated manifest.
- Run worker request/result, numerical and rejection regressions in `tool/tests`.
  Add a contract regression for each changed upstream API before adapting callers.
- Repeat native Rhino/Grasshopper acceptance and relevant CUDA tests separately.
- Do not track upstream latest automatically or modify vendored files for a local feature.

## Publication gates

- Require a passing [Numerical validation workflow](https://github.com/andrea199/TopOptLab-Rhino/actions/workflows/numerics.yml).
- Record installation on a second Windows PC and licensed Rhino UI acceptance.
- Keep the alpha label until those acceptance gaps are resolved; version changes
  and public releases are separate decisions.
- Read the Docs is a follow-up after publication approval: build the integration
  Markdown guides with Sphinx/MyST without importing Rhino or numerical modules,
  check links/assets locally, then connect the approved repository.
- Do not enable public documentation hosting while this repository is private
  without an explicit publication decision.
