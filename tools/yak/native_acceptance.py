# SPDX-License-Identifier: GPL-3.0-or-later
import os, json, time, traceback
import Rhino, System, scriptcontext
import clr
clr.AddReference('Grasshopper')
clr.AddReference('System.Drawing')
clr.AddReference('System.Windows.Forms')
import Grasshopper
from Grasshopper.Kernel import GH_DocumentIO
from Grasshopper.Kernel import GH_Document
from Grasshopper.Kernel.Special import GH_ButtonObject
from Grasshopper.Kernel.Types import GH_Boolean
from System.Windows.Forms import Timer, ToolStripDropDown
from System.Drawing import Bitmap, Rectangle, Size

W = os.path.abspath(os.path.join(os.path.dirname(__file__),'../../tool/build/yak-native'))
if not os.path.isdir(W):os.makedirs(W)
PKG = os.path.join(os.environ['APPDATA'],'McNeel','Rhinoceros','packages','8.0','topoptlab-rhino','0.4.0-alpha.3')
report = {'pid':os.getpid(), 'phases':[], 'status':'running'}
state = {'phase':'baseline_start', 'started':time.time(), 'deadline':time.time()+240}
timer = Timer()
timer.Interval = 500

def write():
    with open(os.path.join(W,'native-acceptance.json'),'w') as f:json.dump(report,f,indent=2)

def data(param):
    return [str(x) for x in param.VolatileData.AllData(True)]

def pulse(button, value):
    prop=button.GetType().GetProperty('ButtonDown')
    if prop is None or not prop.CanWrite:
        raise Exception('Native ButtonDown is not writable: '+str(button.GetType()))
    prop.SetValue(button,value,None)
    button.ExpireSolution(False)
    doc.NewSolution(False)

def stage_button(stage,index):
    return solvers[stage].Params.Input[index].Sources[0].Attributes.GetTopLevel.DocObject

def stage_result(stage):
    values=data(solvers[stage].Params.Output[0])
    return json.loads(values[0]) if values else None

def next_phase(name):
    state['phase']=name
    state['deadline']=time.time()+180
    report['current_phase']=name
    write()

def active_objects():
    return len(list(Rhino.RhinoDoc.ActiveDoc.Objects.GetObjectList(Rhino.DocObjects.ObjectType.AnyObject)))

def finished(stage):
    status=data(solvers[stage].Params.Output[1])
    report['latest_status']=status
    if not status:
        report['diagnostics']=[{'name':str(o.Name),'type':str(o.GetType().Name),
            'errors':[str(x) for x in o.RuntimeMessages(Grasshopper.Kernel.GH_RuntimeMessageLevel.Error)],
            'inputs':[{'name':str(p.Name),'count':p.VolatileDataCount} for p in o.Params.Input]}
            for o in doc.Objects if hasattr(o,'Params') and str(o.Category)=='TopOptLab']
    result=stage_result(stage)
    if result and result.get('status')=='error':raise Exception(str(result))
    if status and status[0].startswith('error'):raise Exception(status[0])
    if result and result.get('status')=='completed':
        report['phases'].append({'stage':stage,'status':status,'job':result.get('job_id'),'metrics':result.get('metrics'),'engineering':result.get('engineering',{}).get('termination_reason')})
        return result
    return None

def screenshot():
    canvas=Grasshopper.Instances.ActiveCanvas
    canvas.Refresh()
    bitmap=Bitmap(canvas.Width,canvas.Height)
    canvas.DrawToBitmap(bitmap,Rectangle(0,0,canvas.Width,canvas.Height))
    bitmap.Save(os.path.join(W,'grasshopper-native.png'))
    bitmap.Dispose()
    viewport=Rhino.RhinoDoc.ActiveDoc.Views.ActiveView.ActiveViewport
    viewport.SetCameraDirection(Rhino.Geometry.Vector3d(0,0,-1),True)
    viewport.ChangeToParallelProjection(True)
    bounds=next(o.ClippingBox for o in doc.Objects if o.GetType().Name in ['FemResultsComponent','ResultsComponent'] and o.LegendVisible)
    bounds.Inflate(1.0)
    viewport.ZoomBoundingBox(bounds)
    Rhino.RhinoDoc.ActiveDoc.Views.Redraw()
    capture=Rhino.Display.ViewCapture()
    capture.Width=1400;capture.Height=900
    image=capture.CaptureToBitmap(Rhino.RhinoDoc.ActiveDoc.Views.ActiveView)
    image.Save(os.path.join(W,'rhino-native.png'));image.Dispose()

def tick(sender,event):
    try:
        if time.time()>state['deadline']:raise Exception('Timed out in '+state['phase'])
        phase=state['phase']
        if phase in ['baseline_start','optimization_start','verification_start']:
            stage={'baseline_start':0,'optimization_start':1,'verification_start':2}[phase]
            pulse(stage_button(stage,7),True)
            next_phase(['baseline_wait','optimization_wait','verification_wait'][stage])
        elif phase.endswith('_wait') and phase in ['baseline_wait','optimization_wait','verification_wait']:
            stage=['baseline_wait','optimization_wait','verification_wait'].index(phase)
            result=finished(stage)
            if result:
                pulse(stage_button(stage,7),False)
                if stage<2:next_phase(['optimization_start','verification_start'][stage])
                else:next_phase('preview')
        elif phase=='preview':
            view_slider=next(o for o in doc.Objects if str(o.NickName).startswith('VIEW:'))
            view_slider.SetSliderValue(System.Decimal(2));view_slider.ExpireSolution(False);doc.NewSolution(False)
            visible=[o for o in doc.Objects if o.GetType().Name in ['FemResultsComponent','ResultsComponent'] and o.LegendVisible]
            assert len(visible)==1,'Expected one visible stage'
            assert visible[0].ClippingBox.IsValid,'Preview bounds invalid'
            report['preview']={'visible_stages':len(visible),'valid_bounds':True}
            try:screenshot()
            except:report['screenshot_error']=traceback.format_exc()
            next_phase('bake')
        elif phase=='bake':
            result_view=next(o for o in doc.Objects if o.GetType().Name=='ResultsComponent')
            button=GH_ButtonObject();button.NickName='BAKE TEST';button.CreateAttributes()
            doc.AddObject(button,False);result_view.Params.Input[3].AddSource(button)
            button.ExpireSolution(False);doc.NewSolution(False)
            before=active_objects()
            pulse(button,True);after=active_objects()
            assert after==before+1,'Bake did not add one mesh'
            pulse(button,False)
            state['bake_before']=before;state['bake_after']=after
            assert Rhino.RhinoApp.RunScript('_Undo',False)
            next_phase('undo_wait')
        elif phase=='undo_wait':
            if active_objects()!=state['bake_before']:return
            report['bake_undo']={'before':state['bake_before'],'baked':state['bake_after'],'after_undo':active_objects()}
            next_phase('reset_start')
        elif phase=='save_reopen':
            io=GH_DocumentIO();io.Document=doc
            saved=os.path.join(W,'YakAcceptance-'+str(os.getpid())+'.gh')
            assert io.SaveQuiet(saved),'Grasshopper save failed'
            opened=GH_DocumentIO();assert opened.Open(saved),'Grasshopper reopen failed'
            reopened=opened.Document
            assert reopened.ObjectCount==doc.ObjectCount
            Grasshopper.Instances.DocumentServer.AddDocument(reopened)
            Grasshopper.Instances.ActiveCanvas.Document=reopened
            reopened.NewSolution(False)
            report['save_reopen']={'objects':reopened.ObjectCount,'saved':saved}
            restarted=[o for o in reopened.Objects if o.GetType().Name=='EngineeringSolveComponent']
            assert all(not data(o.Params.Output[2]) for o in restarted),'Reopen automatically launched a worker'
            report['save_reopen']['no_automatic_jobs']=True
            report['status']='PASS';report['elapsed_seconds']=time.time()-state['started']
            try:Rhino.RhinoDoc.ActiveDoc.Modified=False
            except:pass
            timer.Stop();write()
        elif phase=='reset_start':
            # Exercise Reset and Stop on the original document with real buttons.
            Grasshopper.Instances.ActiveCanvas.Document=doc
            pulse(stage_button(1,9),True);pulse(stage_button(1,9),False)
            assert not data(solvers[1].Params.Output[0]),'Reset retained result'
            report['reset']='PASS'
            pulse(stage_button(1,7),True)
            pulse(stage_button(1,7),False)
            pulse(stage_button(1,8),True)
            next_phase('stop_wait')
        elif phase=='stop_wait':
            jobs=data(solvers[1].Params.Output[2])
            if not jobs:return
            cancel=os.path.join(jobs[0],'cancel')
            assert os.path.isfile(cancel),'Stop did not write cancellation marker'
            field=solvers[1].GetType().GetField('job',System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic)
            worker=field.GetValue(solvers[1])
            if worker is not None and worker.Running:return
            report['stop']={'cancel_file':cancel,'status':data(solvers[1].Params.Output[1])}
            pulse(stage_button(1,8),False)
            pulse(stage_button(1,9),True);pulse(stage_button(1,9),False)
            next_phase('save_reopen')
        write()
    except:
        try:Rhino.RhinoDoc.ActiveDoc.Modified=False
        except:pass
        report['status']='FAIL';report['error']=traceback.format_exc();timer.Stop();write()

try:
    report['current_phase']='open_document';write()
    access=Rhino.RhinoApp.GetPlugInObject('Grasshopper')
    path=os.path.join(PKG,'source','tool','examples','engineering_workflow_2d.gh')
    clr.AddReferenceToFileAndPath(os.path.join(PKG,'TopoptLab.GH.gha'))
    import TopoptLab.GH as TopOpt
    doc=GH_Document()
    GH_Document.EnableSolutions=True
    for obj in TopOpt.EngineeringExample.Build(False):doc.AddObject(obj,False)
    report['document_source']='Native EngineeringExample.Build(False)'
    Grasshopper.Instances.DocumentServer.AddDocument(doc)
    Grasshopper.Instances.ActiveCanvas.Document=doc
    report['current_phase']='initial_solution';write()
    doc.Enabled=True
    for o in doc.Objects:
        if o.GetType().Name=='GH_NumberSlider':
            name=str(o.NickName)
            if name=='Cell size':o.SetSliderValue(System.Decimal(0.5))
            if name.startswith('Backend '):o.SetSliderValue(System.Decimal(0))
            if name=='Verification threshold':o.SetSliderValue(System.Decimal(0.2))
            o.ExpireSolution(False)
    doc.NewSolution(True)
    solvers={}
    for o in doc.Objects:
        if o.GetType().Name=='EngineeringSolveComponent':
            mode=int(data(o.Params.Input[5])[0]);solvers[mode]=o
    assert len(solvers)==3
    report['loaded_assembly']=str(solvers[0].GetType().Assembly.Location)
    assert os.path.normcase(PKG) in os.path.normcase(report['loaded_assembly'])
    report['components']=doc.ObjectCount
    button=stage_button(0,7)
    report['button_properties']=[str(p.Name) for p in button.GetType().GetProperties()]
    menu=ToolStripDropDown();solvers[0].AppendMenuItems(menu)
    report['setup_menu']=any(str(item.Text)=='TopOptLab Python setup folder' for item in menu.Items)
    assert report['setup_menu'],'Setup menu is missing'
    menu.Dispose()
    timer.Tick+=tick
    scriptcontext.sticky['TopOptYakAcceptanceTimer']=timer
    scriptcontext.sticky['TopOptYakAcceptanceState']=state
    write();timer.Start()
except:
    report['status']='FAIL';report['error']=traceback.format_exc();write()
