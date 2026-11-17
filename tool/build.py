# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the thin Windows Grasshopper assembly using the installed Rhino SDK."""
import argparse
from pathlib import Path
import subprocess
import os

ROOT = Path(__file__).resolve().parent


def build(rhino=Path(r'C:\Program Files\Rhino 8')):
    target = ROOT / 'build'
    target.mkdir(exist_ok=True)
    compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    refs = [rhino / 'System/RhinoCommon.dll', rhino / 'System/Newtonsoft.Json.dll',
            rhino / 'Plug-ins/Grasshopper/Grasshopper.dll', rhino / 'Plug-ins/Grasshopper/GH_IO.dll']
    common = [str(compiler), '/nologo', '/optimize+', '/target:library', '/platform:anycpu', '/r:System.Drawing.dll',
              '/r:System.Windows.Forms.dll'] + ['/r:' + str(p) for p in refs]
    assembly = target / 'TopoptLab.GH.gha'
    subprocess.run(common + ['/resource:' + str(ROOT / 'materials.json') + ',TopoptLab.Materials', '/resource:' + str(ROOT / 'scenarios.json') + ',TopoptLab.Scenarios', '/out:' + str(assembly)] + [str(p) for p in sorted((ROOT / 'src').glob('*.cs'))], check=True)
    print(assembly)
    return assembly


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rhino', type=Path, default=Path(r'C:\Program Files\Rhino 8'))
    build(parser.parse_args().rhino)
