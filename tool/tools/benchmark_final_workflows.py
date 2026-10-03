# SPDX-License-Identifier: GPL-3.0-or-later
"""Fresh-process constrained 3D / final FEM benchmarks, with explicit memory semantics."""
import argparse,json,os,platform,subprocess,sys,time,uuid,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def single(spec,out):
    import psutil
    import fem_backends
    from worker import run
    from sample3d import cantilever
    start=time.perf_counter();cp=None;pool=None;gpu=None
    if spec['backend']=='cuda-cg':
        import cupy as cp
        gpu=cp.cuda.runtime.getDeviceProperties(0)['name'];gpu=gpu.decode() if isinstance(gpu,bytes) else str(gpu)
        pool=cp.get_default_memory_pool()
    proc=psutil.Process();done=threading.Event();peaks=dict(rss=0,pool_used=0,pool_reserved=0)
    def sample():
        while not done.is_set():
            try:
                children=proc.children(recursive=True);rss=proc.memory_info().rss
                for child in children:
                    try:rss+=child.memory_info().rss
                    except psutil.Error:pass
                peaks['rss']=max(peaks['rss'],rss)
                if pool is not None:
                    peaks['pool_used']=max(peaks['pool_used'],pool.used_bytes());peaks['pool_reserved']=max(peaks['pool_reserved'],pool.total_bytes())
            except psutil.Error:pass
            done.wait(.025)
    sampler=threading.Thread(target=sample,daemon=True);sampler.start()
    try:
        if spec['workload']=='constrained':
            n=spec['nx'];r=cantilever('optimize',n,n//2,n//4,iterations=spec['iterations']);r['engineering']=True;r['material']=dict(preset='steel');r['load_cases']=[dict(name='Down',weight=1,loads=r['loads']),dict(name='Side',weight=1,loads=[dict(nodes=r['loads'][0]['nodes'],force=[0,100,0])])]
            r['settings'].update(backend=spec['backend'],threads=spec['threads'],volume=.6,preserve_attachments=True,linear_tolerance=1e-9)
            r['design_limits']=dict(max_displacement=.03,max_stress_mpa=10,enforce=True)
        else:
            source=json.loads(Path(spec['source']).read_text());r=dict(workflow='final_geometry',action='analyze',source_result=source,settings=dict(backend=spec['backend'],threads=spec['threads'],mesh_size=spec['mesh_size'],levels=1,linear_tolerance=1e-9))
        r['job_id']=uuid.uuid4().hex;result=run(r,out);e=result['engineering'];elapsed=time.perf_counter()-start
        row=dict(spec=spec,status=result['status'],seconds=elapsed,cases=e['cases'],limits=e['design_limits']['status'],termination=e['termination_reason'],mass_kg=e['mass_kg'],hardware=dict(cpu=platform.processor(),logical_cpus=psutil.cpu_count(),physical_cpus=psutil.cpu_count(logical=False),gpu=gpu),python=sys.version.split()[0])
        if spec['workload']=='constrained':row.update(voxels=len(result['density']),optimizer=e.get('constraint_optimizer'),iterations=len(result['history']),history=result['history'])
        else:row.update(nodes=len(result['nodes']),tetrahedra=len(result['tets']),mesh_study=e['accuracy']['status'])
        return row
    finally:
        done.set();sampler.join()
        if 'row' in locals():row['memory']=dict(peak_process_tree_rss_mb=peaks['rss']/1024**2,peak_cupy_pool_used_mb=peaks['pool_used']/1024**2 if pool else None,peak_cupy_pool_reserved_mb=peaks['pool_reserved']/1024**2 if pool else None,sampling_seconds=.025,note='Sampled host RSS includes mesher children. CuPy pool figures exclude driver/context/library allocations and are not total VRAM. GPU cold start is included in seconds; host imports are excluded.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--single',type=Path);p.add_argument('--output',type=Path);p.add_argument('--surface',type=Path);p.add_argument('--iterations',type=int,default=4);p.add_argument('--cuda',action='store_true');a=p.parse_args()
    if a.single:
        spec=json.loads(a.single.read_text());print(json.dumps(single(spec,a.single.parent/'job')));return
    folder=(a.output or ROOT/'build'/('performance-04-'+uuid.uuid4().hex)).resolve();folder.mkdir(parents=True,exist_ok=True)
    jobs=[dict(workload='constrained',nx=n,backend=b,threads=t,iterations=a.iterations) for n in (24,48) for b,t in [('cpu-cg',1),('cpu-cg',4),('cpu-matrixfree',4)]]+([] if not a.cuda else [dict(workload='constrained',nx=n,backend='cuda-cg',threads=4,iterations=a.iterations) for n in (24,48)])
    if a.surface:
        jobs += [dict(workload='final_fem',source=str(a.surface.resolve()),mesh_size=4.5,backend=b,threads=4) for b in ['cpu-cg','cpu-matrixfree']+(['cuda-cg'] if a.cuda else [])]
    record=dict(created=time.strftime('%Y-%m-%dT%H:%M:%S%z'),scope='Short constrained optimization workloads, not converged designs. Fresh process per job; timings include exports and reports.',rows=[])
    for i,spec in enumerate(jobs):
        directory=folder/('%02d'%(i+1));directory.mkdir(exist_ok=True);file=directory/'spec.json';file.write_text(json.dumps(spec));start=time.perf_counter()
        try:
            r=subprocess.run([sys.executable,__file__,'--single',str(file)],capture_output=True,text=True,timeout=240,check=True)
            (directory/'stdout.log').write_text(r.stdout,encoding='utf-8');(directory/'stderr.log').write_text(r.stderr,encoding='utf-8');row=json.loads(r.stdout.strip().splitlines()[-1]);row['fresh_process_seconds']=time.perf_counter()-start
        except (subprocess.SubprocessError,ValueError) as e:
            row=dict(spec=spec,status='error',error=str(e),stderr=getattr(e,'stderr',None));(directory/'error.txt').write_text(str(row),encoding='utf-8')
        record['rows'].append(row);(folder/'results.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        print(json.dumps({k:row.get(k) for k in ['spec','status','seconds','memory','limits','error']}),flush=True)
    print('Saved '+str(folder/'results.json'),flush=True)

if __name__=='__main__':main()
