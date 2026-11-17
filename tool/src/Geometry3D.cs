// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Linq;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Globalization;
using Newtonsoft.Json;
using Rhino.Geometry;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Types;
namespace TopoptLab.GH
{
    public sealed class Domain3Data
    {
        public int nx,ny,nz;public double cell;public double[] origin;public int[] active,solid;
        public Point3d Node(int n) {int row=n%(ny+1),col=(n/(ny+1))%(nx+1),layer=n/((nx+1)*(ny+1));return new Point3d(origin[0]+col*cell,origin[1]+(ny-row)*cell,origin[2]+layer*cell);}
        public int[] Hex(int e) {int row=e%ny,col=(e/ny)%nx,layer=e/(nx*ny);int n=layer*(nx+1)*(ny+1)+col*(ny+1)+row,s=(nx+1)*(ny+1);return new[]{n+1,n+ny+2,n+ny+1,n,n+s+1,n+s+ny+2,n+s+ny+1,n+s};}
        public static Domain3Data Parse(string text) {var d=JsonConvert.DeserializeObject<Domain3Data>(text);if(d==null||d.nz<1||d.active==null||d.active.Length==0)throw new ArgumentException("Connect Domain 3D");return d;}
        public Mesh Surface()
        {
            // Only boundary cells need connectivity and only boundary nodes become vertices.
            var occupied=new HashSet<int>(active);var mesh=new Mesh();var vertices=new Dictionary<int,int>();
            foreach(int e in active) {
                int y=e%ny,x=(e/ny)%nx,z=e/(nx*ny);int[] hex=null;
                for(int side=0;side<6;side++) {
                    bool neighbor=side==0?z>0&&occupied.Contains(e-nx*ny):side==1?z<nz-1&&occupied.Contains(e+nx*ny):side==2?y<ny-1&&occupied.Contains(e+1):side==3?x<nx-1&&occupied.Contains(e+ny):side==4?y>0&&occupied.Contains(e-1):x>0&&occupied.Contains(e-ny);
                    if(neighbor)continue;
                    if(hex==null)hex=Hex(e);var face=VoxelMesh.Sides[side];int[] indices=new int[4];
                    for(int k=0;k<4;k++){int id=hex[face[k]],index;if(!vertices.TryGetValue(id,out index)){index=mesh.Vertices.Count;vertices.Add(id,index);mesh.Vertices.Add(Node(id));}indices[k]=index;}
                    mesh.Faces.AddFace(indices[0],indices[1],indices[2],indices[3]);
                }
            }
            mesh.Weld(Math.PI);mesh.Normals.ComputeNormals();mesh.Compact();return mesh;
        }
    }
    public sealed class VoxelGeometryPlan
    {
        public int Nx,Ny,Nz;public long BoundingCells,EstimatedBytes;public ulong AvailableBytes;
        public string Info(int active,int kept) {return string.Format(CultureInfo.InvariantCulture,
            "Bounding grid: {0:N0} cells ({1} x {2} x {3}); active: {4:N0}; kept: {5:N0}.\nEstimated geometry/preview allowance: {6:F2} GiB; available RAM at preflight: {7:F2} GiB.\nThis is a conservative geometry estimate, not a solver allocation measurement. The selected solver performs a separate memory check. Reduce Cell size for more detail; preserve the physical filter radius when comparing resolutions.",
            BoundingCells,Nx,Ny,Nz,active,kept,EstimatedBytes/1073741824d,AvailableBytes/1073741824d);}
    }
    public static class VoxelGeometryBudget
    {
        public const int MaximumAxis=2048,MaximumCells=2000000;
        [StructLayout(LayoutKind.Sequential)]struct MemoryStatus {public uint Length,Load;public ulong TotalPhysical,AvailablePhysical,TotalPageFile,AvailablePageFile,TotalVirtual,AvailableVirtual,AvailableExtendedVirtual;}
        [DllImport("kernel32.dll",SetLastError=true)]static extern bool GlobalMemoryStatusEx(ref MemoryStatus status);
        public static ulong AvailableMemory() {if(RuntimePaths.IsMac)return RuntimePaths.MacAvailableMemory();var status=new MemoryStatus();status.Length=(uint)Marshal.SizeOf(typeof(MemoryStatus));if(!GlobalMemoryStatusEx(ref status))throw new ArgumentException("Cannot read available RAM for the 3D geometry preflight. Restart Rhino and retry.");return status.AvailablePhysical;}
        public static VoxelGeometryPlan Plan(double[] sizes,double h,int limit,ulong availableBytes)
        {
            if(!CadGeometry.Finite(h)||h<=0)throw new ArgumentException("Cell size must be finite and positive");
            if(sizes==null||sizes.Length!=3||sizes.Any(v=>!CadGeometry.Finite(v)||v<=0))throw new ArgumentException("Solid dimensions must be finite and positive");
            if(limit<1||limit>MaximumCells)throw new ArgumentException("Voxel limit must be 1..2000000; it is a user budget, not a solver capacity guarantee");
            var axes=sizes.Select(v=>Math.Ceiling(v/h)).ToArray();
            if(axes.Any(v=>!CadGeometry.Finite(v)||v<1||v>MaximumAxis))throw new ArgumentException("Increase Cell size: at most 2048 cells per axis");
            int nx=(int)axes[0],ny=(int)axes[1],nz=(int)axes[2];long cells=(long)nx*ny*nz;
            if(cells>MaximumCells)throw new ArgumentException("Bounding grid exceeds the 2000000-cell format guard; increase Cell size");
            if(cells>limit)throw new ArgumentException(string.Format(CultureInfo.InvariantCulture,"Bounding grid needs {0:N0} cells, exceeding Voxel limit {1:N0}. Increase Limit after reviewing RAM and solver settings, or increase Cell size.",cells,limit));
            if((long)(nx+1)*(ny+1)*(nz+1)>int.MaxValue)throw new ArgumentException("Grid node numbering exceeds the 32-bit format guard; increase Cell size");
            long estimate=256L*1024*1024+cells*12000L;
            if(estimate>.6*availableBytes)throw new ArgumentException(string.Format(CultureInfo.InvariantCulture,"3D geometry needs an estimated {0:F2} GiB, above 60% of currently available RAM ({1:F2} GiB). Increase Cell size or free RAM; no geometry has been allocated.",estimate/1073741824d,availableBytes/1073741824d));
            return new VoxelGeometryPlan{Nx=nx,Ny=ny,Nz=nz,BoundingCells=cells,EstimatedBytes=estimate,AvailableBytes=availableBytes};
        }
    }
    public static class VoxelMesh
    {
        internal static readonly int[][] Sides={new[]{0,3,2,1},new[]{4,5,6,7},new[]{0,1,5,4},new[]{1,2,6,5},new[]{2,3,7,6},new[]{3,0,4,7}};
        struct FaceKey:IEquatable<FaceKey>
        {
            readonly int a,b,c,d;
            static void Order(ref int x,ref int y){if(x>y){int t=x;x=y;y=t;}}
            public FaceKey(int w,int x,int y,int z){Order(ref w,ref x);Order(ref y,ref z);Order(ref w,ref y);Order(ref x,ref z);Order(ref x,ref y);a=w;b=x;c=y;d=z;}
            public bool Equals(FaceKey other){return a==other.a&&b==other.b&&c==other.c&&d==other.d;}
            public override bool Equals(object other){return other is FaceKey&&Equals((FaceKey)other);}
            public override int GetHashCode(){unchecked{return ((a*397^b)*397^c)*397^d;}}
        }
        struct Face {public int A,B,C,D,Cell;public Face(int a,int b,int c,int d,int cell){A=a;B=b;C=c;D=d;Cell=cell;}}
        public static Mesh Build(Point3d[] nodes,int[][] hexes,bool[] include,System.Drawing.Color[] colors,double unused)
        {
            // Canonical value keys avoid six sorted strings and temporary arrays per voxel.
            var faces=new Dictionary<FaceKey,Face>();
            for(int e=0;e<hexes.Length;e++)if(include==null||include[e])foreach(var side in Sides) {
                var hex=hexes[e];int a=hex[side[0]],b=hex[side[1]],c=hex[side[2]],d=hex[side[3]];var key=new FaceKey(a,b,c,d);
                if(!faces.Remove(key))faces.Add(key,new Face(a,b,c,d,e));
            }
            var mesh=new Mesh();foreach(var face in faces.Values) {int k=mesh.Vertices.Count;mesh.Vertices.Add(nodes[face.A]);mesh.Vertices.Add(nodes[face.B]);mesh.Vertices.Add(nodes[face.C]);mesh.Vertices.Add(nodes[face.D]);if(colors!=null){var color=colors[face.Cell];for(int j=0;j<4;j++)mesh.VertexColors.Add(color);}mesh.Faces.AddFace(k,k+1,k+2,k+3);}
            if(colors==null){mesh.Vertices.CombineIdentical(true,true);mesh.Weld(Math.PI);}
            mesh.Normals.ComputeNormals();mesh.Compact();return mesh;
        }
    }
    public sealed class Domain3DComponent:Component
    {
        public Domain3DComponent():base("TopOpt Domain 3D","Domain 3D","Voxelize a closed Brep in WORLD XYZ. Center sampling; up to the selected voxel limit. Keep/Voids are closed solids.","6 Geometry 3D"){}
        public override Guid ComponentGuid {get{return new Guid("6c8b1e31-0011-4e55-8001-010000000001");}}
        protected override void RegisterInputParams(GH_InputParamManager p){p.AddBrepParameter("Solid","B","Closed valid solid",GH_ParamAccess.item);p.AddBrepParameter("Voids","Void","Optional closed void solids",GH_ParamAccess.list);p[1].Optional=true;p.AddBrepParameter("Keep","Keep","Optional preserved solids",GH_ParamAccess.list);p[2].Optional=true;p.AddNumberParameter("Cell size","h","World length units; grid is XYZ aligned",GH_ParamAccess.item,5);p.AddIntegerParameter("Voxel limit","Limit","Bounding-grid user budget, 8000 default; up to 2000000 with RAM preflight. Solver checks its own memory needs",GH_ParamAccess.item,8000);}
        protected override void RegisterOutputParams(GH_OutputParamManager p){p.AddTextParameter("Domain","D","3D model",GH_ParamAccess.item);p.AddMeshParameter("Voxel boundary","Grid","Boundary of active voxels",GH_ParamAccess.item);p.AddTextParameter("Resources","Info","Bounding/active cells and geometry memory preflight",GH_ParamAccess.item);}
        protected override void SolveInstance(IGH_DataAccess da)
        {
            Brep b=null;var holes=new List<Brep>();var keep=new List<Brep>();double h=5;if(!da.GetData(0,ref b)||!da.GetData(3,ref h))return;da.GetDataList(1,holes);da.GetDataList(2,keep);
            try {
                if(b==null||!b.IsValid||!b.IsSolid||holes.Concat(keep).Any(v=>v==null||!v.IsValid||!v.IsSolid))throw new ArgumentException("Use closed valid Breps for Solid, Voids and Keep");
                if(!CadGeometry.Finite(h)||h<=0)throw new ArgumentException("Cell size must be positive");
                int limit=8000;da.GetData(4,ref limit);
                var box=b.GetBoundingBox(true);var sizes=new[]{box.Max.X-box.Min.X,box.Max.Y-box.Min.Y,box.Max.Z-box.Min.Z};
                var plan=VoxelGeometryBudget.Plan(sizes,h,limit,VoxelGeometryBudget.AvailableMemory());
                var d=new Domain3Data{nx=plan.Nx,ny=plan.Ny,nz=plan.Nz,cell=h,origin=new[]{box.Min.X,box.Min.Y,box.Min.Z}};
                var active=new List<int>();var solid=new List<int>();double tol=Math.Max(1e-8,h*1e-6);
                var holeBoxes=holes.Select(v=>{var bounds=v.GetBoundingBox(true);bounds.Inflate(tol);return bounds;}).ToArray();
                var keepBoxes=keep.Select(v=>{var bounds=v.GetBoundingBox(true);bounds.Inflate(tol);return bounds;}).ToArray();
                for(int z=0;z<d.nz;z++)for(int x=0;x<d.nx;x++)for(int y=0;y<d.ny;y++) {
                    var pt=new Point3d(d.origin[0]+(x+.5)*h,d.origin[1]+(d.ny-y-.5)*h,d.origin[2]+(z+.5)*h);
                    if(!b.IsPointInside(pt,tol,false))continue;
                    bool removed=false;for(int k=0;k<holes.Count;k++)if(holeBoxes[k].Contains(pt)&&holes[k].IsPointInside(pt,tol,false)){removed=true;break;}if(removed)continue;
                    int e=z*d.nx*d.ny+x*d.ny+y;active.Add(e);for(int k=0;k<keep.Count;k++)if(keepBoxes[k].Contains(pt)&&keep[k].IsPointInside(pt,tol,false)){solid.Add(e);break;}
                }
                if(active.Count==0)throw new ArgumentException("No active voxels; reduce h or check the solid");
                d.active=active.ToArray();d.solid=solid.ToArray();da.SetData(0,JsonConvert.SerializeObject(d));da.SetData(1,d.Surface());da.SetData(2,plan.Info(active.Count,solid.Count));Message=active.Count+" voxels | "+solid.Count+" kept";
            }catch(Exception e){Error(e);}
        }
    }
    public static class Selection3D
    {
        public static int[] Select(Domain3Data d,List<IGH_GeometricGoo> selections)
        {
            var available=d.active.SelectMany(d.Hex).Distinct().ToArray();var found=new HashSet<int>();double tol=.76*d.cell;
            foreach(var goo in selections) {
                var p=goo as GH_Point;var c=goo as GH_Curve;var b=goo as GH_Brep;var s=goo as GH_Surface;
                if(p!=null){int n=available.OrderBy(i=>d.Node(i).DistanceToSquared(p.Value)).First();if(d.Node(n).DistanceTo(p.Value)>tol)throw new ArgumentException("Point too far from active voxel nodes");found.Add(n);continue;}
                Brep brep=b!=null?b.Value:s!=null?s.Value:null;
                if(c==null&&brep==null)throw new ArgumentException("Select points, curves or Brep faces/surfaces");
                int before=found.Count;bool any=false;
                foreach(int n in available){Point3d pt=d.Node(n),q=Point3d.Unset;if(c!=null){double t;if(c.Value.ClosestPoint(pt,out t))q=c.Value.PointAt(t);}else q=brep.ClosestPoint(pt);if(q.IsValid&&q.DistanceTo(pt)<=tol){found.Add(n);any=true;}}
                if(!any)throw new ArgumentException("Selection does not reach voxel nodes");
            }
            if(found.Count==0)throw new ArgumentException("Empty selection");return found.OrderBy(n=>n).ToArray();
        }
    }
    public sealed class Support3DComponent:Component
    {
        public Support3DComponent():base("TopOpt Support 3D","Support 3D","World X/Y/Z restraints on selected points, curves or surfaces.","7 Conditions 3D"){}
        public override Guid ComponentGuid {get{return new Guid("6c8b1e31-0011-4e55-8001-010000000002");}}
        protected override void RegisterInputParams(GH_InputParamManager p){p.AddTextParameter("Domain","D","Domain 3D",GH_ParamAccess.item);p.AddGeometryParameter("Selection","G","Select a face/surface, curve or point",GH_ParamAccess.list);p.AddBooleanParameter("Fix X","X","World X",GH_ParamAccess.item,true);p.AddBooleanParameter("Fix Y","Y","World Y",GH_ParamAccess.item,true);p.AddBooleanParameter("Fix Z","Z","World Z",GH_ParamAccess.item,true);}
        protected override void RegisterOutputParams(GH_OutputParamManager p){p.AddTextParameter("Support","S","3D support",GH_ParamAccess.item);p.AddPointParameter("Nodes","N","Actual constrained nodes",GH_ParamAccess.list);}
        protected override void SolveInstance(IGH_DataAccess da){string json=null;var gs=new List<IGH_GeometricGoo>();bool x=true,y=true,z=true;if(!da.GetData(0,ref json)||!da.GetDataList(1,gs)||!da.GetData(2,ref x)||!da.GetData(3,ref y)||!da.GetData(4,ref z))return;try{if(!x&&!y&&!z)throw new ArgumentException("Choose a constrained direction");var d=Domain3Data.Parse(json);var ns=Selection3D.Select(d,gs);da.SetData(0,JsonConvert.SerializeObject(new{nodes=ns,fix_x=x,fix_y=y,fix_z=z}));da.SetDataList(1,ns.Select(d.Node));Message=ns.Length+" nodes";}catch(Exception e){Error(e);}}
    }
    public sealed class Load3DComponent:Component
    {
        public Load3DComponent():base("TopOpt Load 3D","Load 3D","TOTAL world force shared equally across selected nodes; not pressure or tributary-area traction.","7 Conditions 3D"){}
        public override Guid ComponentGuid {get{return new Guid("6c8b1e31-0011-4e55-8001-010000000003");}}
        protected override void RegisterInputParams(GH_InputParamManager p){p.AddTextParameter("Domain","D","Domain 3D",GH_ParamAccess.item);p.AddGeometryParameter("Selection","G","Points, curves or surfaces",GH_ParamAccess.list);p.AddVectorParameter("Total force","F","World force vector",GH_ParamAccess.item,new Vector3d(0,0,-100));}
        protected override void RegisterOutputParams(GH_OutputParamManager p){p.AddTextParameter("Load","L","3D load",GH_ParamAccess.item);p.AddPointParameter("Nodes","N","Actual loaded nodes",GH_ParamAccess.list);p.AddLineParameter("Directions","V","Force direction glyphs",GH_ParamAccess.list);}
        protected override void SolveInstance(IGH_DataAccess da){string json=null;var gs=new List<IGH_GeometricGoo>();Vector3d f=Vector3d.Unset;if(!da.GetData(0,ref json)||!da.GetDataList(1,gs)||!da.GetData(2,ref f))return;try{if(!f.IsValid||f.Length==0)throw new ArgumentException("Use a nonzero force");var d=Domain3Data.Parse(json);var ns=Selection3D.Select(d,gs);da.SetData(0,JsonConvert.SerializeObject(new{nodes=ns,force=new[]{f.X,f.Y,f.Z}}));da.SetDataList(1,ns.Select(d.Node));var v=f;v.Unitize();da.SetDataList(2,ns.Select(n=>new Line(d.Node(n),d.Node(n)+v*d.cell)));Message=ns.Length+" nodes | total F="+f.Length.ToString("G4");}catch(Exception e){Error(e);}}
    }
}
