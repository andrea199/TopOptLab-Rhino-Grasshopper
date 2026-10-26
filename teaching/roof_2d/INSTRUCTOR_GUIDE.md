# Instructor guide — 2D roof rib

Use this English teaching plan alongside the
[HTML roof-rib lesson](../../docs/manual/learnings/07-roof-rib/index.html).
The detailed Italian teaching notes remain in the
[original guide](output/GUIDA_DOCENTE.md). PowerPoint files are maintained
separately by the instructor and are not part of this distribution.

## Prepare the classroom

Install the full project on each workstation and run the supplied GH model once.
Check three-stage execution, selected load cases, legends, report paths, Bake and
Undo in the actual Rhino installation. Numerical/SDK checks do not replace this
interactive acceptance. Keep the supplied reference files for comparison and
have students save copies rather than overwrite the reference model.

## Three-hour sequence

| Minutes | Activity | Checkpoint |
| --- | --- | --- |
| 0–20 | Explain the design domain, dimensions and plane-stress assumption | Students distinguish plate thickness from cell size and rib spacing |
| 20–45 | Derive loads, supports and five independent cases | Manual SLS forces and reactions agree |
| 45–70 | Run baseline FEM and read all cases | Units, directions, reactions and displacement scale are understood |
| 70–100 | Run optimization with Volume 0.30 | Students identify Keep, filter and termination reason |
| 100–125 | Threshold 0.40 and final voxel verification | Students explain why a new full-material solve is necessary |
| 125–155 | Group variations and fixed-shape refinement | One variable at a time; distinguish shape change from discretization |
| 155–180 | Compare evidence and discuss real-design gaps | Each group submits a justified conclusion with limitations |

## Board calculations

Use mm, N and MPa for solver input; convert kN/m² actions explicitly.

- One station represents 3 m². SLS vertical force is
  -(0.15 + 0.60 + 0.80) × 3 = **-4.65 kN**.
- Full plate self-weight is 593.46 × 9.80665 = **5.8198545 kN**.
- SLS reactions are (6 × 4.65 + 5.8198545)/2 =
  **16.859927 kN per support**.
- Uniform ULS snow station force is
  -3 × (1.3 × 0.15 + 1.5 × 0.60 + 1.5 × 0.80) = **-6.885 kN**.
  The reduced-snow side uses **-5.085 kN** per station.
- Uplift station force has Fy = 3 × (1.5 - 0.15 - 0.8 × 0.60) =
  **+2.61 kN**, with Fx = -2.25 kN on the left and +2.25 kN on the right.
- The lighter thresholded plate requires greater downward hold-down reactions:
  approximately **-6.850786 kN per support** in the uplift case.

Coefficients above reproduce this teaching model; they do not establish which
combinations govern a real site. The original [sources/method](output/FONTI_E_METODO.md)
records the modeling choices.

## Questions and expected reasoning

**Why do supports need the load direction checked?**
A force on an already restrained degree of freedom does not represent the intended
deforming load path. Inspect selected nodes rather than only the curve picture.

**Why does optimized mass differ from thresholded mass?**
The optimizer stores continuous densities. Thresholding creates a binary material
choice with different stiffness, mass and self-weight.

**Why solve all cases?**
Alternative loading can reverse reactions or change the governing response.
A weighted compliance objective does not replace case-by-case verification.

**Why does stress rise as h decreases?**
The same stepped shape still has point loads, point supports and sharp corners.
Refinement can reveal localized peaks; the supplied sequence does not establish
converged peak stress. Discuss finite loading/support patches and local models.

**What is missing for a roof?**
Out-of-plane stability, connection and anchorage design, realistic details,
complete site actions/combinations, code checks and independent verification.

## Assessment (20 points)

- Assumptions, units and manual equilibrium: 5.
- Correct three-stage execution and evidence from all relevant cases: 5.
- Controlled parameter study and refinement interpretation: 5.
- Clear conclusions, limitations and reproducible deliverables: 5.

Do not grade a smooth or visually attractive topology as proof of accuracy.
A rejected disconnected shape is a valid observation if the cause is explained.
