"""Configure an isolated, persistent CPU worker for the Windows Yak package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import venv

PACKAGE = Path(__file__).resolve().parent


def runtime_id(source):
    paths = sorted((source / 'tool').glob('*.py'))
    paths += [source / 'requirements-runtime-lock.txt', source / 'tool/requirements-tested.txt', source / 'vendor/upstream-sha256.json']
    h = hashlib.sha256()
    for p in paths:
        h.update(p.relative_to(source).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:20]


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(data, indent=2), encoding='utf-8')
    os.replace(temp, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, help='Override state directory for isolated acceptance tests')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if os.name != 'nt' or sys.version_info[:2] != (3, 13):
        parser.error('Run with 64-bit Python 3.13 on Windows: py -3.13 configure.py')
    import struct
    if struct.calcsize('P') != 8:
        parser.error('64-bit Python is required')
    source = PACKAGE / 'source'
    state = (args.state_dir or Path(os.environ['LOCALAPPDATA']) / 'TopOptLab/Rhino8').resolve()
    identity = runtime_id(source)
    runtime = state / 'runtimes' / identity
    config_file = state / 'settings.json'
    lock = state / 'setup.lock'
    state.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit('Another setup may be running. If it stopped unexpectedly, remove setup.lock after confirming no setup process is active.')
    os.close(fd)
    try:
        python = runtime / 'venv/Scripts/python.exe'
        ready = runtime / 'ready.json'
        if not ready.exists():
            if args.check_only:
                raise SystemExit('CPU runtime is not configured. Run SETUP-PYTHON.cmd first.')
            runtime.mkdir(parents=True, exist_ok=True)
            destination = runtime / 'source'
            shutil.copytree(source, destination, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('.venv', '__pycache__', '.pytest_cache', '*.pyc'))
            venv.EnvBuilder(with_pip=True).create(runtime / 'venv')
            subprocess.run([str(python), '-m', 'pip', 'install', '-c', str(destination/'requirements-runtime-lock.txt'), '-r', str(destination/'tool/requirements-tested.txt'), 'threadpoolctl==3.7.0', 'psutil==7.2.2'], check=True)
            subprocess.run([str(python), '-m', 'pip', 'install', '--no-deps', str(destination/'vendor/topoptlab')], check=True)
        probe = "import sys,struct,numpy,scipy,topoptlab,gmsh,threadpoolctl,psutil; assert sys.version_info[:2]==(3,13) and struct.calcsize('P')==8; print('CPU runtime imports OK')"
        subprocess.run([str(python), '-c', probe], check=True)
        worker = runtime / 'source/tool/worker.py'
        if not worker.is_file():
            raise SystemExit('Worker missing; setup is incomplete.')
        config = {'schema': 'topoptlab-runtime-v1', 'runtime_id': identity,
                  'python': str(python), 'worker': str(worker)}
        if args.check_only:
            if not config_file.exists() or json.loads(config_file.read_text()) != config:
                raise SystemExit('Runtime exists but active settings do not match. Run SETUP-PYTHON.cmd.')
        if not args.check_only:
            atomic_json(ready, {'schema': 1, 'runtime_id': identity})
            config = {'schema': 'topoptlab-runtime-v1', 'runtime_id': identity,
                      'python': str(python), 'worker': str(worker)}
            if config_file.exists() and json.loads(config_file.read_text()) != config:
                shutil.copy2(config_file, state / ('settings-backup-' + str(time.time_ns()) + '.json'))
            atomic_json(config_file, config)
        print('PASS: persistent CPU runtime ' + str(runtime))
        print('Restart Rhino after installing/updating the Yak package.')
    finally:
        lock.unlink()


if __name__ == '__main__':
    main()
