"""Build a local AnyCPU Mac Yak candidate. Never install or publish it."""
import argparse,hashlib,importlib.util,json,shutil,struct,subprocess,sys,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
VERSION='0.4.0-alpha.5'

def managed_architecture(path):
    data=path.read_bytes();pe=struct.unpack_from('<I',data,0x3c)[0]
    assert data[pe:pe+4]==b'PE\0\0'
    machine,sections=struct.unpack_from('<HH',data,pe+4)
    optional=pe+24;size=struct.unpack_from('<H',data,pe+20)[0]
    assert struct.unpack_from('<H',data,optional)[0]==0x10b,'Expected an AnyCPU PE32 assembly'
    cli=struct.unpack_from('<I',data,optional+96+14*8)[0]
    offset=None
    for i in range(sections):
        s=optional+size+i*40;virtual_size,va,raw_size,raw=struct.unpack_from('<IIII',data,s+8)
        if va<=cli<va+max(virtual_size,raw_size):offset=raw+cli-va;break
    assert offset is not None
    flags=struct.unpack_from('<I',data,offset+16)[0]
    assert machine==0x14c and flags&1 and not flags&2 and not flags&0x20000,'Assembly is not pure AnyCPU IL'
    return {'machine':hex(machine),'cli_flags':hex(flags),'il_only':True,'requires_32bit':False,'requires_x64':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    out=args.output.resolve()
    if out.exists():parser.error('Output must be a new directory.')
    subprocess.run([sys.executable,str(ROOT/'tools/yak/check_example_archives.py')],check=True)
    subprocess.run([sys.executable,str(ROOT/'tool/build.py')],check=True)
    architecture=managed_architecture(ROOT/'tool/build/TopoptLab.GH.gha')
    stage=out/'package';stage.mkdir(parents=True)
    shutil.copy2(ROOT/'tool/build/TopoptLab.GH.gha',stage/'TopoptLab.GH.gha')
    names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
    for name in sorted(set(names)):
        if Path(name).suffix.lower() in ['.ppt','.pptx','.pptm']:raise ValueError('PowerPoint is not distributed')
        target=stage/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
    shutil.copy2(ROOT/'tools/yak/configure.py',stage/'configure.py')
    spec=importlib.util.spec_from_file_location('mac_setup',ROOT/'tools/yak/configure.py');setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
    (stage/'runtime-id.txt').write_text(setup.runtime_id(stage/'source'),encoding='ascii')
    (stage/'SETUP-PYTHON.command').write_bytes((ROOT/'tools/yak/SETUP-PYTHON.command').read_bytes().replace(b'\r\n',b'\n'))
    shutil.copy2(ROOT/'tools/yak/README_MAC.md',stage/'README.md')
    (stage/'manifest.yml').write_text('name: topoptlab-rhino\nversion: '+VERSION+'\nauthors:\n- Andrea Detry\ndescription: >\n  EXPERIMENTAL Mac alpha: NOT TESTED inside Rhino or Grasshopper for Mac.\n  CPU worker/host tests pass on Apple Silicon and Intel. Requires native Python 3.13 and macOS 15+.\n  Run SETUP-PYTHON.command once. Native Rhino Mac acceptance is still pending.\nurl: https://github.com/andrea199/TopOptLab-Rhino-Grasshopper\nkeywords:\n- FEM\n- topology-optimization\n',encoding='utf-8')
    yak=Path(r'C:\Program Files\Rhino 8\System\Yak.exe')
    result=subprocess.run([str(yak),'build','--platform','mac'],cwd=stage,text=True,capture_output=True,check=True)
    (out/'build.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    artifact=next(stage.glob('*.yak'));delivery=out/'distribution';delivery.mkdir()
    target=delivery/artifact.name
    # Preserve executable permissions for Finder launchers when built on Windows.
    with zipfile.ZipFile(artifact) as incoming,zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as output:
        for entry in incoming.infolist():
            if entry.filename.endswith('.command'):
                entry.create_system=3;entry.external_attr=(0o100755<<16)
            output.writestr(entry,incoming.read(entry.filename))
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        assert z.getinfo('SETUP-PYTHON.command').external_attr>>16&0o111==0o111
        assert z.read('runtime-id.txt').decode()==setup.runtime_id(stage/'source')
        assert not any(n.lower().endswith(('.dll','.exe','.dylib')) for n in z.namelist()),'SDK/native binaries must not be bundled'
    report={'package':target.name,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'assembly':architecture,'platform':'mac','architectures':['arm64','x86_64'],'minimum_macos':'15','python':'3.13 native 64 bit','native_rhino_tested':False,'published':False}
    (delivery/'preparation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (delivery/'SHA256SUMS.txt').write_text(report['sha256']+'  '+target.name+'\n',encoding='ascii')
    print(target)

if __name__=='__main__':main()
