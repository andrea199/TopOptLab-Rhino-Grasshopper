// SPDX-License-Identifier: GPL-3.0-or-later
using System;using System.Linq;using System.Drawing;using System.Collections.Generic;
using Grasshopper.Kernel;using Grasshopper.Kernel.Parameters;using Grasshopper.Kernel.Special;using Grasshopper.Kernel.Types;
namespace TopoptLab.GH {
 public static class ShelfBracketExample {
  static T Add<T>(List<IGH_DocumentObject>a,T o,float x,float y)where T:IGH_DocumentObject{o.CreateAttributes();o.Attributes.Pivot=new PointF(x,y);a.Add(o);return o;}
  static GH_NumberSlider Slider(List<IGH_DocumentObject>a,string name,decimal value,decimal min,decimal max,int dec,float x,float y){var s=new GH_NumberSlider();s.NickName=name;s.Slider.Minimum=min;s.Slider.Maximum=max;s.Slider.DecimalPlaces=dec;s.Slider.Type=dec==0?Grasshopper.GUI.Base.GH_SliderAccuracy.Integer:Grasshopper.GUI.Base.GH_SliderAccuracy.Float;s.SetSliderValue(value);return Add(a,s,x,y);}
  static GH_Panel Note(List<IGH_DocumentObject>a,string text,float x,float y,float w,float h){var p=Add(a,new GH_Panel(),x,y);p.UserText=text;p.Attributes.Bounds=new RectangleF(x,y,w,h);return p;}
  static void SetSlider(IGH_Param input,decimal value,decimal min,decimal max){var s=input.Sources.OfType<GH_NumberSlider>().Single();s.Slider.Minimum=min;s.Slider.Maximum=max;s.SetSliderValue(value);}
  static void Int(GH_Component c,int index,int value){var p=(Param_Integer)c.Params.Input[index];p.PersistentData.Clear();p.SetPersistentData(new GH_Integer(value));}
  public static List<IGH_DocumentObject> Build() {
   var a=FinalExample.Build();var old=a.OfType<Example3DComponent>().Single();var domain=a.OfType<Domain3DComponent>().Single();var material=a.OfType<MaterialComponent>().Single();var settings=a.OfType<EngineeringSettingsComponent>().Single();var review=a.OfType<ReviewControlsComponent>().Single();var limits=a.OfType<DesignLimitsComponent>().Single();
   var obsolete=new List<IGH_DocumentObject>{old};
   obsolete.AddRange(old.Params.Input.SelectMany(p=>p.Sources).Cast<IGH_DocumentObject>());
   obsolete.AddRange(a.OfType<Support3DComponent>().Cast<IGH_DocumentObject>());obsolete.AddRange(a.OfType<LoadCaseComponent>().Cast<IGH_DocumentObject>());
   foreach(var l in a.OfType<Load3DComponent>()){obsolete.Add(l);obsolete.AddRange(l.Params.Input[2].Sources.Cast<IGH_DocumentObject>());}
   obsolete.AddRange(a.OfType<GH_Panel>().Where(p=>p.UserText.StartsWith("PARAMETRIC GEOMETRY")).Cast<IGH_DocumentObject>());
   foreach(var o in obsolete.Distinct())a.Remove(o);
   var title=a.OfType<GH_Panel>().First(p=>p.UserText.StartsWith("ENGINEERING WORKFLOW"));
   title.UserText="SHELF BRACKET / 250 mm / FOUR ALTERNATIVE LOAD CASES\nUnits mm, N. X projects from wall; Y is width; Z is UP. Payload is kg per bracket.\n1 BASELINE > 2 OPTIMIZATION > 3 VOXEL VERIFICATION > 4 EXTRACT > 5 FINAL FEM.\nCase 1 distributed; 2 front; 3 front-right; 4 front-left. Every case adds shelf share and bracket self-weight.\nTwo wall holes and two shelf holes, with reserved tool access. EXTRACT restores nominal CAD plates and holes independently of the voxel grid.\nDefault: 5 mm cells, CPU AMG (2). CUDA (4) requires a separately configured GPU runtime. Never change solver while a job is running.\nABS is an injection-molding reference, not printed-material qualification. Wall pads are rigid idealizations.";
   var geometry=Add(a,new ShelfBracket3DComponent{Hidden=true},-120,460);
   string[] names={"Length / mm","Height / mm","Width / mm","Keep plate thickness / mm","Nominal hole diameter / mm","Wall hole pitch / mm","Top hole inset / mm","Tool access diameter / mm","Tool access depth / mm","Position X / mm","Position Y / mm","Position Z / mm"};
   decimal[] values={250,150,25,10,8,100,40,16,25,0,0,0},mins={200,120,20,5,4,40,25,8,0,-500,-500,-500},maxs={300,220,50,20,12,160,90,24,60,500,500,500};
   for(int k=0;k<12;k++)geometry.Params.Input[k].AddSource(Slider(a,names[k],values[k],mins[k],maxs[k],1,-690,270+k*60));
   for(int k=0;k<3;k++){domain.Params.Input[k].RemoveAllSources();domain.Params.Input[k].AddSource(geometry.Params.Output[k]);}
   SetSlider(domain.Params.Input[3],5m,.5m,10);SetSlider(domain.Params.Input[4],250000,8000,2000000);
   Note(a,"",-700,-280,1700,190).AddSource(domain.Params.Output[2]);
    var conditions=Add(a,new BracketConditions3DComponent{Hidden=true},760,510);
   conditions.Params.Input[0].AddSource(domain.Params.Output[0]);conditions.Params.Input[1].AddSource(geometry.Params.Output[3]);conditions.Params.Input[2].AddSource(material.Params.Output[0]);
   conditions.Params.Input[3].AddSource(Slider(a,"Payload PER BRACKET / kg",4,1,10,2,-350,1100));
   conditions.Params.Input[4].AddSource(Slider(a,"Shelf share per bracket / kg / ASSUMED",.5m,0,5,2,-350,1160));
   conditions.Params.Input[5].AddSource(Slider(a,"Front loaded strip depth / mm",20,5,60,1,-350,1220));
   conditions.Params.Input[6].AddSource(Slider(a,"Lateral offset / fraction of half width",.6m,.1m,.8m,2,-350,1280));
   Note(a,"", -700,1420,1200,380).AddSource(conditions.Params.Output[5]);
   Note(a,"GEOMETRY CONTROLS\nHoles remain circular when resized. Invalid overlapping clearances are rejected.\nB = design envelope; Void = holes/tool space; Keep = attachment plates.\nDefault 5 mm grid; final CAD interfaces restore nominal holes to a separate chord tolerance.\nRAM and GPU budgets are checked before solving. Refinement changes the model; verify convergence.\nFinal surfaces must preserve nominal CAD plates and keep screw/tool space empty.",-700,1010,320,360);
   Note(a,"", -700,1830,1200,150).AddSource(geometry.Params.Output[4]);
   foreach(var p in a.OfType<GH_Panel>().Where(p=>p.Sources.Contains(material.Params.Output[3]))){p.Attributes.Pivot=new PointF(-700,2060);p.Attributes.Bounds=new RectangleF(-700,2060,630,440);}
   SetSlider(material.Params.Input[0],1,0,1);
   SetSlider(settings.Params.Input[0],2,0,4);
    settings.Params.Input[16].AddSource(Slider(a,"RAM budget GiB / 0 automatic",0,0,48,1,580,2110));
    settings.Params.Input[17].AddSource(Slider(a,"Physical filter radius / mm",9,1,30,2,580,2170));SetSlider(settings.Params.Input[10],.35m,.1m,.9m);
   SetSlider(settings.Params.Input[2],.35m,.15m,.8m);SetSlider(settings.Params.Input[3],60,10,200);Int(settings,11,3);
   SetSlider(review.Params.Input[1],1,1,4);
   SetSlider(limits.Params.Input[0],1,0,5);SetSlider(limits.Params.Input[1],0,0,50);
   var notes=a.OfType<GH_Panel>().First(p=>p.UserText.StartsWith("DESIGN LIMITS"));
   notes.UserText="DESIGN LIMITS / preliminary study\nDisplacement target = 1 mm (chosen functional target, not a standard).\nStress limit is OFF until printed material data are supplied.\nEnforce uses MMA for the displacement target in every case.\nNo creep, layer bonding, anchor pull-out, wall contact or long-term load rating.\nReference ABS yield screening is not a printed-part allowable.";
   foreach(var solver in a.OfType<EngineeringSolveComponent>()) {
    solver.Params.Input[1].RemoveAllSources();solver.Params.Input[1].AddSource(conditions.Params.Output[0]);
    solver.Params.Input[2].RemoveAllSources();for(int k=1;k<=4;k++)solver.Params.Input[2].AddSource(conditions.Params.Output[k]);
   }
   var print=a.OfType<PrintReviewComponent>().Single();var dir=(Param_Vector)print.Params.Input[0].Sources[0];dir.PersistentData.Clear();dir.SetPersistentData(new GH_Vector(Rhino.Geometry.Vector3d.YAxis));dir.NickName="Print build direction / +Y / proposed side orientation";
   var surface=a.OfType<FinalGeometry3DComponent>().Single();surface.Params.Input[8].AddSource(geometry.Params.Output[3]);surface.Params.Input[9].AddSource(conditions.Params.Output[8]);surface.Params.Input[10].AddSource(Slider(a,"CAD hole chord tolerance / mm",.05m,.01m,.2m,3,1040,3000));surface.Params.Input[11].AddSource(Slider(a,"CAD envelope cleanup / mm / 0 off",0,0,.1m,3,1040,3060));surface.Params.Input[12].AddSource(Slider(a,"CAD web cleanup / mm / 0 off",.01m,0,.05m,3,1040,3120));
    var fem=a.OfType<FinalFem3DComponent>().Single();SetSlider(fem.Params.Input[1],4,1,12);
   var frame=Note(a,"WALL CONNECTION\nSupports cover two rear face patches around the wall holes.\nAll three displacements are fixed on those patches: ideal rigid anchorage.\nActual screws, wall material, washers and clamping must be designed separately.\nLoad centres/moments shown above are the actual voxel patch resultants.",-700,2580,1200,130);
   return a;
  }
 }
}
