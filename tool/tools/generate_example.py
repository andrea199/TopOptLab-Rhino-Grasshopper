# SPDX-License-Identifier: GPL-3.0-or-later
import os,sys
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
rhino = Path(r'C:\Program Files\Rhino 8')
target = ROOT / 'build'
exe = target / 'ArchiveExample.exe'
compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
refs = [rhino / 'System/Newtonsoft.Json.dll', target / 'TopoptLab.GH.gha', rhino / 'System/RhinoCommon.dll', rhino / 'Plug-ins/Grasshopper/GH_IO.dll', rhino / 'Plug-ins/Grasshopper/Grasshopper.dll']
subprocess.run([str(compiler), '/nologo', '/out:' + str(exe), '/r:System.Drawing.dll'] + ['/r:' + str(p) for p in refs] + [str(ROOT / 'tools/ArchiveExample.cs')], check=True)
subprocess.run([str(exe), str(rhino / 'System'), str(rhino / 'Plug-ins/Grasshopper'), str(target), str(ROOT / 'examples')] + (['shelf'] if '--shelf-only' in sys.argv else []), check=True, timeout=90)
