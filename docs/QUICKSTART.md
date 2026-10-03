# First calculation in Grasshopper

Install the [complete project](INSTALLATION.md) first. For a first lesson use
[engineering_workflow_2d.gh](../tool/examples/engineering_workflow_2d.gh).

1. Open Rhino 8 and run `Grasshopper`. Open the example through File → Open.
2. The example already contains its geometry and connections. Keep the default
   dimensions, position, supports and loads for the first run.
3. Inspect Domain, Material and Units. The model units are declared explicitly:
   do not assume that changing the Rhino document units converts the inputs.
4. Use a CPU backend initially. Read selected support/load nodes in the preview.
   Supports restrain displacement components; loads specify forces in the model axes.
5. Press **BASELINE FEM / Run** and wait for completion. Read the status and Report.
   This solves the starting solid with material, supports **and** loads already applied.
6. Press **OPTIMIZATION / Run**. Volume is the material budget. Read the termination
   reason: an iteration limit is different from convergence.
7. Choose Threshold and run **FINAL VERIFICATION**. This solves the retained
   full-material cells. Changing threshold changes the part and requires another solve.
8. In Review, Stage 0/1/2 selects baseline/design/verification; Case selects a saved
   independent load case. Field selects the displayed response. Review does not run FEM.
9. Open the HTML report path from the component. Compare mass, displacement, stress,
   reactions, feasibility and all load cases. Deformation scale only magnifies the view.
10. Save your own copy of the GH file. Stop before edits; Reset and Run after changing
    the geometry, material or loading. Keep the whole calculation folder for traceability.

## Build your own small example

Start from a copy of a working example and change one item at a time.

- **Domain**: boundary geometry, holes/voids, preserved material (Keep), cell size.
- **Support**: connect Domain to D and a point/curve selection to G; set the restrained axes.
- **Load**: connect Domain to D, a point/curve selection to G, and a vector to F.
  For a downward in-plane force, use Vector XYZ with X=0, Y negative and Z=0.
- **Load Case**: combine simultaneous forces. Separate cases represent alternative
  scenarios; do not add their responses together.
- **Material**: use declared properties/units and read the preset assumptions.
- **Engineering stages**: calculate the solid, optimize, then recalculate the selected shape.

A text panel containing coordinates does not replace a Rhino point or curve.
The message “A force acts in a constrained direction” means a load overlaps a
restrained degree of freedom: inspect the geometry/nodes before moving the load
or changing the support.

## Understand the square cells

Density is stored per finite element; a coarse grid has visible cells.
Smaller Cell size increases the model size sharply in 3D. A smooth-looking
surface does not prove more accurate stresses. Keep the physical filter radius
consistent and compare successive analyses; see [resolution](RESOLUTION_VALIDATION.md).

The advanced [final surface example](../tool/examples/engineering_final_geometry_3d.gh)
adds continuous surface extraction and a new tetrahedral FEM. That is a separate
step from voxel verification. The fine shelf candidate currently has an open
tetrahedral meshing issue.

For Bake, use the result component's Bake control after selecting the intended
result. Check the created Rhino objects; Rhino Undo should remove that bake.
Record native acceptance on your machine using the [user guide](USER_GUIDE.md).

Next: choose a model from the [gallery](EXAMPLES.md) or start the [roof course](../teaching/README.md).
