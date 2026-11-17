# SPDX-License-Identifier: GPL-3.0-or-later
"""Run inside a dedicated Rhino 8 / Grasshopper process; never saves input files.

Runs all 21 canonical examples and 11 lesson files with their saved parameters.
Only intentional student reference selections/wiring are supplied in memory.
Optional tool/build/yak-calculations/selection.json is a list of relative GH paths.
Results, per-stage payloads and progress remain under ignored tool/build.
Run the archive audit too: this exercises each GH graph once, not its duplicate
GHX/manual copies. CPU defaults are validated separately before Yak build.
"""
import os,json,time,traceback,math,clr
import Rhino,System,scriptcontext
clr.AddReference('Grasshopper');clr.AddReference('GH_IO');clr.AddReference('System.Windows.Forms')
import Grasshopper,GH_IO
from Grasshopper.Kernel import GH_Document,GH_RuntimeMessageLevel
from Grasshopper.Kernel.Types import GH_Curve,GH_Point
from System.Windows.Forms import Timer
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'../..'))
W=os.path.join(ROOT,'tool','build','yak-calculations')
if not os.path.isdir(W):os.makedirs(W)
paths=[os.path.join('tool','examples',n) for n in sorted(os.listdir(os.path.join(ROOT,'tool','examples'))) if n.endswith('.gh')]
paths.append(os.path.join('teaching','roof_2d','output','case','roof_2d_classroom.gh'))
for base,dirs,files in os.walk(os.path.join(ROOT,'docs','manual','learnings')):
 for n in sorted(files):
  if n.endswith('.gh'):paths.append(os.path.relpath(os.path.join(base,n),ROOT))
selection=os.path.join(W,'selection.json')
if os.path.isfile(selection):paths=json.load(open(selection))
report={'status':'running','pid':os.getpid(),'started':time.time(),'files':[],'queue':paths}
state={'file':-1,'phase':'open','stage':0,'doc':None,'solvers':[],'deadline':time.time()+1800}
timer=Timer();timer.Interval=300
def write():
 report['elapsed_seconds']=time.time()-report['started']
 report['current']={'file_index':state['file'],'phase':state['phase'],'stage_index':state['stage']}
 # Windows readers can deny delete sharing, so replacing an open progress
 # file can fail even though the calculation is sound. Readers already retry
 # incomplete JSON; write the progress file directly instead of renaming it.
 dest=os.path.join(W,'results.json')
 for attempt in range(20):
  try:
   System.IO.File.WriteAllText(dest,json.dumps(report,indent=2));break
  except IOError:
   if attempt==19:raise
   time.sleep(.01)
def values(p):return [str(v) for v in p.VolatileData.AllData(True)]
def components(doc,name):return [o for o in doc.Objects if o.GetType().Name==name]
def diagnostics(doc):
 return [{'name':str(o.Name),'nickname':str(o.NickName),'errors':[str(x) for x in o.RuntimeMessages(GH_RuntimeMessageLevel.Error)],'warnings':[str(x) for x in o.RuntimeMessages(GH_RuntimeMessageLevel.Warning)]} for o in doc.Objects if hasattr(o,'RuntimeMessages') and (list(o.RuntimeMessages(GH_RuntimeMessageLevel.Error)) or list(o.RuntimeMessages(GH_RuntimeMessageLevel.Warning)))]
def setup_lesson(doc,rel):
 actions=[]
 model=Rhino.FileIO.File3dm.Read(os.path.join(ROOT,'docs','manual','learnings','01-understand-the-problem','files','lesson01_cantilever_mm.3dm'))
 fixtures={}
 for obj in model.Objects:
  layer=model.Layers.FindIndex(obj.Attributes.LayerIndex)
  if layer is not None:fixtures[str(layer.Name)]=obj.Geometry
 for o in doc.Objects:
  name=str(o.NickName)
  key=next((k for k in fixtures if k in name),None)
  if key and hasattr(o,'PersistentData'):
   g=fixtures[key]
   if isinstance(g,Rhino.Geometry.Curve):o.PersistentData.Clear();o.SetPersistentData(GH_Curve(g.DuplicateCurve()));actions.append('Reference '+key)
   elif isinstance(g,Rhino.Geometry.Point):o.PersistentData.Clear();o.SetPersistentData(GH_Point(g.Location));actions.append('Reference '+key)
 # Complete only the deliberately missing student exercise connections in memory.
 if 'starter' in rel:
  for support in components(doc,'SupportComponent'):
   if not support.Params.Input[1].Sources:
    src=next((o for o in doc.Objects if str(o.NickName).startswith('Fixed edge')),None)
    if src:support.Params.Input[1].AddSource(src);actions.append('Complete Fixed edge -> Support G')
  for load in components(doc,'LoadComponent'):
   if not load.Params.Input[1].Sources:
    src=next((o for o in doc.Objects if str(o.NickName).startswith('Load point')),None)
    if src:load.Params.Input[1].AddSource(src);actions.append('Complete Load point -> Load G')
  for case in components(doc,'LoadCaseComponent'):
   if not case.Params.Input[0].Sources:
    loads=components(doc,'LoadComponent')
    if loads:case.Params.Input[0].AddSource(loads[0].Params.Output[0]);actions.append('Complete Load -> Load Case')
  solvers=components(doc,'EngineeringSolveComponent')
  for solver in solvers:
   if not solver.Params.Input[4].Sources:
    settings=components(doc,'EngineeringSettingsComponent')
    if settings:solver.Params.Input[4].AddSource(settings[0].Params.Output[0]);actions.append('Complete Settings -> Engineering')
  if 'lesson06' in rel:
   opt=next(o for o in solvers if str(o.NickName).startswith('OPTIMISATION'))
   verify=next(o for o in solvers if str(o.NickName).startswith('VERIFICATION'))
   if not verify.Params.Input[6].Sources:verify.Params.Input[6].AddSource(opt.Params.Output[0]);actions.append('Complete Optimisation -> Verification Source')
 return actions
def finite(x):
 if isinstance(x,float):assert not math.isnan(x) and not math.isinf(x),'Non-finite result'
 elif isinstance(x,dict):
  for v in x.values():finite(v)
 elif isinstance(x,list):
  for v in x:finite(v)
def validate(result):
 finite(result);m=result.get('metrics',{});e=result.get('engineering',{})
 assert e.get('termination_reason')!='optimizer_failed','Constraint optimizer failed numerically'
 assert not (e.get('constraint_optimizer') or {}).get('numerical_failure'),'Constraint optimizer numerical failure'
 for k in ['compliance','max_displacement','max_von_mises']:
  if k in m:assert m[k]>=0,'Negative '+k
 cases=e.get('cases',[])
 for c in [m]+cases:
  for k in ['residual','equilibrium']:
   if k in c:assert abs(c[k])<1e-5,'Poor '+k+': '+str(c[k])
  if 'applied_force' in c:
   scale=max(1.0,max(abs(v) for v in c['applied_force']))
   assert max(abs(a+b) for a,b in zip(c['applied_force'],c['reaction_force']))/scale<1e-5,'Reaction resultant does not balance applied force'
 density=result.get('density',[])
 if density:
  assert min(density)>=-1e-10 and max(density)<=1+1e-10,'Density outside [0,1]'
 if 'target_volume' in m and 'volume' in m:assert m['volume']<=m['target_volume']+1e-4,'Volume budget exceeded'
 return {'metrics':m,'termination':e.get('termination_reason'),'converged':e.get('converged'),'completed_iterations':result.get('completed_iterations',result.get('iteration')),'cases':[{k:c.get(k) for k in ['name','compliance','max_displacement','max_von_mises','max_von_mises_relaxed','residual','equilibrium','applied_force','reaction_force']} for c in cases],'design_limits':e.get('design_limits'),'geometry':result.get('geometry'),'accuracy':e.get('accuracy')}
def pulse(o,index,value):
 src=o.Params.Input[index].Sources
 assert len(src)==1,'Run control must have one source'
 b=src[0].Attributes.GetTopLevel.DocObject
 prop=b.GetType().GetProperty('ButtonDown')
 if prop is not None:prop.SetValue(b,value,None)
 elif b.GetType().Name=='GH_BooleanToggle':b.Value=value
 else:raise Exception('Unsupported Run control '+b.GetType().Name)
 b.ExpireSolution(False);state['doc'].NewSolution(False)
def worker_running(o):
 t=o.GetType();f=None
 while t is not None and f is None:
  f=t.GetField('job',System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance)
  t=t.BaseType
 j=f.GetValue(o) if f is not None else None
 return j is not None and j.Running
def close():
 d=state.get('doc')
 if d is not None:
  Grasshopper.Instances.ActiveCanvas.Document=None
  Grasshopper.Instances.DocumentServer.RemoveDocument(d)
  d.Dispose();state['doc']=None
def tick(sender,event):
 try:
  if state['phase']=='open':
   close();state['solvers']=[];state['file']+=1;state['stage']=0
   if state['file']>=len(paths):
    report['status']='PASS' if all(r['status']=='PASS' for r in report['files']) else 'FAIL'
    timer.Stop();write();return
   rel=paths[state['file']];row={'path':rel,'status':'running','stages':[],'setup':[]};report['files'].append(row)
   a=GH_IO.Serialization.GH_Archive();assert a.ReadFromFile(os.path.join(ROOT,rel))
   d=GH_Document();assert a.ExtractObject(d,'Definition')
   assert not [m for m in a.Messages if str(m.Type) in ['warning','error']],'Archive warning/error'
   state['doc']=d
   if 'learnings' in rel:row['setup']=setup_lesson(d,rel)
   Grasshopper.Instances.DocumentServer.AddDocument(d);Grasshopper.Instances.ActiveCanvas.Document=d;d.Enabled=True
   GH_Document.EnableSolutions=True;d.NewSolution(True)
   stages=[]
   controls={'SolverComponent':9,'Solver3DComponent':8,'FemAnalyzeComponent':6,'FemAnalyze3DComponent':5,'FinalGeometry3DComponent':5,'FinalFem3DComponent':6}
   for o in d.Objects:
    t=o.GetType().Name
    if t=='EngineeringSolveComponent':stages.append((int(values(o.Params.Input[5])[0]),o,7))
    elif t in controls:stages.append((3 if t=='FinalGeometry3DComponent' else 4 if t=='FinalFem3DComponent' else 0,o,controls[t]))
   stages.sort(key=lambda x:x[0]);state['solvers']=stages
   row['assembly']=str(stages[0][1].GetType().Assembly.Location) if stages else None
   row['initial_diagnostics']=diagnostics(d)
   if not stages:
    errors=[x for x in row['initial_diagnostics'] if x['errors']]
    assert not errors,str(errors)
    # Domain and boundary-condition exercises have no numerical solver by design.
    row['status']='PASS';row['scope']='geometry/conditions exercise; no solver in file';state['phase']='open'
   else:state['phase']='start'
   state['deadline']=time.time()+2700
  elif state['phase']=='start':
   stage,o,index=state['solvers'][state['stage']]
   rec={'component':str(o.GetType().Name),'stage':stage,'status':'running','started':time.time()};report['files'][-1]['stages'].append(rec)
   pulse(o,index,True);pulse(o,index,False)
   state['phase']='wait';state['deadline']=time.time()+2700
  elif state['phase']=='wait':
   stage,o,index=state['solvers'][state['stage']];row=report['files'][-1];rec=row['stages'][-1]
   status=values(o.Params.Output[1]);rec['latest_status']=status
   jobs=values(o.Params.Output[2]);rec['job']=jobs[0] if jobs else None
   outputs=values(o.Params.Output[0]);result=json.loads(outputs[0]) if outputs else None
   if result and result.get('status')=='error':raise Exception(str(result.get('message',result)))
   errors=[str(x) for x in o.RuntimeMessages(GH_RuntimeMessageLevel.Error)]
   if errors and not worker_running(o):raise Exception('; '.join(errors))
   if result and result.get('status')=='completed' and not worker_running(o):
    rec.update(validate(result));rec['status']='PASS';rec['elapsed_seconds']=time.time()-rec['started']
    rec['warnings']=[str(x) for x in o.RuntimeMessages(GH_RuntimeMessageLevel.Warning)]
    with open(os.path.join(W,'result-%02d-%02d.json'%(state['file'],state['stage'])),'w') as f:json.dump(result,f)
    state['stage']+=1
    if state['stage']>=len(state['solvers']):
     row['final_diagnostics']=diagnostics(state['doc'])
     assert not [x for x in row['final_diagnostics'] if x['errors']],str(row['final_diagnostics'])
     row['status']='PASS';state['phase']='open'
    else:state['phase']='start'
   elif time.time()>state['deadline']:raise Exception('Stage timed out after 45 minutes')
   elif not worker_running(o):
    # A process can exit just before GH's scheduled snapshot refresh.
    state['doc'].NewSolution(False)
    if 'idle_since' not in rec:rec['idle_since']=time.time()
    elif time.time()-rec['idle_since']>5:raise Exception('No completed result: '+str(status)+' / '+str(diagnostics(state['doc'])))
   elif 'idle_since' in rec:del rec['idle_since']
  write()
 except:
  row=report['files'][-1] if report['files'] else None
  if row is not None:
   row['status']='FAIL';row['error']=traceback.format_exc()
   row['failure_diagnostics']=diagnostics(state['doc']) if state.get('doc') else []
  else:report['error']=traceback.format_exc()
  # Never detach a still-running numerical job on a validation failure.
  for stage,o,index in state.get('solvers',[]):
   if worker_running(o):
    try:pulse(o,index+1,True);pulse(o,index+1,False)
    except:pass
  state['phase']='open';write()
timer.Tick+=tick
scriptcontext.sticky['TopOptExampleCalculationTimer']=timer
scriptcontext.sticky['TopOptExampleCalculationState']=state
scriptcontext.sticky['TopOptExampleCalculationReport']=report
write();timer.Start()
