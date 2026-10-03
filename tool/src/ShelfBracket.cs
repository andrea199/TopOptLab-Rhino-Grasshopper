// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Linq;
using System.Collections.Generic;
using System.Globalization;
using Newtonsoft.Json.Linq;
using Grasshopper.Kernel;
using Rhino.Geometry;
namespace TopoptLab.GH {
 public sealed class ShelfBracketGeometry {
  public Brep Envelope;
  public List<Brep> Voids=new List<Brep>(),Keep=new List<Brep>();
  public JObject Spec;
  static Brep Box(double x0,double y0,double z0,double x1,double y1,double z1) {return new BoundingBox(new Point3d(x0,y0,z0),new Point3d(x1,y1,z1)).ToBrep();}
  static Brep Cylinder(Point3d p,Vector3d axis,double r,double length) {return new Cylinder(new Circle(new Plane(p,axis),r),length).ToBrep(true,true);}
  public static ShelfBracketGeometry Create(double length,double height,double width,double plate,double diameter,double pitch,double inset,double accessDiameter,double accessDepth,Point3d origin) {
   double[] values={length,height,width,plate,diameter,pitch,inset,accessDiameter,accessDepth,origin.X,origin.Y,origin.Z};
   if(values.Any(v=>!CadGeometry.Finite(v)))throw new ArgumentException("All bracket dimensions and coordinates must be finite");
   if(length<=0||height<=0||width<=0||plate<=0||diameter<=0||pitch<=0||accessDepth<0)throw new ArgumentException("Positive dimensions required; access depth may be zero");
   if(plate>=Math.Min(length,height)/3||diameter>=width||accessDiameter<diameter||accessDiameter>=width)throw new ArgumentException("Check plate thickness, hole diameter and tool diameter against the part size");
   double r=accessDiameter/2,low=(height-pitch)/2,high=(height+pitch)/2;
   if(low<=r||high+r>=height-plate||pitch<=accessDiameter||inset<=plate+r||length-2*inset<=accessDiameter||inset>=length/2||accessDepth>=Math.Min(length,height)-plate)
    throw new ArgumentException("Holes/tool clearances overlap or reach a plate edge; reduce pitch/access or increase the envelope");
   var g=new ShelfBracketGeometry();
   g.Envelope=Box(0,-width/2,0,length,width/2,height);
   g.Keep.Add(Box(0,-width/2,0,plate,width/2,height));
   g.Keep.Add(Box(0,-width/2,height-plate,length,width/2,height));
   foreach(double z in new[]{low,high}) {
    g.Voids.Add(Cylinder(new Point3d(-1,0,z),Vector3d.XAxis,diameter/2,plate+1));
    if(accessDepth>0)g.Voids.Add(Cylinder(new Point3d(plate,0,z),Vector3d.XAxis,r,accessDepth));
   }
   foreach(double x in new[]{inset,length-inset}) {
    g.Voids.Add(Cylinder(new Point3d(x,0,height-plate),Vector3d.ZAxis,diameter/2,plate+1));
    if(accessDepth>0)g.Voids.Add(Cylinder(new Point3d(x,0,height-plate-accessDepth),Vector3d.ZAxis,r,accessDepth));
   }
   var move=Transform.Translation(new Vector3d(origin.X,origin.Y,origin.Z));g.Envelope.Transform(move);
   foreach(var b in g.Voids.Concat(g.Keep))b.Transform(move);
   g.Spec=JObject.FromObject(new {schema="topoptlab-shelf-bracket-v1",length_mm=length,height_mm=height,width_mm=width,plate_mm=plate,hole_diameter_mm=diameter,wall_pitch_mm=pitch,top_inset_mm=inset,access_diameter_mm=accessDiameter,access_depth_mm=accessDepth,origin=new[]{origin.X,origin.Y,origin.Z},wall_hole_z=new[]{low+origin.Z,high+origin.Z}});
   return g;
  }
 }
 public sealed class ShelfBracket3DComponent:Component {
  public ShelfBracket3DComponent():base("TopOpt Shelf Bracket 3D","Shelf Bracket 3D","Parametric shelf bracket in mm. X projects from wall, Y is width, Z is up. Voids reserve screw holes/tool access. Keep preserves attachment plates.","6 Geometry 3D"){}
  public override Guid ComponentGuid {get{return new Guid("5e1120a1-4a97-4d7b-9294-992198314001");}}
  protected override void RegisterInputParams(GH_InputParamManager p) {
   string[] names={"Length","Height","Width","Plate thickness","Hole diameter","Wall hole pitch","Top hole inset","Tool diameter","Tool access depth","Position X","Position Y","Position Z"};
   double[] values={250,150,25,10,8,100,40,16,25,0,0,0};
   for(int k=0;k<names.Length;k++)p.AddNumberParameter(names[k],names[k],"Millimetres. Resizing preserves circular hole/tool diameters.",GH_ParamAccess.item,values[k]);
  }
  protected override void RegisterOutputParams(GH_OutputParamManager p) {
   p.AddBrepParameter("Envelope","B","Starting design space",GH_ParamAccess.item);
   p.AddBrepParameter("Voids","Void","Nominal screw holes and screwdriver/head access",GH_ParamAccess.list);
   p.AddBrepParameter("Keep","Keep","Attachment plates; Voids take precedence in Domain 3D",GH_ParamAccess.list);
   p.AddTextParameter("Specification","Spec","Connect to Bracket Cases 3D",GH_ParamAccess.item);
   p.AddTextParameter("Info","Info","Units and limitations",GH_ParamAccess.item);
  }
  protected override void SolveInstance(IGH_DataAccess da) {
   var v=new double[12];for(int k=0;k<v.Length;k++)if(!da.GetData(k,ref v[k]))return;
   try {
    var g=ShelfBracketGeometry.Create(v[0],v[1],v[2],v[3],v[4],v[5],v[6],v[7],v[8],new Point3d(v[9],v[10],v[11]));
    da.SetData(0,g.Envelope);da.SetDataList(1,g.Voids);da.SetDataList(2,g.Keep);da.SetData(3,g.Spec.ToString());
    da.SetData(4,"mm / N only. Four circular nominal holes. Tool access is reserved space, not a reachability proof.\nGrid holes are voxel approximations, not manufacturing fits. Wall pads idealize the connection; anchors, preload and wall contact are not simulated.");Message="4 nominal holes";
   }catch(Exception e){Error(e);}
  }
 }
 public sealed class ShelfBracketConditions {
  public JObject Support,Summary;
  public List<JObject> Cases=new List<JObject>();
  public List<GridBoundaryFace> Top,Wall,Front,Left,Right;
  public const double Gravity=9.80665;
  static JObject Load(List<GridBoundaryFace> faces,double force,double h) {
   if(faces.Count==0)throw new ArgumentException("A load patch reaches no cells; reduce cell size or widen the patch");
   return new JObject{{"kind","traction"},{"traction",new JArray(0,0,-force/(faces.Count*h*h))},{"faces",new JArray(faces.Select(f=>f.Identity()))}};
  }
  static int Node(Domain3Data d,Point3d p) {
   int x=(int)Math.Round((p.X-d.origin[0])/d.cell),y=d.ny-(int)Math.Round((p.Y-d.origin[1])/d.cell),z=(int)Math.Round((p.Z-d.origin[2])/d.cell);
   return z*(d.nx+1)*(d.ny+1)+x*(d.ny+1)+y;
  }
  public static ShelfBracketConditions Create(string domain,JObject spec,JObject material,double payload,double shelf,double frontDepth,double sideOffset) {
   if((string)spec["schema"]!="topoptlab-shelf-bracket-v1")throw new ArgumentException("Connect Shelf Bracket 3D specification");
   if((string)material["length_unit"]!="mm"||(string)material["force_unit"]!="N")throw new ArgumentException("Bracket example requires Material units mm and N");
   if(new[]{payload,shelf,frontDepth,sideOffset}.Any(v=>!CadGeometry.Finite(v))||payload<=0||shelf<0||frontDepth<=0||sideOffset<=0||sideOffset>=1)throw new ArgumentException("Use payload > 0, shelf mass >= 0, front depth > 0 and 0 < side offset < 1");
   var d=Domain3Data.Parse(domain);double h=d.cell;
   var o=spec["origin"].Values<double>().ToArray();double w=(double)spec["width_mm"],length=(double)spec["length_mm"],height=(double)spec["height_mm"];
   if(Math.Abs(d.origin[0]-o[0])>1e-7||Math.Abs(d.origin[1]-(o[1]-w/2))>1e-7||Math.Abs(d.origin[2]-o[2])>1e-7||d.nx!=(int)Math.Ceiling(length/h)||d.ny!=(int)Math.Ceiling(w/h)||d.nz!=(int)Math.Ceiling(height/h))throw new ArgumentException("Domain and bracket specification differ");
   if(frontDepth>=length-(double)spec["plate_mm"])throw new ArgumentException("Front patch must be shorter than the projecting arm");
   // Reject nominal screw holes that disappear under centre sampling.
   var active=new HashSet<int>(d.active);double plate=(double)spec["plate_mm"],radius=(double)spec["hole_diameter_mm"]/2,inset=(double)spec["top_inset_mm"];
   foreach(int holeIndex in Enumerable.Range(0,4)) {
    double cx=holeIndex==2?inset:length-inset,cz=holeIndex==0?(height-(double)spec["wall_pitch_mm"])/2:(height+(double)spec["wall_pitch_mm"])/2;
    bool resolved=false;
    for(int z=0;z<d.nz&&!resolved;z++)for(int x=0;x<d.nx&&!resolved;x++)for(int y=0;y<d.ny;y++) {
     double px=(x+.5)*h,py=-w/2+(d.ny-y-.5)*h,pz=(z+.5)*h;
     bool inside=holeIndex<2?px<plate&&py*py+(pz-cz)*(pz-cz)<radius*radius: pz>height-plate&&pz<height&&(px-cx)*(px-cx)+py*py<radius*radius;
     if(inside&&Math.Abs(py)<w/2&&!active.Contains(z*d.nx*d.ny+x*d.ny+y)){resolved=true;break;}
    }
    if(!resolved)throw new ArgumentException("A nominal screw hole disappears on this grid; reduce Cell size or increase hole diameter");
   }
   var c=new ShelfBracketConditions();var boundary=DistributedLoadGeometry.Boundary(domain,3);
   double topZ=boundary.Max(f=>f.center.Z),frontX=boundary.Max(f=>f.center.X);
   c.Top=boundary.Where(f=>f.axis==2&&f.side==1&&Math.Abs(f.center.Z-topZ)<1e-7).ToList();
   c.Front=c.Top.Where(f=>f.center.X>frontX-frontDepth-1e-7).ToList();
   double ymin=c.Top.Min(f=>f.corners.Min(p=>p.Y)),ymax=c.Top.Max(f=>f.corners.Max(p=>p.Y));
   c.Right=c.Front.Where(f=>f.center.Y>ymin+(ymax-ymin)*sideOffset-1e-7).ToList();
   c.Left=c.Front.Where(f=>f.center.Y<ymax-(ymax-ymin)*sideOffset+1e-7).ToList();
   var zs=spec["wall_hole_z"].Values<double>().ToArray();double padHeight=(double)spec["access_diameter_mm"]+(double)spec["plate_mm"];
   if(padHeight>=(double)spec["wall_pitch_mm"])throw new ArgumentException("Wall support pads overlap at this resolution; reduce cell size");
   c.Wall=new List<GridBoundaryFace>();
   foreach(double z in zs) {
    var patch=boundary.Where(f=>f.axis==0&&f.side==-1&&Math.Abs(f.center.X-o[0])<1e-7&&Math.Abs(f.center.Z-z)<=padHeight/2).ToList();
    if(patch.Count==0)throw new ArgumentException("A wall pad reaches no faces; reduce cell size");c.Wall.AddRange(patch);
   }
   c.Support=JObject.FromObject(new {nodes=c.Wall.SelectMany(f=>f.corners).Select(p=>Node(d,p)).Distinct().OrderBy(n=>n).ToArray(),fix_x=true,fix_y=true,fix_z=true});
   var patches=new[]{c.Top,c.Front,c.Right,c.Left};var names=new[]{"01 Distributed payload","02 Front payload","03 Front right payload","04 Front left payload"};var records=new JArray();
   for(int k=0;k<4;k++) {
    var loads=new JArray(Load(patches[k],payload*Gravity,h));if(shelf>0)loads.Add(Load(c.Top,shelf*Gravity,h));
    loads.Add(new JObject{{"kind","gravity"},{"acceleration",new JArray(0,0,-Gravity)}});
    c.Cases.Add(new JObject{{"name",names[k]},{"weight",1},{"loads",loads}});
    var center=new Point3d(patches[k].Average(f=>f.center.X),patches[k].Average(f=>f.center.Y),patches[k].Average(f=>f.center.Z));
    var moment=Vector3d.CrossProduct(center-new Point3d(o[0],o[1],o[2]),new Vector3d(0,0,-payload*Gravity));
    records.Add(JObject.FromObject(new {name=names[k],payload_force_n=payload*Gravity,area_mm2=patches[k].Count*h*h,payload_centroid_mm=new[]{center.X,center.Y,center.Z},payload_moment_about_wall_origin_nmm=new[]{moment.X,moment.Y,moment.Z}}));
   }
   if(c.Right.Count==c.Front.Count||c.Left.Count==c.Front.Count||c.Right.Average(f=>f.center.Y)<=c.Left.Average(f=>f.center.Y))throw new ArgumentException("Grid cannot resolve separate lateral patches; reduce cell size");
   c.Summary=JObject.FromObject(new {schema="topoptlab-shelf-load-summary-v1",front_depth_mm=frontDepth,lateral_offset_fraction=sideOffset,case_names=names,support_model="rigid_wall_pads",support_pad_height_mm=padHeight,payload_kg=payload,shelf_kg_per_bracket=shelf,gravity_m_s2=Gravity,origin_mm=o,wall_pad_faces=c.Wall.Count,top_faces=c.Top.Count,hole_cells=(double)spec["hole_diameter_mm"]/h,cases=records});
   return c;
  }
 }
 public sealed class BracketConditions3DComponent:Component {
  public BracketConditions3DComponent():base("TopOpt Bracket Conditions 3D","Bracket Cases 3D","Four independent cases, each with payload, distributed shelf mass and self-weight. Total force is invariant under geometry/grid changes. Rigid wall pads are an idealization.","7 Conditions 3D"){}
  protected override System.Drawing.Bitmap Icon {get{return ComponentIcons.For("SurfaceLoad3DComponent");}}
  public override Guid ComponentGuid {get{return new Guid("5e1120a1-4a97-4d7b-9294-992198314002");}}
  protected override void RegisterInputParams(GH_InputParamManager p) {
   p.AddTextParameter("Domain","D","Matching Domain 3D",GH_ParamAccess.item);p.AddTextParameter("Specification","Spec","Shelf Bracket 3D specification",GH_ParamAccess.item);p.AddTextParameter("Material","M","mm / N material",GH_ParamAccess.item);
   p.AddNumberParameter("Payload per bracket kg","Payload kg","Useful mass on EACH bracket",GH_ParamAccess.item,4);
   p.AddNumberParameter("Shelf share kg","Shelf kg","Distributed shelf mass carried by this bracket; initial value is an assumption",GH_ParamAccess.item,.5);
   p.AddNumberParameter("Front patch depth mm","Front depth","Strip measured back from front edge; actual centroid is reported",GH_ParamAccess.item,20);
   p.AddNumberParameter("Side offset fraction","Offset","Fraction of half width for nominal centroid; actual grid centroid is reported",GH_ParamAccess.item,.6);
  }
  protected override void RegisterOutputParams(GH_OutputParamManager p) {
   p.AddTextParameter("Wall restraints","S","Rigid pads around two wall holes; not bolt/contact elements",GH_ParamAccess.item);
   foreach(string n in new[]{"Distributed","Front","Right","Left"})p.AddTextParameter(n,n,"Independent case including shelf mass and self-weight",GH_ParamAccess.item);
   p.AddTextParameter("Info","Info","Actual force, centroid, moment and limitations",GH_ParamAccess.item);
   p.AddCurveParameter("Top interface","Top","Distributed loading facets",GH_ParamAccess.list);p.AddCurveParameter("Wall pads","Wall","Constrained complete voxel faces",GH_ParamAccess.list);
   p.AddTextParameter("Summary","Data","Machine-readable load checks",GH_ParamAccess.item);
  }
  protected override void SolveInstance(IGH_DataAccess da) {
   string d=null,s=null,m=null;double payload=4,shelf=.5,depth=20,offset=.6;
   if(!da.GetData(0,ref d)||!da.GetData(1,ref s)||!da.GetData(2,ref m)||!da.GetData(3,ref payload)||!da.GetData(4,ref shelf)||!da.GetData(5,ref depth)||!da.GetData(6,ref offset))return;
   try {
    var c=ShelfBracketConditions.Create(d,JObject.Parse(s),JObject.Parse(m),payload,shelf,depth,offset);
    da.SetData(0,c.Support.ToString());for(int k=0;k<4;k++)da.SetData(k+1,c.Cases[k].ToString());
    string info="FOUR ALTERNATIVE CASES / mm, N\nEach: payload + distributed shelf share + bracket self-weight.\nWall pads are rigid: no anchor pull-out, preload, wall contact or creep.\n";
    foreach(var r in c.Summary["cases"])info+=string.Format(CultureInfo.InvariantCulture,"{0}: F={1:F3} N; centre={2}; moment={3} N mm (payload only)\n",r["name"],(double)r["payload_force_n"],r["payload_centroid_mm"].ToString(Newtonsoft.Json.Formatting.None),r["payload_moment_about_wall_origin_nmm"].ToString(Newtonsoft.Json.Formatting.None));
    info+="Nominal hole diameter / h = "+((double)c.Summary["hole_cells"]).ToString("F2",CultureInfo.InvariantCulture)+". Voxel holes are not CAD fits. Replace assumed shelf share with measured mass.";
    da.SetData(5,info);da.SetDataList(6,c.Top.Select(f=>f.Outline()));da.SetDataList(7,c.Wall.Select(f=>f.Outline()));da.SetData(8,c.Summary.ToString());Message="4 cases | "+payload.ToString("G3",CultureInfo.InvariantCulture)+" kg each";
   }catch(Exception e){Error(e);}
  }
 }
}
