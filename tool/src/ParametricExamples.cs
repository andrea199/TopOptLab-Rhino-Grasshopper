using System;
using System.Collections.Generic;
using System.Drawing;
using Rhino.Geometry;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Special;
namespace TopoptLab.GH {
 public static class ParametricExamples {
  public static Transform Read(IGH_DataAccess da,int offset,double width,double height,double depth=0) {
   double w=width,h=height,d=depth,x=0,y=0,z=0;
   da.GetData(offset++,ref w);da.GetData(offset++,ref h);
   if(depth>0)da.GetData(offset++,ref d);
   da.GetData(offset++,ref x);da.GetData(offset++,ref y);da.GetData(offset,ref z);
   foreach(double v in new[]{w,h,x,y,z,d})if(double.IsNaN(v)||double.IsInfinity(v))throw new ArgumentException("Dimensions and position must be finite");
   if(w<=0||h<=0||(depth>0&&d<=0))throw new ArgumentException("Dimensions must be positive");
   return Transform.Translation(x,y,z)*Transform.Scale(Plane.WorldXY,w/width,h/height,depth>0?d/depth:1);
  }
  public static Curve Curve(Curve c,Transform t){c.Transform(t);return c;}
  public static Brep Brep(Brep b,Transform t){b.Transform(t);return b;}
  public static Point3d Point(Point3d p,Transform t){p.Transform(t);return p;}
  public static void Sliders(List<IGH_DocumentObject> objects,GH_Component geometry,int offset,double w,double h,double d=0) {
   var names=new List<string>{"Length X","Height Y"};var values=new List<double>{w,h};
   if(d>0){names.Add("Depth Z");values.Add(d);}
   names.AddRange(new[]{"Position X","Position Y","Position Z"});values.AddRange(new[]{0.0,0.0,0.0});
   float left=geometry.Attributes.Pivot.X-380;
   for(int k=0;k<names.Count;k++){
    var s=new GH_NumberSlider();s.NickName=names[k];s.Slider.Minimum=values[k]>0?(decimal)(values[k]*.5):-200;
    s.Slider.Maximum=values[k]>0?(decimal)(values[k]*1.5):200;s.Slider.DecimalPlaces=2;s.Slider.Type=Grasshopper.GUI.Base.GH_SliderAccuracy.Float;s.SetSliderValue((decimal)values[k]);
    s.CreateAttributes();s.Attributes.Pivot=new PointF(left,280+60*k);objects.Add(s);geometry.Params.Input[offset+k].AddSource(s);
   }
   var note=new GH_Panel();note.UserText="PARAMETRIC GEOMETRY\nOverall dimensions and world XYZ position.\nHoles, supports and loads follow the part.\nNonuniform scaling turns circles into ellipses.\nCell size, thickness and force are independent.\nAfter editing: RESET, then ANALYZE / RUN.\nIncrease h if the cell limit is exceeded.";
   note.CreateAttributes();note.Attributes.Pivot=new PointF(left,660);note.Attributes.Bounds=new RectangleF(left,660,340,180);objects.Add(note);
  }
 }
}
