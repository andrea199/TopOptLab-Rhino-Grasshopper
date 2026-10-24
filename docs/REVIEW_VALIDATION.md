# Repository review validation - 2026-10-23

Scope: documentation, installer entry point compatibility, pytest discovery and
CI report retention. No numerical implementation or vendored snapshot changes.

- Environment: Windows, Python 3.13.5, isolated virtual environment.
- Dependencies: requirements-runtime-lock.txt and tool/requirements-tested.txt,
  threadpoolctl 3.7.0, psutil 7.2.2; bundled upstream installed with --no-deps.
- Full suite: **258 passed, 7 skipped, 1 warning in 16.31 seconds**.
- Warning: near-zero element determinant in the 3D pressure/gravity unit-conversion test.
- Four installer tests cover both help entry points, the batch launcher,
  prepare-only isolation and rejection of an unsupported Python version.
- Integrity checks: 401 upstream files, 82 course files, 21 GH/GHX pairs,
  40 slides/notes and 11 linked guides passed.
- Initial local test invocation failed to create its temporary directory because
  tool/build did not yet exist; rerun passed after that parent existed.
  The CI workflow already creates this parent explicitly.

Reproduce from the root after installing development dependencies:

```powershell
New-Item -ItemType Directory -Force tool/build | Out-Null
.\.venv\Scripts\python.exe -m pytest -q --basetemp=tool/build/review-tests --junitxml=tool/build/review-results.xml
.\.venv\Scripts\python.exe tool/tools/verify_repository.py --tracked
```

Not verified by this run: licensed Rhino UI installation/acceptance, CUDA,
installation on a second PC, and public documentation hosting.
Local results are not a claim that a GitHub Actions run has completed.

## Completed integration — 2026-10-24

- Consolidated the review branch with the single English manual: 8 lessons,
  56 slides, teacher/student guides and native progressive exercise files.
- Full local suite: **265 passed, 1 warning in 23.86 seconds** on the installed
  Windows/Python environment. The warning is the existing near-zero determinant
  warning in the 3D pressure/gravity unit-conversion test.
- Repository integrity passed: all 401 original upstream files remain unchanged.
- Manual checks passed: 36 English HTML pages, 856 relative links/assets,
  33 component images, 346 ports, 16 new exercise archives and 295 valid wires.
- Rebuilding leaves generated manual pages unchanged. Static hosting export
  passed locally without importing Rhino or numerical packages.
- Added a Linux Manual validation job and Read the Docs custom HTML configuration.
  The existing CPU CI retains JUnit results and exercises installer compatibility.

### Review items

1. Tests/CI: existing regressions are visible in the README; numerical and manual
   checks run on push/PR and preserve reviewable artifacts.
2. Upstream link: Implemented links to TopOptLab and explains integration scope.
3. Installation: one concise README section, detailed instructions in INSTALLATION.
4. Readability: scope, limits, development and attribution use bullets.
5. Packaging: the bundled Python package already uses pyproject.toml/setup.cfg.
   Native installation is named install_windows.py with a setup.py compatibility
   shim. Root pyproject.toml explicitly scopes integration test discovery.
6. Maturity: experimental alpha is explicit; no stable-release claim is made.
7. Hosting: .readthedocs.yaml builds the canonical HTML with standard-library
   tools. The account owner must import/authorize the repository in Read the Docs
   and choose visibility before a live URL exists. See DOCUMENTATION_HOSTING.md.

No GitHub visibility change, public release or external-account authorization is
performed by this configuration. Actual Rhino UI, second-PC installation and Mac
acceptance remain practical qualification steps; numerical checks do not claim them.
