"""Reproduce the introductory plate baseline, density optimisation and binary verification."""
from pathlib import Path
import argparse,os,sys,json,copy
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
out=a.output.resolve()
if out.exists():p.error('--output must be a new directory')
out.mkdir(parents=True);os.environ['TOPOPTLAB_ROOT']=str(ROOT);sys.path.insert(0,str(ROOT/'tool'))
from worker import run
reference=json.loads((ROOT/'docs/manual/data/intro-reference.json').read_text(encoding='utf8'));results={};summary={}
for stage in ['fem','optimize','verify']:
 request=copy.deepcopy(reference['request']);request.update(mode=stage,job_id='manual-intro-'+stage)
 if stage=='verify':request['source_result']=results['optimize']
 results[stage]=run(request,out/stage)
 e=results[stage]['engineering'];summary[stage]={'mass_kg':e['mass_kg'],'termination_reason':e['termination_reason'],'cases':e['cases']}
 print(stage,e['termination_reason'],e['mass_kg'],flush=True)
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
