import os,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));from sample3d import cantilever
rhino=Path(r'C:\Program Files\Rhino 8');target=ROOT/'build';exe=target/'EngineeringSmoke.exe'
csc=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
subprocess.run([str(csc),'/nologo','/out:'+str(exe),'/r:'+str(target/'TopoptLab.GH.gha'),'/r:'+str(rhino/'System/Newtonsoft.Json.dll'),str(ROOT/'tools/EngineeringSmoke.cs')],check=True)
r=cantilever('fem',8,4,2);r.update(engineering=True,material={'preset':'steel'},load_cases=[dict(name='Down',weight=1,loads=r['loads']),dict(name='Side',weight=1,loads=[dict(nodes=r['loads'][0]['nodes'],force=[0,100,0])])]);r['settings']['backend']='cuda-cg'
fixture=target/'engineering-bridge.json';fixture.write_text(json.dumps(r));config=target/'engineering-settings.json';config.write_text(json.dumps(dict(python=sys.executable,worker=str(ROOT/'worker.py'))))
subprocess.run([str(exe),str(rhino/'System'),str(rhino/'Plug-ins/Grasshopper'),str(target),str(fixture),str(config)],check=True,timeout=75)
