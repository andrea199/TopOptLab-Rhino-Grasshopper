"""Check every tracked GHX for complete TopOptLab ports and resolvable wires.

Run native_archive_audit.py inside Rhino as well: GHX checks cannot validate GH.
"""
from pathlib import Path
import json
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def check():
    catalog = json.loads((ROOT/'docs/manual/data/components.json').read_text(encoding='utf-8'))
    components = {c['guid'].lower(): c for c in catalog['components']}
    paths = subprocess.check_output(['git', 'ls-files', '*.ghx'], cwd=ROOT, text=True).splitlines()
    count = 0
    for relative in paths:
        path = ROOT/relative
        tree = ET.parse(path)
        ids = [x.text for x in tree.findall(".//item[@name='InstanceGuid']")]
        assert len(ids) == len(set(ids)), f'{relative}: duplicate instance GUID'
        for obj in tree.findall(".//chunk[@name='DefinitionObjects']/chunks/chunk"):
            guid = obj.find("items/item[@name='GUID']").text.lower()
            c = components.get(guid)
            if c is None:
                continue
            container = obj.find("chunks/chunk[@name='Container']")
            for direction, key in [('input', 'inputs'), ('output', 'outputs')]:
                ports = container.findall(f"chunks/chunk[@name='param_{direction}']")
                assert sorted(int(p.attrib['index']) for p in ports) == list(range(len(c[key]))), f'{relative}: {c["name"]}: incomplete {direction} archive'
            count += 1
        for chunk in tree.iter('chunk'):
            n = chunk.find("items/item[@name='SourceCount']")
            if n is None:
                continue
            sources = chunk.findall("items/item[@name='Source']")
            assert int(n.text) == len(sources), f'{relative}: wrong SourceCount'
            assert all(s.text in ids for s in sources), f'{relative}: unresolved wire'
        assert path.with_suffix('.gh').is_file(), f'{relative}: missing binary pair'
    print(f'PASS: {len(paths)} GHX archives; {count} TopOptLab components have complete ports; all archived wires resolve.')


if __name__ == '__main__':
    check()
