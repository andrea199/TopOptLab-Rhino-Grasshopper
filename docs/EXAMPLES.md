# Example gallery

All 20 models below include a binary **.gh** file and a matching readable **.ghx**
archive in [tool/examples](../tool/examples). Open one format, not both copies.
Save your experiments under a different name. Geometry is already supplied and
dimensions/position can be adjusted with sliders.

## Start with a small model

| Study | Baseline FEM | Topology optimization | What to observe |
| --- | --- | --- | --- |
| 2D cantilever | [FEM](../tool/examples/fem_cantilever.gh) | [Optimize](../tool/examples/opt_cantilever.gh) | Material paths between load and fixed edge |
| 2D simply supported beam | [FEM](../tool/examples/fem_simply_supported_beam.gh) | [Optimize](../tool/examples/opt_simply_supported_beam.gh) | Pin/roller supports and symmetric loading |
| 2D plate with two holes | [FEM](../tool/examples/fem_plate_two_holes.gh) | [Optimize](../tool/examples/opt_plate_two_holes.gh) | Load paths around forbidden regions |
| 2D cantilever with two loads | [FEM](../tool/examples/fem_cantilever_two_loads.gh) | [Optimize](../tool/examples/opt_cantilever_two_loads.gh) | Two simultaneous forces |
| 2D plate with one hole | [FEM](../tool/examples/fem_plate_with_hole.gh) | [Original optimization example](../tool/examples/plate_with_hole.gh) | Domain, hole and retained attachments |
| 3D cantilever | [FEM](../tool/examples/fem_cantilever_3d.gh) | [Optimize](../tool/examples/opt_cantilever_3d.gh) | Solid elements, depth and voxel cost |

These component-level examples teach geometry, supports and vector forces.
For explicit materials, units and alternative load cases, continue with the
engineering models.

## Engineering workflow

| Example | Purpose |
| --- | --- |
| [Workflow 2D](../tool/examples/engineering_workflow_2d.gh) | First three-stage workflow: baseline, optimization, voxel verification |
| [Workflow 3D](../tool/examples/engineering_workflow_3d.gh) | Same process with a solid domain |
| [Distributed loads 2D](../tool/examples/engineering_distributed_loads_2d.gh) | Boundary loading and self-weight |
| [Distributed loads 3D](../tool/examples/engineering_distributed_loads_3d.gh) | Surface traction/pressure and gravity |
| [Design limits 2D](../tool/examples/engineering_design_limits_2d.gh) | Displacement/stress constraints and feasibility |
| [Design limits 3D](../tool/examples/engineering_design_limits_3d.gh) | Constrained solid optimization |
| [Final geometry 3D](../tool/examples/engineering_final_geometry_3d.gh) | Continuous surface, print review and new tetrahedral FEM |
| [Shelf bracket 3D](../tool/examples/engineering_shelf_bracket_3d.gh) | 250 mm bracket, holes/clearances, preserved plates and four independent payload cases |

The shelf starts with **2.5 mm cells and CUDA selected**. Without the optional
CUDA installation, select CPU AMG (Backend 2) explicitly before running. It is
more demanding than the introductory examples. The included
[preliminary STL](../tool/examples/shelf_bracket_25mm_candidate_mm.stl) uses mm;
its [provenance](../tool/examples/shelf_bracket_25mm_candidate_mm.json) records
the still-incomplete final-surface FEM. Read the [shelf guide](SHELF_BRACKET.md).

## Engineering class

The separate [roof rib course](../teaching/roof_2d/README.md) adds a 21st GH/GHX
document, Rhino geometry, a 40-slide deck, worksheets and five-case reference
calculations. Use this for a complete lesson rather than a component demonstration.

Before changing a model, inspect its starting values. Keep a physical filter
radius constant when comparing cell sizes. Different thresholds and reconstructed
surfaces create different parts and require reanalysis. See [Quick start](QUICKSTART.md).
