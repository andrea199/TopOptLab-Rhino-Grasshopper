using System;
using System.IO;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Drawing;
using Grasshopper.Kernel;
using Grasshopper.GUI.Canvas;
class RenderDomain {
 [STAThread] static int Main(string[] args) {
  string[] paths={Path.Combine(args[1],"System"),Path.Combine(args[1],"Plug-ins","Grasshopper"),args[2]};
  AppDomain.CurrentDomain.AssemblyResolve+=delegate(object s,ResolveEventArgs e){foreach(var p in paths)foreach(var ext in new[]{".dll",".gha"}){var f=Path.Combine(p,new AssemblyName(e.Name).Name+ext);if(File.Exists(f))return Assembly.LoadFrom(f);}return null;};
  try{Run(args[0]);return 0;}catch(Exception e){Console.Error.WriteLine(e);return 1;}
 }
 [MethodImpl(MethodImplOptions.NoInlining)] static void Run(string output) {
  Directory.CreateDirectory(output);
  Grasshopper.CentralSettings.CanvasObjectIcons=false;
  foreach(var t in typeof(TopoptLab.GH.DomainComponent).Assembly.GetTypes()){ if(!t.IsPublic||t.IsAbstract||!typeof(GH_Component).IsAssignableFrom(t))continue; var component=(GH_Component)Activator.CreateInstance(t);component.CreateAttributes();component.Attributes.Pivot=new PointF(180,140);component.Attributes.PerformLayout();
  var bounds=Rectangle.Ceiling(component.Attributes.Bounds);bounds.Inflate(10,10);
  using(var image=new Bitmap(bounds.Width*4,bounds.Height*4))using(var g=Graphics.FromImage(image)){
   g.Clear(Color.FromArgb(246,246,241));g.ScaleTransform(4,4);g.TranslateTransform(-bounds.X,-bounds.Y);
   g.SmoothingMode=System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
   var attr=(Grasshopper.Kernel.Attributes.GH_ComponentAttributes)component.Attributes;
   var style=new GH_PaletteStyle(Color.FromArgb(217,217,217),Color.FromArgb(80,80,80),Color.Black);
   using(var capsule=GH_Capsule.CreateTextCapsule(attr.Bounds,attr.ContentBox,GH_Palette.Normal,component.NickName)){
    foreach(var p in component.Params.Input)capsule.AddInputGrip(p.Attributes.InputGrip);
    foreach(var p in component.Params.Output)capsule.AddOutputGrip(p.Attributes.OutputGrip);
    capsule.Render(g,style);
   }
   using(var canvas=new GH_Canvas())Grasshopper.Kernel.Attributes.GH_ComponentAttributes.RenderComponentParameters(canvas,g,component,style);
   image.Save(Path.Combine(output,t.Name+".png"));
   Console.WriteLine(t.Name);
  }
 }
 }
}
