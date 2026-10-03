# SPDX-License-Identifier: GPL-3.0-or-later
"""Write concise evidence from completed, saved shelf-bracket calculations."""
import argparse,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("run",type=Path);a=p.parse_args()
ROOT=Path(__file__).resolve().parents[2]
read=lambda name:json.loads((a.run/name/"result.json").read_text())
baseline,design,verify,surface,final=[read(n) for n in ["fem","optimize","verify","surface","final-fem"]]
summary={"example":"engineering_shelf_bracket_3d","date":"2026-09-21","source_request_sha256":hashlib.sha256((a.run/"optimize/project.json").read_bytes()).hexdigest(),"defaults":{"length_mm":250,"height_mm":150,"width_mm":25,"payload_kg":4,"shelf_share_kg":.5,"cell_mm":5,"volume_fraction":.35,"threshold":.35,"iterations":60,"backend":"cpu-direct"},"stages":{}}
for name,d in zip(["baseline","density_design","voxel_verification","final_fem"],[baseline,design,verify,final]):
    e=d["engineering"]
    summary["stages"][name]={k:e.get(k) for k in ["termination_reason","mass_kg","elapsed_seconds","design_limits","accuracy","mesh_quality_status"]}
    summary["stages"][name]["cases"]=[{k:c.get(k) for k in ["name","max_displacement","max_von_mises","max_von_mises_relaxed","applied_force","reaction_force","residual","equilibrium"]} for c in e["cases"]]
summary["surface"]={**surface["geometry"],"mass_kg":surface["engineering"]["mass_kg"]}
summary["scope"]={"native_dataflow":"four size/grid/translation variants; invalid inputs and unresolved hole rejected","regressions":"207 passed, then 54 affected tests passed after calibrated defaults","interactive_rhino_acceptance":False,"printed_part_qualification":False,"mesh_study":"one final mesh; convergence not established"}
(ROOT/"docs/shelf-bracket-reference.json").write_text(json.dumps(summary,indent=2),encoding="utf8")
lines=["# Shelf bracket validation — 2026-09-21","","## Delivered default workflow","",
"Actual 250 × 150 × 25 mm model, 7,328 active 5 mm cells, four independent cases; 4 kg payload per bracket, assumed 0.5 kg shelf share, ABS reference, self-weight. CPU direct, 35% density-design volume, threshold 0.35, 60 MMA updates and 1 mm displacement target.","",
"| Stage | Mass, kg | Maximum displacement over four cases, mm | Termination |","|---|---:|---:|---|"]
for name,key in [("Full-solid baseline","baseline"),("Density design","density_design"),("Thresholded voxel shape","voxel_verification"),("Conforming TET4 FEM","final_fem")]:
    e=summary["stages"][key];lines.append(f'| {name} | {e["mass_kg"]:.6f} | {max(c["max_displacement"] for c in e["cases"]):.6f} | {e["termination_reason"]} |')
lines+=["","The optimiser reached its iteration limit; it is not labelled converged. The density-design and binary/surface masses differ. Stress is not constrained in this example; printed-material allowable is unknown.","",
"## Numerical and native checks","","- 207 regression tests passed (one existing upstream small-Jacobian warning). After calibration, all 54 affected geometry/archive/load tests passed again.",
"- Native RhinoCore/Grasshopper dataflow passed for default, resized, translated and finer-grid variants. Generated fixtures match analytical cylinders, attachment plates and force/moment integration.",
"- Missing/invalid units, zero payload, negative shelf share, inconsistent domain/specification, invalid patches, invalid geometry and an unresolved hole are rejected.",
"- GH and GHX passed native SDK readback: document properties and all 116 objects.",
"- Forces remain mass-normalized across sizes and grids. Opposite eccentric cases are evaluated independently.",
"- Baseline CPU-CG, CUDA-CG and CPU-direct displacements agreed at the shown precision. These runs are not controlled performance benchmarks.","",
"## Findings that changed the delivered example","",
"- Threshold 0.40 on the 60-step density design produced 0.18915 kg and approximately 37.45 mm maximum displacement, exceeding the chosen 1 mm limit. It is not the delivered default.",
"- Threshold 0.30 added disconnected voxel material and was rejected. Lower thresholds are not automatically better.",
"- Threshold 0.35 passed voxel reanalysis and is the delivered value; changing it requires another verification.",
"- CUDA-CG did not satisfy the strict residual criterion on the discarded 0.40 final surface. It was not silently accepted. CPU direct is selected explicitly for the delivered modest grid.",
"- A CPU-CG optimisation trial was intentionally cancelled; no converged result is claimed for that trial.","",
"## Remaining acceptance and qualification","",
f'- Final FEM mesh quality: **{final["engineering"]["mesh_quality_status"]}**. Accuracy study: **{final["engineering"]["accuracy"]["status"]}**. One mesh does not establish convergence.',
"- The extracted surface retains original protected voxels, but its holes remain approximations of nominal CAD geometry.",
"- Test native Rhino preview, selection, Run/Stop/Reset, save/reopen and Bake/Undo interactively. SDK/headless checks do not exercise these UI operations.",
"- Rigid wall pads do not validate bolts, wall anchors, contact, printed layer strength or creep. This is not a certified 4 kg load rating.","",
"Machine-readable evidence: **shelf-bracket-reference.json**. Full job files remain in the local run folder. Reproduce with tool/tools/validate_shelf_bracket.py --final-fem.",""]
(ROOT/"docs/SHELF_BRACKET_VALIDATION.md").write_text("\n".join(lines),encoding="utf8")
print(ROOT/"docs/SHELF_BRACKET_VALIDATION.md")
