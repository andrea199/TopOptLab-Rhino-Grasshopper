# Engineering product development plan

Owner: development agent. User contribution: CAD acceptance and real application requirements.
The target is a qualified linear-static design tool; advanced physics are separate releases.

| Milestone | Deliverable | Acceptance gate | Current state |
|---|---|---|---|
| M0: reproducible core | English repository, installer, version, upstream snapshot, CI | Fresh environment builds, original cases unchanged, traceable sources | Implemented; fresh-environment preparation passed |
| M1: engineering workflow | Units/materials, independent cases, convergence, baseline FEM/report | Analytic/sensitivity tests, no silent lost loads or failed solves | Numerically tested; Rhino UI pending |
| M2: performance | CPU/GPU, reusable matrices, memory and residual diagnostics | Accuracy parity, cancellation, repeated full/low-density benchmarks | Repeated solver comparisons completed; actual shelf FEM solved to 121,875 bounding cells; see RESOLUTION_VALIDATION.md for optimization and remaining qualification |
| M3: final geometry | Extracted topology FEM, conforming remesh, support transfer | Baseline/optimized/exported comparison and mesh convergence | Surface extraction, Keep-preserving editing, Gmsh/TET4 remesh and transfer implemented; extended qualification pending |
| M4: loading/constraints | Integrated pressure, gravity with sensitivities, displacement/stress limits | Equilibrium/derivative tests and feasibility reporting | Pressure/traction, self-weight and relaxed stress/displacement MMA constraints numerically tested; native UI acceptance pending |
| M5: manufacturing | Symmetry/extrusion, minimum feature, tooling/draft/overhang checks | Each constraint tested on process-specific parts | 3D printing chosen; overhang and sampled thickness review implemented; process constraints not yet enforced |
| M6: public beta | Clean-PC installer, tutorials, compatibility, release artifacts | Rhino acceptance, second PC, provenance review | Local repository prepared; not published |

## CPU and CUDA policy

CPU remains mandatory. Expose backend and residual; never silently replace CUDA.
Cache matrix/preconditioner for cases sharing stiffness; warm-start between iterations.
Reject failed convergence. Use float64 for accuracy parity. Measure end-to-end time,
cold/warm GPU runs, repeated-run dispersion and CPU/GPU memory before claiming speedups.

Implemented in the resolution increment: rigid-body AMG candidates, memory admission
estimates, reusable block assembly and FFT cone filtering. Repeated baseline/winner
measurements and larger actual-part trials are recorded in RESOLUTION_VALIDATION.md.
Next: broader high-contrast density and mesh-convergence qualification. Add GPU-resident assembly/filtering or specialized
matrix-free kernels only when profiling supports them. Multi-process scenario sweeps
are possible; one matrix copy per CPU core may exhaust memory.

## Engineering qualification

Already covered: exact tension, affine strain/shear, rigid modes, strain energy,
finite-difference compliance/volume derivatives including manufacturing projections,
unit invariance, independent cases, force/moment balance and backend parity.

Extend bending refinement, load-patch resolution, singularity interpretation and mesh
studies. Compare against an independent solver on solid and thresholded pieces.
Publish acceptance envelopes for grid size, element quality, material contrast and
tolerance. Convergence is separate from structural feasibility and material allowables.

## Current development increment: 0.4.0-dev

Implemented continuous triangle surface extraction with exact original Keep voxel
preservation, explicit edited-mesh validation, STL export, isolated Gmsh remeshing,
TET4 FEM and independent case transfer with force/moment checks. Added mesh studies,
independent scikit-fem element/solution comparison, final-result components and
one five-stage example. Print orientation, overhang and sampled normal thickness
provide the first additive geometric review. Publication remains deferred.

Next engineering priorities:
1. Native Rhino acceptance of the new components, viewing, editing, Stop and Bake/Undo.
2. Better TET quality near preserved/smoothed junctions, adaptive refinement or
   higher-order elements, more bending/stress studies, and an independent solver
   comparison covering a real final part and its load patches.
3. Repeated large/high-contrast CPU/CUDA measurements; GPU assembly/filtering and
   adjoint work only after profiling. Current CPU thread limits do not parallelize
   every stage, and geometric remeshing remains a CPU operation.
4. 3D printing process qualification: choose FDM/SLA/metal and printer/material,
   validate wall/overhang settings and directional material behavior. Enforced
   overhang/minimum-feature optimization and removable support generation remain
   separate work; sampled geometric flags must not be relabelled as guarantees.

## User contributions

1. Save and close Rhino for installation, then follow the native UI acceptance guide.
2. The first process is 3D printing. Specify FDM/SLA/metal and supply a small real part, mounting interfaces,
   credible load cases, material grade, operating temperature and production method.
3. Review design outcomes; report screenshots, job folders and reproduction steps.
4. Provide GitHub owner/repository name and project/author metadata.
5. Arrange a second Windows/Rhino PC and application-specific engineering review before deployment.

## Publication

Use GitHub for source, issues and releases; add food4Rhino when a tagged installer
and tutorials are stable. Publish as an engineering preview/beta until qualification
gates pass. No claim of certified safety follows from successful optimization alone.
Dates and effort estimates depend on the chosen manufacturing scope and benchmark parts.

## Resolution follow-up

Large voxel models and CAD reconstruction are implemented; see RESOLUTION_VALIDATION.md. The next concrete geometry task is robust automatic tetrahedral meshing of the 2.5 mm shelf candidate at threshold 0.32. Its voxel checks pass, but Gmsh parameterization/meshing does not yet produce an accepted final mesh. Do not mark this final part verified based on the earlier 5 mm CAD/FEM success.
