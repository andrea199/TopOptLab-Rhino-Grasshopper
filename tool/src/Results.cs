// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Drawing;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Geometry;
using Grasshopper.Kernel;

namespace TopoptLab.GH
{
    public sealed class ResultsComponent : Component,IResultLegend
    {
        bool lastBake, initialized;
        Mesh preview;ResultLegend legend;bool showPreview=true;
        public bool LegendVisible{get{return showPreview&&preview!=null&&legend!=null;}}
        public ResultsComponent() : base("TopOpt Results", "Results", "Density and thresholded planar mesh. Threshold geometry has not been structurally reanalysed. Bake explicitly adds the threshold mesh to Rhino.", "4 Results") { }
        public override Guid ComponentGuid { get { return new Guid("a31cbe86-489f-4e11-a715-dbf3c00785ca"); } }
        public override BoundingBox ClippingBox { get { return preview == null ? BoundingBox.Empty : preview.GetBoundingBox(false); } }
        public override void ClearData() { preview = null;legend=null; base.ClearData(); }
        public override void DrawViewportMeshes(IGH_PreviewArgs args) { if (showPreview&&preview != null) args.Display.DrawMeshFalseColors(preview); }
        public override void DrawViewportWires(IGH_PreviewArgs args) { if(LegendVisible)legend.Draw(args,this); }
        protected override void RegisterInputParams(GH_InputParamManager p)
        {
            p.AddTextParameter("Result", "R", "Live result from Solver", GH_ParamAccess.item);
            p.AddNumberParameter("Threshold", "T", "Keep cells with density >= threshold", GH_ParamAccess.item, .5);
            p.AddNumberParameter("Deformation scale", "S", "Visual scale only, does not alter calculation", GH_ParamAccess.item, 100);
            p.AddBooleanParameter("Bake", "Bake", "Button pulse: add the current threshold mesh to Rhino", GH_ParamAccess.item, false);
            p.AddIntegerParameter("Field","Field","0 density; 1 displacement; 2 relaxed design stress",GH_ParamAccess.item,0);
            p.AddNumberParameter("Legend maximum","Max","0 auto; positive fixes stress/displacement scale",GH_ParamAccess.item,0);
            p.AddBooleanParameter("Show preview","Preview","Turn this stage preview and legend on/off",GH_ParamAccess.item,true);
        }
        protected override void RegisterOutputParams(GH_OutputParamManager p)
        {
            p.AddMeshParameter("Density", "D", "Undeformed mesh colored by selected Field; default density", GH_ParamAccess.item);
            p.AddMeshParameter("Shape", "M", "Thresholded planar mesh; not reanalysed", GH_ParamAccess.item);
            p.AddMeshParameter("Deformed", "U", "Density mesh with scaled displacement", GH_ParamAccess.item);
            p.AddTextParameter("Metrics", "Info", "Metrics for exactly the displayed density", GH_ParamAccess.item);
        }
        public static Mesh MakeMesh(JObject data, double threshold, double deformScale, bool color, int field=0,double maximum=1)
        {
            var nodes = (JArray)data["nodes"]; var faces = (JArray)data["faces"]; var density = (JArray)data["density"]; var displacement = (JArray)data["displacement"];
            Mesh mesh = new Mesh();
            for (int e = 0; e < faces.Count; e++)
            {
                double rho = (double)density[e]; if (rho < threshold) continue;
                int start = mesh.Vertices.Count;
                for (int k = 0; k < 4; k++)
                {
                    int n = (int)faces[e][k]; var p = nodes[n]; var u = displacement[n];
                    mesh.Vertices.Add((double)p[0] + deformScale * (double)u[0], (double)p[1] + deformScale * (double)u[1], (double)p[2] + deformScale * (double)u[2]);
                    if (color){
                        double value=rho;if(field==1)value=Math.Sqrt((double)u[0]*(double)u[0]+(double)u[1]*(double)u[1]+(double)u[2]*(double)u[2]);if(field==2)value=(double)data["von_mises_relaxed"][e];
                        mesh.VertexColors.Add(field==0?DensityColor(rho):FieldColor(maximum>0?value/maximum:0));
                    }
                }
                mesh.Faces.AddFace(start, start + 1, start + 2, start + 3);
            }
            if (!color) { mesh.Vertices.CombineIdentical(true, true); mesh.Weld(Math.PI); }
            mesh.Normals.ComputeNormals(); mesh.Compact(); return mesh;
        }
        static Color DensityColor(double rho){rho=Math.Max(0,Math.Min(1,rho));return Color.FromArgb((int)(248-228*rho),(int)(250-179*rho),(int)(252-149*rho));}
        static Color FieldColor(double x){x=Math.Max(0,Math.Min(1,x));return x<.5?Color.FromArgb((int)(510*x),(int)(510*x),200):Color.FromArgb(255,(int)(510*(1-x)),(int)(400*(1-x)));}
        protected override void SolveInstance(IGH_DataAccess da)
        {
            preview = null;legend=null;
            bool bake = false; da.GetData(3, ref bake);
            bool edge = initialized && bake && !lastBake; initialized = true; lastBake = bake;
            string json = null; double threshold = .5, scale = 100;
            if (!da.GetData(0, ref json) || !da.GetData(1, ref threshold) || !da.GetData(2, ref scale)) return;
            try {
                if (!CadGeometry.Finite(threshold) || threshold <= 0 || threshold >= 1 || !CadGeometry.Finite(scale) || scale < 0) throw new ArgumentException("Threshold must be between 0 and 1; deformation scale must be finite and nonnegative.");
                int field=0;double legendMax=0;da.GetData(4,ref field);da.GetData(5,ref legendMax);da.GetData(6,ref showPreview);
                if(field<0||field>2||!CadGeometry.Finite(legendMax)||legendMax<0)throw new ArgumentException("Invalid field or legend maximum");
                JObject d = JObject.Parse(json);
                if ((string)d["schema"] != "topoptlab-gh-result-v1") throw new ArgumentException("Unsupported result schema");
                if(field==2&&d["von_mises_relaxed"]==null)throw new ArgumentException("Relaxed stress is available after completion in version 0.3 or during constrained optimization");
                double actual=field==0?d["density"].Values<double>().Max():field==1?(double)d["metrics"]["max_displacement"]:d["von_mises_relaxed"].Values<double>().Max();
                double maximum=field==0?1:legendMax>0?legendMax:actual;
                Mesh density = MakeMesh(d, 0, 0, true,field,maximum), shape = MakeMesh(d, threshold, 0, false), deformed = MakeMesh(d, 0, scale, true,field,maximum);
                preview = deformed;
                da.SetData(0, density); da.SetData(1, shape); da.SetData(2, deformed);
                var m = d["metrics"];
                string metrics = string.Format(System.Globalization.CultureInfo.InvariantCulture,
                    "{0} | displayed iteration {1} | completed steps {2}\nCompliance: {3:G6}\nImprovement from initial: {4:F2}%\nMaterial: {5:P2} / {6:P2}\nMax displacement: {7:G5}\nThreshold mesh area fraction: {8:P2}\nThreshold mesh has not been structurally reanalysed.",
                    d["status"], d["iteration"], d["completed_iterations"], (double)m["compliance"], (double)m["improvement_percent"], (double)m["volume"], (double)m["target_volume"], (double)m["max_displacement"], (double)shape.Faces.Count / density.Faces.Count);
                legend=ResultLegend.Create(d,field==0?"Density":field==1?"Displacement":"Relaxed design stress",field==0?"density":field==1?"displacement":"stress",maximum,actual,scale,field==0?(Func<double,Color>)DensityColor:FieldColor);
                da.SetData(3, metrics+EngineeringInfo.Summary(d)); Message = (string)d["status"];
                if (edge)
                {
                    if ((string)d["status"] != "completed") throw new ArgumentException("Bake is available when the run is completed.");
                    if (shape.Faces.Count == 0) throw new ArgumentException("No cells remain above Threshold.");
                    RhinoDoc doc = RhinoDoc.ActiveDoc; if (doc == null) throw new ArgumentException("Open a Rhino document before Bake.");
                    uint undo = doc.BeginUndoRecord("Bake TopOptLab shape");
                    try {
                        var attr = new Rhino.DocObjects.ObjectAttributes { Name = "TopOptLab 2D - threshold " + threshold.ToString("F2") };
                        attr.SetUserString("topoptlab_job", (string)d["job_id"]);
                        attr.SetUserString("analysis", "Threshold geometry is not reanalysed");
                        doc.Objects.AddMesh(shape, attr); doc.Views.Redraw();
                    } finally { doc.EndUndoRecord(undo); }
                }
            } catch (Exception e) { Error(e); }
        }
    }
}
