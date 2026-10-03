// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Drawing;
using System.IO;
using System.Collections.Generic;
using Rhino.Geometry;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Parameters;
using Grasshopper.Kernel.Special;
using Grasshopper.Kernel.Types;

namespace TopoptLab.GH
{
    /// <summary>Reproducible native example; invoked inside Rhino by make_example.py.</summary>
    public static class ExampleDocument
    {
        static T Add<T>(List<IGH_DocumentObject> doc, T obj, float x, float y) where T : IGH_DocumentObject
        {
            obj.CreateAttributes(); obj.Attributes.Pivot = new PointF(x, y); doc.Add(obj); return obj;
        }
        static GH_Panel Note(List<IGH_DocumentObject> doc, string text, float x, float y, float w, float h)
        {
            GH_Panel panel = Add(doc, new GH_Panel(), x, y); panel.UserText = text;
            panel.Attributes.Bounds = new RectangleF(x, y, w, h); return panel;
        }
        static GH_NumberSlider Slider(List<IGH_DocumentObject> doc, string name, decimal value, decimal min, decimal max, int decimals, float x, float y)
        {
            var s = new GH_NumberSlider(); s.NickName = name; s.Slider.Minimum = min; s.Slider.Maximum = max;
            s.Slider.DecimalPlaces = decimals; s.Slider.Type = decimals == 0 ? Grasshopper.GUI.Base.GH_SliderAccuracy.Integer : Grasshopper.GUI.Base.GH_SliderAccuracy.Float;
            s.SetSliderValue(value); return Add(doc, s, x, y);
        }
        static Param_Curve CurveInput(List<IGH_DocumentObject> doc, string name, IGH_Param source, float x, float y)
        {
            var p = Add(doc, new Param_Curve { NickName = name, Hidden = true }, x, y); p.AddSource(source); return p;
        }
        static Param_Point PointInput(List<IGH_DocumentObject> doc, string name, IGH_Param source, float x, float y)
        {
            var p = Add(doc, new Param_Point { NickName = name, Hidden = true }, x, y); p.AddSource(source); return p;
        }
        public static List<IGH_DocumentObject> BuildObjects()
        {
            var doc = new List<IGH_DocumentObject>();
            Note(doc, "TOPOPTLAB / RHINO 8\n2D plate with a hole - fixed material budget\n1. Inspect the inputs and grid.  2. Press Run.  3. Adjust Threshold.  4. Bake the completed shape.", 40, 20, 1490, 115);
            Note(doc, "01 / CAD GEOMETRY\nTo use your CAD geometry: disconnect the Example wire, then right-click a curve/point parameter and Set one/multiple.", 40, 150, 340, 110);
            var example = Add(doc, new ExampleGeometryComponent { Hidden = true }, -140, 430);
            var boundary = CurveInput(doc, "Outer contour", example.Params.Output[0], 100, 300);
            var hole = CurveInput(doc, "Hole", example.Params.Output[1], 100, 365);
            var keep = CurveInput(doc, "Keep regions", example.Params.Output[2], 100, 430);
            var cell = Slider(doc, "Cell size", .25m, .125m, .75m, 3, 70, 565);
            var domain = Add(doc, new DomainComponent { Hidden = true }, 450, 375);
            domain.Params.Input[0].AddSource(boundary); domain.Params.Input[1].AddSource(hole);
            domain.Params.Input[2].AddSource(keep); domain.Params.Input[3].AddSource(cell);
            var grid = Add(doc, new Param_Mesh { NickName = "Grid preview (off)", Hidden = true }, 460, 620); grid.AddSource(domain.Params.Output[1]);
            var kept = Add(doc, new Param_Mesh { NickName = "Kept cells (off)", Hidden = true }, 460, 685); kept.AddSource(domain.Params.Output[2]);
            Note(doc, "02 / SUPPORTS + FORCE\nPin: X + Y fixed. Roller: Y fixed.\nForce is TOTAL, shared over selected nodes. Directions use the design plane.", 590, 150, 360, 115);
            var pin = PointInput(doc, "Pin point", example.Params.Output[3], 620, 310);
            var roller = PointInput(doc, "Roller point", example.Params.Output[4], 620, 415);
            var loadPoint = PointInput(doc, "Load point", example.Params.Output[5], 620, 530);
            var support1 = Add(doc, new SupportComponent(), 830, 310);
            var support2 = Add(doc, new SupportComponent(), 830, 415);
            var load = Add(doc, new LoadComponent(), 830, 530);
            support1.Params.Input[0].AddSource(domain.Params.Output[0]); support1.Params.Input[1].AddSource(pin);
            support2.Params.Input[0].AddSource(domain.Params.Output[0]); support2.Params.Input[1].AddSource(roller);
            ((Param_Boolean)support2.Params.Input[2]).PersistentData.Clear();
            ((Param_Boolean)support2.Params.Input[2]).SetPersistentData(new GH_Boolean(false));
            load.Params.Input[0].AddSource(domain.Params.Output[0]); load.Params.Input[1].AddSource(loadPoint);
            Note(doc, "03 / OPTIMIZE\nVolume includes the kept material.\nE=1, nu=0.3, thickness=1; total F=(0,-0.001,0).\nEdit component inputs for physical units.", 1000, 150, 350, 115);
            var solve = Add(doc, new SolverComponent(), 1190, 440);
            solve.Params.Input[0].AddSource(domain.Params.Output[0]); solve.Params.Input[1].AddSource(support1.Params.Output[0]);
            solve.Params.Input[1].AddSource(support2.Params.Output[0]); solve.Params.Input[2].AddSource(load.Params.Output[0]);
            solve.Params.Input[3].AddSource(Slider(doc, "Volume", .45m, .20m, .80m, 2, 790, 715));
            solve.Params.Input[4].AddSource(Slider(doc, "Iterations", 80, 10, 200, 0, 790, 760));
            solve.Params.Input[5].AddSource(Slider(doc, "Filter / cells", 2.4m, 1, 6, 1, 790, 805));
            var run = Add(doc, new GH_ButtonObject { NickName = "RUN" }, 1060, 655);
            var stop = Add(doc, new GH_ButtonObject { NickName = "STOP" }, 1060, 700);
            var reset = Add(doc, new GH_ButtonObject { NickName = "RESET" }, 1060, 745);
            solve.Params.Input[9].AddSource(run); solve.Params.Input[10].AddSource(stop); solve.Params.Input[11].AddSource(reset);
            Note(doc, "04 / RESULTS\nWhite = empty, dark blue = solid.\nThreshold changes the extracted shape.\nShape and Deformed previews start OFF.", 1420, 150, 420, 115);
            var result = Add(doc, new ResultsComponent(), 1500, 420); result.Params.Input[0].AddSource(solve.Params.Output[0]);
            result.Params.Input[1].AddSource(Slider(doc, "Threshold", .5m, .1m, .9m, 2, 1350, 665));
            result.Params.Input[2].AddSource(Slider(doc, "Deformation scale", 100, 0, 500, 0, 1350, 710));
            result.Params.Input[3].AddSource(Add(doc, new GH_ButtonObject { NickName = "BAKE" }, 1510, 770));
            var shape = Add(doc, new Param_Mesh { NickName = "Shape (preview off)", Hidden = true }, 1780, 375); shape.AddSource(result.Params.Output[1]);
            var deformed = Add(doc, new Param_Mesh { NickName = "Deformed (preview off)", Hidden = true }, 1780, 455); deformed.AddSource(result.Params.Output[2]);
            var metrics = Note(doc, "", 1610, 555, 510, 295); metrics.AddSource(result.Params.Output[3]);
            var status = Note(doc, "", 1010, 865, 520, 95); status.AddSource(solve.Params.Output[1]);
            Note(doc, "MODEL / Plane stress, linear elasticity, SIMP density method; all load components act together.\nA cell is active when its centre lies inside Boundary and outside Holes. Keep regions are rasterized the same way.\nThe initial design fills the available domain with uniform intermediate density, with Keep at density 1. It is not a bar lattice.\nThe extracted threshold mesh is a CAD interpretation and has not been structurally reanalysed.", 40, 890, 890, 155);
            ParametricExamples.Sliders(doc,example,0,12,6);
            return doc;
        }
        public static GH_Document Create(string folder)
        {
            Directory.CreateDirectory(folder);
            GH_Document doc = new GH_Document();
            foreach (var obj in BuildObjects()) doc.AddObject(obj, false);
            GH_DocumentIO io = new GH_DocumentIO(doc);
            if (!io.SaveQuiet(Path.Combine(folder, "plate_with_hole.gh"))) throw new IOException("Grasshopper could not save the .gh example.");
            if (!io.SaveQuiet(Path.Combine(folder, "plate_with_hole.ghx"))) throw new IOException("Grasshopper could not save the .ghx example.");
            return doc;
        }
    }

    public sealed class ExampleGeometryComponent : Component
    {
        public ExampleGeometryComponent() : base("TopOpt Example Geometry", "Example", "Built-in 12 x 6 plate with a circular hole and preserved end strips. Disconnect its wires to reference your own CAD geometry.", "1 Geometry") { }
        public override Guid ComponentGuid { get { return new Guid("5905b585-0464-4253-b555-ba61584d71f5"); } }
        protected override void RegisterInputParams(GH_InputParamManager p) { RegisterGeometry(p,false); }
        protected override void RegisterOutputParams(GH_OutputParamManager p)
        {
            p.AddCurveParameter("Boundary", "B", "Outer contour", GH_ParamAccess.item);
            p.AddCurveParameter("Hole", "H", "Circular void", GH_ParamAccess.item);
            p.AddCurveParameter("Keep", "K", "Preserved end regions", GH_ParamAccess.list);
            p.AddPointParameter("Pin", "P", "Fixed X/Y support", GH_ParamAccess.item);
            p.AddPointParameter("Roller", "R", "Fixed Y support", GH_ParamAccess.item);
            p.AddPointParameter("Load", "L", "Load location", GH_ParamAccess.item);
        }
        static Curve Rectangle(double x0, double y0, double x1, double y1)
        { return new Rectangle3d(Plane.WorldXY, new Point3d(x0, y0, 0), new Point3d(x1, y1, 0)).ToNurbsCurve(); }
        protected override void SolveInstance(IGH_DataAccess da)
        {
            var transform=ParametricExamples.Read(da,0,12,6);
            da.SetData(0, ParametricExamples.Curve(Rectangle(0, 0, 12, 6),transform));
            da.SetData(1, ParametricExamples.Curve(new Circle(new Point3d(6, 3, 0), 1).ToNurbsCurve(),transform));
            da.SetDataList(2, new[] { ParametricExamples.Curve(Rectangle(0, 0, 1, 6),transform), ParametricExamples.Curve(Rectangle(11, 0, 12, 6),transform) });
            da.SetData(3, ParametricExamples.Point(new Point3d(0, 0, 0),transform)); da.SetData(4, ParametricExamples.Point(new Point3d(12, 0, 0),transform)); da.SetData(5, ParametricExamples.Point(new Point3d(6, 6, 0),transform));
        }
    }
}
