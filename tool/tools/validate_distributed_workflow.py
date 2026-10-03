"""Run the distributed-load examples numerically, independently of Rhino UI."""
import argparse,copy,json,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from test_distributed_loads import rectangle
from sample3d import cantilever
from worker import run

def main():
    p=argparse.ArgumentParser();p.add_argument('--backend',default='cpu-cg');p.add_argument('--iterations',type=int,default=40);args=p.parse_args()
    output=ROOT/'build'/('distributed-reference-'+uuid.uuid4().hex);records=[]
    for dim in (2,3):
        if dim==2:
            r=rectangle(2,scale=6);r['domain']['cell']=.25
        else:
            r=cantilever('fem');r.update(engineering=True,material={'preset':'steel'})
        d=r['domain'];axis=1 if dim==2 else 2
        faces=[dict(cell=e,axis=axis,side=1) for e in d['active'] if (e%d['ny']==0 if dim==2 else e//(d['nx']*d['ny'])==d['nz']-1)]
        g=dict(kind='gravity',acceleration=[0,-9.80665] if dim==2 else [0,0,-9.80665])
        r.update(dimension=dim,mode='fem',load_cases=[dict(name='Surface load + self-weight',weight=1,loads=[dict(kind='pressure',pressure=.1,faces=faces),g]),dict(name='Self-weight only',weight=1,loads=[g])])
        r['material']['poisson']=.3;r['settings'].update(backend=args.backend,volume=.45 if dim==2 else .5,iterations=args.iterations,radius=1.8,thickness=2,preserve_attachments=True)
        record={'dimension':dim,'cells':len(d['active']),'backend':args.backend};folder=output/str(dim)
        baseline=run(r,folder/'baseline');r['mode']='optimize';optimized=run(r,folder/'optimization')
        record.update(baseline_compliance=baseline['metrics']['compliance'],optimization=optimized['engineering'],history=optimized['history'])
        r.update(mode='verify',source_result=optimized,manufacturing={'threshold':.5})
        try:
            verified=run(r,folder/'verification');record['verification']=verified['engineering'];record['verified_compliance']=verified['metrics']['compliance']
        except ValueError as exc:record['verification_error']=str(exc)
        records.append(record);print(json.dumps(dict(dimension=dim,termination=record['optimization']['termination_reason'],verification=record.get('verification_error','completed'),seconds=record['optimization']['elapsed_seconds'],folder=str(folder))),flush=True)
    (output/'summary.json').write_text(json.dumps(records,indent=2));print(output/'summary.json')
if __name__=='__main__':main()
