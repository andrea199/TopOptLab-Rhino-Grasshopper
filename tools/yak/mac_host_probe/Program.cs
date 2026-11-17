using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text.Json;
using TopoptLab.GH;
class Program {
 static void Main() {
  if(!RuntimePaths.IsMac)throw new Exception("The Mac host probe must run on actual macOS");
  string expected=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),"Library","Application Support","TopOptLab","Rhino8");
  if(RuntimePaths.StateDirectory!=expected||RuntimePaths.SetupFileName!="SETUP-PYTHON.command")throw new Exception("Incorrect Mac settings/setup path");
  ulong available=RuntimePaths.MacAvailableMemory();if(available==0)throw new Exception("No available memory reported");
  Console.WriteLine(JsonSerializer.Serialize(new { status="PASS",architecture=RuntimeInformation.ProcessArchitecture.ToString(),available_memory_bytes=available,settings_path="~/Library/Application Support/TopOptLab/Rhino8",native_rhino_tested=false }));
 }
}
