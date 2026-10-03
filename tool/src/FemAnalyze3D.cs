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
    public sealed class FemAnalyze3DComponent : Component
    {
        WorkerJob job;
        readonly List<WorkerJob> detached = new List<WorkerJob>();
        bool lastRun, lastStop, lastReset, initialized;
        public FemAnalyze3DComponent() : base("TopOpt FEM Analyze 3D", "FEM 3D", "Full-solid 3D elasticity. E and nu; thickness is in the solid geometry.", "8 Solve 3D") { }
        public override Guid ComponentGuid { get { return new Guid("6c8b1e31-0011-4e55-8001-010000000004"); } }
        protected override void RegisterInputParams(GH_InputParamManager p)
        {
            p.AddTextParameter("Domain", "D", "TopOpt Domain", GH_ParamAccess.item);
            p.AddTextParameter("Supports", "S", "Connect all TopOpt Support outputs (hold Shift to add wires)", GH_ParamAccess.list);
            p.AddTextParameter("Loads", "L", "Simultaneous TopOpt Load outputs", GH_ParamAccess.list);
            p[0].Optional = true; p[1].Optional = true; p[2].Optional = true;
            p.AddNumberParameter("Young modulus", "E", "Consistent force / model-length squared units", GH_ParamAccess.item, 210000);
            p.AddNumberParameter("Poisson ratio", "nu", "0 to 0.49", GH_ParamAccess.item, .3);
            p.AddBooleanParameter("Analyze", "Analyze", "Button pulse starts full-solid FEM", GH_ParamAccess.item, false);
            p.AddBooleanParameter("Stop", "Stop", "Cancel after the current FEM solve", GH_ParamAccess.item, false);
            p.AddBooleanParameter("Reset", "Reset", "Cancel and detach this job; clear displayed results", GH_ParamAccess.item, false);
        }
        protected override void RegisterOutputParams(GH_OutputParamManager p)
        {
            p.AddTextParameter("FEM Result", "R", "Connect to FEM Results (not optimization Results)", GH_ParamAccess.item);
            p.AddTextParameter("Status", "S", "Job progress or validation error", GH_ParamAccess.item);
            p.AddTextParameter("Job folder", "J", "Request, snapshots, history and errors", GH_ParamAccess.item);
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
            double young = 210000, nu = .3;
            bool run = false, stop = false, reset = false;
            // Read controls first, so Reset/Stop also work with missing geometry inputs.
            da.GetData(5, ref run); da.GetData(6, ref stop); da.GetData(7, ref reset);
            bool startEdge = initialized && run && !lastRun, stopEdge = initialized && stop && !lastStop, resetEdge = initialized && reset && !lastReset;
            initialized = true; lastRun = run; lastStop = stop; lastReset = reset;
            try
            {
                foreach (WorkerJob old in detached.ToArray()) if (!old.Running) { old.Process.Dispose(); detached.Remove(old); }
                if (resetEdge) Detach();
                if (stopEdge && job != null) job.Cancel();
                if (!da.GetData(0, ref domain) || !da.GetDataList(1, supports) || !da.GetDataList(2, loads))
                { da.SetData(1, "Connect Domain, Supports and Loads"); if (job != null && job.Running) Schedule(); if (detached.Any(j => j.Running)) Schedule(); return; }
                if (!da.GetData(3, ref young) || !da.GetData(4, ref nu)) return;
                if (string.IsNullOrWhiteSpace(domain) || supports.Count == 0 || loads.Count == 0 || supports.Any(string.IsNullOrWhiteSpace) || loads.Any(string.IsNullOrWhiteSpace)) throw new ArgumentException("Missing or invalid Domain/Support/Load data. Repair the upstream component before running.");
                JObject request = JObject.FromObject(new { schema = "topoptlab-gh-request-v1", mode = "fem", dimension = 3, domain = JObject.Parse(domain),
                    supports = new JArray(supports.Select(JObject.Parse)), loads = new JArray(loads.Select(JObject.Parse)),
                    settings = new { young = young, poisson = nu } });
                string fingerprint = WorkerJob.Hash(request.ToString(Formatting.None));
                if (startEdge && !resetEdge && !stop)
                {
                    if (job != null && job.Running) AddRuntimeMessage(GH_RuntimeMessageLevel.Warning, "A job is running. Stop or Reset before starting another.");
                    else { Detach(); job = WorkerJob.Start(request, fingerprint, Path.Combine(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location), "local-settings.json")); }
                }
                string status = "Ready - press Analyze";
                if (job != null)
                {
                    da.SetData(2, job.Folder);
                    JObject snapshot = job.Snapshot();
                    bool stale = job.Fingerprint != fingerprint;
                    if (stale) status = "Inputs changed. Result hidden. Stop/Reset, then Analyze to solve the new problem.";
                    else if (snapshot != null)
                    {
                        status = (string)snapshot["status"];
                        if (status == "error") { status += ": " + (string)snapshot["message"]; AddRuntimeMessage(GH_RuntimeMessageLevel.Error, status); }
                        else if (snapshot["displacement"] != null)
                        {
                            da.SetData(0, snapshot.ToString(Formatting.None));
                            status += " | full-solid FEM";
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
