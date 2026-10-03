# SPDX-License-Identifier: GPL-3.0-or-later
"""Run from the TopOptLab Python environment; requires installed project source."""
import argparse,os,sys,json,copy
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--project-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=a.project_root.resolve()
if not (root/'tool/worker.py').is_file():p.error('--project-root must contain tool/worker.py')
out=a.output.resolve()
if out.exists():p.error('--output must be a new directory; existing results are never overwritten')
out.mkdir(parents=True);os.environ['TOPOPTLAB_ROOT']=str(root);sys.path.insert(0,str(root/'tool'))
from roof_model import request
from worker import run
results={}
for stage in ['fem','optimize','verify']:
 r=request(mode=stage)
 if stage=='verify':r['source_result']=results['optimize']
 results[stage]=run(r,out/stage)
 print(stage,results[stage]['engineering']['mass_kg'],results[stage]['engineering']['termination_reason'],flush=True)
for factor in [2,4]:
 req=request(mode='fem');oldny=req['domain']['ny'];newny=oldny*factor
 def remap(n):return n//(oldny+1)*factor*(newny+1)+n%(oldny+1)*factor
 req['domain'].update(nx=60*factor,ny=newny,cell=100/factor,solid=[],active=sorted((e//oldny*factor+dx)*newny+e%oldny*factor+dy for e in results['verify']['cell_ids'] for dx in range(factor) for dy in range(factor)))
 req['settings']['radius']=180/(100/factor)
 for s in req['supports']:s['nodes']=[remap(n) for n in s['nodes']]
 for case in req['load_cases']:
  for load in case['loads']:
   if 'nodes' in load:load['nodes']=[remap(n) for n in load['nodes']]
 result=run(req,out/('refinement_h'+str(100//factor)))
 assert abs(result['engineering']['mass_kg']-results['verify']['engineering']['mass_kg'])<1e-7
 print('fixed geometry h',100//factor,'SLS max u',result['engineering']['cases'][0]['max_displacement'],flush=True)
print('Completed:',out)
