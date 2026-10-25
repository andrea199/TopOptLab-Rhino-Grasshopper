// SPDX-License-Identifier: GPL-3.0-or-later
using System;using System.IO;using System.Reflection;using System.Runtime.CompilerServices;using System.Drawing;using System.Collections.Generic;
using Grasshopper.Kernel;using Grasshopper.Kernel.Parameters;using Grasshopper.Kernel.Special;using Grasshopper.Kernel.Types;using Rhino.Geometry;using TopoptLab.GH;using Point=System.Drawing.Point;
class CreateCourseFiles {
 [STAThread]static int Main(string[] args){string[] dirs={Path.Combine(args[1],"System"),Path.Combine(args[1],"Plug-ins","Grasshopper"),args[2]};AppDomain.CurrentDomain.AssemblyResolve+=delegate(object s,ResolveEventArgs e){foreach(var dir in dirs)foreach(var ext in new[]{".dll",".gha"}){var file=Path.Combine(dir,new AssemblyName(e.Name).Name+ext);if(File.Exists(file))return Assembly.LoadFrom(file);}return null;};try{Builder.Run(args[0]);return 0;}catch(Exception ex){Console.Error.WriteLine(ex);return 1;}}
 class Builder {
 static List<IGH_DocumentObject> objects;
 static T Add<T>(T obj,float x,float y)where T:IGH_DocumentObject{obj.CreateAttributes();obj.Attributes.Pivot=new PointF(x,y);objects.Add(obj);return obj;}
 static GH_Panel Note(string text,float x,float y,float width,float height){var p=Add(new GH_Panel(),x,y);p.UserText=text;p.Attributes.Bounds=new RectangleF(x,y,width,height);return p;}
 static GH_NumberSlider Slider(string name,decimal val,decimal min,decimal max,int digits,float x,float y){var p=new GH_NumberSlider(){NickName=name};p.Slider.Minimum=min;p.Slider.Maximum=max;p.Slider.DecimalPlaces=digits;p.Slider.Type=digits==0?Grasshopper.GUI.Base.GH_SliderAccuracy.Integer:Grasshopper.GUI.Base.GH_SliderAccuracy.Float;p.SetSliderValue(val);return Add(p,x,y);}
 static void Num(GH_Component c,int i,double n){var p=(Param_Number)c.Params.Input[i];p.PersistentData.Clear();p.SetPersistentData(new GH_Number(n));}
 static void Int(GH_Component c,int i,int n){var p=(Param_Integer)c.Params.Input[i];p.PersistentData.Clear();p.SetPersistentData(new GH_Integer(n));}
 static void Text(GH_Component c,int i,string s){var p=(Param_String)c.Params.Input[i];p.PersistentData.Clear();p.SetPersistentData(new GH_String(s));}
 static void Wire(GH_Component to,int input,GH_Component from,int output){to.Params.Input[input].AddSource(from.Params.Output[output]);}
 static void Controls(EngineeringSolveComponent c,string stage,float y){for(int k=0;k<3;k++){var b=Add(new GH_ButtonObject(){NickName=new[]{"RUN "+stage,"STOP "+stage,"RESET "+stage}[k]},1230,y+150+k*50);c.Params.Input[7+k].AddSource(b);}Note("",1390,y+180,400,80).AddSource(c.Params.Output[1]);Note("",1390,y+275,620,75).AddSource(c.Params.Output[3]);}
 [MethodImpl(MethodImplOptions.NoInlining)]public static void Run(string site){string[] slugs={"03-supports-and-loads","04-first-fem-analysis","05-optimise-the-structure","06-extract-and-check"};for(int lesson=3;lesson<=6;lesson++)foreach(bool solution in new[]{false,true})Build(Path.Combine(site,"learnings",slugs[lesson-3],"files"),lesson,solution);}
 static void Build(string folder,int lesson,bool solution){objects=new List<IGH_DocumentObject>();
  string exercise=lesson==3?"Connect Fixed edge -> Support G and Load point -> Load G.":lesson==4?"Connect Load L -> Load Case Loads L.":lesson==5?"Connect Settings O -> OPTIMISATION O.":"Connect completed OPTIMISATION R -> VERIFICATION Source.";
  Note("LESSON "+lesson.ToString("00")+" / ENGLISH COURSE\n120 x 60 mm XY plate; h=6 mm; t=2 mm; steel; left edge fixed; total force (0,-100,0) N.\nSet Boundary, Fixed edge and Load point from the shared lesson 01 Rhino model.\n"+(solution?"WIRED SOLUTION. Select geometry, then run stages in order.":"PARTLY WIRED STARTER. "+exercise)+"\nFiles contain no completed runtime jobs. RUN/STOP/RESET are momentary buttons; no calculation starts automatically.\nMode 0 baseline -> Mode 1 optimisation -> Mode 2 binary verification. Threshold=0.40. Preserve attachments is enabled.\nOpen the unified manual for the full recipe, expected values and limitations.",20,20,2100,180);
  var boundary=Add(new Param_Curve(){NickName="Boundary / 01_Boundary"},150,300);var edge=Add(new Param_Curve(){NickName="Fixed edge / 02_Fixed_edge"},150,420);var point=Add(new Param_Point(){NickName="Load point / 03_Load_point"},150,540);
  Note("Right-click each parameter: Set one Curve / Set one Point.\nSelect the layer named in its nickname.\nDo not select the reference arrow as a load.",20,650,360,150);
  var h=Slider("Cell size / mm",6,3,12,0,80,880);var domain=Add(new DomainComponent(){Hidden=true},450,300);domain.Params.Input[0].AddSource(boundary);domain.Params.Input[3].AddSource(h);
  var support=Add(new SupportComponent(),730,330);Wire(support,0,domain,0);var load=Add(new LoadComponent(),730,560);Wire(load,0,domain,0);
  if(lesson!=3||solution){support.Params.Input[1].AddSource(edge);load.Params.Input[1].AddSource(point);}
  var force=Add(new Param_Vector(){NickName="Total force / N"},450,640);force.SetPersistentData(new GH_Vector(new Vector3d(0,-100,0)));load.Params.Input[2].AddSource(force);
  var sn=Add(new Param_Point(){NickName="Inspect supported nodes"},960,300);sn.AddSource(support.Params.Output[1]);var ln=Add(new Param_Point(){NickName="Inspect loaded nodes"},960,600);ln.AddSource(load.Params.Output[1]);
  Note("CONDITIONS CHECK\nAt h=6 mm: 11 supported nodes, 1 loaded node.\nFix X=true; Fix Y=true. Total force is shared by selected nodes.\nNumerical support/load data is not the illustrative Rhino arrow.",500,800,570,150);
  if(lesson>=4){
   var material=Add(new MaterialComponent(),700,1150);Num(material,4,2);
   Note("",20,1110,550,390).AddSource(material.Params.Output[3]);
   var settings=Add(new EngineeringSettingsComponent(),1050,1120);Num(settings,5,2);
   var volume=Slider("Material fraction",.4m,.2m,.8m,2,600,1550);settings.Params.Input[2].AddSource(volume);
   var threshold=Slider("Shared verification threshold",.4m,.1m,.9m,2,600,1630);settings.Params.Input[10].AddSource(threshold);
   var case1=Add(new LoadCaseComponent(),1040,520);Text(case1,1,"Downward 100 N");if(lesson!=4||solution)Wire(case1,0,load,0);
   var field=Slider("Field 0=default 1=U 2=stress",lesson>=5?0:1,0,2,0,1870,210);
   var scale=Slider("Display scale / 0 original 1 actual",0,0,2000,0,1870,270);
   var legend=Slider("Shared legend maximum / 0 auto",0,0,100,5,1870,330);
   var baseline=Add(new EngineeringSolveComponent(){NickName="BASELINE / Mode 0"},1470,480);
   var solvers=new List<EngineeringSolveComponent>();solvers.Add(baseline);
   if(lesson>=5)solvers.Add(Add(new EngineeringSolveComponent(){NickName="OPTIMISATION / Mode 1"},1470,1080));
   if(lesson>=6)solvers.Add(Add(new EngineeringSolveComponent(){NickName="VERIFICATION / Mode 2"},1470,1680));
   for(int stage=0;stage<solvers.Count;stage++){
    var solver=solvers[stage];Int(solver,5,stage);Wire(solver,0,domain,0);Wire(solver,1,support,0);Wire(solver,2,case1,0);Wire(solver,3,material,0);
    if(!(lesson==5&&!solution&&stage==1))Wire(solver,4,settings,0);
    if(stage==2 && solution)Wire(solver,6,solvers[1],0);
    float y=480+stage*600;Controls(solver,new[]{"BASELINE","OPTIMISATION","VERIFICATION"}[stage],y);
    GH_Component viewer=stage==1?(GH_Component)new ResultsComponent():new FemResultsComponent();Add(viewer,1950,y);Wire(viewer,0,solver,0);
    viewer.Params.Input[stage==1?4:1].AddSource(field);viewer.Params.Input[2].AddSource(scale);viewer.Params.Input[stage==1?5:3].AddSource(legend);
    if(stage==1)viewer.Params.Input[1].AddSource(threshold);
    var show=Add(new GH_BooleanToggle(){NickName="SHOW "+new[]{"BASELINE","DESIGN","VERIFICATION"}[stage],Value=stage==solvers.Count-1},1760,y+170);viewer.Params.Input[stage==1?6:4].AddSource(show);
    Note("",2190,y-70,700,320).AddSource(viewer.Params.Output[stage==1?3:8]);
   }
   if(lesson>=6){var compare=Add(new CompareResultsComponent(),2290,2140);Wire(compare,0,baseline,0);Wire(compare,1,solvers[2],0);Note("",2520,2060,690,300).AddSource(compare.Params.Output[0]);}
   Note("RUN ORDER\nRun BASELINE, wait for completion. Run OPTIMISATION next. Run VERIFICATION only after a completed design.\nUse SHOW toggles for one preview at a time. Field=0 means FEM stress but design density. Field=1 means displacement.\nScale affects display only. Set the same positive legend maximum to compare a physical field.\nSave job folders for reports. Mode 2 Source is a completed engineering result, not a mesh.\nNo automatic building-code, buckling or connection verification.",1100,2440,1700,190);
  }
  Directory.CreateDirectory(folder);string name="lesson"+lesson.ToString("00")+(solution?"_solution":"_starter");Save(folder,name);
 }
 static void Save(string folder,string basename){
  var archive=new GH_IO.Serialization.GH_Archive();var def=archive.CreateTopLevelNode("Definition");def.SetVersion("plugin_version",1,0,7);var header=def.CreateChunk("DocumentHeader");header.SetGuid("DocumentID",Guid.NewGuid());header.SetString("Preview","Shaded");header.SetInt32("PreviewMeshType",1);
  var props=new GH_DocumentProperties(){ProjectFileName=basename+".gh",Description="English progressive teaching file. Set geometry from the shared lesson 01 model. Run stages explicitly; no completed results included.",ViewTarget=new Point(1250,1050),ZoomFactor=.5f};if(!props.Write(def))throw new Exception("Properties write failed");def.CreateChunk("RcpLayout").SetInt32("GroupCount",0);def.CreateChunk("GHALibraries").SetInt32("Count",0);var list=def.CreateChunk("DefinitionObjects");list.SetInt32("ObjectCount",objects.Count);
  for(int i=0;i<objects.Count;i++){var o=objects[i];o.Attributes.PerformLayout();var ch=list.CreateChunk("Object",i);ch.SetGuid("GUID",o.ComponentGuid);ch.SetString("Name",o.Name);if(!o.Write(ch.CreateChunk("Container")))throw new Exception("Write object failed");}
  foreach(var ext in new[]{".gh",".ghx"}){var file=Path.Combine(folder,basename+ext);if(!archive.WriteToFile(file,true,false))throw new Exception("Archive write failed");var read=new GH_IO.Serialization.GH_Archive();if(!read.ReadFromFile(file))throw new Exception("Archive readback failed");var definition=read.GetRootNode.FindChunk("Definition");var properties=new GH_DocumentProperties();if(!properties.Read(definition))throw new Exception("Properties readback failed");var items=definition.FindChunk("DefinitionObjects");for(int i=0;i<objects.Count;i++){var clone=(IGH_DocumentObject)Activator.CreateInstance(objects[i].GetType());clone.CreateAttributes();if(!clone.Read(items.FindChunk("Object",i).FindChunk("Container")))throw new Exception("Object readback failed");}Console.WriteLine("PASS SDK readback: "+Path.GetFileName(file)+" / "+objects.Count+" objects");}
 }
}}
