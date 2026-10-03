// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Reflection;
using System.Runtime.CompilerServices;
class ArchiveExample
{
    [STAThread]
    static int Main(string[] args)
    {
        string[] paths = { args[0], args[1], args[2] };
        AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs e) {
            foreach (string folder in paths) foreach (string ext in new[] { ".dll", ".gha" }) {
                string file = Path.Combine(folder, new AssemblyName(e.Name).Name + ext);
                if (File.Exists(file)) return Assembly.LoadFrom(file);
            }
            return null;
        };
        try { if(args.Length>4 && args[4]=="shelf"){Write(args[3],true,-7);return 0;} Write(args[3],true,-7); Write(args[3], true, -6); Write(args[3], false, -5); Write(args[3], true, -5); Write(args[3], false, -4); Write(args[3], true, -4); Write(args[3], false, -3); Write(args[3], true, -3); Write(args[3], false); Write(args[3], true); Write(args[3], false, -2); Write(args[3], true, -2); for(int k=0;k<4;k++){ Write(args[3], false, k); Write(args[3], true, k); } return 0; } catch (Exception e) { Console.Error.WriteLine(e); return 1; }
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static void Write(string folder, bool fem, int scenario = -1)
    {
        Directory.CreateDirectory(folder);
        if(!fem && scenario < 0) TopoptLab.GH.ComponentIcons.Export(Path.Combine(folder,"../icons"));
        var objects = scenario == -7 ? TopoptLab.GH.ShelfBracketExample.Build() : scenario == -6 ? TopoptLab.GH.FinalExample.Build() : scenario == -5 ? TopoptLab.GH.EngineeringExample.Build(fem,false,true) : scenario == -4 ? TopoptLab.GH.EngineeringExample.Build(fem,true) : scenario == -3 ? TopoptLab.GH.EngineeringExample.Build(fem) : scenario == -2 ? TopoptLab.GH.Example3DDocument.Build(fem) : scenario >= 0 ? TopoptLab.GH.ScenarioDocument.Build(scenario, fem) : fem ? TopoptLab.GH.FemExampleDocument.BuildObjects() : TopoptLab.GH.ExampleDocument.BuildObjects();
        string name = fem ? "fem_plate_with_hole" : "plate_with_hole";
        if(scenario == -7) name = "engineering_shelf_bracket_3d";
        if(scenario == -6) name = "engineering_final_geometry_3d";
        if(scenario == -5) name = fem ? "engineering_design_limits_3d" : "engineering_design_limits_2d";
        if(scenario == -4) name = fem ? "engineering_distributed_loads_3d" : "engineering_distributed_loads_2d";
        if(scenario == -3) name = fem ? "engineering_workflow_3d" : "engineering_workflow_2d";
        if(scenario == -2) name = (fem ? "fem_" : "opt_") + "cantilever_3d";
        if(scenario >= 0) name = (fem ? "fem_" : "opt_") + (string)TopoptLab.GH.Scenarios.Catalog()[scenario]["id"];
        var archive = new GH_IO.Serialization.GH_Archive();
        var definition = archive.CreateTopLevelNode("Definition");
        definition.SetVersion("plugin_version", 1, 0, 7);
        var header = definition.CreateChunk("DocumentHeader");
        header.SetGuid("DocumentID", Guid.NewGuid()); header.SetString("Preview", "Shaded"); header.SetInt32("PreviewMeshType", 1);
        // Native writer includes Date, required by GH_DocumentProperties.Read.
        var properties = new Grasshopper.Kernel.GH_DocumentProperties {
            ProjectFileName = name + ".gh",
            Description = "TopOptLab 2D/3D engineering example; Rhino 8 and external Python",
            ViewTarget = new System.Drawing.Point(100, 70), ZoomFactor = .65f
        };
        if (!properties.Write(definition)) throw new IOException("Cannot write document properties");
        definition.CreateChunk("RcpLayout").SetInt32("GroupCount", 0);
        definition.CreateChunk("GHALibraries").SetInt32("Count", 0);
        var list = definition.CreateChunk("DefinitionObjects"); list.SetInt32("ObjectCount", objects.Count);
        for (int i = 0; i < objects.Count; i++) {
            var obj = objects[i];
            obj.Attributes.PerformLayout();
            var chunk = list.CreateChunk("Object", i); chunk.SetGuid("GUID", obj.ComponentGuid); chunk.SetString("Name", obj.Name);
            if (!obj.Write(chunk.CreateChunk("Container"))) throw new Exception("Cannot serialize " + obj.Name);
        }
        foreach (string ext in new[] { ".ghx", ".gh" })
            if (!archive.WriteToFile(Path.Combine(folder, name + ext), true, false)) throw new IOException("Cannot write example");
        // Read properties and all objects in both formats (not a full Rhino UI test).
        foreach (string ext in new[] { ".ghx", ".gh" }) {
            var readback = new GH_IO.Serialization.GH_Archive();
            if (!readback.ReadFromFile(Path.Combine(folder, name + ext))) throw new IOException("Cannot reopen archive");
            var rdefinition = readback.GetRootNode.FindChunk("Definition");
            var rproperties = new Grasshopper.Kernel.GH_DocumentProperties();
            if (!rproperties.Read(rdefinition) || rproperties.ProjectFileName != properties.ProjectFileName)
                throw new IOException("Document properties readback failed: " + ext);
            var rlist = rdefinition.FindChunk("DefinitionObjects");
            for (int i = 0; i < objects.Count; i++) {
                var clone = (Grasshopper.Kernel.IGH_DocumentObject)Activator.CreateInstance(objects[i].GetType()); clone.CreateAttributes();
                if (!clone.Read(rlist.FindChunk("Object", i).FindChunk("Container"))) throw new IOException("Readback failed: " + clone.Name);
                if (clone.InstanceGuid != objects[i].InstanceGuid) throw new IOException("Object identity changed");
            }
        }
        Console.WriteLine(name + ": SDK readback verified (.gh/.ghx): document properties and " + objects.Count + " objects");
    }
}
