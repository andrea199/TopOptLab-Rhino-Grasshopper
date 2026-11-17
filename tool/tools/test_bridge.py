# SPDX-License-Identifier: GPL-3.0-or-later
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from test_worker import example

rhino = Path(r'C:\Program Files\Rhino 8')
target = ROOT / 'build'
exe = target / 'WorkerSmoke.exe'
compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
refs = [target / 'TopoptLab.GH.gha', rhino / 'System/Newtonsoft.Json.dll']
subprocess.run([str(compiler), '/nologo', '/out:' + str(exe)] + ['/r:' + str(p) for p in refs] + [str(ROOT / 'tools/WorkerSmoke.cs')], check=True)
fixture = target / 'bridge-request.json'
fixture.write_text(json.dumps(example(iterations=15)), encoding='utf8')
config = target / 'local-settings.json'
spaced = target / 'worker path with spaces'
spaced.mkdir(exist_ok=True)
# Keep the worker's sibling modules (resource budget, engineering helpers, etc.).
for module in ROOT.glob('*.py'):
    shutil.copy2(module, spaced / module.name)
config.write_text(json.dumps(dict(python=sys.executable, worker=str(spaced / 'worker.py'))), encoding='utf8')
subprocess.run([str(exe), str(rhino / 'System'), str(rhino / 'Plug-ins/Grasshopper'), str(target), str(fixture), str(config)], check=True, timeout=55)

# Repeat the same process lifecycle checks on the 3D worker.
from sample3d import cantilever
fixture3d = target / 'bridge-request-3d.json'
fixture3d.write_text(json.dumps(cantilever('optimize',8,4,2,8)), encoding='utf8')
subprocess.run([str(exe), str(rhino / 'System'), str(rhino / 'Plug-ins/Grasshopper'), str(target), str(fixture3d), str(config)], check=True, timeout=55)
