// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text.RegularExpressions;
namespace TopoptLab.GH {
 public static class RuntimePaths {
  public static bool IsMac { get { var p=Environment.OSVersion.Platform;return p==PlatformID.MacOSX||(p==PlatformID.Unix&&File.Exists("/usr/bin/sw_vers")); } }
  public static string SetupFileName { get { return IsMac?"SETUP-PYTHON.command":"SETUP-PYTHON.cmd"; } }
  public static string StateDirectory { get {return IsMac?Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),"Library","Application Support","TopOptLab","Rhino8"):Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"TopOptLab","Rhino8");} }
  public static void OpenFolder(string folder) {
   if(IsMac)Process.Start(new ProcessStartInfo("/usr/bin/open","\""+folder.Replace("\"","\\\"")+"\""){UseShellExecute=false});
   else Process.Start(new ProcessStartInfo(folder){UseShellExecute=true});
  }
  public static ulong ParseMacAvailableMemory(string text) {
   var page=Regex.Match(text,@"page size of\s+(\d+)\s+bytes");
   var free=Regex.Match(text,@"^Pages free:\s+(\d+)\.",RegexOptions.Multiline);
   var inactive=Regex.Match(text,@"^Pages inactive:\s+(\d+)\.",RegexOptions.Multiline);
   if(!page.Success||!free.Success||!inactive.Success)throw new ArgumentException("Cannot parse macOS vm_stat memory information; no geometry was allocated.");
   ulong size=ulong.Parse(page.Groups[1].Value,CultureInfo.InvariantCulture),a=ulong.Parse(free.Groups[1].Value,CultureInfo.InvariantCulture),b=ulong.Parse(inactive.Groups[1].Value,CultureInfo.InvariantCulture);
   if(size==0)throw new ArgumentException("Invalid macOS memory page size");
   return checked((a+b)*size); // Conservative available-memory estimate: free + inactive, excluding compression/swap.
  }
  public static ulong MacAvailableMemory() {
   using(var p=new Process()) {
    p.StartInfo=new ProcessStartInfo("/usr/bin/vm_stat"){UseShellExecute=false,RedirectStandardOutput=true,RedirectStandardError=true,CreateNoWindow=true};
    p.Start();var output=p.StandardOutput.ReadToEndAsync();var error=p.StandardError.ReadToEndAsync();
    if(!p.WaitForExit(5000)){p.Kill();p.WaitForExit();throw new ArgumentException("macOS memory preflight timed out; no geometry was allocated.");}
    if(!output.Wait(1000)||!error.Wait(1000)||p.ExitCode!=0)throw new ArgumentException("Cannot read available RAM on macOS; no geometry was allocated.");
    return ParseMacAvailableMemory(output.Result);
   }
  }
 }
}
