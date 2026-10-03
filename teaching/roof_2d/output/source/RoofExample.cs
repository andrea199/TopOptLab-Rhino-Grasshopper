// SPDX-License-Identifier: GPL-3.0-or-later
using System;using System.IO;using System.Linq;using System.Collections.Generic;using System.Drawing;using System.Reflection;using System.Runtime.CompilerServices;
using Grasshopper.Kernel;using Grasshopper.Kernel.Parameters;using Grasshopper.Kernel.Special;using Grasshopper.Kernel.Types;using Rhino.Geometry;using TopoptLab.GH;using Newtonsoft.Json;using Newtonsoft.Json.Linq;
class Bootstrap {
 [STAThread]static int Main(string[] args){string[] paths={args[0],args[1],args[2]};AppDomain.CurrentDomain.AssemblyResolve+=delegate(object sender,ResolveEventArgs e){foreach(string p in paths)foreach(string ext in new[]{".dll",".gha"}){string f=Path.Combine(p,new AssemblyName(e.Name).Name+ext);if(File.Exists(f))return Assembly.LoadFrom(f);}return null;};try{Assembly.GetExecutingAssembly().GetType("RoofExample").GetMethod("Write").Invoke(null,new object[]{args[3]});return 0;}catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
class RoofExample {
 static T Add<T>(List<IGH_DocumentObject>a,T o,float x,float y)where T:IGH_DocumentObject{o.CreateAttributes();o.Attributes.Pivot=new PointF(x,y);a.Add(o);return o;}
 static GH_Panel Note(List<IGH_DocumentObject>a,string text,float x,float y,float w,float h){var p=Add(a,new GH_Panel(),x,y);p.UserText=text;p.Attributes.Bounds=new RectangleF(x,y,w,h);return p;}
 static GH_NumberSlider Slider(List<IGH_DocumentObject>a,string name,decimal value,decimal min,decimal max,int dec,float x,float y){var s=new GH_NumberSlider();s.NickName=name;s.Slider.Minimum=min;s.Slider.Maximum=max;s.Slider.DecimalPlaces=dec;s.Slider.Type=dec==0?Grasshopper.GUI.Base.GH_SliderAccuracy.Integer:Grasshopper.GUI.Base.GH_SliderAccuracy.Float;s.SetSliderValue(value);return Add(a,s,x,y);}
 static void Int(GH_Component c,int i,int v){var p=(Param_Integer)c.Params.Input[i];p.PersistentData.Clear();p.SetPersistentData(new GH_Integer(v));}
 static void Num(GH_Component c,int i,double v){var p=(Param_Number)c.Params.Input[i];p.PersistentData.Clear();p.SetPersistentData(new GH_Number(v));}
 static void Bool(GH_Component c,int i,bool v){var p=(Param_Boolean)c.Params.Input[i];p.PersistentData.Clear();p.SetPersistentData(new GH_Boolean(v));}
 static Curve Closed(params Point3d[] pts){return new PolylineCurve(pts);}
 static Curve Rect(double x0,double y0,double x1,double y1){return Closed(new Point3d(x0,y0,0),new Point3d(x1,y0,0),new Point3d(x1,y1,0),new Point3d(x0,y1,0),new Point3d(x0,y0,0));}
 static double Height(double x){return 300+1500*(1-Math.Abs(2*x/6000-1));}
 [MethodImpl(MethodImplOptions.NoInlining)] public static void Write(string folder){
 var core=new Rhino.Runtime.InProcess.RhinoCore(new string[]{"/nosplash","/notemplate"},Rhino.Runtime.InProcess.WindowStyle.NoWindow);
 var a=new List<IGH_DocumentObject>();
 Note(a,"ROOF RIB / 2D TEACHING CASE / TopOptLab 0.4\nStart: read LEGGIMI.md and the slides. Units: mm, N, MPa. World XY: Y is UP.\n1 BASELINE FEM > 2 OPTIMIZATION > 3 FINAL VERIFICATION. Press one RUN at a time.\nFive independent load cases; each contains six point resultants plus self-weight.\nGeometry is internalized: the file works without selecting Rhino objects.\nKeep the reference h=100 mm for the first run. If h changes, set Radius=180/h cells and rerun all stages.\nThis is an elastic planar plate concept; it does not check buckling, anchorage or building-code compliance.",20,20,1200,230);
 var boundary=Closed(new Point3d(0,0,0),new Point3d(6000,0,0),new Point3d(6000,300,0),new Point3d(3000,1800,0),new Point3d(0,300,0),new Point3d(0,0,0));
 var bp=Add(a,new Param_Curve{NickName="Roof boundary / mm",Hidden=true},40,320);bp.SetPersistentData(new GH_Curve(boundary));
 var keeps=new List<Curve>{Rect(0,0,200,200),Rect(5800,0,6000,200)};for(int j=0;j<6;j++){double x=500+j*1000,y=Height(x);keeps.Add(Rect(x-150,y-150,x+150,y+150));}
 var kp=Add(a,new Param_Curve{NickName="Keep attachment zones",Hidden=true},40,390);kp.SetPersistentData(keeps.Select(c=>new GH_Curve(c)));
 var domain=Add(a,new DomainComponent{Hidden=true},390,360);domain.Params.Input[0].AddSource(bp);domain.Params.Input[2].AddSource(kp);domain.Params.Input[3].AddSource(Slider(a,"Cell size / mm",100,25,100,0,20,480));
 var supports=new List<SupportComponent>();for(int i=0;i<2;i++){
  var pt=Add(a,new Param_Point{NickName=i==0?"A / pin":"B / anchored roller",Hidden=true},40,650+i*180);pt.SetPersistentData(new GH_Point(new Point3d(i*6000,0,0)));
  var s=Add(a,new SupportComponent{Hidden=true},390,650+i*180);s.Params.Input[0].AddSource(domain.Params.Output[0]);s.Params.Input[1].AddSource(pt);Bool(s,2,i==0);Bool(s,3,true);supports.Add(s);
 }
 var material=Add(a,new MaterialComponent(),390,1110);Num(material,4,12);Note(a,"",20,1400,560,330).AddSource(material.Params.Output[3]);
 var settings=Add(a,new EngineeringSettingsComponent(),940,890);Int(settings,0,0);Int(settings,1,4);Int(settings,12,1);Num(settings,5,12);
 settings.Params.Input[2].AddSource(Slider(a,"Volume fraction",.3m,.20m,.60m,2,600,1200));settings.Params.Input[3].AddSource(Slider(a,"Iteration limit",100,10,200,0,600,1260));settings.Params.Input[4].AddSource(Slider(a,"Radius in cells = 180 / h",1.8m,1m,10m,2,600,1320));var threshold=Slider(a,"Threshold",.4m,.2m,.8m,2,600,1380);settings.Params.Input[10].AddSource(threshold);
 Note(a,"REFERENCE SETTINGS\nE=210000 MPa; nu=0.30; density=7850 kg/m3.\nThickness=12 mm; tributary roof width=3000 mm (different quantities).\nVolume includes Keep zones. Symmetry X. No global stress/displacement limits imposed.\nMaterial SF=1.5 is a screening factor, not a code partial factor.\nGravity optimization is experimental; reanalyse the binary geometry.",600,1510,660,220);
 var cases=new List<LoadCaseComponent>();string[] names={"SLS snow uniform","ULS snow uniform","ULS snow left","ULS snow right","ULS wind uplift"};
 for(int ci=0;ci<5;ci++){
  float x=20+ci*680,y=2180;Note(a,"CASE "+(ci+1)+" / "+names[ci]+"\nForces in N; all six loads act together.\nWeight=1 (objective weight, not a load factor).",x,y-150,630,100);
  var lc=Add(a,new LoadCaseComponent(),x+490,y+540);var np=(Param_String)lc.Params.Input[1];np.PersistentData.Clear();np.SetPersistentData(new GH_String(names[ci]));
  for(int j=0;j<6;j++){
   double px=500+j*1000,py=Height(px),fx=0,fy;
   if(ci==0)fy=-4650;else if(ci<4)fy=-(ci==1||(ci==2&&j<3)||(ci==3&&j>=3)?6885:5085);else{fx=(j<3?-2250:2250);fy=2610;}
   var pt=Add(a,new Param_Point{NickName="P"+(j+1),Hidden=true},x+25,y+j*180);pt.SetPersistentData(new GH_Point(new Point3d(px,py,0)));
   var v=Add(a,new Param_Vector{NickName="F"+(j+1)+" = ("+fx+", "+fy+", 0) N"},x+25,y+j*180+65);v.SetPersistentData(new GH_Vector(new Vector3d(fx,fy,0)));
   var load=Add(a,new LoadComponent{Hidden=true},x+295,y+j*180);load.Params.Input[0].AddSource(domain.Params.Output[0]);load.Params.Input[1].AddSource(pt);load.Params.Input[2].AddSource(v);lc.Params.Input[0].AddSource(load.Params.Output[0]);
  }
  var grav=Add(a,new GravityComponent(),x+300,y+1190);grav.Params.Input[0].AddSource(domain.Params.Output[0]);var gv=Add(a,new Param_Vector{NickName="Gravity / m s-2"},x+25,y+1170);gv.SetPersistentData(new GH_Vector(new Vector3d(0,-9.80665*(ci>0&&ci<4?1.3:1),0)));grav.Params.Input[1].AddSource(gv);lc.Params.Input[0].AddSource(grav.Params.Output[0]);cases.Add(lc);
 }
 var review=Add(a,new ReviewControlsComponent(),3490,350);review.Params.Input[0].AddSource(Slider(a,"VIEW stage 0 FEM / 1 OPT / 2 VERIFY",0,0,2,0,3070,190));review.Params.Input[1].AddSource(Slider(a,"Load case",1,1,5,0,3070,250));review.Params.Input[2].AddSource(Slider(a,"Field 0 default / 1 displacement / 2 stress",0,0,2,0,3070,310));var deform=Slider(a,"Deformation display factor",0,0,1000,0,3070,550);var maximum=Slider(a,"Legend maximum / 0 auto",0,0,200,2,3070,610);
 Note(a,"REVIEW\nStage controls preview only. RUN buttons launch calculation.\nCase 1=SLS; 2=ULS snow; 3/4=unbalanced snow; 5=uplift.\nField 0: FEM von Mises / optimization density.\nFor stress comparisons use Field=2 and common maximum=60 MPa.\nOptimization stress is relaxed; only final verification recalculates the binary part.\nSet deformation factor=100 only for display, then return to 0 before inspecting geometry.",3070,750,750,250);
 EngineeringSolveComponent opt=null;
 for(int st=0;st<3;st++){
  float y=400+st*540;Note(a,new[]{"01 BASELINE FEM","02 OPTIMIZATION","03 FINAL VERIFICATION"}[st],1350,y-195,500,60);
  var solver=Add(a,new EngineeringSolveComponent(),1560,y);Int(solver,5,st);solver.Params.Input[0].AddSource(domain.Params.Output[0]);foreach(var s in supports)solver.Params.Input[1].AddSource(s.Params.Output[0]);foreach(var lc in cases)solver.Params.Input[2].AddSource(lc.Params.Output[0]);solver.Params.Input[3].AddSource(material.Params.Output[0]);solver.Params.Input[4].AddSource(settings.Params.Output[0]);if(st==2)solver.Params.Input[6].AddSource(opt.Params.Output[0]);if(st==1)opt=solver;
  for(int k=0;k<3;k++)solver.Params.Input[7+k].AddSource(Add(a,new GH_ButtonObject{NickName=new[]{"RUN","STOP","RESET"}[k]},1330,y+120+k*50));
  var select=Add(a,new CaseResultComponent(),1820,y-50);select.Params.Input[0].AddSource(solver.Params.Output[0]);select.Params.Input[1].AddSource(review.Params.Output[3]);
  GH_Component result=st==1?(GH_Component)new ResultsComponent():new FemResultsComponent();Add(a,result,2070,y);result.Params.Input[0].AddSource(select.Params.Output[0]);if(st==1)result.Params.Input[1].AddSource(threshold);result.Params.Input[st==1?4:1].AddSource(review.Params.Output[4]);result.Params.Input[st==1?6:4].AddSource(review.Params.Output[st]);result.Params.Input[2].AddSource(deform);result.Params.Input[st==1?5:3].AddSource(maximum);
  Note(a,"",2250,y-130,710,280).AddSource(result.Params.Output[st==1?3:8]);Note(a,"",1790,y+200,1140,85).AddSource(solver.Params.Output[1]);Note(a,"",1790,y+300,1140,70).AddSource(solver.Params.Output[3]);
 }
 // Independently verify the exact SDK raster and snapped point mapping against the Python fixture.
 var d=CadGeometry.Rasterize(boundary,new List<Curve>(),keeps,100,Plane.WorldXY);var fixture=JObject.Parse(File.ReadAllText(Path.Combine(folder,"roof_request_h100.json")));var expected=fixture["domain"];
 if(!d.active.SequenceEqual(expected["active"].Values<int>())||!d.solid.SequenceEqual(expected["solid"].Values<int>()))throw new Exception("CAD/Python grid differs");
 for(int j=0;j<6;j++){double x=500+j*1000;var ns=CadGeometry.Select(d,new List<IGH_GeometricGoo>{new GH_Point(new Point3d(x,Height(x),0))});if(ns.Length!=1||ns[0]!=(int)fixture["load_cases"][0]["loads"][j]["nodes"][0])throw new Exception("Load snapping differs");}
 var doc=new GH_Document();GH_Document.EnableSolutions=true;foreach(var obj in a)doc.AddObject(obj,false);doc.Enabled=true;Grasshopper.Instances.DocumentServer.AddDocument(doc);doc.NewSolution(true);
 foreach(var lc in cases){lc.CollectData();lc.ComputeData();if(lc.RuntimeMessageLevel==GH_RuntimeMessageLevel.Error)throw new Exception("Load Case error: "+String.Join(";",lc.RuntimeMessages(GH_RuntimeMessageLevel.Error)));var all=lc.Params.Output[0].VolatileData.AllData(true).ToList();if(all.Count!=1)throw new Exception("Load Case produced no data");var data=JObject.Parse(all[0].ToString());if(((JArray)data["loads"]).Count!=7)throw new Exception("Lost loads");}
 foreach(var comp in a.OfType<GH_Component>())if(comp is DomainComponent||comp is SupportComponent||comp is LoadComponent||comp is GravityComponent||comp is MaterialComponent||comp is EngineeringSettingsComponent){if(comp.RuntimeMessageLevel==GH_RuntimeMessageLevel.Error)throw new Exception(comp.Name+": "+String.Join(";",comp.RuntimeMessages(GH_RuntimeMessageLevel.Error)));}
 Console.WriteLine("Headless Grasshopper dataflow: all five cases contain six nodal loads + gravity; geometry/material/settings without errors.");
 WriteArchive(folder,a);
 Console.WriteLine("CAD and Python match: "+d.active.Length+" active cells; "+d.solid.Length+" keep cells; all six load nodes checked.");core.Dispose();
 }
 static void WriteArchive(string folder,List<IGH_DocumentObject>objects){
 string name="roof_2d_classroom";var archive=new GH_IO.Serialization.GH_Archive();var definition=archive.CreateTopLevelNode("Definition");definition.SetVersion("plugin_version",1,0,7);var header=definition.CreateChunk("DocumentHeader");header.SetGuid("DocumentID",Guid.NewGuid());header.SetString("Preview","Shaded");header.SetInt32("PreviewMeshType",1);
 var properties=new GH_DocumentProperties{ProjectFileName=name+".gh",Description="6 m steel roof rib / teaching case / N-mm-MPa / TopOptLab 0.4",ViewTarget=new System.Drawing.Point(100,70),ZoomFactor=.55f};if(!properties.Write(definition))throw new IOException("Properties");definition.CreateChunk("RcpLayout").SetInt32("GroupCount",0);definition.CreateChunk("GHALibraries").SetInt32("Count",0);var list=definition.CreateChunk("DefinitionObjects");list.SetInt32("ObjectCount",objects.Count);
 for(int i=0;i<objects.Count;i++){var obj=objects[i];obj.Attributes.PerformLayout();var chunk=list.CreateChunk("Object",i);chunk.SetGuid("GUID",obj.ComponentGuid);chunk.SetString("Name",obj.Name);if(!obj.Write(chunk.CreateChunk("Container")))throw new IOException("Serialize "+obj.Name);}
 foreach(string ext in new[]{".ghx",".gh"}){
  string file=Path.Combine(folder,name+ext);if(!archive.WriteToFile(file,true,false))throw new IOException("Write");var rb=new GH_IO.Serialization.GH_Archive();if(!rb.ReadFromFile(file))throw new IOException("Read");var def=rb.GetRootNode.FindChunk("Definition");var rp=new GH_DocumentProperties();if(!rp.Read(def)||rp.ProjectFileName!=properties.ProjectFileName)throw new IOException("Properties readback");var rl=def.FindChunk("DefinitionObjects");
  for(int i=0;i<objects.Count;i++){var clone=(IGH_DocumentObject)Activator.CreateInstance(objects[i].GetType());clone.CreateAttributes();if(!clone.Read(rl.FindChunk("Object",i).FindChunk("Container"))||clone.InstanceGuid!=objects[i].InstanceGuid)throw new IOException("Object readback");}
 }
 Console.WriteLine("Grasshopper SDK archive readback passed: "+objects.Count+" objects; .gh and .ghx. Not an interactive Rhino test.");
 }
}
