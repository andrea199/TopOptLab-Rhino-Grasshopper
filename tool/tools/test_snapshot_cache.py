# SPDX-License-Identifier: GPL-3.0-or-later
"""WorkerJob polling regression, with local fixture files and no Rhino process."""
import os, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
rhino=Path(r"C:\Program Files\Rhino 8")
target=ROOT/"build/snapshot-cache-probe";target.mkdir(parents=True,exist_ok=True)
refs=[rhino/"System/RhinoCommon.dll",rhino/"System/Newtonsoft.Json.dll",rhino/"Plug-ins/Grasshopper/Grasshopper.dll",rhino/"Plug-ins/Grasshopper/GH_IO.dll"]
csc=Path(os.environ["WINDIR"])/"Microsoft.NET/Framework64/v4.0.30319/csc.exe"
assembly=target/"TopoptLab.GH.gha"
subprocess.run([str(csc),"/nologo","/optimize+","/target:library","/r:System.Drawing.dll","/r:System.Windows.Forms.dll"]+["/r:"+str(p) for p in refs]+["/resource:"+str(ROOT/"materials.json")+",TopoptLab.Materials","/resource:"+str(ROOT/"scenarios.json")+",TopoptLab.Scenarios","/out:"+str(assembly)]+[str(p) for p in sorted((ROOT/"src").glob("*.cs"))],check=True)
exe=target/"SnapshotCacheProbe.exe"
subprocess.run([str(csc),"/nologo","/out:"+str(exe),"/r:System.Drawing.dll","/r:"+str(assembly)]+["/r:"+str(p) for p in refs]+[str(ROOT/"tools/SnapshotCacheProbe.cs")],check=True)
subprocess.run([str(exe),str(rhino/"System"),str(rhino/"Plug-ins/Grasshopper"),str(target),str(target)],check=True,timeout=30)
