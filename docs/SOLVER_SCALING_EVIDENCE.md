# Solver scaling evidence

Measured on 2026-09-21 on the project workstation. These are solver microbenchmarks, not full shelf-bracket optimization timings. No default backend was changed and no CUDA fallback or tolerance relaxation was introduced.

## Scope and bounded variants

- Baseline: saved unmodified `tool/build/solver-scaling-baseline/fem_backends.py`.
- Variant 1: cache node-pair sparsity and scatter indices, update dense nodal blocks with bounded temporary arrays; retain exact FEM equations. HEX8 uses 64 cached node-pair indices instead of two fresh arrays of 576 DOF-pair indices each.
- Variant 2: supply the physical translation and rotation modes to explicitly selected CPU AMG. Q4 receives three modes; HEX8/TET4 receive six.
- Budget: these two implementation changes, two paired confirmation runs, 8,000 and 27,000 element fixed inputs. No search over tolerance or hidden backend selection.

## Measurements

Each process prepares or solves three identical predefined positive stiffness distributions; case geometry, loads, material, four CPU threads and tolerance 1e-9 match between implementations. Peak RSS is the Windows process peak working set, including imports and model creation; it is not GPU memory.

| Operation | Repeat | Baseline | Updated | Evidence |
|---|---:|---:|---:|---|
| 27,000-cell peak RSS | 1 | 971.8 MiB | 457.6 MiB | 52.9% lower |
| Two subsequent matrix updates, 27,000 cells | 1 | 1.178 s | 0.714 s | 1.65x faster |
| Three AMG preparations + solves, 8,000 cells | 1 | 15.676 s | 3.171 s | 4.94x faster |
| 27,000-cell peak RSS | 2 | 972.8 MiB | 458.9 MiB | 52.8% lower |
| Two subsequent matrix updates, 27,000 cells | 2 | 1.119 s | 0.673 s | 1.66x faster |
| Three AMG preparations + solves, 8,000 cells | 2 | 9.338 s | 4.327 s | 2.16x faster |

AMG iterations were **103 / 110 / 106 before, 17 / 18 / 17 after**, identically across both repetitions. Compliance agrees to approximately 1e-12 relative; every measured solve independently passed free-DOF residual <= 5e-9 and the work/strain-energy equality. Updated residuals were below 8e-10. Wall times vary with the workstation state: the observed speedup range is reported rather than a single optimistic factor.

At 27,000 cells the persistent block map consumes 10,063,692 bytes. Full stiffness and reduced system matrices still exist; this is not a matrix-free or GPU-native assembly implementation. The existing explicit matrix-free backend remains available.

## Correctness gate

Test-first: the new test module initially failed importing the missing BlockAssembly implementation. After implementation, **51 tests passed in 15.71 seconds**, including independent COO comparisons for shared and element-specific matrices, repeated densities, partial constraints, translated geometry, cancellation, multi-load parity, all existing backend checks, and independent scikit-fem TET4 comparison.

```powershell
rtk proxy .\.venv\Scripts\python.exe -m pytest tool/tests/test_solver_scaling.py tool/tests/test_engineering.py tool/tests/test_final_geometry.py -q --basetemp=tool/build/pytest-solver-scaling-1
```

The full repository suite and larger end-to-end shelf benchmark are separate integration checks documented by the main change. These microbenchmarks do not establish stress convergence, final printed strength, or million-cell feasibility.

## Reproduction and rollback

Use a fresh process for each line and alternate baseline/current. Repeat twice, changing the output filename to keep both records. The current script supports assembly-only runs and FEM solve runs; never run two timing jobs simultaneously.

```powershell
rtk proxy .\.venv\Scripts\python.exe tool/tools/benchmark_solver_scaling.py --implementation baseline --shape 60 30 15 --output tool/build/solver-scaling-baseline/assembly-27000-1.json
rtk proxy .\.venv\Scripts\python.exe tool/tools/benchmark_solver_scaling.py --implementation current --shape 60 30 15 --output tool/build/solver-scaling-baseline/current-assembly-27000-1.json
rtk proxy .\.venv\Scripts\python.exe tool/tools/benchmark_solver_scaling.py --implementation baseline --shape 40 20 10 --backend cpu-amg --solve --output tool/build/solver-scaling-baseline/amg-8000-1.json
rtk proxy .\.venv\Scripts\python.exe tool/tools/benchmark_solver_scaling.py --implementation current --shape 40 20 10 --backend cpu-amg --solve --output tool/build/solver-scaling-baseline/current-amg-8000-1.json
```

The original solver is preserved in the baseline folder for local rollback. SHA-256 values, Python/package versions, raw elapsed times, iterations, residuals and peak memory are recorded in [solver-scaling-evidence.json](solver-scaling-evidence.json). The baseline backup must be present to rerun the historical comparison.

## Remaining limits

- Topology iteration histories include high density contrast, multiple cases and adjoint loads; results here use three controlled stiffness distributions and must not be extrapolated to full optimization runtime.
- CPU AMG is optional and explicitly selected; CUDA still assembles on CPU and transfers the reduced matrix.
- AMG candidates improve elasticity coarsening but do not guarantee convergence on every density pattern. Nonconvergence and cancellation still raise errors.
- No physical print or anchorage capacity is inferred from this solver performance work.

## Density-dependent RHS warm starts

An additional bounded integration fix adds optional stable solve slots, because self-weight and adjoint RHS vectors change every density iteration and the previous exact-RHS-byte cache therefore missed every iteration. Forward cases use `(forward, case_name)` and constraint adjoints use `(adjoint, case_name, constraint_kind)`. The existing API remains valid without a slot. The cache retains at most 16 solutions, updates recency, and always solves the **current** matrix and RHS. An old guess is discarded if its current residual is no better than a zero start. Convergence tolerances, equilibrium checks and explicit backend selection are unchanged. Performance metadata now reports `warm_start` and `initial_relative_residual`.

Three test-first cases initially failed for the absent API/metadata, then **76 focused tests passed in 11.86 s**, including finite-difference gradients for density-dependent gravity and displacement/stress constraints, isolated case/adjoint keys, rejection of harmful guesses and the 16-entry bound. One pre-existing upstream tiny-element Jacobian warning remains.

A repeated CPU-only comparison used 512 HEX8 cells, one CPU thread, gravity-only loading, and density states 0.8 → 0.801 → 0.802. Exact-RHS matching required **49 / 49 / 49 CG steps**, while stable slots required **49 / 48 / 48**. Initial relative residual on later states fell from 1 to approximately 0.0025. Both repeats agree; solutions match and all strict residual/equilibrium checks pass. This is a modest iteration improvement, **not evidence of a major runtime acceleration**. Other root validation jobs were active, so wall times are illustrative only and no wall-time speedup is claimed. Raw data: [solver-warmstart-evidence.json](solver-warmstart-evidence.json).

The earlier assembly/AMG timings above and the in-progress full shelf optimization used the pre-warm-start module; their evidence hashes are retained unchanged. The raw warm-start evidence records the updated file hashes separately.
