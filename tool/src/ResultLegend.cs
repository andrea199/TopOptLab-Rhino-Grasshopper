// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.Linq;
using System.Drawing;
using System.Globalization;
using Newtonsoft.Json.Linq;
using Grasshopper.Kernel;
using Rhino.Geometry;
namespace TopoptLab.GH {
 public interface IResultLegend { bool LegendVisible{get;} }
 public sealed class ResultLegend {
  public string Title,Field,Units,Case,Checks;
  public double Maximum,ActualMaximum,Scale;
  public Func<double,Color> Ramp;
  static string Short(string text,int length){return text!=null&&text.Length>length?text.Substring(0,length-3)+"...":text??"";}
  public static ResultLegend Create(JObject data,string field,string quantity,double maximum,double actual,double scale,Func<double,Color> ramp){
   var e=data["engineering"] as JObject;var material=e==null?null:e["material"] as JObject;
   string length=material==null?"length":(string)material["length_unit"],force=material==null?"force":(string)material["force_unit"];
   string mode=e==null?(string)data["mode"]:(string)e["mode"];
   var limits=e==null?null:e["design_limits"] as JObject;
   return new ResultLegend{Title=mode=="verify"?"FINAL VERIFICATION":mode=="optimize"||string.IsNullOrEmpty(mode)&&data["schema"]!=null&&(string)data["schema"]=="topoptlab-gh-result-v1"?"OPTIMIZATION / DESIGN":"BASELINE FEM",
    Field=field,Units=quantity=="density"?"0..1":quantity=="displacement"?length:force+"/"+length+"^2",
    Case=e==null?"Case 1":(string)e["display_case"],Checks=limits==null?"Limits: not requested":"All cases: "+(string)limits["status"],Maximum=maximum,ActualMaximum=actual,Scale=scale,Ramp=ramp};
  }
  public void Draw(IGH_PreviewArgs args,GH_Component owner){
   int slot=0;var doc=owner.OnPingDocument();
   if(doc!=null){var visible=doc.Objects.OfType<GH_Component>().Where(o=>o is IResultLegend&&!o.Hidden&&((IResultLegend)o).LegendVisible).ToList();slot=Math.Max(0,visible.IndexOf(owner));}
   int x=Math.Max(8,args.Viewport.Size.Width-342),y=20+slot*136;
   args.Display.Draw2dRectangle(new Rectangle(x,y,330,128),Color.FromArgb(60,70,80),1,Color.FromArgb(248,249,252));
   Action<string,int,Color> text=(s,dy,color)=>args.Display.Draw2dText(Short(s,48),color,new Point2d(x+10,y+dy),false,12);
   text(Title+" | "+Case,18,Color.FromArgb(25,45,65));
   text(Field+" ["+Units+"]",37,Color.FromArgb(25,45,65));
   for(int k=0;k<60;k++)args.Display.Draw2dRectangle(new Rectangle(x+10+k*5,y+47,5,12),Ramp(k/59.0),0,Ramp(k/59.0));
   args.Display.Draw2dText("0",Color.Black,new Point2d(x+10,y+76),false,12);
   args.Display.Draw2dText((Maximum/2).ToString("G4",CultureInfo.InvariantCulture),Color.Black,new Point2d(x+160,y+76),true,12);
   args.Display.Draw2dText(Maximum.ToString("G4",CultureInfo.InvariantCulture),Color.Black,new Point2d(x+292,y+76),true,12);
   text("Peak "+ActualMaximum.ToString("G5",CultureInfo.InvariantCulture)+" | deformation x"+Scale.ToString("G4",CultureInfo.InvariantCulture),96,Color.Black);
   text(Checks,116,Checks.Contains("exceeded")||Checks.Contains("not_satisfied")?Color.DarkRed:Color.FromArgb(35,65,80));
  }
 }
}
