// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Linq;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Types;
using Rhino.Geometry;
namespace TopoptLab.GH {
 public sealed class GridBoundaryFace {
  public int cell,axis,side;
  public Point3d center;
  public Vector3d normal;
  public Point3d[] corners;
  public JObject Identity(){return new JObject{{"cell",cell},{"axis",axis},{"side",side}};}
  public Curve Outline(){
   if(corners.Length==2)return new LineCurve(corners[0],corners[1]);
   var plane=new Plane(center,normal);
   var sorted=corners.OrderBy(p=>Math.Atan2((p-center)*plane.YAxis,(p-center)*plane.XAxis)).ToList();
   sorted.Add(sorted[0]);return new PolylineCurve(sorted);
  }
 }
 public static class DistributedLoadGeometry {
  public static List<GridBoundaryFace> Boundary(string json,int dim){
   var data=JObject.Parse(json);if(data["nz"]!=null && dim!=3)throw new ArgumentException("Use Surface Load 3D for a 3D domain");
   int nx=(int)data["nx"],ny=(int)data["ny"],nz=dim==3?(int)data["nz"]:1;
   double h=(double)data["cell"];var active=new HashSet<int>(data["active"].Values<int>());
   DomainData d2=dim==2?DomainData.Parse(json):null;Domain3Data d3=dim==3?Domain3Data.Parse(json):null;
   var axes=dim==2?new[]{new Vector3d(d2.frame[1][0],d2.frame[1][1],d2.frame[1][2]),new Vector3d(d2.frame[2][0],d2.frame[2][1],d2.frame[2][2])}:new[]{Vector3d.XAxis,Vector3d.YAxis,Vector3d.ZAxis};
   Func<int,Point3d> node=n=>dim==2?new Point3d(d2.frame[0][0],d2.frame[0][1],d2.frame[0][2])+axes[0]*(d2.origin[0]+n/(ny+1)*h)+axes[1]*(d2.origin[1]+(ny-n%(ny+1))*h):d3.Node(n);
   var result=new List<GridBoundaryFace>();
   foreach(int e in active.OrderBy(v=>v))for(int axis=0;axis<dim;axis++)foreach(int side in new[]{-1,1}){
    int x=e/ny%nx,y=e%ny,z=e/(nx*ny);int[] other={x,y,z};other[axis]+=axis==1?-side:side;
    if(other[0]>=0&&other[0]<nx&&other[1]>=0&&other[1]<ny&&other[2]>=0&&other[2]<nz&&active.Contains(other[2]*nx*ny+other[0]*ny+other[1]))continue;
    var corners=new List<Point3d>();
    for(int dz=0;dz<(dim==3?2:1);dz++)for(int dx=0;dx<2;dx++)for(int dy=0;dy<2;dy++){
     int offset=new[]{dx,dy,dz}[axis],want=axis==1?(side>0?0:1):(side>0?1:0);
     if(offset==want)corners.Add(node((z+dz)*(nx+1)*(ny+1)+(x+dx)*(ny+1)+y+dy));
    }
    result.Add(new GridBoundaryFace{cell=e,axis=axis,side=side,corners=corners.ToArray(),normal=axes[axis]*side,center=new Point3d(corners.Average(p=>p.X),corners.Average(p=>p.Y),corners.Average(p=>p.Z))});
   }
   return result;
  }
  public static double[] InDomain(string json,Vector3d vector){
   var data=JObject.Parse(json);
   if(data["nz"]!=null)return new[]{vector.X,vector.Y,vector.Z};
   var frame=DomainData.Parse(json).frame;
   var ax=new Vector3d(frame[1][0],frame[1][1],frame[1][2]);var ay=new Vector3d(frame[2][0],frame[2][1],frame[2][2]);
   if(Math.Abs(vector*Vector3d.CrossProduct(ax,ay))>1e-8*Math.Max(1,vector.Length))throw new ArgumentException("2D force/acceleration must lie in the domain plane; use 3D for out-of-plane loading");
   return new[]{vector*ax,vector*ay};
  }
  public static bool Touches(GridBoundaryFace f,IGH_GeometricGoo goo,double tolerance,int dim){
   var c=goo as GH_Curve;var b=goo as GH_Brep;var s=goo as GH_Surface;
   if(dim==2){if(c==null)throw new ArgumentException("Select boundary curves for 2D surface loads");double t;return c.Value.ClosestPoint(f.center,out t)&&c.Value.PointAt(t).DistanceTo(f.center)<=tolerance;}
   Brep brep=b!=null?b.Value:s!=null?s.Value:null;
   if(brep==null)throw new ArgumentException("Select Brep faces/surfaces for 3D surface loads");
   Point3d q=brep.ClosestPoint(f.center);return q.IsValid&&q.DistanceTo(f.center)<=tolerance;
  }
 }
 public abstract class SurfaceLoadBase:Component {
  protected abstract int Dimension{get;}
  protected SurfaceLoadBase(string name,string nickname,string category):base(name,nickname,"Uniform pressure or vector traction integrated on grid boundary facets. Positive pressure acts inward. Loaded cells are automatically preserved by Engineering optimization.",category){}
  protected override void RegisterInputParams(GH_InputParamManager p){
   p.AddTextParameter("Domain","D","Matching 2D/3D domain",GH_ParamAccess.item);
   p.AddGeometryParameter("Patch selection","G","Optional curves (2D) or surfaces (3D); selects facets by center distance. Inspect Patch output",GH_ParamAccess.list);p[1].Optional=true;
   p.AddIntegerParameter("Mode","Mode","0 normal pressure; 1 vector traction",GH_ParamAccess.item,0);
   p.AddNumberParameter("Pressure","P","Force/length squared in Material units; positive inward, negative outward",GH_ParamAccess.item,.1);
   p.AddVectorParameter("Traction","T","World vector in force/length squared, used in Mode 1",GH_ParamAccess.item,new Vector3d(0,-.1,0));
   p.AddIntegerParameter("Boundary side","Side","0 all exposed faces; 1 +X; 2 -X; 3 +Y; 4 -Y; 5 +Z; 6 -Z. 2D uses domain axes",GH_ParamAccess.item,1);
   p.AddNumberParameter("Selection tolerance","Tol","Distance from facet center to selection, as fraction of h. Geometry selection is optional",GH_ParamAccess.item,.1);
  }
  protected override void RegisterOutputParams(GH_OutputParamManager p){p.AddTextParameter("Load","L","Connect to Load Case, then Engineering",GH_ParamAccess.item);p.AddCurveParameter("Loaded facets","Patch","Actual discretized loading boundary; verify selection",GH_ParamAccess.list);p.AddLineParameter("Directions","V","Load directions; display length is one cell, not force magnitude",GH_ParamAccess.list);p.AddTextParameter("Info","Info","Facet count and integration convention",GH_ParamAccess.item);}
  protected override void SolveInstance(IGH_DataAccess da){
   string json=null;var selection=new List<IGH_GeometricGoo>();int mode=0,side=1;double p=.1,tol=.1;Vector3d t=Vector3d.Unset;
   if(!da.GetData(0,ref json)||!da.GetData(2,ref mode)||!da.GetData(3,ref p)||!da.GetData(4,ref t)||!da.GetData(5,ref side)||!da.GetData(6,ref tol))return;da.GetDataList(1,selection);
   try{
    if(mode<0||mode>1||side<0||side>2*Dimension||!CadGeometry.Finite(tol)||tol<=0||tol>1)throw new ArgumentException("Invalid mode, side or tolerance (0 < Tol <= 1 cell)");
    if(mode==0&&(!CadGeometry.Finite(p)||p==0))throw new ArgumentException("Use finite nonzero pressure");
    if(mode==1&&(!t.IsValid||t.Length==0))throw new ArgumentException("Use a nonzero traction vector");
    var data=JObject.Parse(json);double h=(double)data["cell"];
    var facets=DistributedLoadGeometry.Boundary(json,Dimension).Where(f=>side==0||(f.axis==(side-1)/2&&f.side==(side%2==1?1:-1))).ToList();
    if(selection.Count>0){var selected=new HashSet<GridBoundaryFace>();foreach(var g in selection){var matches=facets.Where(f=>DistributedLoadGeometry.Touches(f,g,tol*h,Dimension)).ToList();if(matches.Count==0)throw new ArgumentException("A patch selection reaches no facet centers; check Side, Cell size and Tol");foreach(var f in matches)selected.Add(f);}facets=facets.Where(selected.Contains).ToList();}
    if(facets.Count==0)throw new ArgumentException("No exposed facets selected");
    var load=new JObject{{"kind",mode==0?"pressure":"traction"},{"faces",new JArray(facets.Select(f=>f.Identity()))}};
    if(mode==0)load["pressure"]=p;else load["traction"]=new JArray(DistributedLoadGeometry.InDomain(json,t));
    da.SetData(0,load.ToString());da.SetDataList(1,facets.Select(f=>f.Outline()));
    da.SetDataList(2,facets.Select(f=>{var v=mode==0?f.normal*(-Math.Sign(p)):t;v.Unitize();return new Line(f.center,f.center+v*h);}));
    da.SetData(3,facets.Count+" grid facets; "+facets.Select(f=>f.cell).Distinct().Count()+" interface cells preserved during optimization.\n"+(Dimension==3?"Area = facet count * h^2.":"Area = edge count * h * Settings thickness.")+"\nPressure/traction uses Material force / length^2. Fixed grid boundary, not follower pressure on the evolving surface. Inspect Patch output after resizing.");Message=facets.Count+" facets";
   }catch(Exception e){Error(e);}
  }
 }
 public sealed class SurfaceLoadComponent:SurfaceLoadBase {
  public SurfaceLoadComponent():base("TopOpt Surface Load","Surface Load","2 Conditions"){}
  protected override int Dimension{get{return 2;}}
  public override Guid ComponentGuid{get{return new Guid("42fe95a1-7700-4900-a000-000000000005");}}
 }
 public sealed class SurfaceLoad3DComponent:SurfaceLoadBase {
  public SurfaceLoad3DComponent():base("TopOpt Surface Load 3D","Surface Load 3D","7 Conditions 3D"){}
  protected override int Dimension{get{return 3;}}
  public override Guid ComponentGuid{get{return new Guid("42fe95a1-7700-4900-a000-000000000006");}}
 }
 public sealed class GravityComponent:Component {
  public GravityComponent():base("TopOpt Gravity","Gravity","Self-weight from Material density. Acceleration always in m/s^2, independent of model units. Connect to the same Load Case as other simultaneous loads.","0 Engineering"){}
  public override Guid ComponentGuid{get{return new Guid("42fe95a1-7700-4900-a000-000000000007");}}
  protected override void RegisterInputParams(GH_InputParamManager p){p.AddTextParameter("Domain","D","2D or 3D domain",GH_ParamAccess.item);p.AddVectorParameter("Acceleration","g","World acceleration in m/s^2; for XY 2D use (0,-9.80665,0)",GH_ParamAccess.item,new Vector3d(0,0,-9.80665));}
  protected override void RegisterOutputParams(GH_OutputParamManager p){p.AddTextParameter("Load","L","Connect to Load Case, then Engineering",GH_ParamAccess.item);p.AddTextParameter("Info","Info","Self-weight behavior",GH_ParamAccess.item);}
  protected override void SolveInstance(IGH_DataAccess da){string json=null;Vector3d g=Vector3d.Unset;if(!da.GetData(0,ref json)||!da.GetData(1,ref g))return;try{if(!g.IsValid||g.Length==0)throw new ArgumentException("Use nonzero finite acceleration");da.SetData(0,new JObject{{"kind","gravity"},{"acceleration",new JArray(DistributedLoadGeometry.InDomain(json,g))}}.ToString());da.SetData(1,"Acceleration in m/s^2; mass density comes from Material. Weight follows physical element density. Optimization uses a fixed material budget and projected-gradient updates, including load sensitivities. Inspect convergence status.");Message="Self-weight";}catch(Exception e){Error(e);}}
 }
}
