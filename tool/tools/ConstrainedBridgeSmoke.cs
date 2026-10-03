// SPDX-License-Identifier: GPL-3.0-or-later
using System;using System.IO;using System.Reflection;using System.Runtime.CompilerServices;using System.Threading;using Newtonsoft.Json.Linq;using TopoptLab.GH;
class ConstrainedBridgeSmoke {
 static int Main(string[] args){string[] paths={args[0],args[1],args[2]};AppDomain.CurrentDomain.AssemblyResolve+=delegate(object sender,ResolveEventArgs e){foreach(string p in paths)foreach(string ext in new[]{".dll",".gha"}){string f=Path.Combine(p,new AssemblyName(e.Name).Name+ext);if(File.Exists(f))return Assembly.LoadFrom(f);}return null;};try{Test(args[3],args[4],args[2]);return 0;}catch(Exception e){Console.Error.WriteLine(e);return 1;}}
 [MethodImpl(MethodImplOptions.NoInlining)]static void Test(string fixture,string config,string assemblyFolder){
  string loaded=typeof(WorkerJob).Assembly.Location;
  if(!string.Equals(Path.GetFullPath(loaded),Path.GetFullPath(Path.Combine(assemblyFolder,"TopoptLab.GH.gha")),StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong assembly loaded: "+loaded);
  var request=JObject.Parse(File.ReadAllText(fixture));var job=WorkerJob.Start(request,WorkerJob.Hash(request.ToString()),config);var deadline=DateTime.UtcNow.AddSeconds(60);
  while(job.Running&&DateTime.UtcNow<deadline)Thread.Sleep(50);if(job.Running){job.Cancel();throw new Exception("Timeout");}
  var result=job.Snapshot();if(result==null||(string)result["status"]!="completed")throw new Exception("Constrained worker failed: "+job.Folder+" "+result);
  if(!File.Exists(Path.Combine(job.Folder,"report.html")))throw new Exception("Missing report");
  if((string)result["engineering"]["constraint_optimizer"]["method"]!="MMA")throw new Exception("Constraints were not enforced");
  var selected=CaseResults.Select(result,2);if((string)selected["load_case"]["name"]!="Side")throw new Exception("Lost second case");
  if((string)result["engineering"]["cases"][0]["performance"]["backend"]!=(string)request["settings"]["backend"])throw new Exception("Unexpected backend fallback");
  Console.WriteLine(request["dimension"]+"D MMA C#/external Python bridge and saved-case selection passed. Assembly: "+loaded+" | Job: "+job.Folder);
 }
}
