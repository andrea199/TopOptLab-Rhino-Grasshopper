"""Export the canonical static manual to an empty hosting directory (standard library only)."""
import argparse, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'docs/manual'
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
 if out==ROOT or out.is_relative_to(SOURCE) or SOURCE.is_relative_to(out):p.error('Output must be separate from the source manual')
 if out.exists() and any(out.iterdir()):p.error('Output directory must be empty; existing files are never replaced')
 shutil.copytree(SOURCE,out,dirs_exist_ok=True)
 print('Exported the single canonical manual:',out)
if __name__=='__main__':main()
