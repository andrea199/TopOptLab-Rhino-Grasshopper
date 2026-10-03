// SPDX-License-Identifier: GPL-3.0-or-later
using System;using System.IO;using System.Reflection;using System.Runtime.CompilerServices;using System.Drawing;using Newtonsoft.Json.Linq;using TopoptLab.GH;
class ReviewSmoke {
 static int Main(string[] args){string[] paths={args[0],args[1],args[2]};AppDomain.CurrentDomain.AssemblyResolve+=delegate(object sender,ResolveEventArgs e){foreach(string p in paths)foreach(string ext in new[]{".dll",".gha"}){string f=Path.Combine(p,new AssemblyName(e.Name).Name+ext);if(File.Exists(f))return Assembly.LoadFrom(f);}return null;};try{Test(args[3]);return 0;}catch(Exception e){Console.Error.WriteLine(e);return 1;}}
 static void Reject(Action action){bool rejected=false;try{action();}catch(ArgumentException){rejected=true;}if(!rejected)throw new Exception("Invalid comparison/selection was accepted");}
 [MethodImpl(MethodImplOptions.NoInlining)]static void Test(string folder){
  var baseline=JObject.Parse(File.ReadAllText(Path.Combine(folder,"baseline/result.json")));
  var design=JObject.Parse(File.ReadAllText(Path.Combine(folder,"optimization/result.json")));
  var final=JObject.Parse(File.ReadAllText(Path.Combine(folder,"verification/result.json")));
  foreach(var result in new[]{baseline,design,final}){
   var first=CaseResults.Select(result,1);var second=CaseResults.Select(result,2);
   if((string)second["engineering"]["display_case"]!="Case 2"||(string)first["load_case"]["name"]!="Case 1")throw new Exception("Case selection mismatch");
   if((double)second["metrics"]["compliance"]!=(double)result["engineering"]["cases"][1]["compliance"])throw new Exception("Selected compliance mismatch");
   Reject(()=>CaseResults.Select(result,0));Reject(()=>CaseResults.Select(result,3));
   var altered=(JObject)result.DeepClone();altered["job_id"]="different-job";Reject(()=>CaseResults.Select(altered,1));
   altered=(JObject)result.DeepClone();altered["engineering"]["case_files"][0]="../case-01.json";Reject(()=>CaseResults.Select(altered,1));
  }
  var comparison=ResultComparison.Compare(baseline,design);
  if(comparison["cases"][0]["candidate_stress"]!=null)throw new Exception("Relaxed stress compared as physical stress");
  var verified=ResultComparison.Compare(baseline,final);
  if(verified["cases"][1]["candidate_stress"]==null)throw new Exception("Final stress comparison missing");
  var changed=(JObject)final.DeepClone();changed["engineering"]["input_signature"]="different";Reject(()=>ResultComparison.Compare(baseline,changed));
  var legend=ResultLegend.Create(final,"Von Mises","stress",10,5,20,x=>Color.Blue);
  if(legend.Title!="FINAL VERIFICATION"||legend.Units!="N/mm^2")throw new Exception("Legend mode or units incorrect");
  legend=ResultLegend.Create(baseline,"Von Mises","stress",10,5,0,x=>Color.Blue);
  if(legend.Title!="BASELINE FEM")throw new Exception("Baseline legend incorrect");
  Console.WriteLine("Case selection, comparison rejection guards and legend metadata passed: "+folder);
 }
}
