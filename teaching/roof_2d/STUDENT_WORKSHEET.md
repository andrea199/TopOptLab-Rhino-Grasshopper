# Student worksheet — 2D roof rib

Group: __________  Students: __________  Date: __________

## Objective

Model the 6 m steel roof rib, check baseline FEM, optimize material placement,
reanalyze the thresholded shape, and justify a design choice.
Use the [case assumptions](README.md) and supplied GH file.

## Before running

1. Draw the left/right supports and their restrained displacement components.
2. Calculate the full plate mass and one SLS station force.
3. Calculate SLS support reactions including rib self-weight.
4. Explain FEM thickness, Stock thickness, rib spacing and Cell size.
5. Predict the main material paths and the effect of removing mass on uplift.

## Calculation

Open the supplied Rhino and Grasshopper files. Run baseline, optimization and
verification in order. Review each load case and save your reports.
Do not reuse an old result after changing the input model.

| Quantity | Full plate | Optimized density | Thresholded plate | Your variant |
| --- | --- | --- | --- | --- |
| Cell size / filter radius | | | | |
| Volume / Threshold | | | | |
| Mass [kg] | | | | |
| SLS maximum displacement [mm] | | | | |
| Left-snow ULS von Mises [MPa] | | Relaxed design stress | | |
| Uplift Ay, By [kN] | | | | |
| Iterations / termination reason | FEM | | Reanalysis | |
| Connectivity / retained attachments | | | | |

## Assigned experiment

- Group A: Volume 0.25 and 0.40; keep the other settings fixed.
- Group B: Threshold 0.35 and 0.50; rerun verification for each.
- Group C: Cell size 50 mm and Radius 3.6 cells, preserving the 180 mm physical
  filter; rerun all stages. Compare this new optimization with the separate
  supplied fixed-shape refinement study.

Change one variable at a time. Record rejection messages and their causes.

## Discussion and submission

Explain mass/displacement tradeoffs; the importance of self-weight in uplift;
reoptimization versus refinement of one fixed shape; the increasing stress peak;
and the evidence still missing before construction.

Submit your GH file, completed table, one figure with units/legend and one page
of conclusions. Record software version and report locations. Do not claim
code compliance from this lesson alone.
