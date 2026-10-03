// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Drawing;
using System.Collections.Generic;
using Rhino.Geometry;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Parameters;
using Grasshopper.Kernel.Special;
namespace TopoptLab.GH
{
    public sealed class Example3DComponent:Component
    {
        public Example3DComponent():base("TopOpt Example 3D","Example 3D","120x60x30 cantilever; left face fixed, right 10x10 load patch. Keep 5mm end layers.","6 Geometry 3D"){}
        public override Guid ComponentGuid{get{return new Guid("6c8b1e31-0011-4e55-8001-010000000007");}}
        protected override void RegisterInputParams(GH_InputParamManager p){RegisterGeometry(p,true);}
        protected override void RegisterOutputParams(GH_OutputParamManager p){p.AddBrepParameter("Solid","B","120x60x30 block",GH_ParamAccess.item);p.AddBrepParameter("Support face","S","Minimum X face; follows geometry dimensions and position",GH_ParamAccess.item);p.AddBrepParameter("Load patch","L","Patch on maximum X face; follows geometry dimensions and position",GH_ParamAccess.item);p.AddBrepParameter("Keep","Keep","5mm end layers",GH_ParamAccess.list);}
        static Brep Block(double x0,double x1){return new Box(Plane.WorldXY,new Interval(x0,x1),new Interval(0,60),new Interval(0,30)).ToBrep();}
        protected override void SolveInstance(IGH_DataAccess da){
         var t=ParametricExamples.Read(da,0,120,60,30);
         da.SetData(0,ParametricExamples.Brep(Block(0,120),t));
         da.SetData(1,ParametricExamples.Brep(Brep.CreateFromCornerPoints(new Point3d(0,0,0),new Point3d(0,60,0),new Point3d(0,60,30),new Point3d(0,0,30),1e-6),t));
         da.SetData(2,ParametricExamples.Brep(Brep.CreateFromCornerPoints(new Point3d(120,25,10),new Point3d(120,35,10),new Point3d(120,35,20),new Point3d(120,25,20),1e-6),t));
         da.SetDataList(3,new[]{ParametricExamples.Brep(Block(0,5),t),ParametricExamples.Brep(Block(115,120),t)});
        }

    }
    public static class Example3DDocument
    {
        static T Add<T>(List<IGH_DocumentObject>a,T o,float x,float y)where T:IGH_DocumentObject{o.CreateAttributes();o.Attributes.Pivot=new PointF(x,y);a.Add(o);return o;}
        static GH_Panel Note(List<IGH_DocumentObject>a,string text,float x,float y,float w,float h){var p=Add(a,new GH_Panel(),x,y);p.UserText=text;p.Attributes.Bounds=new RectangleF(x,y,w,h);return p;}
        static GH_NumberSlider Slider(List<IGH_DocumentObject>a,string name,decimal value,decimal min,decimal max,int decimals,float x,float y){var s=new GH_NumberSlider();s.NickName=name;s.Slider.Minimum=min;s.Slider.Maximum=max;s.Slider.DecimalPlaces=decimals;s.Slider.Type=decimals==0?Grasshopper.GUI.Base.GH_SliderAccuracy.Integer:Grasshopper.GUI.Base.GH_SliderAccuracy.Float;s.SetSliderValue(value);return Add(a,s,x,y);}
        public static List<IGH_DocumentObject> Build(bool fem)
        {
            var a=new List<IGH_DocumentObject>();Note(a,"3D CANTILEVER / "+(fem?"FULL-SOLID FEM":"OPTIMIZATION")+"\nDefault: 120x60x30 mm, 5 mm voxels (1728 cells). E=210000 N/mm2, nu=0.3.\nLeft face fixed XYZ; TOTAL force (0,0,-100) N on a 10x10 mm right patch.\nKeep: 5 mm end layers. Illustrative data; use your actual material and loads.",30,20,1550,140);
            var example=Add(a,new Example3DComponent{Hidden=true},80,330);
            var domain=Add(a,new Domain3DComponent{Hidden=true},360,290);domain.Params.Input[0].AddSource(example.Params.Output[0]);domain.Params.Input[2].AddSource(example.Params.Output[3]);domain.Params.Input[3].AddSource(Slider(a,"Voxel h / mm",5,5,10,1,80,630));
            var grid=Add(a,new Param_Mesh{NickName="Grid OFF",Hidden=true},480,610);grid.AddSource(domain.Params.Output[1]);
            var support=Add(a,new Support3DComponent(),650,280);support.Params.Input[0].AddSource(domain.Params.Output[0]);support.Params.Input[1].AddSource(example.Params.Output[1]);
            var load=Add(a,new Load3DComponent(),650,480);load.Params.Input[0].AddSource(domain.Params.Output[0]);load.Params.Input[1].AddSource(example.Params.Output[2]);
            var force=Add(a,new Param_Vector{NickName="F = (0,0,-100) N"},390,510);force.SetPersistentData(new Grasshopper.Kernel.Types.GH_Vector(new Vector3d(0,0,-100)));load.Params.Input[2].AddSource(force);
            GH_Component solver=fem?(GH_Component)new FemAnalyze3DComponent():new Solver3DComponent();Add(a,solver,980,360);solver.Params.Input[0].AddSource(domain.Params.Output[0]);solver.Params.Input[1].AddSource(support.Params.Output[0]);solver.Params.Input[2].AddSource(load.Params.Output[0]);
            int material=fem?3:6;solver.Params.Input[material].AddSource(Slider(a,"E / N per mm2",210000,1,300000,0,650,720));solver.Params.Input[material+1].AddSource(Slider(a,"nu",.3m,0,.49m,2,650,770));
            if(!fem){solver.Params.Input[3].AddSource(Slider(a,"Volume",.35m,.15m,.8m,2,650,850));solver.Params.Input[4].AddSource(Slider(a,"Iterations",40,5,100,0,650,900));solver.Params.Input[5].AddSource(Slider(a,"Filter / voxels",1.8m,1,4,1,650,950));}
            int start=fem?5:8;for(int k=0;k<3;k++)solver.Params.Input[start+k].AddSource(Add(a,new GH_ButtonObject{NickName=new[]{fem?"ANALYZE":"RUN","STOP","RESET"}[k]},960,660+55*k));
            var results=Add(a,new Results3DComponent(),1350,350);results.Params.Input[0].AddSource(solver.Params.Output[0]);
            results.Params.Input[1].AddSource(Slider(a,"Threshold / OPT only",.5m,.1m,.9m,2,1250,680));results.Params.Input[2].AddSource(Slider(a,"Field 0=stress or density; 1=U",0,0,1,0,1250,730));results.Params.Input[3].AddSource(Slider(a,"Deformation scale",0,0,1000,0,1250,780));results.Params.Input[4].AddSource(Slider(a,"Cut 0=OFF 1=X 2=Y 3=Z",0,0,3,0,1250,830));results.Params.Input[5].AddSource(Slider(a,"Cut fraction",.5m,0,1,2,1250,880));
            if(!fem){results.Params.Input[6].AddSource(Add(a,new GH_ButtonObject{NickName="BAKE"},1380,970));var shape=Add(a,new Param_Mesh{NickName="Shape OFF",Hidden=true},1620,290);shape.AddSource(results.Params.Output[1]);}
            var status=Note(a,"",930,1050,580,100);status.AddSource(solver.Params.Output[1]);var info=Note(a,"",1630,440,700,560);info.AddSource(results.Params.Output[2]);
            Note(a,"FIRST RUN\n1. Press "+(fem?"ANALYZE":"RUN")+". 2. Read Status and Info.\nCut removes voxels from the preview only, not the model.\nTo see inside: Cut=2, Fraction=0.5.\nScale=0 original geometry; Scale=1 actual displacement.\nOPT: disable Results 3D preview and enable Shape.\nBake: completed OPT, Cut=0; unsmoothed mesh, not reanalysed.\nInitial limit: 8000 bounding-box voxels. WORLD XYZ.",30,780,570,280);
            ParametricExamples.Sliders(a,example,0,120,60,30);
            return a;
        }
    }
}
