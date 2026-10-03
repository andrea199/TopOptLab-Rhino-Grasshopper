# SPDX-License-Identifier: GPL-3.0-or-later
"""Reproduce the actual shelf example; keep generated data in a fresh job folder."""
import argparse,copy,json,sys,uuid,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engineering import run_engineering
from final_workflow import run_final
p=argparse.ArgumentParser();p.add_argument("--backend",default="cpu-amg");p.add_argument("--request",type=Path,default=ROOT/"build/resolution-probe/variant-1.json");p.add_argument("--summary",type=Path,default=ROOT/"build/resolution-probe/summary-1.json");p.add_argument("--iterations",type=int);p.add_argument("--final-fem",action="store_true");p.add_argument("--output",type=Path);a=p.parse_args()
out=a.output or ROOT/"build"/"shelf-bracket-runs"/uuid.uuid4().hex;out.mkdir(parents=True,exist_ok=False)
r=json.loads(a.request.read_text());r["settings"]["backend"]=a.backend
if a.iterations:r["settings"]["iterations"]=a.iterations
records={}
def save_records():
    (out/"validation-summary.json").write_text(json.dumps(records,indent=2))
for mode in ["fem","optimize","verify"]:
    request=copy.deepcopy(r);request.update(mode=mode,job_id="shelf-"+mode)
    if mode=="verify":request["source_result"]=design
    result=run_engineering(request,out/mode)
    if result.get("status")!="completed":raise RuntimeError(result.get("message",result["status"]))
    e=result["engineering"];records[mode]={k:e.get(k) for k in ["termination_reason","mass_kg","cases","design_limits","elapsed_seconds","constraint_optimizer"]}
    save_records()
    if mode=="optimize":design=result
    print(mode,e["termination_reason"],"mass kg",e["mass_kg"],"max U",max(c["max_displacement"] for c in e["cases"]),flush=True)
request=dict(job_id="shelf-surface",action="extract",source_result=design,settings=dict(threshold=r["manufacturing"]["threshold"],smoothing=.5,cad_interfaces=dict(specification=r["example_geometry"],loading=json.loads(a.summary.read_text()),chord_tolerance_mm=.05)),manufacturing_review=dict(enabled=True,build_direction=[0,1,0],minimum_wall=2,overhang_angle=45,samples=500))
surface=run_final(request,out/"surface");records["surface"]=surface["geometry"];save_records()
print("surface",surface["geometry"],flush=True)
if a.final_fem:
    request=dict(job_id="shelf-final-fem",action="analyze",source_result=surface,settings=dict(backend=a.backend,threads=4,mesh_size=4,levels=1,accuracy_tolerance=.05),design_limits=r["design_limits"])
    final=run_final(request,out/"final-fem");e=final["engineering"];records["final_fem"]={k:e.get(k) for k in ["termination_reason","mass_kg","cases","design_limits","elapsed_seconds","accuracy","mesh_quality_status"]}
    print("final FEM",e["mesh_quality_status"],"max U",max(c["max_displacement"] for c in e["cases"]),flush=True)
(out/"validation-summary.json").write_text(json.dumps(records,indent=2))
print(out,flush=True)
