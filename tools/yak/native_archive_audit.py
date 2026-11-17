"""Run with Rhino 8 RunPythonScript after loading Grasshopper and TopOptLab.

Reads every repository example using GH_IO, including binary GH archives.
Solutions remain disabled: opening examples must not launch numerical jobs.
Writes tool/build/yak-native/archive-audit.json. Never rewrites examples.
"""
import os, json, traceback, clr
clr.AddReference('Grasshopper')
clr.AddReference('GH_IO')
import Grasshopper, GH_IO
from Grasshopper.Kernel import GH_Document

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
OUTPUT = os.path.join(ROOT, 'tool', 'build', 'yak-native', 'archive-audit.json')
report = {'status': 'running', 'pid': os.getpid(), 'files': []}
enabled = Grasshopper.Kernel.GH_Document.EnableSolutions
try:
    Grasshopper.Kernel.GH_Document.EnableSolutions = False
    for folder in ['tool/examples', 'docs/manual', 'teaching']:
        for base, dirs, files in os.walk(os.path.join(ROOT, folder)):
            for name in sorted(files):
                if not name.lower().endswith(('.gh', '.ghx')):
                    continue
                path = os.path.join(base, name)
                archive = GH_IO.Serialization.GH_Archive()
                doc = GH_Document()
                try:
                    assert archive.ReadFromFile(path), 'Archive read failed: '+path
                    assert archive.ExtractObject(doc, 'Definition'), 'Document extraction failed: '+path
                    messages = [{'type': str(m.Type), 'message': str(m.Message)} for m in archive.Messages]
                    row = {'path': os.path.relpath(path, ROOT), 'objects': len(list(doc.Objects)), 'messages': messages}
                    report['files'].append(row)
                    assert not [m for m in messages if m['type'] in ['error', 'warning']], str(row)
                finally:
                    doc.Dispose()
    report['status'] = 'PASS'
except:
    report['status'] = 'FAIL'
    report['error'] = traceback.format_exc()
finally:
    Grasshopper.Kernel.GH_Document.EnableSolutions = enabled
    directory = os.path.dirname(OUTPUT)
    if not os.path.isdir(directory): os.makedirs(directory)
    with open(OUTPUT, 'w') as stream: json.dump(report, stream, indent=2)
print(report['status']+' / '+str(len(report['files']))+' archives')
