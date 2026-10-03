# Final geometry and conforming FEM — 0.4.0-dev

Open `tool/examples/engineering_final_geometry_3d.gh`. This extends the constrained
3D cantilever example. Dimensions and position remain parametric; units default to
mm and N. The final surface and FEM components are under **10 Final Geometry 3D**.
All calculations start from buttons, with no automatic launch when the file opens.

## Work through the example

1. Set dimensions, cell size, material, supports, independent load cases and limits.
   Keep the starting mesh modest. Run **BASELINE FEM**, then **OPTIMIZATION**.
   Check the optimizer termination and feasibility separately.
2. The existing **FINAL VERIFICATION**, viewed at Stage 2, is binary full-material
   voxel FEM. It remains a useful intermediate check.
3. Press **EXTRACT**. The completed optimization feeds **Final Geometry 3D**.
   Threshold shares the example's verification-threshold slider; smoothing defaults
   to 0.5 cells. Use **VIEW = 3** for the extracted surface and print flags.
4. Read the geometry report: closure, connected material components, volume and
   retained Keep volume. The Files output gives `final-surface.stl`. STL coordinates
   use the declared model units; STL itself does not store units. Select the correct
   units when importing it into another application.
5. Set the independent **Final tetrahedral mesh size**, initially 6 mm in this example.
   Set **Levels = 1** for a first FEM run and press **FINAL FEM**. The default backend
   is CPU CG. The final solver also accepts CPU direct, AMG, matrix-free and CUDA CG.
6. Use **VIEW = 4**, select each Case, and choose Field 0/2 for stress or 1 for
   displacement. A common positive legend maximum makes color ranges comparable.
   Deformation scale changes the display only. The mesh output and Bake are undeformed.
7. Inspect the final HTML report and Compare panel. Extraction changes the volume;
   its mass need not equal the optimization's density-weighted mass or the binary
   threshold mesh mass. The final FEM checks the actual tetrahedral volume.
8. For a mesh study, set **Levels = 3**, Reset, then Run. Sizes are h, 0.75h and
   0.5625h. Compare every case's compliance, maximum displacement and maximum stress.
   `stable_over_two_refinements` requires both successive changes to pass the
   relative tolerance (default 5%). `not_established` requires further investigation;
   completing three solves alone does not establish accuracy.

## Extraction and editing

Density is sampled at voxel centers. Optional Gaussian filtering precedes a marching
cubes isosurface. Exact protected voxel solids are restored with manifold boolean
operations, then the surface is clipped to the original active voxel envelope.
The result is a continuous triangle surface, not a NURBS reconstruction of the
original CAD. It can have flat Keep interfaces and local facets. This preserves
attachment material and makes its limitations traceable.

Disconnected material is reported, never silently deleted. Final FEM currently
requires one connected solid; enclosed cavities are supported by the mesher.
An extraction is labelled **NOT REANALYSED** even if the source design passed its limits.

To edit a part: Bake or import the surface into Rhino, modify a copy, and set the
**Optional edited closed mesh** parameter. Keep the source optimization connected.
Press EXTRACT again to validate the edited mesh and create a new geometry record.
Edits must preserve every original Keep voxel and stay inside the original voxel
envelope. Restore interfaces if rejected. Changes to the design envelope, loads or
material require a new baseline/design. Final FEM only accepts the recorded surface
and embedded physical inputs; geometry hashes and input signatures reject stale data.

## Support and load transfer

- Supports must cover complete original exposed voxel faces. Their directions are
  transferred to boundary nodes lying on those original face patches. Point/line-only
  supports are rejected by this first conforming-FEM implementation.
- Original nodal loads must still lie on the new boundary. A load is distributed
  barycentrically onto its containing surface triangle, preserving its point of
  application, force and moment. No force is silently moved to the nearest remaining
  piece when its interface is missing.
- Pressure/traction stays on the original selected planar face patches. Integration
  clips remeshed triangles against each original loaded patch and checks area,
  force and moment. It is not pressure on the new evolving exterior surface.
- Gravity is recomputed from full-material tetrahedral volume and actual material
  density, including force contributions at fixed nodes.

Keep the saved job folders in place. Report/Case Result reads the corresponding
case files. Each final FEM saves `mesh-N/final.msh`, `level-NN.json`, per-case JSON,
result JSON and an HTML report. Source STL and the final FEM volume mesh describe
different discretizations of the same intended boundary.

## Accuracy and limits

The element is a first-order **TET4**, with constant strain/stress per tetrahedron.
It can be too stiff in bending on coarse meshes; near-incompressible materials can
lock. Peaks near point loads, corners or ideal rigid restraints can remain singular
as the mesh is refined. Smooth colors or a converged linear solver do not remove
these effects. Use finite load patches and refinement studies where appropriate.

The mesher checks volume agreement (within 2%), mesh connectivity, nondegenerate
and oriented tetrahedra, quality, and restraint of all six rigid-body modes. Results
include free residual, force/moment balance and work/strain-energy agreement.
Elements with quality below 0.05 are flagged; below 0.0001 they are rejected.
The geometric mean-ratio quality is 1 for a regular tetrahedron and tends to 0
for a collapsed one. Passing limits on a mesh with poor elements or an unfinished
refinement study is not labelled final-shape verification.
Current safeguards: 250,000 tetrahedra, an estimated volume/h^3 budget of 40,000 at
every refinement, 300 seconds per meshing process. These are resource guards, not
validated universal accuracy envelopes. A larger mesh may still be rejected for
quality, interface transfer or linear convergence.

Stop interrupts the separate mesher process and iterative solves. Direct matrix
factorization and individual geometry operations may finish their current operation
before cancellation is handled. Reset clears the selected result. Changed inputs
hide old results until a new run completes.

## Native Rhino acceptance for this increment

Open the example, confirm all buttons are idle, run the five stages, and switch
VIEW 0 through 4. Check each Case/Field against its report. Verify that only the
selected stage is visible and that legend units and Max agree. Rotate the print
build direction, re-extract, and inspect the flags. Test Stop during meshing and FEM;
Reset after changing geometry. Bake the surface, Undo, and repeat for the final mesh.
Save/reopen without automatic calculations. SDK tests do not exercise these native UI actions.

## Numerical implementation references

- [scikit-image marching cubes](https://scikit-image.org/docs/stable/api/skimage.measure.html)
- [Manifold geometry library](https://manifoldcad.org/docs/html/classmanifold_1_1_manifold.html)
- [Gmsh manual and STL remeshing tutorial](https://gmsh.info/doc/texinfo/)
- [scikit-fem API](https://scikit-fem.readthedocs.io/en/stable/api.html), used for independent
  TET4 stiffness assembly and solution comparison in tests. Both implementations can
  use SciPy linear algebra; this is independent element assembly, not a comparison
  against an independently qualified commercial solver.

## Optional shelf CAD contract

The shelf example appends CAD specification, CAD loading summary and CAD chord tolerance
inputs to Final Geometry 3D. Existing generic definitions keep their old behavior.
With the validated contract, nominal shelf plates and clearance cylinders supersede their
sampled voxel boundaries. Added protected material remains preserved inside the nominal
envelope. Physical CAD top/front/lateral patches replace raster patches, normalize total
force, and report their moment difference from the raster source explicitly.
See [CAD interfaces](CAD_INTERFACES.md) for exact edit/provenance rules and meshing scope.
The generic voxel rules above do not describe this optional shelf-specific reconstruction.
