"""Validate the single static manual before local use or GitHub publication."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import json,re
REPO=Path(__file__).resolve().parents[2];SITE=REPO/'docs/manual'
class Page(HTMLParser):
 def __init__(self):super().__init__();self.refs=[];self.ids=[];self.lang=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='html':self.lang=a.get('lang')
  if 'id' in a:self.ids.append(a['id'])
  for key in ['href','src']:
   if key in a:self.refs.append((tag,key,a[key]))
def main():
 pages={};errors=[];count=0
 for f in SITE.rglob('*.html'):
  p=Page();p.feed(f.read_text(encoding='utf8'));pages[f]=p
  if p.lang!='en':errors.append(f'Language: {f.relative_to(SITE)}')
  if len(p.ids)!=len(set(p.ids)):errors.append(f'Duplicate IDs: {f.relative_to(SITE)}')
  text=f.read_text(encoding='utf8')
  if 'file:///' in text or re.search(r'C:[/\\]Users[/\\]',text):errors.append(f'Host path: {f.relative_to(SITE)}')
  if f.name!='slides.html' and text.count('<!-- MANUAL NAV START -->')!=1:errors.append(f'Navigation: {f.relative_to(SITE)}')
 for f,p in pages.items():
  for tag,key,ref in p.refs:
   url=urlsplit(ref)
   if url.scheme or url.netloc:
    if tag in ['script','img','link'] and url.scheme in ['http','https']:errors.append(f'External runtime dependency: {ref}')
    continue
   target=(f.parent/unquote(url.path)).resolve() if url.path else f
   count+=1
   if not target.is_relative_to(SITE.resolve()):errors.append(f'Outside manual: {f.relative_to(SITE)} → {ref}')
   elif not target.exists():errors.append(f'Missing file: {f.relative_to(SITE)} → {ref}')
   elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:errors.append(f'Missing anchor: {f.relative_to(SITE)} → {ref}')
 data=json.loads((SITE/'data/components.json').read_text(encoding='utf8'))
 assert len(data['components'])==33
 assert sum(len(c['inputs'])+len(c['outputs']) for c in data['components'])==346
 assert len(list((SITE/'assets/components').glob('*.png')))==33
 course=json.loads((SITE/'data/course.json').read_text(encoding='utf8'))
 assert sum(x['minutes'] for x in course['lessons'])+course['break_minutes']==course['total_minutes']==180
 for lesson in course['lessons']:
  if lesson['status']=='available':assert (SITE/'learnings'/lesson['path']).is_file()
 for f in SITE.rglob('*'):
  if f.is_file() and (f.suffix in ['.zip','.exe','.dll','.gha','.pyc'] or f.stat().st_size>50*1024**2):errors.append(f'Distribution/build artefact: {f.relative_to(SITE)}')
 if errors:raise SystemExit('\n'.join(errors))
 print(f'PASS: {len(pages)} English pages; {count} relative links/assets; 33 components; 346 ports; 8 planned/available lessons; no host paths or installer archives.')
if __name__=='__main__':main()
