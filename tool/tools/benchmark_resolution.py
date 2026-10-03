# SPDX-License-Identifier: GPL-3.0-or-later
"""Reproducible whole-job shelf-resolution measurement; no automatic solver fallback."""
import argparse,copy,json,sys,time,threading,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import psutil
from engineering import run_engineering

def main():
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--mode',choices=['fem','optimize'],default='fem');p.add_argument('--iterations',type=int,default=60);p.add_argument('--backend',default='cpu-amg');a=p.parse_args()
    r=json.loads(a.request.read_text());r.update(mode=a.mode,job_id=a.output.name);r['settings'].update(backend=a.backend,iterations=a.iterations)
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);(out/'input.json').write_text(json.dumps(r))
    proc=psutil.Process();stop=threading.Event();peak=[proc.memory_info().rss];started=time.perf_counter()
    def monitor():
        while not stop.wait(.025):
            try:peak[0]=max(peak[0],proc.memory_info().rss)
            except psutil.Error:pass
    t=threading.Thread(target=monitor,daemon=True);t.start();record=dict(mode=a.mode,backend=a.backend,cell=r['domain']['cell'],bounding_cells=r['domain']['nx']*r['domain']['ny']*r['domain']['nz'],active_cells=len(r['domain']['active']),requested_iterations=a.iterations,source=str(a.request.resolve()))
    try:
        result=run_engineering(r,out/'job');e=result.get('engineering',{})
        record.update(status=result['status'],termination=e.get('termination_reason'),completed_iterations=result.get('completed_iterations'),mass_kg=e.get('mass_kg'),cases=e.get('cases'),limits=e.get('design_limits'),resources=e.get('resources'))
    except Exception as error:
        record.update(status='error',error=str(error));(out/'traceback.txt').write_text(traceback.format_exc())
    finally:
        stop.set();t.join();record.update(seconds=time.perf_counter()-started,peak_host_rss_mib=peak[0]/2**20)
        (out/'measurement.json').write_text(json.dumps(record,indent=2))
    print(json.dumps({k:v for k,v in record.items() if k not in ['cases','limits','resources']}),flush=True)
    if record['status']!='completed':raise SystemExit(1)
if __name__=='__main__':main()
