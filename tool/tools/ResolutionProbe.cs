// SPDX-License-Identifier: GPL-3.0-or-later
using System;using System.IO;using System.Linq;using System.Reflection;using System.Runtime.CompilerServices;using System.Collections.Generic;
using Grasshopper.Kernel;using Grasshopper.Kernel.Special;using Grasshopper.Kernel.Types;using Newtonsoft.Json;using Newtonsoft.Json.Linq;using Rhino.Geometry;using TopoptLab.GH;
class ResolutionProbe {
 [STAThread]static int Main(string[] args) {
  string[] paths={args[0],args[1],args[2]};
  AppDomain.CurrentDomain.AssemblyResolve+=delegate(object sender,ResolveEventArgs e){foreach(string p in paths)foreach(string ext in new[]{".dll",".gha"}){string f=Path.Combine(p,new AssemblyName(e.Name).Name+ext);if(File.Exists(f))return Assembly.LoadFrom(f);}return null;};
  try{Test(args[3]);return 0;}catch(Exception e){Console.Error.WriteLine(e);return 1;}
 }
 static JObject Output(GH_Component c,int i){var v=c.Params.Output[i].VolatileData.AllData(true).ToList();if(v.Count!=1)throw new Exception(c.Name+" missing output "+i);return JObject.Parse(v[0].ToString());}
 static void Value(IGH_Param p,decimal value){var s=(GH_NumberSlider)p.Sources[0];s.SetSliderValue(value);s.ExpireSolution(false);}
 static void Bad(Action f,string name){try{f();}catch(ArgumentException){return;}throw new Exception("Expected rejection: "+name);}
 [MethodImpl(MethodImplOptions.NoInlining)]static void Test(string folder) {
  Directory.CreateDirectory(folder);
  using(var core=new Rhino.Runtime.InProcess.RhinoCore(new[]{"/nosplash","/notemplate"},Rhino.Runtime.InProcess.WindowStyle.NoWindow)) {
   var objects=ShelfBracketExample.Build();var doc=new GH_Document();GH_Document.EnableSolutions=true;foreach(var o in objects)doc.AddObject(o,false);doc.Enabled=true;Grasshopper.Instances.DocumentServer.AddDocument(doc);
   var geo=objects.OfType<ShelfBracket3DComponent>().Single();var domain=objects.OfType<Domain3DComponent>().Single();var cases=objects.OfType<BracketConditions3DComponent>().Single();var material=objects.OfType<MaterialComponent>().Single();var settings=objects.OfType<EngineeringSettingsComponent>().Single();var limits=objects.OfType<DesignLimitsComponent>().Single();
   for(int variant=0;variant<3;variant++) {
    Value(domain.Params.Input[3],new decimal[]{5m,2.5m,2m}[variant]);
    Value(domain.Params.Input[4],250000);Value(settings.Params.Input[0],2);
    doc.NewSolution(true);
    foreach(var c in new GH_Component[]{geo,domain,cases,material,settings,limits})if(c.RuntimeMessageLevel==GH_RuntimeMessageLevel.Error)throw new Exception(c.Name+": "+string.Join("; ",c.RuntimeMessages(GH_RuntimeMessageLevel.Error)));
    var cfg=Output(settings,0);var request=new JObject{{"schema","topoptlab-gh-request-v1"},{"engineering",true},{"dimension",3},{"mode","fem"},{"domain",Output(domain,0)},{"supports",new JArray(Output(cases,0))},{"load_cases",new JArray(Enumerable.Range(1,4).Select(i=>Output(cases,i)))},{"material",Output(material,0)},{"settings",cfg["settings"]},{"manufacturing",cfg["manufacturing"]},{"design_limits",Output(limits,0)},{"example_geometry",Output(geo,3)}};
    var summary=Output(cases,8);File.WriteAllText(Path.Combine(folder,"variant-"+variant+".json"),request.ToString(Formatting.None));File.WriteAllText(Path.Combine(folder,"summary-"+variant+".json"),summary.ToString());
    if(variant==0){
     var model=new Rhino.FileIO.File3dm();model.Settings.ModelUnitSystem=Rhino.UnitSystem.Millimeters;
     model.AllLayers.Add(new Rhino.DocObjects.Layer{Name="Nominal attachment plates",Color=System.Drawing.Color.Teal});
     model.AllLayers.Add(new Rhino.DocObjects.Layer{Name="VOID screw and tool references",Color=System.Drawing.Color.OrangeRed,IsVisible=false});
     int plateLayer=model.AllLayers.First(l=>l.Name=="Nominal attachment plates").Index,voidLayer=model.AllLayers.First(l=>l.Name=="VOID screw and tool references").Index;
     var keeps=geo.Params.Output[2].VolatileData.AllData(true).Cast<GH_Brep>().Select(b=>b.Value).ToArray();
     var voids=geo.Params.Output[1].VolatileData.AllData(true).Cast<GH_Brep>().Select(b=>b.Value).ToArray();
     var united=Brep.CreateBooleanUnion(keeps,1e-6);var plates=Brep.CreateBooleanDifference(united,voids,1e-6);
     if(plates==null||plates.Length!=1||!plates[0].IsSolid)throw new Exception("Nominal CAD interface boolean failed");
     foreach(var b in plates)model.Objects.AddBrep(b,new Rhino.DocObjects.ObjectAttributes{Name="Nominal plates with four circular holes - no optimized web",LayerIndex=plateLayer});
     foreach(var b in voids)model.Objects.AddBrep(b,new Rhino.DocObjects.ObjectAttributes{Name="Reserved screw/tool volume",LayerIndex=voidLayer});
     model.Write(Path.Combine(folder,"shelf_bracket_nominal_interfaces.3dm"),8);
     var spec=Output(geo,3);var mat=Output(material,0);string data=Output(domain,0).ToString();
     Bad(()=>ShelfBracketConditions.Create(data,spec,mat,0,.5,20,.6),"zero payload");
     Bad(()=>ShelfBracketConditions.Create(data,spec,mat,4,-.5,20,.6),"negative shelf");
     Bad(()=>ShelfBracketConditions.Create(data,spec,mat,4,.5,250,.6),"front patch");
     Bad(()=>ShelfBracketConditions.Create(data,spec,mat,4,.5,20,1),"offset");
     var tiny=(JObject)spec.DeepClone();tiny["hole_diameter_mm"]=.1;Bad(()=>ShelfBracketConditions.Create(data,tiny,mat,4,.5,20,.6),"unresolved hole");
     var wrong=(JObject)mat.DeepClone();wrong["length_unit"]="m";Bad(()=>ShelfBracketConditions.Create(data,spec,wrong,4,.5,20,.6),"units");
     var shifted=(JObject)spec.DeepClone();shifted["origin"][0]=1;Bad(()=>ShelfBracketConditions.Create(data,shifted,mat,4,.5,20,.6),"mismatched geometry");
     Bad(()=>ShelfBracketGeometry.Create(250,150,25,10,8,140,40,16,25,Point3d.Origin),"overlap");
    }
    Console.WriteLine("Fine-grid native variant "+variant+": "+((JArray)request["domain"]["active"]).Count+" cells; four independent cases; payload "+summary["payload_kg"]+" kg");
   }
   doc.Dispose();
  }
 }
}
