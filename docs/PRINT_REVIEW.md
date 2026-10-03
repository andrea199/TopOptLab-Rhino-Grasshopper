# 3D printing geometry review

The first selected manufacturing process is **3D printing**. Version 0.4 adds a
geometric review of the final surface. The checks do not yet constrain the optimizer.

Connect **Print Review** to **Final Geometry 3D**, then press EXTRACT after changes.
Build is a world vector pointing upward from the print plate. Only its direction
matters. Try `(0,0,1)` and `(0,1,0)` to compare orientations; the physical model,
loads and FEM material remain unchanged. The review does not rotate the exported STL.
Rotate and position the part explicitly in Rhino or the slicer before printing.

**Angle** is maximum overhang measured from vertical, in degrees. The example's
45 degrees is an adjustable demonstration value, not a printer/material guarantee.
A vertical wall has zero overhang and a downward horizontal face has 90 degrees.
Faces on the lowest flat build-plane contact are excluded. Orange means the chosen
angle is exceeded; it does not mean support is necessarily reachable or removable.

**Wall** is a requested thickness in the model's length units. Zero disables this
limit. The example uses 2 mm for demonstration. Inward normal rays sample 500
area-weighted face locations. Red identifies a sampled thickness below the limit.
The reported minimum is only the minimum of these samples. Small local defects,
oblique thin features and unsampled regions can be missed. Red takes color priority
over orange when a face is flagged by both checks.

Report statuses:

| Status | Meaning |
|---|---|
| `not_requested` | Review disabled |
| `incomplete_samples` | One or more thickness rays failed; inspect the geometry |
| `flags_present` | Overhangs or sampled thin walls exceeded the selected settings |
| `no_flags_at_samples` | No failures at the tested faces/samples; no global guarantee |

Normal-ray thickness is neither a guaranteed minimum wall nor a medial-axis feature
size. The review does not generate support material, check a support-removal path,
find trapped powder/resin, or check toolpaths, shrinkage, build volume, temperatures
or process-specific tolerances. Steel and ABS presets remain isotropic reference
materials; they do not describe printed directional strength or layer bonding.

Use the flags to compare orientations, improve an edited mesh, and rerun Final FEM
on the accepted geometry. Process-specific enforcement and anisotropic material
models require a defined printer/process, orientation-dependent test data and
manufacturing qualification. Supply the intended FDM/SLA/metal process and a real
part when defining that next increment.
