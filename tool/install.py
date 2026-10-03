# SPDX-License-Identifier: GPL-3.0-or-later
"""Build and install the local Windows example, preserving the external Python path."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from build import build, ROOT


def install(python, rhino):
    python = Path(python).resolve()
    # Verify the exact interpreter that Grasshopper will launch.
    subprocess.run([str(python), '-c', 'import sys; assert sys.version_info >= (3,12,4); import topoptlab, numpy, scipy; from topoptlab.solve_linsystem import solve_lin'], check=True)
    source = build(rhino)
    target = Path(os.environ['APPDATA']) / 'Grasshopper/Libraries/TopoptLabExample'
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target / source.name)
    config = dict(python=str(python), worker=str(ROOT / 'worker.py'))
    (target / 'local-settings.json').write_text(json.dumps(config, indent=2), encoding='utf8')
    # Also configure the build copy for API tests run during development.
    (ROOT / 'build/local-settings.json').write_text(json.dumps(config, indent=2), encoding='utf8')
    print('Installed: ' + str(target))
    print('Start/restart Grasshopper, then open examples/plate_with_hole.gh.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--rhino', type=Path, default=Path(r'C:\Program Files\Rhino 8'))
    args = parser.parse_args()
    install(args.python, args.rhino)
