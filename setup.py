"""Windows source installer. --prepare-only builds without touching the Rhino installation."""
import argparse,csv,io,json,os,shutil,subprocess,sys,venv
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def run(*args):subprocess.run([str(a) for a in args],check=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('--cuda',action='store_true');p.add_argument('--prepare-only',action='store_true');p.add_argument('--rhino',type=Path,default=Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Rhino 8');a=p.parse_args()
    if os.name!='nt':raise RuntimeError('Rhino integration installer currently supports Windows only')
    if sys.version_info[:2]!=(3,13):raise RuntimeError('Use Python 3.13 for this tested dependency set')
    if not (a.rhino/'System/RhinoCommon.dll').exists():raise RuntimeError('Rhino 8 SDK not found; specify --rhino')
    if not a.prepare_only:
        tasks=subprocess.check_output(['tasklist','/FI','IMAGENAME eq Rhino.exe','/FO','CSV','/NH'],text=True)
        if any(row and row[0].lower()=='rhino.exe' for row in csv.reader(io.StringIO(tasks))):raise RuntimeError('Save your work and close ALL Rhino windows before installing')
    env=ROOT/'.venv';python=env/'Scripts/python.exe'
    if not python.exists():venv.EnvBuilder(with_pip=True).create(env)
    run(python,'-m','pip','install','-c',ROOT/'requirements-runtime-lock.txt','-r',ROOT/'tool/requirements-tested.txt','threadpoolctl==3.7.0','psutil==7.2.2')
    run(python,'-m','pip','install','--no-deps',ROOT/'vendor/topoptlab')
    if a.cuda:run(python,'-m','pip','install','-c',ROOT/'requirements-runtime-lock.txt','cupy-cuda13x[ctk]==14.2.0')
    run(python,ROOT/'tool/build.py','--rhino',a.rhino)
    config=dict(python=str(python),worker=str(ROOT/'tool/worker.py'))
    (ROOT/'tool/build/local-settings.json').write_text(json.dumps(config,indent=2),encoding='utf8')
    if a.prepare_only:print('Prepared. Close Rhino, then run INSTALL.cmd'+(' --cuda' if a.cuda else '')+' to install.');return
    target=Path(os.environ['APPDATA'])/'Grasshopper/Libraries/TopoptLabExample';target.mkdir(parents=True,exist_ok=True)
    backup=ROOT/'tool/build/installation-backups'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup.mkdir(parents=True)
    names=['TopoptLab.GH.gha','local-settings.json'];old={n:(target/n).exists() for n in names}
    for n in names:
        if old[n]:shutil.copy2(target/n,backup/n)
    try:
        shutil.copy2(ROOT/'tool/build/TopoptLab.GH.gha',target/'TopoptLab.GH.gha')
        (target/'local-settings.json').write_text(json.dumps(config,indent=2),encoding='utf8')
    except Exception:
        for n in names:
            if old[n]:shutil.copy2(backup/n,target/n)
            elif (target/n).exists():(target/n).unlink()
        raise
    print('Installed TopOptLab engineering preview. Backup: '+str(backup))
    print('Open '+str(ROOT/'tool/examples/engineering_final_geometry_3d.gh'))
if __name__=='__main__':main()
