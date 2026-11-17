"""Real native-macOS bootstrap and worker acceptance; does not claim Rhino UI acceptance."""
from pathlib import Path
import argparse,json,os,platform,shutil,subprocess,sys,time

ROOT=Path(__file__).resolve().parents[2]

def run(*args,**kwargs):return subprocess.run([str(x) for x in args],check=True,**kwargs)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--expected-arch',choices=['arm64','x86_64'],required=True);a=p.parse_args()
    assert sys.platform=='darwin' and platform.machine()==a.expected_arch
    output=a.output.resolve();output.mkdir(parents=True,exist_ok=False)
    package=output/'Yak Mac package with spaces';source=package/'source';source.mkdir(parents=True)
    files=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    for name in files:
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
    shutil.copy2(ROOT/'tools/yak/configure.py',package/'configure.py')
    state=output/'TopOptLab state with spaces'
    started=time.time()
    run(sys.executable,package/'configure.py','--state-dir',state)
    settings=json.loads((state/'settings.json').read_text());python=Path(settings['python'])
    assert settings['platform']=='macos' and settings['architecture']==a.expected_arch
    assert python.parts[-2:] == ('bin','python')
    run(python,'-m','pip','check')
    run(sys.executable,package/'configure.py','--state-dir',state,'--check-only')
    # Every integration numerical regression, including real Gmsh/TET4 tests.
    result=subprocess.run([str(python),'-m','pytest',str(source/'tool/tests'),'-q','--basetemp',str(output/'pytest'),'--junitxml',str(output/'test-results.xml')],cwd=source)
    report={'architecture':platform.machine(),'macos':platform.mac_ver()[0],'python':sys.version.split()[0],'bootstrap':'PASS','runtime_reuse':'PASS','worker_tests_exit_code':result.returncode,'seconds':time.time()-started,'native_rhino_tested':False,'scope':'Real macOS CPU dependency imports and Python integration tests. No Rhino GUI or GHA loading is claimed.'}
    (output/'acceptance.json').write_text(json.dumps(report,indent=2))
    raise SystemExit(result.returncode)

if __name__=='__main__':main()
