using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Threading;
using Newtonsoft.Json.Linq;
using Rhino.Geometry;
using TopoptLab.GH;
class DistributedLoadSmoke {
 static int Main(string[] args){string[] paths={args[0],args[1],args[2]};AppDomain.CurrentDomain.AssemblyResolve+=delegate(object sender,ResolveEventArgs e){foreach(string p in paths)foreach(string ext in new[]{".dll",".gha"}){string f=Path.Combine(p,new AssemblyName(e.Name).Name+ext);if(File.Exists(f))return Assembly.LoadFrom(f);}return null;};try{Test(args[3],args[4]);return 0;}catch(Exception e){Console.Error.WriteLine(e);return 1;}}
 [MethodImpl(MethodImplOptions.NoInlining)]static void Test(string fixture,string config){
  var request=JObject.Parse(File.ReadAllText(fixture));int dim=(int)request["dimension"];string domain=request["domain"].ToString();
  var all=DistributedLoadGeometry.Boundary(domain,dim);var faces=all.Where(f=>f.axis==0&&f.side==1).ToList();
  int nx=(int)request["domain"]["nx"],ny=(int)request["domain"]["ny"],nz=dim==3?(int)request["domain"]["nz"]:1;
  if(faces.Count!=ny*nz||all.Count!=(dim==3?2*(nx*ny+ny*nz+nx*nz):2*(nx+ny)))throw new Exception("Boundary facet enumeration mismatch");
  double h=(double)request["domain"]["cell"];
  if(faces.Any(f=>Math.Abs(f.center.X-nx*h)>1e-9||f.normal!=Vector3d.XAxis||f.corners.Length!=(dim==3?4:2)))throw new Exception("Wrong boundary geometry");
  var acceleration=DistributedLoadGeometry.InDomain(domain,dim==3?new Vector3d(0,0,-9.80665):new Vector3d(0,-9.80665,0));
  if(dim==2){bool caught=false;try{DistributedLoadGeometry.InDomain(domain,Vector3d.ZAxis);}catch(ArgumentException){caught=true;}if(!caught)throw new Exception("Out of plane gravity was accepted");}
  var surface=new JObject{{"kind","pressure"},{"pressure",.1},{"faces",new JArray(faces.Select(f=>f.Identity()))}};
  var gravity=new JObject{{"kind","gravity"},{"acceleration",new JArray(acceleration)}};
  request["load_cases"]=new JArray(new JObject{{"name","Surface + weight"},{"weight",1},{"loads",new JArray(surface,gravity)}},new JObject{{"name","Weight"},{"weight",1},{"loads",new JArray(gravity.DeepClone())}});
  var job=WorkerJob.Start(request,WorkerJob.Hash(request.ToString()),config);var deadline=DateTime.UtcNow.AddSeconds(60);
  while(job.Running&&DateTime.UtcNow<deadline)Thread.Sleep(50);if(job.Running){job.Cancel();throw new Exception("Timeout");}
  var result=job.Snapshot();if(result==null||(string)result["status"]!="completed")throw new Exception("Worker failed: "+job.Folder+" "+result);
  if(!File.Exists(Path.Combine(job.Folder,"report.html")))throw new Exception("Missing report");
  if(((JArray)result["engineering"]["cases"]).Count!=2)throw new Exception("Lost case");
  double expected=-.1*ny*nz*(dim==3?h*h:h*(double)request["settings"]["thickness"]);
  if(Math.Abs((double)result["engineering"]["cases"][0]["applied_force"][0]-expected)>1e-8)throw new Exception("Wrong integrated force");
  Console.WriteLine(dim+"D distributed-load C#/Python bridge passed: "+job.Folder);
 }
}
