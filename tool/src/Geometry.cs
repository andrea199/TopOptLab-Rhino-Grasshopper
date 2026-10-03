// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using Newtonsoft.Json;
using Rhino.Geometry;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Types;

namespace TopoptLab.GH
{
    public sealed class DomainData
    {
        public int nx, ny;
        public double cell;
        public double[] origin;
        public double[][] frame;
        public int[] active, solid;
        public Plane Plane { get { return new Plane(new Point3d(frame[0][0], frame[0][1], frame[0][2]), new Vector3d(frame[1][0], frame[1][1], frame[1][2]), new Vector3d(frame[2][0], frame[2][1], frame[2][2])); } }
        public int[] Face(int e)
        {
            int col = e / ny, row = e % ny, topLeft = col * (ny + 1) + row;
            return new[] { topLeft + 1, topLeft + ny + 2, topLeft + ny + 1, topLeft };
        }
        public Point3d Node(int n) { return Plane.PointAt(origin[0] + n / (ny + 1) * cell, origin[1] + (ny - n % (ny + 1)) * cell); }
        public Mesh Mesh(IEnumerable<int> elements)
        {
            Mesh mesh = new Mesh();
            foreach (int e in elements)
            {
                int k = mesh.Vertices.Count;
                foreach (int n in Face(e)) mesh.Vertices.Add(Node(n));
                mesh.Faces.AddFace(k, k + 1, k + 2, k + 3);
            }
            mesh.Normals.ComputeNormals();
            return mesh;
        }
        public static DomainData Parse(string json)
        {
            DomainData d = JsonConvert.DeserializeObject<DomainData>(json);
            if (d == null || d.active == null || d.active.Length == 0) throw new ArgumentException("Connect a valid TopOpt Domain.");
            return d;
        }
    }

    public static class CadGeometry
    {
        public static bool Finite(double x) { return !double.IsNaN(x) && !double.IsInfinity(x); }
        static bool Inside(Curve c, Point3d p, double tol)
        {
            PointContainment state = c.Contains(p, Plane.WorldXY, tol);
            return state == PointContainment.Inside || state == PointContainment.Coincident;
        }
        static Curve Local(Curve curve, Transform toLocal, double tol)
        {
            if (curve == null || !curve.IsValid || !curve.IsClosed) throw new ArgumentException("Boundary, holes and keep regions must be valid closed curves.");
            Curve c = curve.DuplicateCurve();
            c.Transform(toLocal);
            BoundingBox box = c.GetBoundingBox(true);
            if (Math.Abs(box.Min.Z) > tol || Math.Abs(box.Max.Z) > tol) throw new ArgumentException("All region curves must lie in the selected Plane.");
            using (var intersections = Rhino.Geometry.Intersect.Intersection.CurveSelf(c, tol))
                if (intersections != null && intersections.Count > 0) throw new ArgumentException("Region curves must not intersect themselves.");
            return c;
        }
        public static DomainData Rasterize(Curve boundary, IList<Curve> holes, IList<Curve> keep, double h, Plane plane)
        {
            if (!Finite(h) || h <= 0 || !plane.IsValid) throw new ArgumentException("Cell size must be positive and Plane valid.");
            double tol = Math.Max(1e-8, h * 1e-6);
            Transform tr = Transform.PlaneToPlane(plane, Plane.WorldXY);
            Curve b = Local(boundary, tr, tol);
            Curve[] hs = holes.Select(c => Local(c, tr, tol)).ToArray();
            Curve[] ks = keep.Select(c => Local(c, tr, tol)).ToArray();
            BoundingBox bb = b.GetBoundingBox(true);
            double gx = Math.Ceiling((bb.Max.X - bb.Min.X) / h - 1e-9), gy = Math.Ceiling((bb.Max.Y - bb.Min.Y) / h - 1e-9);
            if (gx < 2 || gy < 2 || gx > 500 || gy > 500 || gx * gy > 60000) throw new ArgumentException("Choose a cell size giving at least 2 x 2 and at most 60000 cells (500 per axis).");
            int nx = (int)gx, ny = (int)gy;
            List<int> active = new List<int>(), solid = new List<int>();
            for (int col = 0; col < nx; col++) for (int row = 0; row < ny; row++)
            {
                Point3d center = new Point3d(bb.Min.X + (col + .5) * h, bb.Min.Y + (ny - row - .5) * h, 0);
                if (!Inside(b, center, tol) || hs.Any(c => Inside(c, center, tol))) continue;
                int e = col * ny + row;
                active.Add(e);
                if (ks.Any(c => Inside(c, center, tol))) solid.Add(e);
            }
            if (active.Count == 0) throw new ArgumentException("The domain contains no cells. Reduce Cell size.");
            return new DomainData { nx = nx, ny = ny, cell = h, origin = new[] { bb.Min.X, bb.Min.Y },
                frame = new[] { new[] { plane.OriginX, plane.OriginY, plane.OriginZ }, new[] { plane.XAxis.X, plane.XAxis.Y, plane.XAxis.Z }, new[] { plane.YAxis.X, plane.YAxis.Y, plane.YAxis.Z } },
                active = active.ToArray(), solid = solid.ToArray() };
        }
        public static int[] Select(DomainData d, IList<IGH_GeometricGoo> selections)
        {
            if (selections.Count == 0) throw new ArgumentException("Select at least one point or curve.");
            int[] available = d.active.SelectMany(d.Face).Distinct().OrderBy(n => n).ToArray();
            HashSet<int> result = new HashSet<int>();
            double tolerance = d.cell * .76; // Less than one cell; diagonal point snapping still works.
            foreach (IGH_GeometricGoo g in selections)
            {
                GH_Point gp = g as GH_Point;
                GH_Curve gc = g as GH_Curve;
                if (gp != null)
                {
                    int n = available.OrderBy(i => d.Node(i).DistanceToSquared(gp.Value)).First();
                    if (d.Node(n).DistanceTo(gp.Value) > tolerance) throw new ArgumentException("A selected point is too far from the active grid.");
                    result.Add(n);
                }
                else if (gc != null)
                {
                    bool found = false;
                    foreach (int n in available)
                    {
                        double t;
                        if (gc.Value.ClosestPoint(d.Node(n), out t) && gc.Value.PointAt(t).DistanceTo(d.Node(n)) <= tolerance)
                        { result.Add(n); found = true; }
                    }
                    if (!found) throw new ArgumentException("A selected curve does not reach the active grid.");
                }
                else throw new ArgumentException("Use point or curve geometry for supports and loads.");
            }
            return result.OrderBy(n => n).ToArray();
        }
    }

    public abstract class Component : GH_Component
    {
  protected static void RegisterGeometry(GH_InputParamManager p,bool solid,int offset=0) {
   p.AddNumberParameter("Length","Length","Overall X dimension",GH_ParamAccess.item,solid?120:12);
   p.AddNumberParameter("Height","Height","Overall Y dimension",GH_ParamAccess.item,solid?60:6);
   if(solid)p.AddNumberParameter("Depth","Depth","Overall Z dimension",GH_ParamAccess.item,30);
   foreach(string axis in new[]{"X","Y","Z"})p.AddNumberParameter("Position "+axis,axis,"World translation",GH_ParamAccess.item,0);
  }

        protected Component(string name, string nick, string description, string section) : base(name, nick, description, "TopOptLab", section) { }
        protected override Bitmap Icon { get { return ComponentIcons.For(GetType().Name); } }
        protected void Error(Exception e) { AddRuntimeMessage(GH_RuntimeMessageLevel.Error, e.Message); }
    }

    public sealed class DomainComponent : Component
    {
        public DomainComponent() : base("TopOpt Domain", "Domain", "Planar domain discretized by cell centers. Preview is the actual solver grid.", "1 Geometry") { }
        public override Guid ComponentGuid { get { return new Guid("b8c177b6-11e6-44b8-9344-25e04c4d59bc"); } }
        protected override void RegisterInputParams(GH_InputParamManager p)
        {
            p.AddCurveParameter("Boundary", "B", "One closed planar outer contour", GH_ParamAccess.item);
            p.AddCurveParameter("Holes", "H", "Closed void contours", GH_ParamAccess.list); p[1].Optional = true;
            p.AddCurveParameter("Keep", "K", "Closed regions kept at full density; counted in Volume", GH_ParamAccess.list); p[2].Optional = true;
            p.AddNumberParameter("Cell size", "h", "Square cell edge in model units", GH_ParamAccess.item, .25);
            p.AddPlaneParameter("Plane", "P", "Design plane; also defines support X/Y", GH_ParamAccess.item, Plane.WorldXY);
        }
        protected override void RegisterOutputParams(GH_OutputParamManager p)
        {
            p.AddTextParameter("Domain", "D", "Discretized domain", GH_ParamAccess.item);
            p.AddMeshParameter("Grid", "G", "Actual active FEM cells", GH_ParamAccess.item);
            p.AddMeshParameter("Preserved", "K", "Cells held at density one", GH_ParamAccess.item);
        }
        protected override void SolveInstance(IGH_DataAccess da)
        {
            Curve b = null; var hs = new List<Curve>(); var ks = new List<Curve>(); double h = .25; Plane plane = Plane.WorldXY;
            if (!da.GetData(0, ref b) || !da.GetData(3, ref h) || !da.GetData(4, ref plane)) return;
            da.GetDataList(1, hs); da.GetDataList(2, ks);
            try {
                DomainData d = CadGeometry.Rasterize(b, hs, ks, h, plane);
                da.SetData(0, JsonConvert.SerializeObject(d, new JsonSerializerSettings { ContractResolver = new FieldsOnlyResolver() }));
                da.SetData(1, d.Mesh(d.active)); da.SetData(2, d.Mesh(d.solid));
                Message = d.active.Length + " cells | " + d.solid.Length + " kept";
            } catch (Exception e) { Error(e); }
        }
    }

    // DomainData's computed Rhino properties must never enter the JSON protocol.
    public sealed class FieldsOnlyResolver : Newtonsoft.Json.Serialization.DefaultContractResolver
    {
        protected override IList<Newtonsoft.Json.Serialization.JsonProperty> CreateProperties(Type type, MemberSerialization serialization)
        { return base.CreateProperties(type, MemberSerialization.Fields); }
    }

    public sealed class SupportComponent : Component
    {
        public SupportComponent() : base("TopOpt Support", "Support", "Select points/curves and constrained local directions. Points show snapped FEM nodes.", "2 Conditions") { }
        public override Guid ComponentGuid { get { return new Guid("7ccf2a95-4300-46f0-8c6d-ec2fd3460fcc"); } }
        protected override void RegisterInputParams(GH_InputParamManager p)
        {
            p.AddTextParameter("Domain", "D", "TopOpt Domain", GH_ParamAccess.item);
            p.AddGeometryParameter("Selection", "G", "Support points or curves", GH_ParamAccess.list);
            p.AddBooleanParameter("Fix X", "X", "Constrain local X translation", GH_ParamAccess.item, true);
            p.AddBooleanParameter("Fix Y", "Y", "Constrain local Y translation", GH_ParamAccess.item, true);
        }
        protected override void RegisterOutputParams(GH_OutputParamManager p)
        {
            p.AddTextParameter("Support", "S", "Connect one or more supports to Solver", GH_ParamAccess.item);
            p.AddPointParameter("Nodes", "N", "Actual constrained nodes", GH_ParamAccess.list);
        }
        protected override void SolveInstance(IGH_DataAccess da)
        {
            string json = null; var gs = new List<IGH_GeometricGoo>(); bool x = true, y = true;
            if (!da.GetData(0, ref json) || !da.GetDataList(1, gs) || !da.GetData(2, ref x) || !da.GetData(3, ref y)) return;
            try {
                if (!x && !y) throw new ArgumentException("Choose at least one constrained direction.");
                DomainData d = DomainData.Parse(json); int[] ns = CadGeometry.Select(d, gs);
                da.SetData(0, JsonConvert.SerializeObject(new { nodes = ns, fix_x = x, fix_y = y }));
                da.SetDataList(1, ns.Select(d.Node)); Message = ns.Length + " nodes";
            } catch (Exception e) { Error(e); }
        }
    }

    public sealed class LoadComponent : Component
    {
        public LoadComponent() : base("TopOpt Load", "Load", "TOTAL vector force shared equally among unique selected nodes. All loads act simultaneously.", "2 Conditions") { }
        public override Guid ComponentGuid { get { return new Guid("c19c2185-75b5-4df9-a79e-084e84cd814d"); } }
        protected override void RegisterInputParams(GH_InputParamManager p)
        {
            p.AddTextParameter("Domain", "D", "TopOpt Domain", GH_ParamAccess.item);
            p.AddGeometryParameter("Selection", "G", "Load points or curves", GH_ParamAccess.list);
            p.AddVectorParameter("Total force", "F", "World vector, in plane. Total force for this component", GH_ParamAccess.item, new Vector3d(0, -.001, 0));
        }
        protected override void RegisterOutputParams(GH_OutputParamManager p)
        {
            p.AddTextParameter("Load", "L", "Connect one or more loads to Solver", GH_ParamAccess.item);
            p.AddPointParameter("Nodes", "N", "Actual loaded nodes", GH_ParamAccess.list);
            p.AddLineParameter("Directions", "V", "Direction glyphs, one cell long; force magnitude is the input F", GH_ParamAccess.list);
        }
        protected override void SolveInstance(IGH_DataAccess da)
        {
            string json = null; var gs = new List<IGH_GeometricGoo>(); Vector3d force = Vector3d.Unset;
            if (!da.GetData(0, ref json) || !da.GetDataList(1, gs) || !da.GetData(2, ref force)) return;
            try {
                DomainData d = DomainData.Parse(json); int[] ns = CadGeometry.Select(d, gs);
                if (!force.IsValid || force.Length == 0 || Math.Abs(force * d.Plane.ZAxis) > force.Length * 1e-8) throw new ArgumentException("Force must be nonzero and lie in the design plane.");
                da.SetData(0, JsonConvert.SerializeObject(new { nodes = ns, force = new[] { force * d.Plane.XAxis, force * d.Plane.YAxis } }));
                da.SetDataList(1, ns.Select(d.Node)); Vector3d direction = force; direction.Unitize();
                da.SetDataList(2, ns.Select(n => new Line(d.Node(n), d.Node(n) + direction * d.cell)));
                Message = ns.Length + " nodes | total F=" + force.Length.ToString("G3");
            } catch (Exception e) { Error(e); }
        }
    }
}
