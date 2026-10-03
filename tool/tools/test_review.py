# SPDX-License-Identifier: GPL-3.0-or-later
import os,subprocess,sys,json,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from test_distributed_loads import rectangle
from worker import run
import copy
rhino=Path(r'C:\Program Files\Rhino 8');target=ROOT/'build';exe=target/'ReviewSmoke.exe'
csc=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
refs=[target/'TopoptLab.GH.gha',rhino/'System/Newtonsoft.Json.dll',rhino/'System/RhinoCommon.dll',rhino/'Plug-ins/Grasshopper/Grasshopper.dll']
subprocess.run([str(csc),'/nologo','/out:'+str(exe),'/r:System.Drawing.dll']+['/r:'+str(r) for r in refs]+[str(ROOT/'tools/ReviewSmoke.cs')],check=True)
folder=target/('review-reference-'+uuid.uuid4().hex)
for dim in (2,3):
    r=rectangle(dim);r['load_cases'][0]['name']='Case 1';case=copy.deepcopy(r['load_cases'][0]);case['name']='Case 2';case['loads'][0]['pressure']*=-2;r['load_cases'].append(case)
    r['design_limits']=dict(max_displacement=.01,max_stress_mpa=10);r['settings'].update(iterations=3,volume=.8)
    d=folder/str(dim);run(r,d/'baseline');r['mode']='optimize';optimized=run(r,d/'optimization')
    r.update(mode='verify',source_result=optimized,manufacturing={'threshold':.01});run(r,d/'verification')
    subprocess.run([str(exe),str(rhino/'System'),str(rhino/'Plug-ins/Grasshopper'),str(target),str(d)],check=True,timeout=60)
