// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Grasshopper.Kernel;

namespace TopoptLab.GH
{
    public sealed class EngineeringSolveComponent : Component
    {
        WorkerJob job;
        readonly List<WorkerJob> detached = new List<WorkerJob>();
        bool lastRun, lastStop, lastReset, initialized;
        public EngineeringSolveComponent():base("TopOpt Engineering","Engineering","Units, independent load cases, convergence and final-shape voxel verification. Read Report for case results and limitations.","0 Engineering"){}
        public override Guid ComponentGuid{get{return new Guid("42fe95a1-7700-4900-a000-000000000004");}}
        protected override void RegisterInputParams(GH_InputParamManager p){
            p.AddTextParameter("Domain","D","2D or 3D Domain",GH_ParamAccess.item);
            p.AddTextParameter("Supports","S","All Support outputs",GH_ParamAccess.list);
            p.AddTextParameter("Load cases","Cases","Named independent Load Case outputs",GH_ParamAccess.list);
            p.AddTextParameter("Material","M","Material component",GH_ParamAccess.item);
            p.AddTextParameter("Settings","O","Engineering Settings",GH_ParamAccess.item);
            p.AddIntegerParameter("Mode","Mode","0 FEM baseline; 1 optimization; 2 threshold verification",GH_ParamAccess.item,0);
            p.AddTextParameter("Source result","Source","Mode 2 only: completed engineering optimization with unchanged inputs",GH_ParamAccess.item);p[6].Optional=true;
            p.AddBooleanParameter("Run","Run","Start a new job",GH_ParamAccess.item,false);
            p.AddBooleanParameter("Stop","Stop","Cancel job",GH_ParamAccess.item,false);
            p.AddBooleanParameter("Reset","Reset","Detach job and clear result",GH_ParamAccess.item,false);
            p.AddTextParameter("Design limits","Limits","Optional Design Limits component; applies to every case",GH_ParamAccess.item);p[10].Optional=true;
            for(int k=0;k<5;k++)p[k].Optional=true;
        }
        protected override void RegisterOutputParams(GH_OutputParamManager p){
            p.AddTextParameter("Result","R","Use Results 3D, or 2D FEM Results / Results matching Mode. Use Case Result to select a case after completion",GH_ParamAccess.item);
            p.AddTextParameter("Status","S","Completion is distinct from convergence",GH_ParamAccess.item);
            p.AddTextParameter("Job folder","J","Project, case files, history and report.html",GH_ParamAccess.item);
            p.AddTextParameter("Report","Report","HTML report file path",GH_ParamAccess.item);
        }
        void Schedule()
        {
            GH_Document doc = OnPingDocument();
            if (doc != null) doc.ScheduleSolution(400, delegate(GH_Document d) { if (OnPingDocument() == d) ExpireSolution(false); });
        }
        void Detach()
        {
            if (job == null) return;
            job.Cancel(); detached.Add(job); job = null;
        }
        public override void RemovedFromDocument(GH_Document document)
        {
            Detach(); foreach (WorkerJob previous in detached) previous.Cancel();
            base.RemovedFromDocument(document);
        }
        protected override void SolveInstance(IGH_DataAccess da)
        {
            string domain = null; var supports = new List<string>(); var loads = new List<string>();
            string material=null,options=null,source=null,limits=null;int mode=0;
            bool run = false, stop = false, reset = false;
            // Read controls first, so Reset/Stop also work with missing geometry inputs.
            da.GetData(7, ref run); da.GetData(8, ref stop); da.GetData(9, ref reset);
            bool startEdge = initialized && run && !lastRun, stopEdge = initialized && stop && !lastStop, resetEdge = initialized && reset && !lastReset;
            initialized = true; lastRun = run; lastStop = stop; lastReset = reset;
            try
            {
                foreach (WorkerJob old in detached.ToArray()) if (!old.Running) { old.Process.Dispose(); detached.Remove(old); }
                if (resetEdge) Detach();
                if (stopEdge && job != null) job.Cancel();
                if (!da.GetData(0, ref domain) || !da.GetDataList(1, supports) || !da.GetDataList(2, loads))
                { da.SetData(1, "Connect Domain, Supports and Loads"); if (job != null && job.Running) Schedule(); if (detached.Any(j => j.Running)) Schedule(); return; }
                if(!da.GetData(3,ref material)||!da.GetData(4,ref options)||!da.GetData(5,ref mode))return;
                da.GetData(6,ref source);da.GetData(10,ref limits);
                if(string.IsNullOrWhiteSpace(domain)||supports.Count==0||supports.Any(string.IsNullOrWhiteSpace)||loads.Count==0||loads.Any(string.IsNullOrWhiteSpace))throw new ArgumentException("Connect valid Domain, Supports and Load Cases; repair any upstream error first");
                if(mode<0||mode>2)throw new ArgumentException("Mode must be 0 FEM, 1 optimization, or 2 verification");
                JObject dom=JObject.Parse(domain),cfg=JObject.Parse(options);
                JObject request=new JObject{{"schema","topoptlab-gh-request-v1"},{"engineering",true},{"dimension",dom["nz"]==null?2:3},{"mode",new[]{"fem","optimize","verify"}[mode]},
                    {"domain",dom},{"supports",new JArray(supports.Select(JObject.Parse))},{"load_cases",new JArray(loads.Select(JObject.Parse))},{"material",JObject.Parse(material)},
                    {"settings",cfg["settings"]},{"manufacturing",cfg["manufacturing"]}};
                if(!string.IsNullOrWhiteSpace(limits))request["design_limits"]=JObject.Parse(limits);
                if(mode==2){var design=string.IsNullOrWhiteSpace(source)?null:JObject.Parse(source);
                    if(design==null||(string)design["status"]!="completed"){
                        if(startEdge)throw new ArgumentException("Run optimization to completion before final verification");
                        Message="Awaiting completed design";da.SetData(1,"Waiting for completed optimization. Then press Run for final verification.");
                        if(job!=null&&job.Running||detached.Any(j=>j.Running))Schedule();return;
                    }
                    request["source_result"]=design;
                }
                string fingerprint = WorkerJob.Hash(request.ToString(Formatting.None));
                if (startEdge && !resetEdge && !stop)
                {
                    if (job != null && job.Running) AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "A job is running. Stop or Reset before starting another.");
                    else { Detach(); job = WorkerJob.Start(request, fingerprint, Path.Combine(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location), "local-settings.json")); }
                }
                string status = "Ready - press Run";
                if (job != null)
                {
                    da.SetData(2, job.Folder);
                    JObject snapshot = job.Snapshot();
                    bool stale = job.Fingerprint != fingerprint;
                    if (stale) status = "Inputs changed. Result hidden. Stop/Reset, then Run to solve the new problem.";
                    else if (snapshot != null)
                    {
                        status = (string)snapshot["status"];
                        if (status == "error") { status += ": " + (string)snapshot["message"]; AddRuntimeMessage(GH_RuntimeMessageLevel.Error, status); }
                        else if (snapshot["displacement"] != null)
                        {
                            da.SetData(0, snapshot.ToString(Formatting.None));
                            status += " | " + (string)snapshot["engineering"]["termination_reason"];
                            if((string)snapshot["engineering"]["termination_reason"]=="optimizer_failed")AddRuntimeMessage(GH_RuntimeMessageLevel.Warning,"Optimizer stopped after a numerical failure. Saved design is for inspection; read Report.");
                            var checks=snapshot["engineering"]["design_limits"] as JObject;if(checks!=null){status+=" | limits: "+(string)checks["status"];if((string)checks["status"]=="exceeded"||(string)checks["status"]=="constraints_not_satisfied")AddRuntimeMessage(GH_RuntimeMessageLevel.Warning,"Calculation completed but design limits are NOT satisfied. Inspect Report.");}
                            da.SetData(3,(string)snapshot["engineering"]["report_file"]);
                        }
                    }
                    else status = job.Running ? "Starting external Python..." : "Worker exited without a result. Inspect Job folder and Python installation.";
                    if (!job.Running && snapshot != null && (string)snapshot["status"] == "running")
                    { status = "Worker stopped unexpectedly. Inspect Job folder."; AddRuntimeMessage(GH_RuntimeMessageLevel.Error, status); }
                    if (job.Running && File.Exists(Path.Combine(job.Folder, "cancel"))) status = "Stopping after current iteration...";
                    if (job.Running) Schedule();
                }
                if (detached.Any(j => j.Running)) Schedule();
                Message = status; da.SetData(1, status);
            }
            catch (Exception e) { Error(e); Message = "Error"; da.SetData(1, e.Message); if (job != null && job.Running) Schedule(); }
        }
    }

}
