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
    public sealed class WorkerJob
    {
        public string Folder, Id, Fingerprint;
        public Process Process;
        readonly object logLock = new object();
        void Log(string name, string line)
        {
            if (line == null) return;
            try { lock (logLock) File.AppendAllText(Path.Combine(Folder, name), line + Environment.NewLine); }
            catch (IOException) { } // Logging failure must not throw on a process event thread.
            catch (UnauthorizedAccessException) { }
        }
        public static string Hash(string text)
        { using (SHA256 sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(text))).Replace("-", ""); }
        static string Quote(string text)
        {
            if (text.Contains("\"") || text.EndsWith("\\")) throw new ArgumentException("Invalid worker path");
            return "\"" + text + "\"";
        }
        public static WorkerJob Start(JObject request, string fingerprint, string configPath)
        {
            bool persistentSettings = !File.Exists(configPath);
            if (!File.Exists(configPath)) configPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "TopOptLab", "Rhino8", "settings.json");
            if (!File.Exists(configPath)) throw new FileNotFoundException("Configure Python first: right-click a TopOptLab component and open the Python setup folder, then run SETUP-PYTHON.cmd. For a source install use INSTALL.cmd.", configPath);
            JObject config = JObject.Parse(File.ReadAllText(configPath));
            string runtimeIdentity = Path.Combine(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location), "runtime-id.txt");
            if (persistentSettings && File.Exists(runtimeIdentity) && ((string)config["schema"] != "topoptlab-runtime-v1" || (string)config["runtime_id"] != File.ReadAllText(runtimeIdentity).Trim()))
                throw new InvalidDataException("The configured Python worker belongs to another package runtime. Run SETUP-PYTHON.cmd for this Yak version.");
            string python = (string)config["python"], worker = (string)config["worker"];
            if (!File.Exists(python) || !File.Exists(worker)) throw new FileNotFoundException("Python or worker is missing. Run SETUP-PYTHON.cmd again (Yak) or INSTALL.cmd (source).");
            WorkerJob job = new WorkerJob { Id = Guid.NewGuid().ToString("N"), Fingerprint = fingerprint };
            job.Folder = Path.Combine(Path.GetTempPath(), "topoptlab-gh", job.Id);
            Directory.CreateDirectory(job.Folder);
            request["job_id"] = job.Id;
            string requestPath = Path.Combine(job.Folder, "request.json");
            File.WriteAllText(requestPath, request.ToString(Formatting.None), new UTF8Encoding(false));
            ProcessStartInfo info = new ProcessStartInfo(python, Quote(worker) + " --request " + Quote(requestPath) + " --output " + Quote(job.Folder)) {
                UseShellExecute = false, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden,
                RedirectStandardOutput = true, RedirectStandardError = true,
                WorkingDirectory = Path.GetDirectoryName(worker)
            };
            job.Process = new Process { StartInfo = info };
            job.Process.OutputDataReceived += delegate(object sender, DataReceivedEventArgs e) { job.Log("stdout.log", e.Data); };
            job.Process.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs e) { job.Log("stderr.log", e.Data); };
            job.Process.Start(); job.Process.BeginOutputReadLine(); job.Process.BeginErrorReadLine();
            return job;
        }
        public bool Running { get { return Process != null && !Process.HasExited; } }
        public void Cancel() { if (Running) File.WriteAllText(Path.Combine(Folder, "cancel"), "cancel"); }
        readonly object snapshotLock = new object();
        JObject cachedSnapshot;
        string cachedSnapshotPath, cachedSnapshotJob;
        long cachedSnapshotLength;
        DateTime cachedSnapshotWriteTime, cachedSnapshotCreationTime;
        // Callers treat snapshots as read-only. Avoid parsing the same large JSON on every 400 ms poll.
        public JObject Snapshot()
        {
            lock (snapshotLock)
            {
                try
                {
                    string resultPath = Path.GetFullPath(Path.Combine(Folder, "result.json"));
                    string path = File.Exists(resultPath) ? resultPath : Path.GetFullPath(Path.Combine(Folder, "progress.json"));
                    var before = new FileInfo(path);
                    if (!before.Exists) { cachedSnapshot = null; return null; }
                    long length = before.Length;
                    DateTime written = before.LastWriteTimeUtc, created = before.CreationTimeUtc;
                    if (cachedSnapshot != null && cachedSnapshotPath == path && cachedSnapshotJob == Id && cachedSnapshotLength == length && cachedSnapshotWriteTime == written && cachedSnapshotCreationTime == created)
                        return cachedSnapshot;
                    // A changed or failed file must never fall back to an older successful result.
                    cachedSnapshot = null;
                    string json;
                    using (var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
                    using (var reader = new StreamReader(stream)) json = reader.ReadToEnd();
                    JObject data = JObject.Parse(json);
                    if ((string)data["job_id"] != Id) throw new InvalidDataException("Result belongs to another job.");
                    var after = new FileInfo(path);
                    // The worker atomically replaces snapshots. Do not cache a read spanning a replacement.
                    if (after.Exists && after.Length == length && after.LastWriteTimeUtc == written && after.CreationTimeUtc == created)
                    {
                        cachedSnapshotPath = path; cachedSnapshotJob = Id; cachedSnapshotLength = length;
                        cachedSnapshotWriteTime = written; cachedSnapshotCreationTime = created; cachedSnapshot = data;
                    }
                    return data;
                }
                catch { cachedSnapshot = null; throw; }
            }
        }

    }

    public sealed class SolverComponent : Component
    {
        WorkerJob job;
        readonly List<WorkerJob> detached = new List<WorkerJob>();
        bool lastRun, lastStop, lastReset, initialized;
        public SolverComponent() : base("TopOpt Solver", "Optimize", "External Python solver. Run on a button pulse. Stop after current iteration. Reset clears this component. Inputs are frozen per job.", "3 Solve") { }
        public override Guid ComponentGuid { get { return new Guid("693da4b7-ad69-4562-baef-97926dc926e6"); } }
        protected override void RegisterInputParams(GH_InputParamManager p)
        {
            p.AddTextParameter("Domain", "D", "TopOpt Domain", GH_ParamAccess.item);
            p.AddTextParameter("Supports", "S", "Connect all TopOpt Support outputs (hold Shift to add wires)", GH_ParamAccess.list);
            p.AddTextParameter("Loads", "L", "Simultaneous TopOpt Load outputs", GH_ParamAccess.list);
            p[0].Optional = true; p[1].Optional = true; p[2].Optional = true;
            p.AddNumberParameter("Volume", "V", "Material fraction of active domain, including preserved regions", GH_ParamAccess.item, .4);
            p.AddIntegerParameter("Iterations", "I", "Optimization steps", GH_ParamAccess.item, 80);
            p.AddNumberParameter("Filter radius", "R", "Density filter radius in CELLS, between 1 and 10", GH_ParamAccess.item, 2.4);
            p.AddNumberParameter("Young modulus", "E", "Consistent force / model-length squared units", GH_ParamAccess.item, 1);
            p.AddNumberParameter("Poisson ratio", "nu", "0 to 0.49", GH_ParamAccess.item, .3);
            p.AddNumberParameter("Thickness", "t", "Physical out-of-plane thickness in model units", GH_ParamAccess.item, 1);
            p.AddBooleanParameter("Run", "Run", "Button pulse starts a new run", GH_ParamAccess.item, false);
            p.AddBooleanParameter("Stop", "Stop", "Cancel after the current FEM solve", GH_ParamAccess.item, false);
            p.AddBooleanParameter("Reset", "Reset", "Cancel and detach this job; clear displayed results", GH_ParamAccess.item, false);
        }
        protected override void RegisterOutputParams(GH_OutputParamManager p)
        {
            p.AddTextParameter("Result", "R", "Live or completed result; empty after changing solver inputs", GH_ParamAccess.item);
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
            double volume = .4, radius = 2.4, young = 1, nu = .3, thickness = 1; int iterations = 80;
            bool run = false, stop = false, reset = false;
            // Read controls first, so Reset/Stop also work with missing geometry inputs.
            da.GetData(9, ref run); da.GetData(10, ref stop); da.GetData(11, ref reset);
            bool startEdge = initialized && run && !lastRun, stopEdge = initialized && stop && !lastStop, resetEdge = initialized && reset && !lastReset;
            initialized = true; lastRun = run; lastStop = stop; lastReset = reset;
            try
            {
                foreach (WorkerJob old in detached.ToArray()) if (!old.Running) { old.Process.Dispose(); detached.Remove(old); }
                if (resetEdge) Detach();
                if (stopEdge && job != null) job.Cancel();
                if (!da.GetData(0, ref domain) || !da.GetDataList(1, supports) || !da.GetDataList(2, loads))
                { da.SetData(1, "Connect Domain, Supports and Loads"); if (job != null && job.Running) Schedule(); if (detached.Any(j => j.Running)) Schedule(); return; }
                if (!da.GetData(3, ref volume) || !da.GetData(4, ref iterations) || !da.GetData(5, ref radius) || !da.GetData(6, ref young) || !da.GetData(7, ref nu) || !da.GetData(8, ref thickness)) return;
                if (string.IsNullOrWhiteSpace(domain) || supports.Count == 0 || loads.Count == 0 || supports.Any(string.IsNullOrWhiteSpace) || loads.Any(string.IsNullOrWhiteSpace)) throw new ArgumentException("Missing or invalid Domain/Support/Load data. Repair the upstream component before running.");
                JObject request = JObject.FromObject(new { schema = "topoptlab-gh-request-v1", domain = JObject.Parse(domain),
                    supports = new JArray(supports.Select(JObject.Parse)), loads = new JArray(loads.Select(JObject.Parse)),
                    settings = new { volume = volume, iterations = iterations, radius = radius, young = young, poisson = nu, thickness = thickness, penal = 3 } });
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
                        else if (snapshot["density"] != null)
                        {
                            da.SetData(0, snapshot.ToString(Formatting.None));
                            status += " | iteration " + snapshot["completed_iterations"] + "/" + iterations;
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

    public sealed class AssemblyInfo : GH_AssemblyInfo
    {
        public override string Name { get { return "topoptlab-rhino"; } }
        public override string Description { get { return "Rhino 8 / external Python teaching integration for topoptlab"; } }
        public override Guid Id { get { return new Guid("f4f8bfcd-9314-42fd-bb29-0887143d49eb"); } }
        public override string AuthorName { get { return "Andrea Detry; upstream TopOptLab by Stefan Hiemer"; } }
        public override string Version { get { return "0.4.0-alpha.4"; } }
    }
}
