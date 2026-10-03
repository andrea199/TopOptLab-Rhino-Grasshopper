# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise actual Grasshopper dataflow in RhinoCore, without opening a UI or starting solver jobs."""
import os, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
rhino=Path(r"C:\Program Files\Rhino 8")
target=ROOT/"build"/"resolution-probe";target.mkdir(parents=True,exist_ok=True)
refs=[ROOT/"build/TopoptLab.GH.gha",rhino/"System/RhinoCommon.dll",rhino/"System/Newtonsoft.Json.dll",rhino/"Plug-ins/Grasshopper/Grasshopper.dll",rhino/"Plug-ins/Grasshopper/GH_IO.dll"]
exe=target/"ResolutionProbe.exe"
csc=Path(os.environ["WINDIR"])/"Microsoft.NET/Framework64/v4.0.30319/csc.exe"
subprocess.run([str(csc),"/nologo","/out:"+str(exe),"/r:System.Drawing.dll"]+["/r:"+str(p) for p in refs]+[str(ROOT/"tools/ResolutionProbe.cs")],check=True)
subprocess.run([str(exe),str(rhino/"System"),str(rhino/"Plug-ins/Grasshopper"),str(ROOT/"build"),str(target)],check=True,timeout=180)
print(target)
