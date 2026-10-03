"""Create a complete source archive without local runtimes or cached jobs."""
from pathlib import Path
import hashlib
import json
import os
import zipfile

ROOT = Path(__file__).resolve().parent
EXCLUDE = {'.git', '.venv', 'runtime_deps', '__pycache__', '.pytest_cache',
           'build', 'dist', 'node_modules'}
LOCAL_SUFFIXES = {'.pyc', '.zip', '.user', '.gha', '.dll', '.exe', '.pem',
                  '.key', '.pfx', '.3dmbak', '.ghbak'}


def is_local(path):
    return (any(p in EXCLUDE or p.startswith('.chart-data-') for p in path.parts)
            or path.suffix.lower() in LOCAL_SUFFIXES
            or path.name in {'local-settings.json', '.env', '.DS_Store', 'Thumbs.db'}
            or (path.name.startswith('.env.') and path.name != '.env.example')
            or path.name.startswith('~$'))


def source_files(root):
    for folder, directories, names in os.walk(root):
        directories[:] = [d for d in directories if not is_local(Path(d))]
        for name in sorted(names):
            path = Path(folder) / name
            if not is_local(path.relative_to(root)):
                yield path


def main():
    manifest = json.loads((ROOT / 'vendor/upstream-sha256.json').read_text())
    for name, digest in manifest.items():
        if hashlib.sha256((ROOT / 'vendor/topoptlab' / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Upstream snapshot changed: ' + name)
    version = (ROOT / 'VERSION').read_text().strip()
    out = ROOT / 'dist'
    out.mkdir(exist_ok=True)
    target = out / ('TopOptLab-Rhino-' + version + '-source.zip')
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in source_files(ROOT):
            archive.write(path, Path('TopOptLab-Rhino') / path.relative_to(ROOT))
    (out / (target.name + '.sha256')).write_text(
        hashlib.sha256(target.read_bytes()).hexdigest() + '  ' + target.name + '\n'
    )
    print(target)


if __name__ == '__main__':
    main()
