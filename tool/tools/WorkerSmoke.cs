// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Threading;
using Newtonsoft.Json.Linq;
using TopoptLab.GH;
class WorkerSmoke
{
    static int Main(string[] args)
    {
        string[] paths = { args[0], args[1], args[2] };
        AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs e) {
            foreach (string folder in paths) foreach (string ext in new[] { ".dll", ".gha" }) {
                string path = Path.Combine(folder, new AssemblyName(e.Name).Name + ext); if (File.Exists(path)) return Assembly.LoadFrom(path);
            }
            return null;
        };
        try { Test(args[3], args[4]); return 0; } catch (Exception e) { Console.Error.WriteLine(e); return 1; }
    }
    static void Wait(WorkerJob job)
    {
        DateTime deadline = DateTime.UtcNow.AddSeconds(40);
        while (job.Running && DateTime.UtcNow < deadline) Thread.Sleep(50);
        if (job.Running) { job.Cancel(); throw new Exception("Worker test timed out"); }
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    static void Test(string fixture, string config)
    {
        JObject request = JObject.Parse(File.ReadAllText(fixture));
        string hash = WorkerJob.Hash(request.ToString());
        if (hash != WorkerJob.Hash(request.ToString())) throw new Exception("Hash is not stable");
        WorkerJob first = WorkerJob.Start((JObject)request.DeepClone(), hash, config);
        Wait(first);
        JObject snapshot = first.Snapshot();
        if (snapshot == null || (string)snapshot["status"] != "completed") throw new Exception("Worker did not complete: " + first.Folder);
        request["settings"]["iterations"] = (int?)request["dimension"] == 3 ? 300 : 1000;
        string changed = WorkerJob.Hash(request.ToString());
        if (hash == changed) throw new Exception("Changed input did not change fingerprint");
        WorkerJob second = WorkerJob.Start((JObject)request.DeepClone(), changed, config);
        if (first.Id == second.Id || first.Folder == second.Folder) throw new Exception("Jobs share state");
        second.Cancel(); Wait(second);
        JObject cancelled = second.Snapshot();
        if (cancelled == null || (string)cancelled["status"] != "cancelled" || File.Exists(Path.Combine(second.Folder, "result.json"))) throw new Exception("Cancellation was not honored");
        string id = first.Id; first.Id = second.Id;
        bool rejected = false;
        try { first.Snapshot(); } catch (InvalidDataException) { rejected = true; }
        first.Id = id;
        if (!rejected) throw new Exception("Foreign job result accepted");
        request["mode"] = "fem";
        request["settings"] = JObject.FromObject(new { young = 210000, poisson = .3, thickness = 2 });
        WorkerJob fem = WorkerJob.Start((JObject)request.DeepClone(), WorkerJob.Hash(request.ToString()), config);
        Wait(fem);
        JObject result = fem.Snapshot();
        if (result == null || (string)result["status"] != "completed" || (string)result["schema"] != ((int?)request["dimension"] == 3 ? "topoptlab-gh-3d-result-v1" : "topoptlab-gh-fem-result-v1"))
            throw new Exception("FEM worker did not return a completed FEM result: " + fem.Folder);
        if ((double)result["metrics"]["max_von_mises"] <= 0 || result["reactions"].Count() != result["nodes"].Count())
            throw new Exception("FEM outputs invalid");
        fem.Process.Dispose();
        first.Process.Dispose(); second.Process.Dispose();
        Console.WriteLine("PASS: FEM stress/reactions and external launch, completion, cancellation, isolated jobs, changed-input fingerprint, foreign-result rejection");
    }
}
