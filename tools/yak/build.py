"""Build a clean Windows Yak prerelease; never install or publish it."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
VERSION = '0.4.0-alpha.3'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    output = args.output.resolve()
    if output.exists():
        p.error('Output must be a new directory; never reuse a configured package folder.')
    subprocess.run([sys.executable, str(ROOT/'tools/yak/check_example_archives.py')], check=True)
    output.mkdir(parents=True)
    stage = output / 'package'
    stage.mkdir()
    subprocess.run([sys.executable, str(ROOT/'tool/build.py')], check=True)
    shutil.copy2(ROOT/'tool/build/TopoptLab.GH.gha', stage/'TopoptLab.GH.gha')
    files = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard'], cwd=ROOT, text=True).splitlines()
    for name in sorted(set(files)):
        source = ROOT/name
        if source.suffix.lower() in {'.ppt', '.pptx', '.pptm'}:
            raise RuntimeError('PowerPoint is forbidden in packages: ' + name)
        target = stage/'source'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    shutil.copy2(ROOT/'tools/yak/configure.py', stage/'configure.py')
    import importlib.util
    spec = importlib.util.spec_from_file_location('yak_configure', ROOT/'tools/yak/configure.py')
    bootstrap = importlib.util.module_from_spec(spec); spec.loader.exec_module(bootstrap)
    (stage/'runtime-id.txt').write_text(bootstrap.runtime_id(stage/'source'), encoding='ascii')
    shutil.copy2(ROOT/'tools/yak/README.md', stage/'README.md')
    (stage/'SETUP-PYTHON.cmd').write_bytes(b'@echo off\r\npy -3.13 "%~dp0configure.py" %*\r\nif errorlevel 1 pause\r\n')
    (stage/'manifest.yml').write_text('name: topoptlab-rhino\nversion: '+VERSION+'\nauthors:\n- Andrea Detry\ndescription: >\n  Experimental FEM and topology optimisation for Rhino 8 Grasshopper on Windows.\n  Run SETUP-PYTHON.cmd once to prepare a persistent CPU Python worker.\n  Requires Python 3.13 x64 and internet access.\nurl: https://github.com/andrea199/TopOptLab-Rhino-Grasshopper\nkeywords:\n- FEM\n- topology-optimization\n', encoding='utf-8')
    yak = Path(r'C:\Program Files\Rhino 8\System\Yak.exe')
    log = subprocess.run([str(yak), 'build', '--platform', 'win'], cwd=stage, text=True, capture_output=True, check=True)
    (output/'build.log').write_text(log.stdout+log.stderr, encoding='utf-8')
    artifacts = list(stage.glob('*.yak'))
    assert len(artifacts) == 1
    with zipfile.ZipFile(artifacts[0]) as z:
        assert z.testzip() is None
        assert not any(n.endswith('local-settings.json') or '/.venv/' in n for n in z.namelist())
    final = output/artifacts[0].name
    shutil.copy2(artifacts[0], final)
    print(str(final))


if __name__ == '__main__':
    main()
