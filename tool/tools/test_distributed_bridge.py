import os,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from test_distributed_loads import rectangle
rhino=Path(r'C:\Program Files\Rhino 8');target=ROOT/'build';exe=target/'DistributedLoadSmoke.exe'
csc=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
refs=[target/'TopoptLab.GH.gha',rhino/'System/Newtonsoft.Json.dll',rhino/'System/RhinoCommon.dll']
subprocess.run([str(csc),'/nologo','/out:'+str(exe)]+['/r:'+str(r) for r in refs]+[str(ROOT/'tools/DistributedLoadSmoke.cs')],check=True)
config=target/'distributed-settings.json';config.write_text(json.dumps(dict(python=sys.executable,worker=str(ROOT/'worker.py'))))
for dim in (2,3):
 r=rectangle(dim);r['settings']['backend']='cuda-cg' if '--cuda' in sys.argv else 'cpu-cg'
 fixture=target/f'distributed-bridge-{dim}d.json';fixture.write_text(json.dumps(r))
 subprocess.run([str(exe),str(rhino/'System'),str(rhino/'Plug-ins/Grasshopper'),str(target),str(fixture),str(config)],check=True,timeout=75)
