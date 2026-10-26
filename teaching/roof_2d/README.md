# 2D roof rib: engineering lab

**Duration:** 3 hours. **Level:** engineering students familiar with statics and
linear elasticity. **Software:** Rhino 8, Grasshopper, TopOptLab 0.4.0-dev.
CPU direct is sufficient; CUDA is not needed.

This is a plane-stress model of a constant-thickness steel plate shaped as a roof
rib. The cover illustration shows a conceptual roof structure, not the calculated
topology. Climatic actions are assumed teaching inputs, not site-specific design data.

## Files and first run

1. [Install the complete software](../../docs/INSTALLATION.md) before class.
2. Open the [HTML lesson and instructions](../../docs/manual/learnings/07-roof-rib/index.html).
   Instructor PowerPoint files are distributed separately and are not included here.
3. Open [roof_geometry_mm.3dm](output/case/roof_geometry_mm.3dm) in Rhino.
   Use millimetres, Top view and Zoom Extents.
4. Open [roof_2d_classroom.gh](output/case/roof_2d_classroom.gh) in Grasshopper.
   Geometry is internalized; external Rhino selection is not needed.
5. Run **01 BASELINE FEM → 02 OPTIMIZATION → 03 FINAL VERIFICATION**, waiting for
   each stage to complete. Keep defaults for the first comparison.
6. Review Stage 0/1/2 and Case 1–5. Field 0 is the default, 1 displacement, 2 stress.
7. Compare reports with [teaching_values.json](output/reference/teaching_values.json).

Use the [instructor guide](INSTRUCTOR_GUIDE.md) and
[student worksheet](STUDENT_WORKSHEET.md). The original Italian
[lesson guide](output/GUIDA_DOCENTE.md) and [worksheet](output/ESERCITAZIONE_STUDENTI.md)
remain available.

## Reference assumptions

| Quantity | Value / meaning |
| --- | --- |
| Span | 6,000 mm |
| Heel height / additional rise | 300 mm / 1,500 mm |
| Tributary rib spacing | 3,000 mm |
| FEM thickness | 12 mm |
| Material | Steel reference, E = 210,000 MPa, nu = 0.30, density = 7,850 kg/m³ |
| Supports | Left: X and Y fixed; right: Y fixed, X free |
| Starting discretization | h = 100 mm, 630 active cells, 44 Keep cells |
| Filter | 180 mm physical radius, entered as Radius = 180/h cells |
| Material budget / threshold | 0.30 / 0.40 |
| Roof station positions X | 500, 1,500, 2,500, 3,500, 4,500, 5,500 mm |

Six station loads represent 3 m² of horizontal tributary area each.
G1 = 0.15 and G2 = 0.60 kN/m²; assumed ground snow = 1.00 kN/m².
The model uses uniform roof snow of 0.80 kN/m² and 0.40 kN/m² on the reduced side
of asymmetric cases. Net normal wind suction is assumed as 1.00 kN/m².
Rib self-weight is added separately.

Five independent cases: SLS uniform snow, ULS uniform snow, ULS left snow,
ULS right snow and ULS wind uplift. Objective weights are all one; they are
not load factors. Supports are bilateral, so they can transmit uplift tension
in this idealized model.

These are the existing lesson assumptions, not a review of current building
regulations. See the original [sources and method](output/FONTI_E_METODO.md).

## Reference results

| Metric | Full plate | Optimized density | Thresholded plate |
| --- | ---: | ---: | ---: |
| Mass [kg] | 593.460 | 178.038 | 199.704 |
| SLS maximum displacement [mm] | 0.446785 | 2.455073 | 1.229039 |
| Left-snow ULS maximum von Mises [MPa] | 39.794733 | 74.499572 (relaxed design stress) | 57.027307 |
| Uplift vertical reaction per support [kN] | -4.920073 | See per-case data | -6.850786 |

The reference optimization stopped as converged after 36 iterations.
Refining the **same thresholded geometry** from 100 to 50 to 25 mm gives SLS
maximum displacements 1.2290, 1.4521 and 1.5787 mm; peak left-snow stress grows
57.03 → 86.64 → 141.16 MPa. The stress peak has not converged.

This lab does not verify out-of-plane buckling, connections, anchorages, contact,
fatigue or structural-code compliance. Point loads/supports and sharp corners
need further physical modeling before a real application.

## Reproduce the numerical lesson

From the repository root after installation:

```powershell
.\.venv\Scripts\python.exe teaching/roof_2d/output/source/reproduce.py --project-root . --output tool/build/roof-course-reproduction
```

The output directory must be new. This runs all three stages and fixed-shape
50/25 mm refinement. Existing reference results are never overwritten.
The [reference reports](output/reference/fem/report.html) are downloadable HTML;
GitHub shows their source, so open them locally in a browser.

Course checksums are recorded in [MANIFEST_SHA256.json](output/MANIFEST_SHA256.json).
During repository preparation only machine-specific path metadata in reference
JSON/HTML was made relative; numeric values and figures were preserved.
PowerPoint files were subsequently removed from the GitHub distribution on
26 October 2026; the current manifest records the remaining course assets.
The original local export was backed up outside tracked files and the course
manifest was regenerated. Historical job/NPZ paths describe the originating run;
use the reproduction command for a fresh complete job folder.
