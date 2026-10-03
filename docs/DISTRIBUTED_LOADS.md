# Pressure, traction and self-weight

Available in 0.2.1-dev through Load Case -> Engineering. Legacy Load and Load 3D
still mean a TOTAL force shared equally over selected nodes.

## Ready-to-use examples

Open tool/examples/engineering_distributed_loads_2d.gh or
engineering_distributed_loads_3d.gh. Dimensions, position, cell size, pressure,
surface-load mode, material, solver and volume remain parametric.

The default surface is the top boundary: +Y for XY 2D and +Z for 3D.
Case 1 combines pressure with gravity; Case 2 contains gravity alone and is solved
independently. Run BASELINE FEM, then OPTIMIZATION, then FINAL VERIFICATION.
All buttons start off. Default CPU backend is CG.

Pressure = 0.1 in N/mm^2 by default. Positive pressure acts INTO the material.
Mode = 1 switches to the traction vector; P is then ignored. Its components are
force per area, not a total force. Changing dimensions changes total force at
constant pressure. Changing mesh size preserves the integrated force on the same
planar boundary when that boundary is represented exactly.

## Selecting a loading patch

Surface Load is for 2D; Surface Load 3D is for solids. Connect Domain to D.
Side = 1 +X, 2 -X, 3 +Y, 4 -Y, 5 +Z, 6 -Z; 0 considers all exposed boundaries.
2D directions follow the domain plane; 3D directions follow world XYZ.

G is optional. Without it, all exposed facets matching Side are selected. Connect
boundary curves for 2D or Brep faces/surfaces for 3D to restrict the patch. Selection
uses facet-center distance with Tol expressed as a fraction of cell size h (default
0.1). Every input selection must reach a facet; empty matches cause an error.
Overlapping selections are deduplicated. Inspect Patch and direction outputs after
any geometry, cell size or tolerance change. Curved CAD surfaces are approximated
by grid facets, so their area and normals require a mesh refinement study.

Uniform loads are integrated using the element shape functions: each 2D edge node
receives half the edge load and each 3D face corner receives one quarter of the
face load. Contributions accumulate at shared nodes. The 2D loaded area is edge
length multiplied by Settings thickness; the 3D area is the actual voxel facet area.
Pressure is normal to the selected grid facet. Traction is a world vector, projected
into the 2D domain plane; an out-of-plane component is rejected.

The cells supporting surface loads are always preserved during optimization. This
is a fixed loading interface, not fluid pressure following an evolving material
boundary. Keep attachments in Settings additionally preserves active cells touching
support and point-load nodes. It is on in newly generated examples; older JSON
requests without the option retain their previous behavior. Preserved cells count
toward the material budget and may require increasing Volume.

## Gravity and units

Connect Domain to Gravity D and a world acceleration vector to g. Acceleration is
ALWAYS m/s^2: use (0,-9.80665,0) for an XY example or (0,0,-9.80665) for 3D.
No mm/s^2 conversion is needed. Out-of-plane gravity is rejected for a 2D domain.
Material density is kg/m^3; model volume is converted to m^3 before multiplying by
density and acceleration. Forces are converted to the Material force unit (N or kN).
Connect Gravity L to the same Load Case as simultaneous external loads. Separate
Load Cases are independent alternatives, not automatically summed forces.

Each element distributes its weight consistently across its nodes. During
optimization its mass scales linearly with physical density. During final binary
verification, only retained full-density elements contribute weight.

Distributed loads that touch fixed directions still contribute to support reactions.
This is physically required for gravity and boundary traction. The existing rule
rejecting a nodal point force in a constrained direction is unchanged. A load case
with no effective force on any free direction is rejected explicitly.

## Self-weight optimization

For C = f(rho)^T u and K(rho)u = f(rho), the implemented derivative is

dC/drho_e = 2 u^T (df/drho_e) - u^T (dK/drho_e) u.

The filter/manufacturing projection is applied by its transpose in the gradient.
The additional load derivative is essential: sensitivities can be positive, so the
legacy square-root optimality-criteria update is not used for gravity cases.

A projected-gradient step with an Armijo line search keeps the material budget
fixed, includes Keep, limits each design change to 0.15, and bounds design density
between 0.001 and 1. Convergence additionally checks projected stationarity.
The volume here is an equality, not simply an upper bound. A failed search produces
line_search_stalled, not converged. Pressure-only and conventional load cases keep
the existing optimality-criteria update and volume policy.

This is an experimental self-weight formulation. SIMP low-density parasitic effects,
mesh dependence, fixed load interfaces and local optimization behavior remain
qualification limits. A correct derivative and a successful solve do not establish
that a thresholded shape meets stress or displacement requirements. Reanalyse it.

## Reports and reproducibility

Reports include load definitions, integrated area/resultants, mass, reactions,
material units, algorithm, budget policy and termination reason. Vector summaries
use domain axes in 2D and world XYZ in 3D. Per-case FEM files include applied nodal
forces in world coordinates. The main viewport still displays the first case.

Run tool/tools/validate_distributed_workflow.py to reproduce the full example-size
baseline/optimization/threshold workflow. The --backend and --iterations options
allow controlled comparisons. Run tool/tools/test_distributed_bridge.py --cuda
for the actual C#/Python/CUDA boundary-loading bridge test.

## Numerical background

The body-force and boundary-traction integrals follow the standard weak form in
[J. Bleyer's linear elasticity tutorial](https://bleyerj.github.io/comet-fenicsx/intro/linear_elasticity/linear_elasticity.html).
Reactions are computed from the discrete residual, including loads at supported
nodes, consistent with the approach discussed in
[Computing consistent reaction forces](https://comet-fenics.readthedocs.io/en/latest/demo/tips_and_tricks/computing_reactions.html).
The difficulty of design-dependent self-weight, including non-monotonic behavior
and low-density effects, is discussed by Prabhat Kumar in
[Topology optimization of stiff structures under self-weight for given volume](https://arxiv.org/abs/2111.13875).
Our implementation is a projected-gradient formulation; it does not implement that
paper's Heaviside formulation and is not claimed to reproduce its results.
