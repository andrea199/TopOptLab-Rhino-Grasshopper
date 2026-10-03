# SPDX-License-Identifier: GPL-3.0-or-later
import argparse,os,json,subprocess,sys,uuid,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from test_distributed_loads import rectangle
p=argparse.ArgumentParser();p.add_argument('--assembly-dir',type=Path,default=ROOT/'build');p.add_argument('--config',type=Path);p.add_argument('--cuda',action='store_true');a=p.parse_args()
rhino=Path(r'C:\Program Files\Rhino 8');assembly=a.assembly_dir.resolve();target=ROOT/'build'/'bridge-probes'/uuid.uuid4().hex;target.mkdir(parents=True);exe=target/'FinalBridgeSmoke.exe';csc=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
subprocess.run([str(csc),'/nologo','/out:'+str(exe),'/r:'+str(assembly/'TopoptLab.GH.gha'),'/r:'+str(rhino/'System/Newtonsoft.Json.dll'),'/r:'+str(rhino/'System/RhinoCommon.dll'),'/r:'+str(rhino/'Plug-ins/Grasshopper/Grasshopper.dll'),'/r:'+str(rhino/'Plug-ins/Grasshopper/GH_IO.dll'),str(ROOT/'tools/FinalBridgeSmoke.cs')],check=True)
config=a.config
if config is None:
 config=target/'settings.json';config.write_text(json.dumps(dict(python=sys.executable,worker=str(ROOT/'worker.py'))))
r=rectangle(3);r['settings'].update(iterations=2,preserve_attachments=True,backend='cuda-cg' if a.cuda else 'cpu-cg');other=copy.deepcopy(r['load_cases'][0]);other['name']='Half load';other['loads'][0]['pressure']/=2;r['load_cases'].append(other)
fixture=target/'request.json';fixture.write_text(json.dumps(r));subprocess.run([str(exe),str(rhino/'System'),str(rhino/'Plug-ins/Grasshopper'),str(assembly),str(fixture),str(config),str(target/'evidence.json')],check=True,timeout=150)
