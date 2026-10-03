"""Run each benchmark in its own process and record numerical accuracy and peak RSS."""
import argparse,json,os,subprocess,sys,time,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def single(n,backend,threads):
    import fem_backends,psutil,numpy as np
    from worker3d import Model3D
    from sample3d import cantilever
    proc=psutil.Process();peak=[proc.memory_info().rss];done=threading.Event()
    def sample():
        while not done.wait(.02):peak[0]=max(peak[0],proc.memory_info().rss)
    t=threading.Thread(target=sample,daemon=True);t.start();start=time.perf_counter()
    r=cantilever('fem',n,n//2,n//4);r['settings'].update(backend=backend,threads=threads)
    try:
        m=Model3D(r);res=m.solve(np.ones(m.n));elapsed=time.perf_counter()-start
        return dict(voxels=m.n,dofs=m.ndof,backend=backend,threads=threads,seconds=elapsed,peak_rss_mb=peak[0]/1024**2,
                    compliance=res['compliance'],residual=res['residual'],equilibrium=res['balance'],performance=res['performance'])
    finally:done.set();t.join()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--single',nargs=3);p.add_argument('--output',default=str(ROOT/'build/engineering-benchmarks.json'));a=p.parse_args()
    if a.single:print(json.dumps(single(int(a.single[0]),a.single[1],int(a.single[2]))));sys.exit()
    rows=[]
    jobs=[(24,b,4) for b in ['cpu-direct','cpu-cg','cpu-amg','cpu-matrixfree','cuda-cg']]+[(48,b,t) for b,t in [('cpu-cg',4),('cpu-matrixfree',1),('cpu-matrixfree',8),('cuda-cg',4)]]
    for n,b,t in jobs:
        try:
            r=subprocess.run([sys.executable,__file__,'--single',str(n),b,str(t)],capture_output=True,text=True,timeout=120,check=True)
            row=json.loads(r.stdout.strip().splitlines()[-1]);rows.append(row);print(json.dumps(row),flush=True)
        except Exception as exc:
            row=dict(n=n,backend=b,threads=t,error=str(exc));rows.append(row);print(json.dumps(row),flush=True)
        Path(a.output).write_text(json.dumps(rows,indent=2),encoding='utf8')
