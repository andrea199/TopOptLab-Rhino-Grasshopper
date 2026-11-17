"""Configure an isolated persistent CPU worker for Windows or native macOS."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import time
import venv

PACKAGE = Path(__file__).resolve().parent
NATIVE_WHEELS = 'numpy,scipy,matplotlib,cvxopt,gmsh,pyamg,rhino3dm,scikit-image,manifold3d,psutil,pillow,contourpy,kiwisolver'


def host_details():
    if sys.platform == 'win32':
        return {'system': 'windows', 'architecture': platform.machine().lower(),
                'python_relative': 'venv/Scripts/python.exe', 'setup': 'SETUP-PYTHON.cmd'}
    if sys.platform != 'darwin':
        raise ValueError('Supported platforms: Windows x64 and native macOS arm64/x86_64.')
    version = platform.mac_ver()[0]
    if not version or int(version.split('.')[0]) < 15:
        raise ValueError('This pinned macOS runtime requires macOS 15 or later.')
    arch = platform.machine().lower()
    if arch not in ('arm64', 'x86_64'):
        raise ValueError('Unsupported Mac Python architecture: ' + arch)
    translated = subprocess.run(['/usr/sbin/sysctl', '-in', 'sysctl.proc_translated'], capture_output=True, text=True)
    if translated.returncode == 0 and translated.stdout.strip() == '1':
        raise ValueError('Python is running through Rosetta. Use native Python 3.13 and Terminal for this Mac.')
    return {'system': 'macos', 'architecture': arch,
            'python_relative': 'venv/bin/python', 'setup': 'SETUP-PYTHON.command'}


def default_state(host):
    if host['system'] == 'macos':
        return Path.home() / 'Library/Application Support/TopOptLab/Rhino8'
    return Path(os.environ['LOCALAPPDATA']) / 'TopOptLab/Rhino8'


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
    if sys.version_info[:2] != (3, 13) or struct.calcsize('P') != 8:
        parser.error('Run with native 64-bit Python 3.13.')
    try:
        host = host_details()
    except ValueError as exc:
        parser.error(str(exc))
    source = PACKAGE / 'source'
    state = (args.state_dir or default_state(host)).resolve()
    identity = runtime_id(source)
    # Keep the already released Windows directory/config contract unchanged.
    suffix = '' if host['system'] == 'windows' else '-macos-' + host['architecture']
    runtime = state / 'runtimes' / (identity + suffix)
    config_file = state / 'settings.json'
    lock = state / 'setup.lock'
    state.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit('Another setup may be running. If it stopped unexpectedly, remove setup.lock after confirming no setup process is active.')
    os.close(fd)
    try:
        python = runtime / host['python_relative']
        ready = runtime / 'ready.json'
        if not ready.exists():
            if args.check_only:
                raise SystemExit('CPU runtime is not configured. Run ' + host['setup'] + ' first.')
            runtime.mkdir(parents=True, exist_ok=True)
            destination = runtime / 'source'
            shutil.copytree(source, destination, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('.git', '.venv', '__pycache__', '.pytest_cache', '*.pyc'))
            venv.EnvBuilder(with_pip=True).create(runtime / 'venv')
            command = [str(python), '-m', 'pip', 'install']
            if host['system'] == 'macos':
                # Fail clearly on missing native wheels; do not compile numerical libraries on a student's Mac.
                command += ['--only-binary=' + NATIVE_WHEELS]
            command += ['-c', str(destination/'requirements-runtime-lock.txt'), '-r', str(destination/'tool/requirements-tested.txt'), 'threadpoolctl==3.7.0', 'psutil==7.2.2']
            subprocess.run(command, check=True)
            subprocess.run([str(python), '-m', 'pip', 'install', '--no-deps', str(destination/'vendor/topoptlab')], check=True)
        probe = "import sys,struct,numpy,scipy,topoptlab,gmsh,threadpoolctl,psutil; assert sys.version_info[:2]==(3,13) and struct.calcsize('P')==8; print('CPU runtime imports OK')"
        if host['system'] == 'macos':
            probe = "from pathlib import Path; import appdirs; Path(appdirs.user_cache_dir()).mkdir(parents=True,exist_ok=True); Path(appdirs.user_cache_dir('symfem')).mkdir(parents=True,exist_ok=True); " + probe
            probe += "; import platform; assert platform.machine().lower()==" + repr(host['architecture'])
        subprocess.run([str(python), '-c', probe], check=True)
        worker = runtime / 'source/tool/worker.py'
        if not worker.is_file():
            raise SystemExit('Worker missing; setup is incomplete.')
        config = {'schema': 'topoptlab-runtime-v1', 'runtime_id': identity,
                  'python': str(python), 'worker': str(worker)}
        if host['system'] == 'macos':
            config.update(platform='macos', architecture=host['architecture'])
        if args.check_only:
            if not config_file.exists() or json.loads(config_file.read_text(encoding='utf-8')) != config:
                raise SystemExit('Runtime exists but active settings do not match. Run ' + host['setup'] + '.')
        else:
            atomic_json(ready, {'schema': 1, 'runtime_id': identity})
            if config_file.exists() and json.loads(config_file.read_text(encoding='utf-8')) != config:
                shutil.copy2(config_file, state / ('settings-backup-' + str(time.time_ns()) + '.json'))
            atomic_json(config_file, config)
        print('PASS: persistent CPU runtime ' + str(runtime))
        print('Restart Rhino after installing/updating the Yak package.')
    finally:
        lock.unlink()


if __name__ == '__main__':
    main()
