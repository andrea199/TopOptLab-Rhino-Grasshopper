// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
using System.Drawing;
using Newtonsoft.Json.Linq;
using Rhino.Geometry;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Parameters;
using Grasshopper.Kernel.Special;
using Grasshopper.Kernel.Types;
namespace TopoptLab.GH
{
    public static class Scenarios
    {
        public static JArray Catalog()
        { using(var stream=Assembly.GetExecutingAssembly().GetManifestResourceStream("TopoptLab.Scenarios"))
          using(var reader=new StreamReader(stream)) return JArray.Parse(reader.ReadToEnd()); }
    }
    public sealed class ScenarioGeometryComponent : Component
    {
        public ScenarioGeometryComponent():base("TopOpt Scenario Geometry","Scenario","0 Cantilever; 1 Supported beam; 2 Two holes; 3 Two loads. Teaching geometry in XY.","1 Geometry") {}
        public override Guid ComponentGuid { get { return new Guid("00e42d62-5359-4473-8294-9a923e2a8a01"); } }
        protected override void RegisterInputParams(GH_InputParamManager p) { p.AddIntegerParameter("Case","Case","0 to 3",GH_ParamAccess.item,0); RegisterGeometry(p,false); ((Param_Number)p[1]).PersistentData.Clear();p[1].Optional=true;((Param_Number)p[2]).PersistentData.Clear();p[2].Optional=true; }
        protected override void RegisterOutputParams(GH_OutputParamManager p)
        {
            p.AddCurveParameter("Boundary","B","Closed boundary",GH_ParamAccess.item);
            p.AddCurveParameter("Holes","H","Void contours",GH_ParamAccess.list);
            p.AddCurveParameter("Keep","K","Preserved strips, if present",GH_ParamAccess.list);
            p.AddGeometryParameter("Support 1","S1","Edge or point",GH_ParamAccess.item);
            p.AddGeometryParameter("Support 2","S2","Second support, if present",GH_ParamAccess.item);
            p.AddPointParameter("Load 1","L1","First load point",GH_ParamAccess.item);
            p.AddPointParameter("Load 2","L2","Second load point, if present",GH_ParamAccess.item);
        }
        static Curve Rect(double x,double y,double X,double Y)
        { return new Rectangle3d(Plane.WorldXY,new Point3d(x,y,0),new Point3d(X,Y,0)).ToNurbsCurve(); }
        protected override void SolveInstance(IGH_DataAccess da)
        {
            int index=0;if(!da.GetData(0,ref index))return;
            try {
                var cases=Scenarios.Catalog();if(index<0||index>=cases.Count)throw new ArgumentException("Case must be 0 to 3");
                var c=cases[index];var transform=ParametricExamples.Read(da,1,(double)c["width"],(double)c["height"]);da.SetData(0,ParametricExamples.Curve(Rect(0,0,(double)c["width"],(double)c["height"]),transform));
                var holes=new List<Curve>();foreach(var h in c["holes"])holes.Add(ParametricExamples.Curve(new Circle(new Point3d((double)h[0],(double)h[1],0),(double)h[2]).ToNurbsCurve(),transform));da.SetDataList(1,holes);
                var keep=new List<Curve>();foreach(var k in c["keep"])keep.Add(ParametricExamples.Curve(Rect((double)k[0],(double)k[1],(double)k[2],(double)k[3]),transform));da.SetDataList(2,keep);
                for(int k=0;k<((JArray)c["supports"]).Count;k++) {
                    var s=c["supports"][k];var pt=new Point3d((double)s["x"],(double)s["y"],0);
                    if((string)s["kind"]=="edge")da.SetData(3+k,new GH_Curve(ParametricExamples.Curve(new LineCurve(pt,new Point3d(pt.X,(double)s["y2"],0)),transform)));
                    else da.SetData(3+k,new GH_Point(ParametricExamples.Point(pt,transform)));
                }
                for(int k=0;k<((JArray)c["loads"]).Count;k++)da.SetData(5+k,ParametricExamples.Point(new Point3d((double)c["loads"][k][0],(double)c["loads"][k][1],0),transform));
                Message=(string)c["title"];
            } catch(Exception e){Error(e);}
        }
    }
    public static class ScenarioDocument
    {
        static T Add<T>(List<IGH_DocumentObject> a,T o,float x,float y) where T:IGH_DocumentObject
        {o.CreateAttributes();o.Attributes.Pivot=new PointF(x,y);a.Add(o);return o;}
        static GH_Panel Note(List<IGH_DocumentObject> a,string text,float x,float y,float w,float h)
        {var p=Add(a,new GH_Panel(),x,y);p.UserText=text;p.Attributes.Bounds=new RectangleF(x,y,w,h);return p;}
        static GH_NumberSlider Slider(List<IGH_DocumentObject>a,string name,decimal value,decimal min,decimal max,int decimals,float x,float y)
        {var s=new GH_NumberSlider();s.NickName=name;s.Slider.Minimum=min;s.Slider.Maximum=max;s.Slider.DecimalPlaces=decimals;s.Slider.Type=decimals==0?Grasshopper.GUI.Base.GH_SliderAccuracy.Integer:Grasshopper.GUI.Base.GH_SliderAccuracy.Float;s.SetSliderValue(value);return Add(a,s,x,y);}
        public static List<IGH_DocumentObject> Build(int index,bool fem)
        {
            var c=Scenarios.Catalog()[index];var a=new List<IGH_DocumentObject>();
            Note(a,(string)c["title"]+" / "+(fem?"FULL-SOLID FEM":"OPTIMIZATION")+"\n"+(string)c["note"]+"\nExample units: mm, N; E=210000 N/mm2, nu=0.3, thickness=2 mm. Each load: (0,-1,0) N.\nIllustrative data: use your actual material and loads. No automatic yield check.",30,20,1450,135);
            var geometry=Add(a,new ScenarioGeometryComponent{Hidden=true},60,330);
            ((Param_Integer)geometry.Params.Input[0]).PersistentData.Clear();
            ((Param_Integer)geometry.Params.Input[0]).SetPersistentData(new GH_Integer(index));
            var boundary=Add(a,new Param_Curve{NickName="Boundary",Hidden=true},260,250);boundary.AddSource(geometry.Params.Output[0]);
            var domain=Add(a,new DomainComponent{Hidden=true},460,300);domain.Params.Input[0].AddSource(boundary);
            if(((JArray)c["holes"]).Count>0)domain.Params.Input[1].AddSource(geometry.Params.Output[1]);
            if(((JArray)c["keep"]).Count>0)domain.Params.Input[2].AddSource(geometry.Params.Output[2]);
            domain.Params.Input[3].AddSource(Slider(a,"Cell size h",.25m,.125m,.5m,3,240,640));
            var grid=Add(a,new Param_Mesh{NickName="Grid OFF",Hidden=true},490,700);grid.AddSource(domain.Params.Output[1]);
            GH_Component solver=fem?(GH_Component)new FemAnalyzeComponent():new SolverComponent();Add(a,solver,1180,350);solver.Params.Input[0].AddSource(domain.Params.Output[0]);
            for(int k=0;k<((JArray)c["supports"]).Count;k++) {
                var selection=Add(a,new Param_Geometry{NickName="Support "+(k+1),Hidden=true},700,260+130*k);selection.AddSource(geometry.Params.Output[3+k]);
                var support=Add(a,new SupportComponent(),940,260+130*k);support.Params.Input[0].AddSource(domain.Params.Output[0]);support.Params.Input[1].AddSource(selection);
                ((Param_Boolean)support.Params.Input[2]).PersistentData.Clear();
                ((Param_Boolean)support.Params.Input[2]).SetPersistentData(new GH_Boolean((bool)c["supports"][k]["fix_x"]));
                ((Param_Boolean)support.Params.Input[3]).PersistentData.Clear();
                ((Param_Boolean)support.Params.Input[3]).SetPersistentData(new GH_Boolean((bool)c["supports"][k]["fix_y"]));
                solver.Params.Input[1].AddSource(support.Params.Output[0]);
            }
            for(int k=0;k<((JArray)c["loads"]).Count;k++) {
                var pt=Add(a,new Param_Point{NickName="Load point "+(k+1),Hidden=true},700,550+130*k);pt.AddSource(geometry.Params.Output[5+k]);
                var force=Add(a,new Param_Vector{NickName="F"+(k+1)+" = (0,-1,0) N"},700,600+130*k);force.SetPersistentData(new GH_Vector(new Vector3d(0,-1,0)));
                var load=Add(a,new LoadComponent(),940,550+130*k);load.Params.Input[0].AddSource(domain.Params.Output[0]);load.Params.Input[1].AddSource(pt);load.Params.Input[2].AddSource(force);solver.Params.Input[2].AddSource(load.Params.Output[0]);
            }
            int material=fem?3:6;
            solver.Params.Input[material].AddSource(Slider(a,"E N/mm2",210000,1,300000,0,720,860));
            solver.Params.Input[material+1].AddSource(Slider(a,"nu",.3m,0,.49m,2,720,910));
            solver.Params.Input[material+2].AddSource(Slider(a,"Thickness mm",2,.1m,20,2,720,960));
            if(!fem) {
                solver.Params.Input[3].AddSource(Slider(a,"Volume",.45m,.25m,.8m,2,1030,820));
                solver.Params.Input[4].AddSource(Slider(a,"Iterations",80,10,200,0,1030,870));
                solver.Params.Input[5].AddSource(Slider(a,"Filter / cells",2.4m,1,6,1,1030,920));
            }
            int button=fem?6:9;
            for(int k=0;k<3;k++)solver.Params.Input[button+k].AddSource(Add(a,new GH_ButtonObject{NickName=new[]{fem?"ANALYZE":"RUN","STOP","RESET"}[k]},1100,600+55*k));
            GH_Component results=fem?(GH_Component)new FemResultsComponent():new ResultsComponent();Add(a,results,1500,350);results.Params.Input[0].AddSource(solver.Params.Output[0]);
            if(fem) {
                results.Params.Input[1].AddSource(Slider(a,"0 stress / 1 displacement",0,0,1,0,1380,800));
                results.Params.Input[2].AddSource(Slider(a,"Deformation scale",0,0,10000,0,1380,860));
            } else {
                results.Params.Input[1].AddSource(Slider(a,"Threshold",.5m,.1m,.9m,2,1380,800));
                results.Params.Input[2].AddSource(Slider(a,"Deformation scale",100,0,10000,0,1380,860));
                results.Params.Input[3].AddSource(Add(a,new GH_ButtonObject{NickName="BAKE"},1460,940));
                var shape=Add(a,new Param_Mesh{NickName="Shape OFF",Hidden=true},1750,290);shape.AddSource(results.Params.Output[1]);
                var deform=Add(a,new Param_Mesh{NickName="Deformed OFF",Hidden=true},1750,350);deform.AddSource(results.Params.Output[2]);
            }
            var status=Note(a,"",1040,1030,620,100);status.AddSource(solver.Params.Output[1]);
            var info=Note(a,"",1750,440,670,fem?570:320);info.AddSource(results.Params.Output[fem?8:3]);
            Note(a,fem?"Press ANALYZE. Field=0: von Mises; Field=1: displacement.\nNumerical legend in Info. Scale changes the preview only.\nFull-solid FEM, not reanalysis of the optimized shape.\nPoint loads and corners may create mesh-dependent peaks.":"Press RUN. Color represents density, not stress.\nThreshold extracts the shape. BAKE adds a Rhino mesh.\nFor Shape/Deformed: turn Results preview off and the parameter on.\nThe extracted shape has not been reanalysed.\nWhen halving h, double R to preserve the physical filter radius.",30,850,640,210);
            ParametricExamples.Sliders(a,geometry,1,(double)c["width"],(double)c["height"]);
            return a;
        }
    }
}
