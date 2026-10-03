// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Linq;
using System.Globalization;
using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using Grasshopper.Kernel;
namespace TopoptLab.GH {
 public sealed class DesignLimitsComponent:Component {
  public DesignLimitsComponent():base("TopOpt Design Limits","Design Limits","Displacement and stress limits for all independent load cases. FEM checks full material; optimization uses explicitly labelled relaxed stress constraints.","0 Engineering"){}
  public override Guid ComponentGuid{get{return new Guid("42fe95a1-7700-4900-a000-000000000008");}}
  protected override void RegisterInputParams(GH_InputParamManager p){
   p.AddNumberParameter("Maximum displacement","U max","Model length units (Material mm or m). 0 disables",GH_ParamAccess.item,0);
   p.AddNumberParameter("Maximum stress MPa","Stress MPa","Explicit von Mises limit in MPa, independent of model units. 0 disables",GH_ParamAccess.item,0);
   p.AddBooleanParameter("Use material allowable","Material limit","Use Material allowable instead of explicit stress. Requires available material/stock data",GH_ParamAccess.item,false);
   p.AddBooleanParameter("Enforce in optimization","Enforce","True uses MMA and adjoint constraints; False reports checks only",GH_ParamAccess.item,true);
   p.AddNumberParameter("Constraint tolerance","Tolerance","Normalized numerical tolerance; .001 = 0.1%. Exceedance within this band is labelled explicitly",GH_ParamAccess.item,.001);
  }
  protected override void RegisterOutputParams(GH_OutputParamManager p){p.AddTextParameter("Limits","Limits","Connect to Engineering Limits",GH_ParamAccess.item);p.AddTextParameter("Info","Info","Scope and stress convention",GH_ParamAccess.item);}
  protected override void SolveInstance(IGH_DataAccess da){double u=0,s=0,t=.001;bool material=false,enforce=true;if(!da.GetData(0,ref u)||!da.GetData(1,ref s)||!da.GetData(2,ref material)||!da.GetData(3,ref enforce)||!da.GetData(4,ref t))return;try{if(!CadGeometry.Finite(u)||u<0||!CadGeometry.Finite(s)||s<0||!CadGeometry.Finite(t)||t<1e-8||t>.01||material&&s>0)throw new ArgumentException("Use nonnegative limits, tolerance 1e-8..0.01, and either explicit stress OR material allowable");da.SetData(0,JObject.FromObject(new{max_displacement=u,max_stress_mpa=s,use_material_allowable=material,enforce=enforce,tolerance=t,aggregation=50}).ToString());da.SetData(1,"Limits apply to every case independently. U uses model length units; stress input is MPa. During optimization, stress is sqrt(density) times solid-material stress, a relaxed surrogate. Reanalyse the final shape. 0 disables an explicit limit. No structural-code certification.");Message=(u>0||s>0||material)?(enforce?"Enforced / design surrogate":"Check only"):"No limits";}catch(Exception e){Error(e);}}
 }
 public static class CaseResults {
  public static JObject Select(JObject parent,int index){
   if(index<1)throw new ArgumentException("Case index starts at 1");
   var engineering=parent["engineering"] as JObject;var cases=engineering==null?null:engineering["cases"] as JArray;
   if((string)parent["status"]!="completed"){
    if(index!=1)throw new ArgumentException("Other cases become available when the run completes");return parent;
   }
   var files=engineering==null?null:engineering["case_files"] as JArray;
   if(files==null){if(index==1)return parent;throw new ArgumentException("Recompute with version 0.3 to select other cases");}
   if(cases==null||index>cases.Count||files.Count!=cases.Count)throw new ArgumentException("Case index is outside the available cases");
   string file=(string)files[index-1];if(file!=string.Format(CultureInfo.InvariantCulture,"case-{0:00}.json",index))throw new ArgumentException("Invalid case manifest");
   string report=(string)engineering["report_file"];if(string.IsNullOrWhiteSpace(report))throw new ArgumentException("Missing job location; recompute the result");
   string path=Path.Combine(Path.GetDirectoryName(Path.GetFullPath(report)),file);
   if(!File.Exists(path))throw new ArgumentException("Case file is missing or the job folder moved. Recompute the result");
   var selected=JObject.Parse(File.ReadAllText(path));
   if((string)selected["job_id"]!=(string)parent["job_id"]||(string)selected["status"]!="completed"||(string)selected["engineering"]["input_signature"]!=(string)engineering["input_signature"]||(string)selected["load_case"]["name"]!=(string)cases[index-1]["name"])throw new ArgumentException("Case file does not match this job");
   return selected;
  }
 }
 public sealed class CaseResultComponent:Component {
  public CaseResultComponent():base("TopOpt Case Result","Case Result","Select a completed load-case response without rerunning the solver. Uses the saved job folder; keep it in place.","0 Engineering"){}
  public override Guid ComponentGuid{get{return new Guid("42fe95a1-7700-4900-a000-000000000009");}}
  protected override void RegisterInputParams(GH_InputParamManager p){p.AddTextParameter("Engineering result","R","Any Engineering stage",GH_ParamAccess.item);p.AddIntegerParameter("Case index","Case","1-based case index",GH_ParamAccess.item,1);}
  protected override void RegisterOutputParams(GH_OutputParamManager p){p.AddTextParameter("Case result","R","Connect to the matching Results component",GH_ParamAccess.item);p.AddTextParameter("Info","Info","Case list and selected case",GH_ParamAccess.item);}
  protected override void SolveInstance(IGH_DataAccess da){string json=null;int index=1;if(!da.GetData(0,ref json)||!da.GetData(1,ref index))return;try{var root=JObject.Parse(json);var selected=CaseResults.Select(root,index);var e=root["engineering"] as JObject;var cases=e==null?null:e["cases"] as JArray;da.SetData(0,selected.ToString(Newtonsoft.Json.Formatting.None));da.SetData(1,(cases==null?"First preview case; other cases available after completion.":string.Join("\n",cases.Select((c,i)=>(i+1)+": "+(string)c["name"])))+EngineeringInfo.Summary(selected));Message="Case "+index;}catch(Exception ex){Error(ex);}}
 }
 public static class ResultComparison {
  public static JObject Compare(JObject baseline,JObject candidate){
   if((string)baseline["status"]!="completed"||(string)candidate["status"]!="completed")throw new ArgumentException("Comparison requires two completed results");
   var a=baseline["engineering"] as JObject;var b=candidate["engineering"] as JObject;
   if(a==null||b==null||(string)a["mode"]!="fem")throw new ArgumentException("Baseline must be a full-solid Engineering FEM result");
   string signature=(string)a["input_signature"];
   if(string.IsNullOrWhiteSpace(signature)||signature!=(string)b["input_signature"])throw new ArgumentException("Geometry, supports, loads, material or units differ. Recompute a matching baseline");
   bool relaxed=(string)b["mode"]=="optimize";var rows=new JArray();
   foreach(var ca in (JArray)a["cases"]){string name=(string)ca["name"];var cb=((JArray)b["cases"]).Single(c=>(string)c["name"]==name);double u0=(double)ca["max_displacement"],u1=(double)cb["max_displacement"];
    var row=new JObject{{"case",name},{"baseline_displacement",u0},{"candidate_displacement",u1},{"displacement_ratio",u0>0?new JValue(u1/u0):JValue.CreateNull()},{"baseline_compliance",ca["compliance"]},{"candidate_compliance",cb["compliance"]}};
    if(!relaxed&&ca["max_von_mises"]!=null&&cb["max_von_mises"]!=null){double s0=(double)ca["max_von_mises"],s1=(double)cb["max_von_mises"];row["baseline_stress"]=s0;row["candidate_stress"]=s1;row["stress_ratio"]=s0>0?new JValue(s1/s0):JValue.CreateNull();}
    rows.Add(row);
   }
   double mass0=(double)a["mass_kg"],mass1=(double)b["mass_kg"];
   return new JObject{{"units",new JObject{{"length",a["material"]["length_unit"]},{"stress",(string)a["material"]["force_unit"]+"/"+(string)a["material"]["length_unit"]+"^2"}}},{"baseline_mass_kg",mass0},{"candidate_mass_kg",mass1},{"mass_saving_percent",100*(1-mass1/mass0)},{"candidate_mode",b["mode"]},{"cases",rows},{"limits",b["design_limits"]},{"stress_comparison",relaxed?"Unavailable: relaxed design stress is not comparable to full-solid stress":"Full-material FEM on the respective meshes; check mesh-study status"}};
  }
  public static string Summary(JObject comparison){
   string text=string.Format(CultureInfo.InvariantCulture,"MASS: {0:G6} -> {1:G6} kg | reduction {2:F2}%\n",(double)comparison["baseline_mass_kg"],(double)comparison["candidate_mass_kg"],(double)comparison["mass_saving_percent"]);
   foreach(var c in (JArray)comparison["cases"]){text+=(string)c["case"]+": U ("+comparison["units"]["length"]+") "+c["baseline_displacement"]+" -> "+c["candidate_displacement"]+" (ratio "+c["displacement_ratio"]+")";if(c["candidate_stress"]!=null)text+="; VM ("+comparison["units"]["stress"]+") "+c["baseline_stress"]+" -> "+c["candidate_stress"];text+="\n";}
   text+=(string)comparison["stress_comparison"];
   var limits=comparison["limits"] as JObject;if(limits!=null)text+="\nLimits: "+limits["status"]+" | "+limits["scope"];
   return text;
  }
 }
 public sealed class CompareResultsComponent:Component {
  public CompareResultsComponent():base("TopOpt Compare Results","Compare","Compare every load case and mass against a matching full-solid baseline. Relaxed optimization stress is not compared with final-shape stress.","0 Engineering"){}
  public override Guid ComponentGuid{get{return new Guid("42fe95a1-7700-4900-a000-000000000010");}}
  protected override void RegisterInputParams(GH_InputParamManager p){p.AddTextParameter("Baseline FEM","Baseline","Completed full-solid Engineering FEM",GH_ParamAccess.item);p.AddTextParameter("Candidate","Candidate","Completed optimization or final verification",GH_ParamAccess.item);}
  protected override void RegisterOutputParams(GH_OutputParamManager p){p.AddTextParameter("Summary","Info","Mass, displacement, stress and checks",GH_ParamAccess.item);p.AddTextParameter("Comparison","Data","Structured comparison JSON",GH_ParamAccess.item);p.AddNumberParameter("Mass saving percent","Saving","Positive means lighter than baseline",GH_ParamAccess.item);}
  protected override void SolveInstance(IGH_DataAccess da){string a=null,b=null;if(!da.GetData(0,ref a)||!da.GetData(1,ref b))return;try{var comparison=ResultComparison.Compare(JObject.Parse(a),JObject.Parse(b));da.SetData(0,ResultComparison.Summary(comparison));da.SetData(1,comparison.ToString());da.SetData(2,(double)comparison["mass_saving_percent"]);Message="All cases";}catch(Exception ex){Error(ex);}}
 }
 public sealed class ReviewControlsComponent:Component {
  public ReviewControlsComponent():base("TopOpt Review Controls","Review","Show one stage at a time. Route Case and Field to the case selectors and result viewers.","0 Engineering"){}
  public override Guid ComponentGuid{get{return new Guid("42fe95a1-7700-4900-a000-000000000011");}}
  protected override void RegisterInputParams(GH_InputParamManager p){p.AddIntegerParameter("Visible stage","Stage","0 baseline FEM; 1 optimization; 2 voxel verification; 3 extracted geometry; 4 final TET4 FEM",GH_ParamAccess.item,0);p.AddIntegerParameter("Case index","Case","1-based",GH_ParamAccess.item,1);p.AddIntegerParameter("Field","Field","0 default (FEM stress / design density); 1 displacement; 2 stress (relaxed during design)",GH_ParamAccess.item,0);}
  protected override void RegisterOutputParams(GH_OutputParamManager p){p.AddBooleanParameter("Show baseline","Baseline","Connect to Results Preview input",GH_ParamAccess.item);p.AddBooleanParameter("Show optimization","Optimize","Connect to Results Preview input",GH_ParamAccess.item);p.AddBooleanParameter("Show verification","Verify","Connect to Results Preview input",GH_ParamAccess.item);p.AddIntegerParameter("Case index","Case","Connect to Case Result",GH_ParamAccess.item);p.AddIntegerParameter("Field","Field","Connect to Results Field",GH_ParamAccess.item);p.AddBooleanParameter("Show surface","Surface","Connect to Final Geometry Results Preview",GH_ParamAccess.item);p.AddBooleanParameter("Show final FEM","Final FEM","Connect to Final FEM Results Preview",GH_ParamAccess.item);}
  protected override void SolveInstance(IGH_DataAccess da){int stage=0,c=1,f=0;if(!da.GetData(0,ref stage)||!da.GetData(1,ref c)||!da.GetData(2,ref f))return;try{if(stage<0||stage>4||c<1||c>16||f<0||f>2)throw new ArgumentException("Stage 0..4, Case 1..16, Field 0..2");for(int k=0;k<3;k++)da.SetData(k,stage==k);da.SetData(3,c);da.SetData(4,f);da.SetData(5,stage==3);da.SetData(6,stage==4);Message=new[]{"Baseline FEM","Optimization","Voxel verification","Extracted geometry","Final TET4 FEM"}[stage];}catch(Exception e){Error(e);}}
 }
}
