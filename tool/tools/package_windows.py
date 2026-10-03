# Compatibility entry point for the current source distribution packager.
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[2] / 'package_release.py'), run_name='__main__')
