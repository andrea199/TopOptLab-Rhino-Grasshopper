# SPDX-License-Identifier: GPL-3.0-or-later
import argparse,os,json,subprocess,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from test_distributed_loads import rectangle
import copy
p=argparse.ArgumentParser();p.add_argument('--assembly-dir',type=Path,default=ROOT/'build');p.add_argument('--config',type=Path);p.add_argument('--cuda',action='store_true');args=p.parse_args()
rhino=Path(r'C:\Program Files\Rhino 8');assembly=args.assembly_dir.resolve();target=ROOT/'build'/'bridge-probes'/uuid.uuid4().hex;target.mkdir(parents=True);exe=target/'ConstrainedBridgeSmoke.exe'
csc=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
subprocess.run([str(csc),'/nologo','/out:'+str(exe),'/r:'+str(assembly/'TopoptLab.GH.gha'),'/r:'+str(rhino/'System/Newtonsoft.Json.dll'),str(ROOT/'tools/ConstrainedBridgeSmoke.cs')],check=True)
config=args.config
if config is None:
    config=target/'settings.json';config.write_text(json.dumps(dict(python=sys.executable,worker=str(ROOT/'worker.py'))))
for dim in (2,3):
    r=rectangle(dim,'optimize');r['settings'].update(iterations=4,backend='cuda-cg' if args.cuda else 'cpu-cg')
    other=copy.deepcopy(r['load_cases'][0]);other['name']='Side';other['loads'][0]['pressure']*=-1;r['load_cases'].append(other)
    r['design_limits']=dict(max_displacement=.001,max_stress_mpa=10)
    fixture=target/f'constrained-{dim}d.json';fixture.write_text(json.dumps(r))
    subprocess.run([str(exe),str(rhino/'System'),str(rhino/'Plug-ins/Grasshopper'),str(assembly),str(fixture),str(config)],check=True,timeout=75)
