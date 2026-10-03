// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Linq;
using System.Drawing;
using System.Globalization;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Geometry;
using Grasshopper.Kernel;
namespace TopoptLab.GH
{
    public sealed class Results3DComponent:Component,IResultLegend
    {
        Mesh preview;ResultLegend legend;bool showPreview=true,initialized,lastBake;
        public bool LegendVisible{get{return showPreview&&preview!=null&&legend!=null;}}
        public Results3DComponent():base("TopOpt Results 3D","Results 3D","FEM stress or optimization density. Cut removes voxels from preview only. Bake exports unsmoothed threshold boundary; only completed optimization with Cut axis=0.","9 Results 3D"){}
        public override Guid ComponentGuid{get{return new Guid("6c8b1e31-0011-4e55-8001-010000000006");}}
        public override BoundingBox ClippingBox{get{return preview==null?BoundingBox.Empty:preview.GetBoundingBox(false);}}
        public override void ClearData(){preview=null;legend=null;base.ClearData();}
        public override void DrawViewportMeshes(IGH_PreviewArgs args){if(showPreview&&preview!=null)args.Display.DrawMeshFalseColors(preview);}
        public override void DrawViewportWires(IGH_PreviewArgs args){if(LegendVisible)legend.Draw(args,this);}
        protected override void RegisterInputParams(GH_InputParamManager p){p.AddTextParameter("Result","R","FEM 3D or Optimize 3D",GH_ParamAccess.item);p.AddNumberParameter("Threshold","T","Optimization shape only; FEM ignores this",GH_ParamAccess.item,.5);p.AddIntegerParameter("Field","Field","0: FEM von Mises / optimization density; 1: displacement magnitude; 2: stress (relaxed during optimization)",GH_ParamAccess.item,0);p.AddNumberParameter("Deformation scale","Scale","Display only, 0=original shape",GH_ParamAccess.item,0);p.AddIntegerParameter("Cut axis","Cut","0=none, 1=X, 2=Y, 3=Z; preview only",GH_ParamAccess.item,0);p.AddNumberParameter("Cut fraction","Fraction","Keep centers below this fraction of axis extent",GH_ParamAccess.item,1);p.AddBooleanParameter("Bake","Bake","Completed optimization; Cut must be zero. Bake full threshold mesh, undeformed.",GH_ParamAccess.item,false);p.AddNumberParameter("Legend maximum","Max","0 auto; positive fixes the scale for displacement/stress",GH_ParamAccess.item,0);p.AddBooleanParameter("Show preview","Preview","Turn this stage preview and legend on/off",GH_ParamAccess.item,true);}
        protected override void RegisterOutputParams(GH_OutputParamManager p){p.AddMeshParameter("Preview","View","Colored outer/cut voxel faces",GH_ParamAccess.item);p.AddMeshParameter("Shape","Shape","Full undeformed threshold boundary; not reanalysed",GH_ParamAccess.item);p.AddTextParameter("Info","Info","Legend, units and metrics",GH_ParamAccess.item);p.AddPointParameter("Nodes","P","World nodes",GH_ParamAccess.list);p.AddVectorParameter("Displacement","U","World displacement aligned to P",GH_ParamAccess.list);p.AddVectorParameter("Reactions","Reac","FEM only: world reactions aligned to P",GH_ParamAccess.list);p.AddNumberParameter("Von Mises","VM","FEM only: max of 8 Gauss points per voxel, force/length^2",GH_ParamAccess.list);}
        static Color ColorAt(double value){value=Math.Max(0,Math.Min(1,value));return value<.5?Color.FromArgb((int)(510*value),(int)(510*value),200):Color.FromArgb(255,(int)(510*(1-value)),(int)(400*(1-value)));}
        protected override void SolveInstance(IGH_DataAccess da)
        {
            preview=null;legend=null;bool bake=false;da.GetData(6,ref bake);bool edge=initialized&&bake&&!lastBake;initialized=true;lastBake=bake;
            string json=null;double threshold=.5,scale=0,fraction=1;int field=0,axis=0;double legendMax=0;da.GetData(7,ref legendMax);da.GetData(8,ref showPreview);
            if(!da.GetData(0,ref json)||!da.GetData(1,ref threshold)||!da.GetData(2,ref field)||!da.GetData(3,ref scale)||!da.GetData(4,ref axis)||!da.GetData(5,ref fraction))return;
            try {
                if(!CadGeometry.Finite(legendMax)||legendMax<0||!CadGeometry.Finite(threshold)||threshold<=0||threshold>=1||field<0||field>2||axis<0||axis>3||!CadGeometry.Finite(fraction)||fraction<0||fraction>1||!CadGeometry.Finite(scale)||scale<0)throw new ArgumentException("Invalid threshold, field, scale or cut settings");
                var d=JObject.Parse(json);if((string)d["schema"]!="topoptlab-gh-3d-result-v1")throw new ArgumentException("Connect a 3D result");
                bool fem=(string)d["mode"]=="fem";
                var nodes=((JArray)d["nodes"]).Select(p=>new Point3d((double)p[0],(double)p[1],(double)p[2])).ToArray();
                var u=((JArray)d["displacement"]).Select(p=>new Vector3d((double)p[0],(double)p[1],(double)p[2])).ToArray();
                var hex=d["hexes"].ToObject<int[][]>();var rho=d["density"].ToObject<double[]>();
                var vm=fem?d["von_mises"].ToObject<double[]>():d["von_mises_relaxed"]==null?null:d["von_mises_relaxed"].ToObject<double[]>();
                if(field==2&&vm==null)throw new ArgumentException("Relaxed stress is available after completion in version 0.3 or while constrained optimization runs");
                var values=hex.Select((h,e)=>field==1?h.Max(n=>u[n].Length):(fem||field==2)?vm[e]:rho[e]).ToArray();
                double actual=values.Max();double maximum=field==0&&!fem?1:legendMax>0?legendMax:actual;
                bool[] included=Enumerable.Repeat(true,hex.Length).ToArray();
                if(axis>0){double lo=nodes.Min(p=>p[axis-1]),hi=nodes.Max(p=>p[axis-1]),cut=lo+fraction*(hi-lo);for(int e=0;e<hex.Length;e++)included[e]=hex[e].Average(n=>nodes[n][axis-1])<=cut;}
                var colors=values.Select(v=>ColorAt(maximum>0?v/maximum:0)).ToArray();
                preview=VoxelMesh.Build(nodes.Select((p,n)=>p+scale*u[n]).ToArray(),hex,included,colors,0);
                Mesh shape=fem?null:VoxelMesh.Build(nodes,hex,rho.Select(v=>v>=threshold).ToArray(),null,0);
                da.SetData(0,preview);if(shape!=null)da.SetData(1,shape);da.SetDataList(3,nodes);da.SetDataList(4,u);
                if(fem){da.SetDataList(5,((JArray)d["reactions"]).Select(p=>new Vector3d((double)p[0],(double)p[1],(double)p[2])));da.SetDataList(6,vm);}
                var m=d["metrics"];string label=field==1?"Voxel max displacement (length)":fem?"Von Mises":field==2?"Relaxed design stress":"Density";
                string info=string.Format(CultureInfo.InvariantCulture,"{0} | {1} voxels | {2}\n{3}: blue=0; red={4:G6}\nMax displacement={5:G6}; compliance={6:G6}\nRelative equilibrium error={7:G3}\nDisplay scale={8}; cut axis={9}, fraction={10}\nWORLD XYZ. mm+N+E in N/mm2 => displacement mm, stress MPa.\nLinear isotropic 3D elasticity; no contact or buckling check; Design Limits are reported separately.\nFEM stress=max of 8 Gauss points/voxel; point-load peaks depend on mesh.",fem?"FULL SOLID FEM 3D":"OPTIMIZATION 3D",hex.Length,d["status"],label,maximum,(double)m["max_displacement"],(double)m["compliance"],(double)m["equilibrium"],scale,axis,fraction);
                if(d["engineering"]!=null&&(string)d["engineering"]["mode"]=="verify")info=info.Replace("FULL SOLID FEM 3D","FINAL VERIFICATION 3D / BINARY GRID");
                if(!fem)info+=string.Format(CultureInfo.InvariantCulture,"\nMaterial={0:P2}; target={1:P2}; improvement={2:F2}%\nThreshold retained volume={3:P2}. Shape is unsmoothed and NOT reanalysed.\nDisable Results 3D preview and enable Shape to inspect threshold geometry.",(double)m["volume"],(double)m["target_volume"],(double)m["improvement_percent"],rho.Count(v=>v>=threshold)/(double)rho.Length);
                legend=ResultLegend.Create(d,label,field==1?"displacement":field==0&&!fem?"density":"stress",maximum,actual,scale,ColorAt);
                da.SetData(2,info+EngineeringInfo.Summary(d));Message=label;
                if(edge){if(fem||(string)d["status"]!="completed"||axis!=0)throw new ArgumentException("Bake requires completed optimization and Cut axis=0");if(shape==null||shape.Faces.Count==0||!shape.IsValid||!shape.IsClosed)throw new ArgumentException("Threshold mesh is empty or not a closed valid mesh");var doc=RhinoDoc.ActiveDoc;if(doc==null)throw new ArgumentException("Open a Rhino document");uint undo=doc.BeginUndoRecord("Bake TopOptLab 3D");try{var attr=new Rhino.DocObjects.ObjectAttributes{Name="TopOptLab 3D threshold"};attr.SetUserString("analysis","Voxel threshold, not reanalysed");doc.Objects.AddMesh(shape,attr);doc.Views.Redraw();}finally{doc.EndUndoRecord(undo);}}
            }catch(Exception e){Error(e);}
        }
    }
}
