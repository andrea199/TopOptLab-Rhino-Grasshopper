# Engineering workflow guide

1. Open an engineering_workflow example. Geometry, supports and two independent cases
   are prewired; resize and translate with the sliders on the left.
2. Material: 0 steel, 1 ABS. Default units mm/N. Coordinate units are declared explicitly,
   not automatically converted from the Rhino document. Read Material Info. Steel yield
   screening requires declared stock thickness in the documented range; ABS nu is assumed.
3. Backend: 0 direct, 1 CPU CG, 2 CPU AMG, 3 matrix-free CPU, 4 CUDA CG. Start with CPU CG.
   Start with a modest grid. Domain Resources reports larger-grid admission; Cell size,
   selected Voxel limit and available memory are separate controls. See RESOLUTION_VALIDATION.md.
4. Run BASELINE FEM. Open the HTML path in Report. Use REVIEW Stage=0 and select each completed Case.
   The report and case-01.json/case-02.json contain the separate responses. Weighted
   compliance is not the response to simultaneous summed forces.
5. Set optional Design Limits, then run OPTIMIZATION. Use REVIEW Stage=1.
   Inspect feasibility separately from converged / iteration_limit / optimizer_failed.
6. Run FINAL VERIFICATION after optimization completes; set REVIEW Stage=2. Remaining cells are solved
   at full stiffness. Disconnected material or removed selected nodes are rejected.
   Preserve support/load interfaces using Keep and inspect the resulting shape.
7. Stop before editing. Reset and Run after changes. Changed geometry, material or
   loads cannot reuse an old optimization result for verification.
8. Use FEM Results for 2D baseline/verification, Results for 2D optimization, and
   Results 3D for all 3D stages. Inspect every load case; preview scaling is not displacement.

## Manufacturing

Process adds notes; Symmetry and 3D Extrusion constrain density. Symmetry requires
matching domain/Keep. Extrusion requires complete columns and consistent Keep along
its axis. Loads need not be symmetric. Minimum feature is a voxel erosion diagnostic,
not a proven wall-thickness, tool-access or printability constraint.

## Saved data

Each job saves request/project JSON, result JSON, history and report.html. Every engineering stage also
saves each case response, including optimization. Project JSON can be rerun through the worker CLI with a
fresh output directory. Importing it into a new Grasshopper document is not implemented.

## Native Rhino acceptance

For each example: open; inspect geometry; resize/move; check selected nodes;
run/stop/reset; save/reopen; confirm no automatic launch; inspect density, stress,
deformation, cuts and threshold; Bake and Undo. Test missing inputs and invalid
constraints. Run all three engineering stages and open reports. Record Rhino version,
backend and job folder for failures.

## Distributed loads and self-weight

See [the loading guide](DISTRIBUTED_LOADS.md) and the two engineering_distributed_loads examples.
Surface Load and Gravity connect through Load Case to Engineering. Keep attachments
preserves support/point-load interfaces. Positive pressure acts inward.

## Design limits and clearer result review

See [Design Limits](DESIGN_LIMITS.md) for the 0.3 workflow, precise constraint
meanings, stress convention and status explanations. Start with the two
engineering_design_limits examples. Use one visible stage, a selected case,
Field=0/1/2 and the viewport legend. Use common positive Max for comparable color
scales. The Compare panels evaluate all cases against a matching baseline.

Native acceptance for this increment: verify Stage switches remove the previous
result preview, each Case agrees with its report, Field and units agree with the
legend, Scale changes only the display, and fixed Max remains fixed across stages.
Try a deliberately impossible limit and confirm the run is not labelled converged.
Restore the example defaults afterwards. Save/reopen with idle buttons; test Stop
and Reset during MMA and verify that a previous result is hidden after input edits.

## Final surface, conforming FEM and 3D printing

Open `engineering_final_geometry_3d.gh` for the five-stage workflow. After the
optimization, EXTRACT produces a closed triangle surface and print review. FINAL FEM
creates a new tetrahedral mesh and reapplies the recorded supports and loads.
Use VIEW 3 for the surface and 4 for final FEM. Read [Final Geometry](FINAL_GEOMETRY.md)
for every input, editing/export, mesh studies and the native acceptance sequence.
Read [3D Printing Review](PRINT_REVIEW.md) before interpreting the colored flags.

## Physical filter and memory settings

Physical filter radius is in the declared model length units; zero preserves legacy
Radius-in-cells behavior. The 2D filter retains its existing 1..min(10,nx,ny)-cell
range; the 3D FFT filter accepts 1..64 cells. FEM does not apply a density filter.
RAM budget GiB is currently 3D-only: zero uses automatic free-memory budgeting;
leave zero for 2D. Positive 2D values are rejected rather than silently ignored.
An explicit 3D budget can lower admission but cannot override available memory.
