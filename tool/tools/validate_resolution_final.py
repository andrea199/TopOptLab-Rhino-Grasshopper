# SPDX-License-Identifier: GPL-3.0-or-later
"""Reanalyse/extract a completed shelf design without rerunning optimization."""
import argparse,copy,json,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engineering import run_engineering
from final_workflow import run_final
p=argparse.ArgumentParser();p.add_argument('--design-dir',type=Path,required=True);p.add_argument('--summary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--backend',default='cuda-cg');p.add_argument('--threshold',type=float);p.add_argument('--mesh-size',type=float,default=4);p.add_argument('--skip-verify',action='store_true');p.add_argument('--skip-fem',action='store_true');a=p.parse_args()
source=json.loads((a.design_dir/'result.json').read_text());r=json.loads((a.design_dir/'project.json').read_text())
if source.get('status')!='completed' or r.get('mode')!='optimize':raise ValueError('Use a completed optimization job')
if a.threshold is not None:r['manufacturing']['threshold']=a.threshold
out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);records={}
def stage(name,request,fn):
    started=time.perf_counter()
    try:
        data=fn(request,out/name)
        e=data.get('engineering',{})
        records[name]=dict(status=data.get('status'),seconds=time.perf_counter()-started,job=str(out/name),geometry=data.get('geometry'),engineering={k:e.get(k) for k in ['termination_reason','mass_kg','cases','design_limits','accuracy','mesh_quality_status','support_transfer']})
        print(name,records[name]['status'],records[name]['seconds'],flush=True)
        return data
    except Exception as exc:
        records[name]=dict(status='error',seconds=time.perf_counter()-started,error=str(exc),job=str(out/name));(out/(name+'-error.txt')).write_text(traceback.format_exc());print(name,'ERROR',str(exc),flush=True)
    finally:(out/'validation-summary.json').write_text(json.dumps(records,indent=2))
if not a.skip_verify:
    request=copy.deepcopy(r);request.update(mode='verify',source_result=source,job_id='fine-voxel-verify');request['settings']['backend']=a.backend
    stage('verify',request,run_engineering)
cad=dict(specification=r['example_geometry'],loading=json.loads(a.summary.read_text()),chord_tolerance_mm=.05,envelope_snap_mm=0,web_cleanup_mm=.01)
request=dict(job_id='fine-cad-surface',action='extract',source_result=source,settings=dict(threshold=r['manufacturing']['threshold'],smoothing=.5,cad_interfaces=cad),manufacturing_review=dict(enabled=True,build_direction=[0,1,0],minimum_wall=2,overhang_angle=45,samples=500))
surface=stage('surface',request,run_final)
if surface and not a.skip_fem:
    request=dict(job_id='fine-cad-fem',action='analyze',source_result=surface,settings=dict(backend=a.backend,threads=4,mesh_size=a.mesh_size,levels=1,accuracy_tolerance=.05),design_limits=r['design_limits'])
    stage('final-fem',request,run_final)
print(out,flush=True)
if any(v['status']!='completed' for v in records.values()):raise SystemExit(1)
