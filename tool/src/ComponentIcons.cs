// SPDX-License-Identifier: GPL-3.0-or-later
using System;
using System.IO;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Collections.Generic;
namespace TopoptLab.GH
{
    // Code-native glyphs: no external image files are needed at runtime.
    public static class ComponentIcons
    {
        static readonly Dictionary<string,Bitmap> cache=new Dictionary<string,Bitmap>();
        public static Bitmap For(string kind)
        {
            if(kind=="MaterialComponent")kind="DomainComponent";
            if(kind=="LoadCaseComponent")kind="LoadComponent";
            if(kind=="EngineeringSettingsComponent")kind="ScenarioGeometryComponent";
            if(kind=="EngineeringSolveComponent")kind="SolverComponent";

            lock(cache) {
                Bitmap icon;if(cache.TryGetValue(kind,out icon))return icon;
                if(kind.Contains("3D")) {
                    string source=kind=="FinalGeometry3DComponent"?"FinalSurfaceGlyph":kind=="FinalFem3DComponent"?"FinalFemGlyph":kind=="FinalResults3DComponent"?"FinalResultsGlyph":kind=="SurfaceLoad3DComponent"?"SurfaceLoadComponent":kind=="Domain3DComponent"?"DomainComponent":kind=="Support3DComponent"?"SupportComponent":kind=="Load3DComponent"?"LoadComponent":kind=="FemAnalyze3DComponent"?"FemAnalyzeComponent":kind=="Solver3DComponent"?"SolverComponent":kind=="Results3DComponent"?"FemResultsComponent":"ExampleGeometryComponent";
                    icon=new Bitmap(24,24,PixelFormat.Format32bppArgb);
                    using(var g=Graphics.FromImage(icon)) {
                        g.Clear(Color.Transparent);g.DrawImage(For(source),new Rectangle(3,0,18,17));
                        g.FillRectangle(Brushes.MidnightBlue,1,17,22,7);
                        string[] three={"111","001","111","001","111"};string[] letter={"110","101","101","101","110"};
                        for(int y=0;y<5;y++)for(int x=0;x<3;x++){if(three[y][x]=='1')g.FillRectangle(Brushes.White,8+x,18+y,1,1);if(letter[y][x]=='1')g.FillRectangle(Brushes.White,13+x,18+y,1,1);}
                    }
                    cache.Add(kind,icon);return icon;
                }
                icon=new Bitmap(24,24,PixelFormat.Format32bppArgb);
                using(var g=Graphics.FromImage(icon))using(var ink=new Pen(Color.FromArgb(24,49,70),1.6f))using(var accent=new Pen(Color.FromArgb(0,140,170),2f)) {
                    g.SmoothingMode=SmoothingMode.AntiAlias;g.Clear(Color.Transparent);
                    using(var b=new SolidBrush(Color.FromArgb(240,247,250)))g.FillRectangle(b,1,1,22,22);
                    if(kind=="FinalSurfaceGlyph") {
                        g.FillClosedCurve(Brushes.Teal,new[]{new Point(3,18),new Point(5,5),new Point(12,9),new Point(20,4),new Point(17,20),new Point(10,15)});g.DrawCurve(ink,new[]{new Point(3,18),new Point(9,11),new Point(17,20)});
                    } else if(kind=="FinalFemGlyph") {
                        var p=new[]{new Point(12,3),new Point(3,18),new Point(21,18)};g.DrawPolygon(ink,p);foreach(var q in p)g.DrawLine(accent,q,new Point(12,13));g.DrawLine(ink,3,18,12,13);
                    } else if(kind=="FinalResultsGlyph") {
                        g.FillPolygon(Brushes.SteelBlue,new[]{new Point(3,18),new Point(5,5),new Point(12,13)});g.FillPolygon(Brushes.DarkOrange,new[]{new Point(5,5),new Point(21,6),new Point(12,13)});g.FillPolygon(Brushes.Firebrick,new[]{new Point(3,18),new Point(12,13),new Point(20,20)});g.DrawLine(ink,3,22,22,22);
                    } else if(kind=="PrintReviewComponent") {
                        g.DrawRectangle(ink,3,3,18,18);g.DrawLine(accent,6,17,18,17);g.DrawLine(accent,7,14,17,14);g.DrawLine(accent,8,11,16,11);g.DrawLine(ink,12,3,12,8);g.FillPolygon(Brushes.DarkOrange,new[]{new Point(9,6),new Point(15,6),new Point(12,10)});
                    } else if(kind=="DesignLimitsComponent") {
                        g.DrawRectangle(ink,3,3,18,18);g.DrawLine(accent,5,16,10,16);g.DrawLine(accent,10,16,18,7);using(var red=new Pen(Color.Firebrick,2))g.DrawLine(red,4,8,20,8);
                    } else if(kind=="CaseResultComponent") {
                        g.DrawRectangle(ink,3,3,14,14);g.DrawRectangle(accent,7,7,14,14);g.DrawLine(ink,10,11,18,11);g.DrawLine(ink,10,15,18,15);
                    } else if(kind=="CompareResultsComponent") {
                        g.DrawLine(ink,2,21,22,21);g.FillRectangle(Brushes.SteelBlue,4,4,6,16);g.FillRectangle(Brushes.DarkOrange,14,10,6,10);
                    } else if(kind=="ReviewControlsComponent") {
                        for(int y=5;y<=19;y+=7)g.DrawLine(ink,3,y,21,y);g.FillEllipse(Brushes.Teal,7,2,6,6);g.FillEllipse(Brushes.Teal,14,9,6,6);g.FillEllipse(Brushes.Teal,4,16,6,6);
                    } else if(kind=="DomainComponent") {
                        g.DrawRectangle(ink,3,3,18,18);for(int k=9;k<21;k+=6){g.DrawLine(accent,k,3,k,21);g.DrawLine(accent,3,k,21,k);}
                    } else if(kind=="SupportComponent") {
                        g.DrawLine(ink,3,20,21,20);g.DrawPolygon(accent,new[]{new Point(12,5),new Point(5,17),new Point(19,17)});
                        for(int k=4;k<22;k+=4)g.DrawLine(ink,k,20,k-2,23);
                    } else if(kind=="LoadComponent") {
                        using(var p=new Pen(Color.FromArgb(221,90,41),3)){g.DrawLine(p,12,3,12,18);g.DrawLine(p,6,12,12,18);g.DrawLine(p,18,12,12,18);}g.DrawLine(ink,3,21,21,21);
                    } else if(kind=="SurfaceLoadComponent") {
                        g.DrawLine(ink,2,20,22,20);using(var p=new Pen(Color.FromArgb(221,90,41),2)){for(int x=5;x<=19;x+=7){g.DrawLine(p,x,3,x,16);g.DrawLine(p,x-3,12,x,16);g.DrawLine(p,x+3,12,x,16);}}
                    } else if(kind=="GravityComponent") {
                        g.FillEllipse(Brushes.SlateGray,3,3,8,8);using(var p=new Pen(Color.FromArgb(221,90,41),2)){g.DrawLine(p,16,4,16,21);g.DrawLine(p,11,16,16,21);g.DrawLine(p,21,16,16,21);}
                    } else if(kind=="SolverComponent") {
                        g.DrawLine(ink,3,3,3,21);using(var p=new Pen(Color.FromArgb(0,133,141),3)){g.DrawLines(p,new[]{new Point(4,4),new Point(20,12),new Point(4,20)});g.DrawLine(p,4,12,20,12);}
                    } else if(kind=="ResultsComponent") {
                        for(int x=0;x<4;x++)for(int y=0;y<4;y++)using(var b=new SolidBrush(Color.FromArgb(30+45*x,70+35*y,150+20*x)))g.FillRectangle(b,3+5*x,3+5*y,4,4);
                    } else if(kind=="FemAnalyzeComponent") {
                        g.DrawRectangle(ink,3,4,17,16);g.DrawLine(ink,3,4,20,20);g.DrawLine(ink,3,20,20,4);g.DrawLine(ink,3,12,20,12);
                        using(var p=new Pen(Color.FromArgb(221,90,41),2)){g.DrawLine(p,20,1,20,8);g.DrawLine(p,17,5,20,8);g.DrawLine(p,23,5,20,8);}
                    } else if(kind=="FemResultsComponent") {
                        Color[] colors={Color.FromArgb(45,70,180),Color.FromArgb(0,156,190),Color.FromArgb(244,184,51),Color.FromArgb(210,57,46)};
                        for(int k=0;k<4;k++)using(var b=new SolidBrush(colors[k]))g.FillRectangle(b,3+5*k,4,5,16);
                        using(var p=new Pen(Color.White,1.3f))g.DrawLines(p,new[]{new Point(3,17),new Point(8,15),new Point(13,8),new Point(21,6)});
                    } else if(kind=="ScenarioGeometryComponent") {
                        for(int x=0;x<2;x++)for(int y=0;y<2;y++)g.DrawRectangle(x==y?accent:ink,3+x*11,3+y*11,7,7);
                    } else {
                        g.DrawRectangle(ink,3,5,18,14);g.DrawEllipse(accent,9,9,6,6);g.DrawLine(accent,3,5,3,19);
                    }
                }
                cache.Add(kind,icon);return icon;
            }
        }
        public static void Export(string folder)
        {
            Directory.CreateDirectory(folder);foreach(string k in new[]{"DesignLimitsComponent","CaseResultComponent","CompareResultsComponent","ReviewControlsComponent","PrintReviewComponent","SurfaceLoadComponent","SurfaceLoad3DComponent","GravityComponent"})For(k).Save(Path.Combine(folder,k+".png"),ImageFormat.Png);
            string[] threeKinds={"Example3DComponent","Domain3DComponent","Support3DComponent","Load3DComponent","FemAnalyze3DComponent","Solver3DComponent","Results3DComponent","FinalGeometry3DComponent","FinalFem3DComponent","FinalResults3DComponent"};
            using(var strip=new Bitmap(threeKinds.Length*150,100))using(var g=Graphics.FromImage(strip))using(var font=new Font("Segoe UI",9)) {
                g.Clear(Color.White);g.InterpolationMode=InterpolationMode.NearestNeighbor;g.PixelOffsetMode=PixelOffsetMode.Half;
                for(int k=0;k<threeKinds.Length;k++){For(threeKinds[k]).Save(Path.Combine(folder,threeKinds[k]+".png"),ImageFormat.Png);g.DrawImage(For(threeKinds[k]),new Rectangle(k*150+35,4,72,72));g.DrawString(threeKinds[k].Replace("Component",""),font,Brushes.Black,k*150+2,82);}
                strip.Save(Path.Combine(folder,"icone_3d.png"),ImageFormat.Png);
            }

            string[] kinds={"ExampleGeometryComponent","ScenarioGeometryComponent","DomainComponent","SupportComponent","LoadComponent","SolverComponent","ResultsComponent","FemAnalyzeComponent","FemResultsComponent"};
            string[] labels={"Example","Scenario","Domain","Support","Load","Optimize","Results","FEM Analyze","FEM Results"};
            using(var sheet=new Bitmap(990,125))using(var g=Graphics.FromImage(sheet))using(var font=new Font("Segoe UI",10)) {
                g.Clear(Color.White);g.InterpolationMode=InterpolationMode.NearestNeighbor;g.PixelOffsetMode=PixelOffsetMode.Half;
                for(int k=0;k<kinds.Length;k++) {var icon=For(kinds[k]);icon.Save(Path.Combine(folder,kinds[k]+".png"),ImageFormat.Png);g.DrawImage(icon,new Rectangle(k*110+19,10,72,72));g.DrawString(labels[k],font,Brushes.Black,k*110+7,94);}
                sheet.Save(Path.Combine(folder,"icone_componenti.png"),ImageFormat.Png);
            }
        }
    }
}
