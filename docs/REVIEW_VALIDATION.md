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
