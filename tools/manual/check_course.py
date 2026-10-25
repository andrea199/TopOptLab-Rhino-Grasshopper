"""Check course continuity, exercise wiring and published numerical reference consistency."""
from pathlib import Path
import json,xml.etree.ElementTree as X,math
ROOT=Path(__file__).resolve().parents[2];SITE=ROOT/'docs/manual'
def item(node,name):
 value=node.find("./items/item[@name='"+name+"']")
 return value.text if value is not None else None
def port(node,direction,index):return node.find("./chunks/chunk[@name='param_"+direction+"'][@index='"+str(index)+"']")
def output(node,index):return item(port(node,'output',index),'InstanceGuid')
def sources(node,index):return [i.text for i in port(node,'input',index).findall("./items/item[@name='Source']")]
def named(nodes,name):return next(n for n in nodes if item(n,'Name')==name)
def stage(nodes,label):return next(n for n in nodes if (item(n,'NickName') or '').startswith(label+' /'))
def main():
 course=json.loads((SITE/'data/course.json').read_text(encoding='utf8'))
 assert len(course['lessons'])==8 and all(l['status']=='available' for l in course['lessons'])
 assert sum(l['minutes'] for l in course['lessons'])+course['break_minutes']==180
 files=0;connections=0
 for l in course['lessons']:
  folder=SITE/'learnings'/Path(l['path']).parent
  for name in ['index.html','slides.html','teacher-guide.html','student-sheet.html']:assert (folder/name).is_file()
  assert (folder/'slides.html').read_text(encoding='utf8').count('class="slide"')==7
  if not 3<=int(l['id'])<=6:continue
  for kind in ['starter','solution']:
   file=folder/'files'/('lesson'+l['id']+'_'+kind+'.ghx');tree=X.parse(file).getroot()
   ids=[v.text for v in tree.findall(".//item[@name='InstanceGuid']")];assert len(ids)==len(set(ids)),file
   for chunk in tree.iter('chunk'):
    count=item(chunk,'SourceCount')
    if count is not None:
     refs=chunk.findall("./items/item[@name='Source']");assert int(count)==len(refs),file
     assert all(ref.text in ids for ref in refs),file
     connections+=len(refs)
   nodes=[o.find("./chunks/chunk[@name='Container']") for o in tree.findall("./chunks/chunk[@name='Definition']/chunks/chunk[@name='DefinitionObjects']/chunks/chunk")]
   domain=named(nodes,'TopOpt Domain');support=named(nodes,'TopOpt Support');load=named(nodes,'TopOpt Load')
   assert sources(support,0)==sources(load,0)==[output(domain,0)]
   for target in [support,load]:assert len(sources(target,1))==(0 if l['id']=='03' and kind=='starter' else 1)
   if int(l['id'])>=4:
    case=named(nodes,'TopOpt Load Case');material=named(nodes,'TopOpt Material');settings=named(nodes,'TopOpt Engineering Settings')
    assert sources(case,0)==([] if l['id']=='04' and kind=='starter' else [output(load,0)])
    for solver in [n for n in nodes if item(n,'Name')=='TopOpt Engineering']:
     assert sources(solver,0)==[output(domain,0)] and sources(solver,1)==[output(support,0)]
     assert sources(solver,2)==[output(case,0)] and sources(solver,3)==[output(material,0)]
     missing=l['id']=='05' and kind=='starter' and (item(solver,'NickName') or '').startswith('OPTIMISATION')
     assert sources(solver,4)==([] if missing else [output(settings,0)])
   if l['id']=='06':
    verify=stage(nodes,'VERIFICATION');optimize=stage(nodes,'OPTIMISATION');baseline=stage(nodes,'BASELINE')
    assert sources(verify,6)==([] if kind=='starter' else [output(optimize,0)])
    compare=named(nodes,'TopOpt Compare Results');assert sources(compare,0)==[output(baseline,0)] and sources(compare,1)==[output(verify,0)]
   assert file.with_suffix('.gh').is_file();files+=2
 reference=json.loads((SITE/'data/intro-reference.json').read_text(encoding='utf8'))
 result=reference['results'];m0=result['fem']['mass_kg'];m1=result['optimize']['mass_kg'];m2=result['verify']['mass_kg']
 assert math.isclose(m1/m0,.4,abs_tol=1e-12) and math.isclose(1-m2/m0,.52,abs_tol=1e-12)
 assert result['optimize']['termination_reason']=='converged'
 assert all(abs(v['cases'][0]['reaction_force'][1]-100)<1e-6 for v in result.values())
 rho=json.loads((SITE/'data/intro-visuals.json').read_text())['density'];assert sum(x>=.4 for x in rho)==96
 print(f'PASS: 8 available lessons; 56 slides; {files} native files; {connections} archived wires resolve; intentional starter gaps match exercises; numerical reference consistent.')
if __name__=='__main__':main()
