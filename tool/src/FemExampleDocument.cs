// SPDX-License-Identifier: GPL-3.0-or-later
using System.Collections.Generic;
using System.Drawing;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Parameters;
using Grasshopper.Kernel.Special;
using Grasshopper.Kernel.Types;
namespace TopoptLab.GH
{
    public static class FemExampleDocument
    {
        static T Add<T>(List<IGH_DocumentObject> objects,T obj,float x,float y) where T:IGH_DocumentObject
        { obj.CreateAttributes();obj.Attributes.Pivot=new PointF(x,y);objects.Add(obj);return obj; }
        static GH_Panel Panel(List<IGH_DocumentObject> objects,string text,float x,float y,float width,float height)
        { var p=Add(objects,new GH_Panel(),x,y);p.UserText=text;p.Attributes.Bounds=new RectangleF(x,y,width,height);return p; }
        static GH_NumberSlider Slider(List<IGH_DocumentObject> objects,string name,decimal value,decimal max,int decimals,float x,float y)
        { var s=new GH_NumberSlider();s.NickName=name;s.Slider.Minimum=0;s.Slider.Maximum=max;s.Slider.DecimalPlaces=decimals;s.SetSliderValue(value);return Add(objects,s,x,y); }
        public static List<IGH_DocumentObject> BuildObjects()
        {
            var objects=new List<IGH_DocumentObject>();
            Panel(objects,"FEM / PLATE WITH HOLE\nFull-solid domain, no optimization. Holes remain empty.\nIllustrative mm/N inputs: E=210000 N/mm^2, nu=0.3, t=2 mm; default total load 0.001 N downward.\nReplace these values with your actual material and loading. Point loads can create stress peaks.",30,20,1100,140);
            var example=Add(objects,new ExampleGeometryComponent { Hidden=true },60,300);
            var domain=Add(objects,new DomainComponent { Hidden=true },300,260);
            domain.Params.Input[0].AddSource(example.Params.Output[0]);domain.Params.Input[1].AddSource(example.Params.Output[1]);
            var support1=Add(objects,new SupportComponent(),520,310);
            var support2=Add(objects,new SupportComponent(),520,440);
            support1.Params.Input[0].AddSource(domain.Params.Output[0]);support1.Params.Input[1].AddSource(example.Params.Output[3]);
            support2.Params.Input[0].AddSource(domain.Params.Output[0]);support2.Params.Input[1].AddSource(example.Params.Output[4]);
            ((Param_Boolean)support2.Params.Input[2]).PersistentData.Clear();
            ((Param_Boolean)support2.Params.Input[2]).SetPersistentData(new GH_Boolean(false));
            var load=Add(objects,new LoadComponent(),520,570);
            load.Params.Input[0].AddSource(domain.Params.Output[0]);load.Params.Input[1].AddSource(example.Params.Output[5]);
            var fem=Add(objects,new FemAnalyzeComponent(),850,380);
            fem.Params.Input[0].AddSource(domain.Params.Output[0]);fem.Params.Input[1].AddSource(support1.Params.Output[0]);
            fem.Params.Input[1].AddSource(support2.Params.Output[0]);fem.Params.Input[2].AddSource(load.Params.Output[0]);
            fem.Params.Input[3].AddSource(Slider(objects,"E / N per mm2",210000,300000,0,530,730));
            fem.Params.Input[4].AddSource(Slider(objects,"Poisson",.3m,.49m,2,530,780));
            fem.Params.Input[5].AddSource(Slider(objects,"Thickness / mm",2,20,2,530,830));
            for(int k=0;k<3;k++) fem.Params.Input[6+k].AddSource(Add(objects,new GH_ButtonObject { NickName=new[]{"ANALYZE","STOP","RESET"}[k]},800,670+55*k));
            var result=Add(objects,new FemResultsComponent(),1170,380);result.Params.Input[0].AddSource(fem.Params.Output[0]);
            var field=Slider(objects,"Field 0=stress 1=displacement",0,1,0,1030,680);
            field.Slider.Type=Grasshopper.GUI.Base.GH_SliderAccuracy.Integer;
            result.Params.Input[1].AddSource(field);
            result.Params.Input[2].AddSource(Slider(objects,"Deformation scale",0,10000,0,1030,740));
            var status=Panel(objects,"",760,900,500,100);status.AddSource(fem.Params.Output[1]);
            var info=Panel(objects,"",1400,220,640,530);info.AddSource(result.Params.Output[8]);
            Panel(objects,"FIELD: 0 = von Mises stress; 1 = displacement magnitude.\nScale=0: original shape; Scale=1: actual displacement.\nLegend in Info: blue=zero, white=half, red=maximum.\nP, U and Reac lists share node order. Sx/Sy/Txy use the domain plane axes.\nDisable other mesh previews for clean FEM colors.",30,740,460,240);
            ParametricExamples.Sliders(objects,example,0,12,6);
            return objects;
        }
    }
}
