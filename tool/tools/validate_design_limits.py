# SPDX-License-Identifier: GPL-3.0-or-later
"""Numerical reference for the default design-limit examples (not a Rhino UI test)."""
import argparse,copy,json,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from worker import run
from sample3d import cantilever
from scenarios import request

def fixture(dim,backend='cpu-cg',iterations=80):
    r=cantilever('fem') if dim==3 else request(3,'fem')
    r.update(dimension=dim,engineering=True,material={'preset':'steel'})
    if dim==3:
        loads=[r['loads'][0],dict(nodes=r['loads'][0]['nodes'],force=[0,100,0])]
    else:loads=r['loads']
    r['load_cases']=[dict(name='Case '+str(i+1),weight=1,loads=[load]) for i,load in enumerate(loads)]
    r['settings'].update(backend=backend,threads=4,volume=.6,iterations=iterations,radius=1.8,thickness=2,preserve_attachments=True,
                         objective_tolerance=.001,design_tolerance=.01,minimum_iterations=10,convergence_window=5)
    r['design_limits']=dict(max_displacement=.03 if dim==3 else .0002,max_stress_mpa=10,enforce=True)
    r['manufacturing']=dict(threshold=.4)
    return r

def main():
    p=argparse.ArgumentParser();p.add_argument('--backend',default='cpu-cg');p.add_argument('--iterations',type=int,default=80);p.add_argument('--baseline-only',action='store_true');args=p.parse_args()
    output=ROOT/'build'/('design-limits-reference-'+uuid.uuid4().hex);records=[]
    for dim in (2,3):
        r=fixture(dim,args.backend,args.iterations);folder=output/str(dim)
        baseline=run(r,folder/'baseline');record=dict(dimension=dim,cells=len(r['domain']['active']),baseline=baseline['engineering'])
        print(json.dumps(dict(dimension=dim,stage='baseline',cases=baseline['engineering']['cases'],folder=str(folder))),flush=True)
        if not args.baseline_only:
            r['mode']='optimize';optimized=run(r,folder/'optimization');record['optimization']=optimized['engineering']
            print(json.dumps(dict(dimension=dim,stage='optimization',reason=optimized['engineering']['termination_reason'],limits=optimized['engineering']['design_limits']['status'],optimizer=optimized['engineering']['constraint_optimizer'],seconds=optimized['engineering']['elapsed_seconds'])),flush=True)
            r.update(mode='verify',source_result=optimized)
            try:
                verified=run(r,folder/'verification');record['verification']=verified['engineering']
                print(json.dumps(dict(dimension=dim,stage='verification',limits=verified['engineering']['design_limits']['status'])),flush=True)
            except ValueError as exc:record['verification_error']=str(exc);print(str(exc),flush=True)
        records.append(record)
    (output/'summary.json').write_text(json.dumps(records,indent=2));print(output/'summary.json',flush=True)
if __name__=='__main__':main()
