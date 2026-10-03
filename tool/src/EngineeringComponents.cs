// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using Grasshopper.Kernel;
namespace TopoptLab.GH {
 public sealed class MaterialComponent:Component {
  public MaterialComponent():base("TopOpt Material","Material","Sourced elastic reference presets with explicit units. Read Info for provenance and limitations.","0 Engineering"){}
  public override Guid ComponentGuid{get{return new Guid("42fe95a1-7700-4900-a000-000000000001");}}
  protected override void RegisterInputParams(GH_InputParamManager p){
   p.AddIntegerParameter("Preset","Preset","0: structural steel; 1: injection-molded ABS GP-22 reference",GH_ParamAccess.item,0);
   p.AddIntegerParameter("Length unit","Units","0: mm; 1: m. Must match geometry coordinates",GH_ParamAccess.item,0);
   p.AddIntegerParameter("Force unit","Force units","0: N; 1: kN",GH_ParamAccess.item,0);
   p.AddNumberParameter("Safety factor","SF","Screening only, not automatic code verification",GH_ParamAccess.item,1.5);
   p.AddNumberParameter("Stock thickness mm","Stock","S235 reference yield only enabled for declared stock thickness >0 and <=16 mm",GH_ParamAccess.item,0);
   p.AddNumberParameter("E override MPa","E override","0 uses preset",GH_ParamAccess.item,0);
   p.AddNumberParameter("Poisson override","nu override","-1 uses preset. ABS default 0.35 is an assumption",GH_ParamAccess.item,-1);
  }
  protected override void RegisterOutputParams(GH_OutputParamManager p){p.AddTextParameter("Material","M","Connect to Engineering",GH_ParamAccess.item);p.AddNumberParameter("Young modulus","E","Force/length squared in selected units",GH_ParamAccess.item);p.AddNumberParameter("Poisson ratio","nu","Elastic Poisson ratio",GH_ParamAccess.item);p.AddTextParameter("Provenance","Info","Sources and limitations",GH_ParamAccess.item);}
  protected override void SolveInstance(IGH_DataAccess da){
   int preset=0,lu=0,fu=0;double sf=1.5,stock=0,e=0,nu=-1;
   if(!da.GetData(0,ref preset)||!da.GetData(1,ref lu)||!da.GetData(2,ref fu)||!da.GetData(3,ref sf)||!da.GetData(4,ref stock)||!da.GetData(5,ref e)||!da.GetData(6,ref nu))return;
   try{
    if(preset<0||preset>1||lu<0||lu>1||fu<0||fu>1||!CadGeometry.Finite(sf)||sf<1||!CadGeometry.Finite(stock)||stock<0||!CadGeometry.Finite(e)||e<0||!CadGeometry.Finite(nu)||(nu!=-1&&(nu<0||nu>.49)))throw new ArgumentException("Invalid material/units settings");
    string id=preset==0?"steel":"abs";JObject record;
    using(var stream=Assembly.GetExecutingAssembly().GetManifestResourceStream("TopoptLab.Materials"))using(var reader=new StreamReader(stream))record=(JObject)JObject.Parse(reader.ReadToEnd())["materials"][id];
    var spec=new JObject{{"preset",id},{"length_unit",lu==0?"mm":"m"},{"force_unit",fu==0?"N":"kN"},{"safety_factor",sf},{"stock_thickness_mm",stock}};
    if(e>0)spec["young_pa"]=e*1e6;if(nu>=0)spec["poisson"]=nu;
    double length=lu==0?.001:1,force=fu==0?1:1000;
    da.SetData(0,spec.ToString());da.SetData(1,(e>0?e*1e6:(double)record["young_pa"])*length*length/force);da.SetData(2,nu>=0?nu:(double)record["poisson"]);
    da.SetData(3,record.ToString()+"\nSelected units: "+spec["length_unit"]+", "+spec["force_unit"]+"\nYield comparison is screening only. No fatigue, creep, buckling or code verification.");Message=(string)record["name"];
   }catch(Exception ex){Error(ex);}
  }
 }
 public sealed class LoadCaseComponent:Component {
  public LoadCaseComponent():base("TopOpt Load Case","Load Case","Forces inside one case act simultaneously. Different cases are solved independently with a weighted compliance objective.","0 Engineering"){}
  public override Guid ComponentGuid{get{return new Guid("42fe95a1-7700-4900-a000-000000000002");}}
  protected override void RegisterInputParams(GH_InputParamManager p){p.AddTextParameter("Loads","L","Point loads, Surface Load or Gravity outputs",GH_ParamAccess.list);p.AddTextParameter("Name","Name","Unique case name",GH_ParamAccess.item,"Case 1");p.AddNumberParameter("Weight","W","Positive objective weight",GH_ParamAccess.item,1);}
  protected override void RegisterOutputParams(GH_OutputParamManager p){p.AddTextParameter("Load case","Case","Engineering load case",GH_ParamAccess.item);}
  protected override void SolveInstance(IGH_DataAccess da){var loads=new List<string>();string name=null;double w=1;if(!da.GetDataList(0,loads)||!da.GetData(1,ref name)||!da.GetData(2,ref w))return;try{if(loads.Count==0||loads.Any(string.IsNullOrWhiteSpace)||string.IsNullOrWhiteSpace(name)||!CadGeometry.Finite(w)||w<=0)throw new ArgumentException("Connect valid loads and a unique nonempty case name; weight must be positive");da.SetData(0,new JObject{{"name",name},{"weight",w},{"loads",new JArray(loads.Select(JObject.Parse))}}.ToString());Message=name;}catch(Exception e){Error(e);}}
 }
 public sealed class EngineeringSettingsComponent:Component {
  public EngineeringSettingsComponent():base("TopOpt Engineering Settings","Settings","Solver, convergence and manufacturing controls. Minimum feature is diagnostic only; symmetry/extrusion are enforced.","0 Engineering"){}
  public override Guid ComponentGuid{get{return new Guid("42fe95a1-7700-4900-a000-000000000003");}}
  protected override void RegisterInputParams(GH_InputParamManager p){
   p.AddIntegerParameter("Backend","Backend","0 CPU direct; 1 CPU CG; 2 CPU AMG; 3 CPU matrix-free; 4 CUDA CG",GH_ParamAccess.item,0);
   p.AddIntegerParameter("CPU threads","Threads","BLAS thread limit; not a guarantee all solver stages run in parallel",GH_ParamAccess.item,4);
   p.AddNumberParameter("Volume fraction","Volume","Includes Keep material",GH_ParamAccess.item,.4);
   p.AddIntegerParameter("Iteration limit","Iterations","Maximum optimization iterations",GH_ParamAccess.item,80);
   p.AddNumberParameter("Filter radius","Radius","In cells",GH_ParamAccess.item,1.8);
   p.AddNumberParameter("2D thickness","Thickness","In selected model length units",GH_ParamAccess.item,2);
   p.AddNumberParameter("Objective tolerance","C tolerance","Relative objective change",GH_ParamAccess.item,.001);
   p.AddNumberParameter("Design tolerance","D tolerance","Maximum density change",GH_ParamAccess.item,.01);
   p.AddIntegerParameter("Convergence window","Window","Consecutive stable iterations",GH_ParamAccess.item,5);
   p.AddIntegerParameter("Minimum iterations","Minimum","Before testing convergence",GH_ParamAccess.item,10);
   p.AddNumberParameter("Threshold","Threshold","Final-shape verification threshold",GH_ParamAccess.item,.5);
   p.AddIntegerParameter("Manufacturing process","Process","0 unspecified; 1 machining; 2 injection molding; 3 additive. Process checks are advisory",GH_ParamAccess.item,0);
   p.AddIntegerParameter("Symmetry axis","Symmetry","0 none; 1 X; 2 Y; 3 Z. Domain and Keep must be symmetric",GH_ParamAccess.item,0);
   p.AddIntegerParameter("Extrusion axis","Extrusion","3D only; 0 none; 1 X; 2 Y; 3 Z",GH_ParamAccess.item,0);
   p.AddNumberParameter("Minimum feature","Feature","Requested length; voxel erosion diagnostic, not an enforced thickness constraint",GH_ParamAccess.item,0);
   p.AddBooleanParameter("Keep attachments","Keep attachments","Preserve active cells touching support and point-load nodes. Surface-load cells are always preserved",GH_ParamAccess.item,true);
   p.AddNumberParameter("RAM budget GiB","RAM","3D only: 0 uses 60% of currently free RAM. Positive value is a lower budget. Leave 0 for 2D.",GH_ParamAccess.item,0);
   p.AddNumberParameter("Physical filter radius","Radius length","Model length units; 0 uses Radius in cells. Keep this length fixed when comparing grid refinements.",GH_ParamAccess.item,0);
  }
  protected override void RegisterOutputParams(GH_OutputParamManager p){p.AddTextParameter("Settings","O","Connect to Engineering",GH_ParamAccess.item);}
  protected override void SolveInstance(IGH_DataAccess da){
   int backend=0,threads=4,it=80,window=5,min=10,process=0,sym=0,ext=0;double volume=.4,radius=1.8,t=2,ct=.001,dt=.01,threshold=.5,feature=0;
   if(!da.GetData(0,ref backend)||!da.GetData(1,ref threads)||!da.GetData(2,ref volume)||!da.GetData(3,ref it)||!da.GetData(4,ref radius)||!da.GetData(5,ref t)||!da.GetData(6,ref ct)||!da.GetData(7,ref dt)||!da.GetData(8,ref window)||!da.GetData(9,ref min)||!da.GetData(10,ref threshold)||!da.GetData(11,ref process)||!da.GetData(12,ref sym)||!da.GetData(13,ref ext)||!da.GetData(14,ref feature))return;
   try{if(backend<0||backend>4||process<0||process>3||sym<0||sym>3||ext<0||ext>3)throw new ArgumentException("Invalid backend or manufacturing selection");
    bool attachments=true;da.GetData(15,ref attachments);double ram=0,radiusLength=0;da.GetData(16,ref ram);da.GetData(17,ref radiusLength);
    if(!CadGeometry.Finite(ram)||ram<0||!CadGeometry.Finite(radiusLength)||radiusLength<0)throw new ArgumentException("RAM budget and physical filter radius must be finite and nonnegative");
    var settings=JObject.FromObject(new{memory_budget_gib=ram,radius_length=radiusLength,preserve_attachments=attachments,backend=new[]{"cpu-direct","cpu-cg","cpu-amg","cpu-matrixfree","cuda-cg"}[backend],threads=threads,volume=volume,iterations=it,radius=radius,thickness=t,objective_tolerance=ct,design_tolerance=dt,convergence_window=window,minimum_iterations=min,linear_tolerance=1e-9,linear_iterations=5000});
    var manufacturing=JObject.FromObject(new{process=new[]{"unspecified","machining","injection_molding","additive"}[process],symmetry=new[]{"none","x","y","z"}[sym],extrusion=new[]{"none","x","y","z"}[ext],threshold=threshold,minimum_feature=feature});
    da.SetData(0,new JObject{{"settings",settings},{"manufacturing",manufacturing}}.ToString());Message=(string)settings["backend"];
   }catch(Exception e){Error(e);}
  }
 }
 public static class EngineeringInfo {
  public static string Summary(JObject data){
   var e=data["engineering"] as JObject;if(e==null)return "";
   string text="\nENGINEERING: "+(string)e["mode"]+" | "+(string)e["termination_reason"]+"\nPreview case: "+(string)e["display_case"];
   if(e["weighted_compliance"]!=null)text+="\nWeighted objective (all cases): "+e["weighted_compliance"]+". Case Result displays the selected case response.";
   var m=e["material"] as JObject;
   if(m!=null)text+="\nDeclared units: "+(string)m["length_unit"]+", "+(string)m["force_unit"]+". Stress: force / length squared.\nMass: "+e["mass_kg"]+" kg.";
   var limits=e["design_limits"] as JObject;if(limits!=null)text+="\nLimits: "+limits["status"]+" | "+limits["scope"];
   var resources=e["resources"] as JObject;if(resources!=null)text+="\nGrid: "+resources["bounding_cells"]+" bounding cells; estimated RAM: "+((double)resources["estimated_host_bytes"]/1073741824d).ToString("F2")+" GiB; filter radius: "+resources["filter_radius_length"]+" model units.";
   if((string)e["mode"]=="optimize")text+="\nRelaxed stress is a design surrogate; verify the thresholded final shape.";
   return text;
  }
 }

}
