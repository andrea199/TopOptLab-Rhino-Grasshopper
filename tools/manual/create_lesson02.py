"""Regenerate lesson 02 Grasshopper files using the installed Rhino8 SDK on Windows."""
import argparse,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--rhino',type=Path,default=Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Rhino 8')
p.add_argument('--assembly-dir',type=Path,required=True)
a=p.parse_args()
if os.name!='nt':p.error('The current SDK image exporter runs on Windows')
refs=[a.rhino/'System/RhinoCommon.dll',a.rhino/'System/Newtonsoft.Json.dll',a.rhino/'Plug-ins/Grasshopper/Grasshopper.dll',a.rhino/'Plug-ins/Grasshopper/GH_IO.dll',a.assembly_dir/'TopoptLab.GH.gha']
for f in refs:
 if not f.is_file():p.error('Missing SDK/assembly file: '+str(f))
with tempfile.TemporaryDirectory(prefix='TopOptLesson02-') as tmp:
 exe=Path(tmp)/'CreateLesson02.exe'
 subprocess.run([str(Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'),'/nologo','/target:exe','/r:System.Drawing.dll','/r:System.Windows.Forms.dll',*['/r:'+str(f) for f in refs],'/out:'+str(exe),str(Path(__file__).with_name('CreateLesson02.cs'))],check=True)
 subprocess.run([str(exe),str(ROOT/'docs/manual/learnings/02-build-the-domain/files'),str(a.rhino.resolve()),str(a.assembly_dir.resolve())],check=True)
