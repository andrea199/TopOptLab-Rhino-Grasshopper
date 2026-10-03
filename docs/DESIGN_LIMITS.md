# Design limits and result review — 0.3.0-dev

## Start with the supplied examples

Open tool/examples/engineering_design_limits_2d.gh or engineering_design_limits_3d.gh.
All Run/Stop/Reset controls start idle. The two cases are independent; both must meet
all enabled limits. Default units are mm and N. The reference steel is linear elastic.

| Example | Cells | Material budget | Displacement limit | Stress limit | Threshold |
|---|---:|---:|---:|---:|---:|
| 2D cantilever, two independent positions | 1152 | 60% | 0.0002 mm | 10 MPa | 0.4 |
| 3D cantilever, down and side cases | 1728 | 60% | 0.03 mm | 10 MPa | 0.4 |

These limits are deliberately illustrative, not recommendations for a real part.
Changing geometry, loads, material, mesh or budget may make them infeasible.
The 2D thickness is 2 mm. Both examples use CPU CG and at most 80 design iterations.

1. Run BASELINE FEM. Set REVIEW Stage=0 and inspect Case=1, then Case=2.
2. Set Design Limits: U max in the declared length unit; Stress MPa always in MPa.
   Zero disables that explicit limit. Enforce=True activates MMA in optimization.
   Enforce=False leaves the original optimizer unchanged and reports checks only.
3. Run OPTIMIZATION. Stage=1 previews density with Field=0. Field=1 shows displacement;
   Field=2 shows **relaxed design stress**. Keep Case=1 during a live solve; other saved
   case responses become available when that run completes.
4. Read both termination and feasibility. A feasible result may reach the iteration
   limit without converging. A converged density model is still not the final shape.
5. Run FINAL VERIFICATION after optimization completes. Stage=2 displays the actual
   retained binary grid, at full material stiffness. Inspect every case and the report.
6. Compare panels show mass and response against the matching baseline. If the
   geometry, supports, loads, material or units differ, comparison is rejected.

Material limit=True selects the material screening allowable instead of explicit
stress; do not also enter a positive stress value. If that allowable is unavailable,
the calculation explains why rather than silently dropping the stress constraint.
For S235 the stock-thickness requirement still applies. See MATERIALS.md.

## What is enforced

The objective remains the sum of weighted case compliances. Case weights affect
that objective, not the limits: even a case with a small weight must meet its limits.
Displacement is the largest nodal vector magnitude. Stress is evaluated at all 4
Q4 / 8 HEX8 integration points in each active element.

In density optimization the stress field is
`sqrt(rho) * von_Mises(C * B * u)`, where `rho` is physical filtered density.
This is a relaxed optimization surrogate, not the physical stress in a porous material
or in the extracted part. The lower design-density bound is 0.001. Preserved cells
remain solid. Final verification computes full-material stress on retained cells.

Each case and enabled field uses a conservative unnormalised KS upper bound:
`max(r) + log(sum(exp(p * (r - max(r))))) / p`, where `r` is sampled value / limit.
Default `p=50`. Its conservatism grows with sample count; changing the mesh changes
both the numerical response and aggregation. The actual sampled maxima, aggregate
utilizations and tolerance are saved separately. There is no hidden normalization
that could underestimate the sampled maximum.

MMA uses the checked adjoints, including density-dependent gravity loads and the
filter/manufacturing projection. Constraint rows are scaled once from their initial
magnitudes for conditioning. Feasibility is always evaluated in the original
normalized inequalities, including the volume constraint. With gravity, volume is
fixed within a normalized 1e-6 band; without gravity it is an upper bound.

Default numerical feasibility tolerance is 0.001 (0.1%). A sampled value just above
its limit is labelled within_tolerance, not within_limit. Optimizer feasibility also
checks conservative aggregates and volume. These conditions can be stricter than
the individual sampled-maximum checks. When any optimizer inequality fails, the
overall status is constraints_not_satisfied, even if sampled maxima appear acceptable.

## Status meanings

| Status | Meaning |
|---|---|
| within_limits | All enabled sampled maxima satisfy the limits; when MMA is active, its aggregate/budget inequalities are also feasible to the declared tolerance |
| within_tolerance | A sampled maximum exceeds its limit only within the stated numerical tolerance |
| exceeded | A FEM/check-only sampled limit is exceeded |
| constraints_not_satisfied | At least one MMA aggregate or material-budget inequality exceeds tolerance |
| not_requested | No displacement or stress limit was enabled |
| converged | Feasible design and the objective/design change window plus scaled MMA KKT residual passed |
| iteration_limit | The iteration budget ended; inspect feasibility separately |
| optimizer_failed | MMA suffered a numerical breakdown; the best previously evaluated state is saved for diagnosis, not declared converged |

The best feasible objective is preferred to every infeasible design. If no feasible
iterate exists, the least violating sampled iterate is retained. A failed linear FEM
solve is still an error. Cancellation is still cancellation. No automatic backend
fallback or relaxation of user limits is performed.

## Review and comparison

Stage controls preview visibility only. It does not run a solver or change its Mode.
Case is 1-based. All engineering stages save case-01.json etc. Case Result validates
job identity, physical-input signature and case name before reading a saved file.
Keep the job folder in place; moved/deleted files require recomputation.

The viewport legend states stage, selected case, quantity, units, color range,
actual peak, visual deformation factor and all-case limit status. Max=0 auto-scales
colors. Set a common positive Max to compare the same field across stages; a value
above Max saturates the color, but the actual peak is still printed. Reset Max when
changing quantities or units. Density always uses 0..1. A 3D cut is visual only;
the legend peak remains the full selected-case peak, including hidden voxels.

Compare reports mass saving, per-case displacement/compliance and final FEM stress.
It intentionally omits stress ratios between relaxed design stress and baseline
full-material stress. The selected case's compliance is distinct from the weighted
all-case objective. Scaling deformation does not alter any numerical result.

## Qualification limits

This increment remains an engineering preview. Point loads, sharp supports and
reentrant corners may have mesh-sensitive stress peaks. A numerical pass applies
to this particular linear-static discretization and stated tolerance. Final-shape
verification is still on the same voxel grid, with no independent conforming mesh.
Mesh refinement, independent solver comparison, nonlinear material response,
buckling, fatigue and process-specific manufacturability remain separate work.

Method references: [MMA Python implementation](https://github.com/arjendeetman/GCMMA-MMA-Python)
and [stress constraint aggregation/relaxation discussion](https://backend.orbit.dtu.dk/ws/files/124880709/PREPRINT.pdf).
The implemented sqrt-density stress model and KS settings are specified above;
this is not a reproduction of every method in that discussion.
