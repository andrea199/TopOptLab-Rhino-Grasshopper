using System;
using System.Drawing;
using System.Collections.Generic;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Parameters;
using Grasshopper.Kernel.Special;
using Grasshopper.Kernel.Types;
using Rhino.Geometry;
namespace TopoptLab.GH {
 public static class EngineeringExample {
  static T Add<T>(List<IGH_DocumentObject>a,T o,float x,float y)where T:IGH_DocumentObject{o.CreateAttributes();o.Attributes.Pivot=new PointF(x,y);a.Add(o);return o;}
  static GH_NumberSlider Slider(List<IGH_DocumentObject>a,string name,decimal value,decimal min,decimal max,int decimals,float x,float y){var s=new GH_NumberSlider();s.NickName=name;s.Slider.Minimum=min;s.Slider.Maximum=max;s.Slider.DecimalPlaces=decimals;s.Slider.Type=decimals==0?Grasshopper.GUI.Base.GH_SliderAccuracy.Integer:Grasshopper.GUI.Base.GH_SliderAccuracy.Float;s.SetSliderValue(value);return Add(a,s,x,y);}
  static GH_Panel Note(List<IGH_DocumentObject>a,string text,float x,float y,float w,float h){var p=Add(a,new GH_Panel(),x,y);p.UserText=text;p.Attributes.Bounds=new RectangleF(x,y,w,h);return p;}
  static CaseResultComponent AddCase(List<IGH_DocumentObject>a,EngineeringSolveComponent solver,ReviewControlsComponent review,float y){var c=Add(a,new CaseResultComponent(),1720,y-80);c.Params.Input[0].AddSource(solver.Params.Output[0]);c.Params.Input[1].AddSource(review.Params.Output[3]);return c;}
  public static List<IGH_DocumentObject> Build(bool solid,bool distributed=false,bool limited=false){
   var a=new List<IGH_DocumentObject>();
   Note(a,"ENGINEERING WORKFLOW / "+(solid?"3D":"2D")+"\n1 Run BASELINE FEM. 2 Run OPTIMIZATION. 3 After completion, Run FINAL VERIFICATION.\nUse REVIEW to choose Stage, Case and Field. Only one stage preview is visible. Read the viewport legend.\nThreshold verification is binary voxel FEM on the same grid, without smoothing or remeshing.\nA removed support/load node or disconnected shape is rejected. Preserve interfaces or change the design.\nMaterial properties are reference data; inspect Material Info and report limitations.",20,20,1800,170);
   GH_Component geometry=solid?(GH_Component)new Example3DComponent():new ScenarioGeometryComponent();geometry.Hidden=true;Add(a,geometry,60,380);
   if(!solid){var param=(Param_Integer)geometry.Params.Input[0];param.PersistentData.Clear();param.SetPersistentData(new GH_Integer(distributed?0:3));}
   ParametricExamples.Sliders(a,geometry,solid?0:1,solid?120:12,solid?60:6,solid?30:0);
   GH_Component domain=solid?(GH_Component)new Domain3DComponent():new DomainComponent();domain.Hidden=true;Add(a,domain,380,320);domain.Params.Input[0].AddSource(geometry.Params.Output[0]);
   if(solid){domain.Params.Input[2].AddSource(geometry.Params.Output[3]);domain.Params.Input[4].AddSource(Slider(a,"Voxel limit",8000,8000,32768,0,30,880));}
   domain.Params.Input[3].AddSource(Slider(a,"Cell size",solid?5m:.25m,solid?2.5m:.125m,solid?10m:.5m,3,30,810));
   GH_Component support=solid?(GH_Component)new Support3DComponent():new SupportComponent();Add(a,support,650,290);support.Params.Input[0].AddSource(domain.Params.Output[0]);support.Params.Input[1].AddSource(geometry.Params.Output[solid?1:3]);
   var cases=new List<LoadCaseComponent>();
   if(distributed){
    GH_Component surface=solid?(GH_Component)new SurfaceLoad3DComponent():new SurfaceLoadComponent();Add(a,surface,650,520);surface.Params.Input[0].AddSource(domain.Params.Output[0]);
    // Apply pressure to the top boundary; optional G restricts the patch.
    var side=(Param_Integer)surface.Params.Input[5];side.PersistentData.Clear();side.SetPersistentData(new GH_Integer(solid?5:3));
    surface.Params.Input[3].AddSource(Slider(a,"Pressure / force per length squared",.1m,-1m,1m,3,320,840));
    surface.Params.Input[2].AddSource(Slider(a,"Surface mode 0=pressure 1=traction",0,0,1,0,320,900));
    var traction=Add(a,new Param_Vector{NickName="Traction / force per length squared"},320,780);traction.SetPersistentData(new GH_Vector(solid?new Vector3d(0,0,-.1):new Vector3d(0,-.1,0)));surface.Params.Input[4].AddSource(traction);
    var gravity=Add(a,new GravityComponent(),650,730);gravity.Params.Input[0].AddSource(domain.Params.Output[0]);
    var g=Add(a,new Param_Vector{NickName="Acceleration / m per second squared"},320,720);g.SetPersistentData(new GH_Vector(solid?new Vector3d(0,0,-9.80665):new Vector3d(0,-9.80665,0)));gravity.Params.Input[1].AddSource(g);
    for(int i=0;i<2;i++){
     var c=Add(a,new LoadCaseComponent(),900,510+i*200);if(i==0)c.Params.Input[0].AddSource(surface.Params.Output[0]);c.Params.Input[0].AddSource(gravity.Params.Output[0]);
     var name=(Param_String)c.Params.Input[1];name.PersistentData.Clear();name.SetPersistentData(new GH_String(i==0?"Surface load + self-weight":"Self-weight only"));cases.Add(c);
    }
    Note(a,"DISTRIBUTED LOADS\nPressure is positive inward. Mode 1 uses vector traction. Units follow Material: default N/mm^2.\nGravity always uses m/s^2; Material supplies mass density.\nCase 1: surface load and gravity simultaneously. Case 2: gravity alone, independent.\nPressure interface cells remain solid. Gravity optimization uses a fixed volume budget and a signed-gradient update.\nInspect Patch output, reports and termination status. These are fixed grid facets, not evolving-surface pressure.",20,1960,1250,210);
   }else{
   for(int i=0;i<2;i++){
    GH_Component load=solid?(GH_Component)new Load3DComponent():new LoadComponent();Add(a,load,650,510+i*190);load.Params.Input[0].AddSource(domain.Params.Output[0]);load.Params.Input[1].AddSource(geometry.Params.Output[solid?2:5+i]);
    var force=Add(a,new Param_Vector{NickName=solid?(i==0?"Down / 100 force units":"Side / 100 force units"):"Down / 1 force unit"},420,530+i*190);
    force.SetPersistentData(new GH_Vector(solid?(i==0?new Vector3d(0,0,-100):new Vector3d(0,100,0)):new Vector3d(0,-1,0)));load.Params.Input[2].AddSource(force);
    var c=Add(a,new LoadCaseComponent(),900,510+i*190);c.Params.Input[0].AddSource(load.Params.Output[0]);var name=(Param_String)c.Params.Input[1];name.PersistentData.Clear();name.SetPersistentData(new GH_String("Case "+(i+1)));cases.Add(c);
   }
   }
   var material=Add(a,new MaterialComponent(),650,1070);material.Params.Input[0].AddSource(Slider(a,"Material 0=steel 1=ABS",0,0,1,0,30,1000));
   material.Params.Input[4].AddSource(Slider(a,"Stock thickness / mm",0,0,100,1,30,1060));
   Note(a,"",20,1450,570,440).AddSource(material.Params.Output[3]);
   var settings=Add(a,new EngineeringSettingsComponent(),1000,1180);
   settings.Params.Input[0].AddSource(Slider(a,"Backend 0=direct 1=CG 2=AMG 3=matrixfree 4=CUDA",1,0,4,0,580,1540));
   settings.Params.Input[1].AddSource(Slider(a,"CPU thread limit",4,1,16,0,580,1600));
   settings.Params.Input[2].AddSource(Slider(a,"Material fraction",limited?.6m:solid?.5m:.45m,.2m,.8m,2,580,1660));
   settings.Params.Input[3].AddSource(Slider(a,"Iteration limit",limited?80:40,10,200,0,580,1720));
   settings.Params.Input[10].AddSource(Slider(a,"Verification threshold",limited?.4m:.5m,.1m,.9m,2,580,1780));
   var review=Add(a,new ReviewControlsComponent(),3270,420);
   review.Params.Input[0].AddSource(Slider(a,"VIEW: 0 baseline / 1 design / 2 verification",0,0,2,0,2880,220));
   review.Params.Input[1].AddSource(Slider(a,"Load case",1,1,2,0,2880,280));
   review.Params.Input[2].AddSource(Slider(a,"Field: 0 default / 1 displacement / 2 stress",0,0,2,0,2880,340));
   var deformation=Slider(a,"Deformation display factor",0,0,10000,0,2880,600);
   var maximum=Slider(a,"Shared legend maximum / 0 auto",0,0,1000,5,2880,660);
   Note(a,"REVIEW\nStage selects the visible result, not the calculation to run.\nCase selects a saved response after completion.\nField 0: FEM stress or design density. Field 1: displacement.\nField 2: stress; during optimization this is RELAXED design stress.\nSet the same positive legend maximum to compare a field across stages.\nDeformation scale changes display only. Report contains all cases.",2880,730,740,230);
   var limits=Add(a,new DesignLimitsComponent(),650,2330);
   limits.Params.Input[0].AddSource(Slider(a,"Maximum displacement / model units",limited?(solid?.03m:.0002m):0,0,solid?1m:.01m,7,20,2250));
   limits.Params.Input[1].AddSource(Slider(a,"Maximum stress / MPa",limited?10m:0,0,250,3,20,2310));
   Note(a,"DESIGN LIMITS\n0 disables a limit. Limits apply to every independent case.\nEnforce=True uses MMA during optimization; False only checks results.\nThese are illustrative values; choose project-specific limits.\nConvergence and feasibility are separate: read both in Status and Report.\nAfter extraction, run FINAL VERIFICATION: relaxed design stress does not certify the part.",20,2430,1250,200);
   Note(a,"",750,2310,700,140).AddSource(limits.Params.Output[1]);
   EngineeringSolveComponent previous=null,baseline=null;
   for(int stage=0;stage<3;stage++){
    float y=380+stage*650;
    Note(a,new[]{"BASELINE FEM","OPTIMIZATION","FINAL VERIFICATION"}[stage],1370,y-220,450,65);
    var solver=Add(a,new EngineeringSolveComponent(),1500,y);solver.Params.Input[0].AddSource(domain.Params.Output[0]);solver.Params.Input[1].AddSource(support.Params.Output[0]);foreach(var c in cases)solver.Params.Input[2].AddSource(c.Params.Output[0]);solver.Params.Input[3].AddSource(material.Params.Output[0]);solver.Params.Input[4].AddSource(settings.Params.Output[0]);
    solver.Params.Input[10].AddSource(limits.Params.Output[0]);
    var mode=(Param_Integer)solver.Params.Input[5];mode.PersistentData.Clear();mode.SetPersistentData(new GH_Integer(stage));
    if(stage==2)solver.Params.Input[6].AddSource(previous.Params.Output[0]);
    for(int k=0;k<3;k++)solver.Params.Input[7+k].AddSource(Add(a,new GH_ButtonObject{NickName=new[]{"RUN","STOP","RESET"}[k]},1290,y+180+k*50));
    GH_Component result=solid?(GH_Component)new Results3DComponent():stage==1?(GH_Component)new ResultsComponent():new FemResultsComponent();Add(a,result,1910,y);result.Params.Input[0].AddSource(AddCase(a,solver,review,y).Params.Output[0]);if(stage==1)result.Params.Input[1].AddSource(settings.Params.Input[10].Sources[0]);
    result.Params.Input[solid?2:stage==1?4:1].AddSource(review.Params.Output[4]);
    result.Params.Input[solid?8:stage==1?6:4].AddSource(review.Params.Output[stage]);
    result.Params.Input[solid?3:2].AddSource(deformation);
    result.Params.Input[solid?7:stage==1?5:3].AddSource(maximum);
    if(stage==0)baseline=solver;
    else {var comparison=Add(a,new CompareResultsComponent(),3060,y+30);comparison.Params.Input[0].AddSource(baseline.Params.Output[0]);comparison.Params.Input[1].AddSource(solver.Params.Output[0]);Note(a,"",3270,y-70,770,300).AddSource(comparison.Params.Output[0]);}
    Note(a,"",1720,y+280,640,90).AddSource(solver.Params.Output[1]);Note(a,"",2130,y-100,710,330).AddSource(result.Params.Output[solid?2:stage==1?3:8]);
    Note(a,"",1720,y+390,1140,80).AddSource(solver.Params.Output[3]);
    if(stage==1)previous=solver;
   }
   return a;
  }
 }
}
