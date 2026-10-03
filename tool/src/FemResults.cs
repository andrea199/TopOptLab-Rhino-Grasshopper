// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Drawing;
using System.Linq;
using System.Collections.Generic;
using System.Globalization;
using Newtonsoft.Json.Linq;
using Rhino.Geometry;
using Grasshopper.Kernel;
namespace TopoptLab.GH
{
    public sealed class FemResultsComponent : Component,IResultLegend
    {
        Mesh preview;ResultLegend legend;bool showPreview=true;
        public bool LegendVisible{get{return showPreview&&preview!=null&&legend!=null;}}
        public FemResultsComponent() : base("TopOpt FEM Results", "FEM Results", "Full-solid FEM: stress, displacement and reactions. Stress components use domain axes; vectors use world axes. See Info for units and color range.", "5 FEM") { }
        public override Guid ComponentGuid { get { return new Guid("b60ce452-cb02-48ac-a917-1c047bc3dd73"); } }
        public override BoundingBox ClippingBox { get { return preview == null ? BoundingBox.Empty : preview.GetBoundingBox(false); } }
        public override void ClearData() { preview = null;legend=null; base.ClearData(); }
        public override void DrawViewportMeshes(IGH_PreviewArgs args) { if (showPreview&&preview != null) args.Display.DrawMeshFalseColors(preview); }
        public override void DrawViewportWires(IGH_PreviewArgs args) { if(LegendVisible)legend.Draw(args,this); }
        protected override void RegisterInputParams(GH_InputParamManager p)
        {
            p.AddTextParameter("FEM Result", "R", "From FEM Analyze", GH_ParamAccess.item);
            p.AddIntegerParameter("Field", "Field", "0 or 2 = von Mises stress; 1 = displacement magnitude", GH_ParamAccess.item, 0);
            p.AddNumberParameter("Deformation scale", "Scale", "Preview only: 0 = original shape; 1 = actual displacements", GH_ParamAccess.item, 0);
            p.AddNumberParameter("Legend maximum","Max","0 auto; positive fixes the field scale",GH_ParamAccess.item,0);
            p.AddBooleanParameter("Show preview","Preview","Turn this stage preview and legend on/off",GH_ParamAccess.item,true);
        }
        protected override void RegisterOutputParams(GH_OutputParamManager p)
        {
            p.AddMeshParameter("Colored mesh", "Mesh", "Selected field on scaled geometry", GH_ParamAccess.item);
            p.AddNumberParameter("Von Mises", "VM", "Maximum of four Gauss-point values per cell; force/length^2", GH_ParamAccess.list);
            p.AddNumberParameter("Sigma X", "Sx", "Mean Gauss-point sigma_x per cell, DOMAIN axes; force/length^2", GH_ParamAccess.list);
            p.AddNumberParameter("Sigma Y", "Sy", "Mean Gauss-point sigma_y per cell, DOMAIN axes; force/length^2", GH_ParamAccess.list);
            p.AddNumberParameter("Tau XY", "Txy", "Mean Gauss-point shear per cell, DOMAIN axes; force/length^2", GH_ParamAccess.list);
            p.AddPointParameter("Nodes", "P", "World nodes in the same order as U and reactions", GH_ParamAccess.list);
            p.AddVectorParameter("Displacements", "U", "Actual WORLD displacement vectors, length units, aligned to P", GH_ParamAccess.list);
            p.AddVectorParameter("Reactions", "Reac", "WORLD support reactions, force units, aligned to P; zero on free DOFs", GH_ParamAccess.list);
            p.AddTextParameter("Info", "Info", "Color legend, material, extrema and limitations", GH_ParamAccess.item);
        }
        static Color Ramp(double x)
        {
            x = Math.Max(0, Math.Min(1, x));
            if (x < .5) return Color.FromArgb((int)(2*x*255), (int)(2*x*255), (int)(180+2*x*75));
            return Color.FromArgb(255, (int)(510*(1-x)), (int)(510*(1-x)));
        }
        protected override void SolveInstance(IGH_DataAccess da)
        {
            preview = null;legend=null;
            string json = null; int field = 0; double scale = 0;
            if (!da.GetData(0, ref json) || !da.GetData(1, ref field) || !da.GetData(2, ref scale)) return;
            try {
                double legendMax=0;da.GetData(3,ref legendMax);da.GetData(4,ref showPreview);
                if(field==2)field=0;
                if (!CadGeometry.Finite(legendMax)||legendMax<0||field < 0 || field > 1 || !CadGeometry.Finite(scale) || scale < 0)
                    throw new ArgumentException("Field must be 0, 1 or 2; Scale must be finite and nonnegative.");
                JObject d = JObject.Parse(json);
                if ((string)d["schema"] != "topoptlab-gh-fem-result-v1" || (string)d["status"] != "completed")
                    throw new ArgumentException("Connect a completed FEM Analyze result.");
                var nodes = (JArray)d["nodes"]; var faces = (JArray)d["faces"];
                var u = (JArray)d["displacement"]; var r = (JArray)d["reactions"];
                double[] vm = d["von_mises"].ToObject<double[]>();
                var points = new List<Point3d>(); var vectors = new List<Vector3d>(); var reactions = new List<Vector3d>();
                for (int n=0;n<nodes.Count;n++) {
                    points.Add(new Point3d((double)nodes[n][0], (double)nodes[n][1], (double)nodes[n][2]));
                    vectors.Add(new Vector3d((double)u[n][0], (double)u[n][1], (double)u[n][2]));
                    reactions.Add(new Vector3d((double)r[n][0], (double)r[n][1], (double)r[n][2]));
                }
                double actual = field == 0 ? vm.Max() : vectors.Max(v => v.Length);double maximum=legendMax>0?legendMax:actual;
                Mesh mesh = new Mesh();
                for (int e=0;e<faces.Count;e++) {
                    int start = mesh.Vertices.Count;
                    for (int k=0;k<4;k++) {
                        int n=(int)faces[e][k];
                        mesh.Vertices.Add(points[n]+scale*vectors[n]);
                        double value=field == 0 ? vm[e] : vectors[n].Length;
                        mesh.VertexColors.Add(Ramp(maximum > 0 ? value/maximum : 0));
                    }
                    mesh.Faces.AddFace(start,start+1,start+2,start+3);
                }
                mesh.Normals.ComputeNormals(); mesh.Compact(); preview=mesh;
                da.SetData(0,mesh); da.SetDataList(1,vm);
                for(int k=0;k<3;k++) da.SetDataList(2+k, ((JArray)d["stress_mean"]).Select(row=>(double)row[k]));
                da.SetDataList(5,points); da.SetDataList(6,vectors); da.SetDataList(7,reactions);
                var m=d["metrics"]; var material=d["material"];
                bool verified=d["engineering"]!=null&&(string)d["engineering"]["mode"]=="verify";
                string info=string.Format(CultureInfo.InvariantCulture,
                    "FULL-SOLID FEM | {0} cells\n{1}: blue=0, white={2:G6}, red={3:G6} ({4})\nScale: {5:G6} (display only)\nMax displacement: {6:G6} length\nMax von Mises: {7:G6} force/length^2\nCompliance: {8:G6} force*length\nE={9:G6}; nu={10:G6}; thickness={11:G6}\nRelative force residual={12:G3}; equilibrium={13:G3}\nStress: max of 4 Gauss points per cell; Sx/Sy/Txy are cell means in DOMAIN axes.\nWorld displacement/reaction lists match P.\nPlane stress, small strain; Design Limits are reported separately.\nPoint loads and sharp supports can create mesh-dependent peaks.\nUse mm + N + E in N/mm^2 for stresses in MPa. No automatic unit conversion.",
                    faces.Count,field==0?"Von Mises":"Displacement",maximum/2,maximum,field==0?"force/length^2":"length",scale,
                    (double)m["max_displacement"],(double)m["max_von_mises"],(double)m["compliance"],
                    (double)material["young"],(double)material["poisson"],(double)material["thickness"],(double)m["residual"],(double)m["equilibrium"]);
                if(verified)info=info.Replace("FULL-SOLID FEM","FINAL VERIFICATION / BINARY GRID");
                legend=ResultLegend.Create(d,field==0?"Von Mises":"Displacement",field==0?"stress":"displacement",maximum,actual,scale,Ramp);
                da.SetData(8,info+EngineeringInfo.Summary(d));
                Message = (field==0?"Von Mises":"Displacement")+(verified?" | final verification":" | full solid");
            } catch(Exception e) { Error(e); }
        }
    }
}
