# SPDX-License-Identifier: GPL-3.0-or-later
"""Teaching roof case: all geometry in mm, forces in N, stress in MPa."""
import copy,json,sys,math,os
from pathlib import Path
import numpy as np
ROOT=Path(os.environ['TOPOPTLAB_ROOT']).resolve();sys.path.insert(0,str(ROOT/'tool'))
L=6000.;HEEL=300.;RISE=1500.;THICKNESS=12.;SPACING=3000.;G=9.80665
CASE_NAMES=['SLS snow uniform','ULS snow uniform','ULS snow left','ULS snow right','ULS wind uplift']

def roof(x):return HEEL+RISE*(1-abs(2*x/L-1))

def geometry(h=100):
 nx=round(L/h);ny=round((HEEL+RISE)/h)
 if not np.isclose(nx*h,L) or not np.isclose(ny*h,HEEL+RISE):raise ValueError('Use h=100, 50 or 25 for the teaching reference')
 nominal=np.array([[x,roof(x)] for x in np.arange(500,6000,1000)])
 keepboxes=[[0,0,200,200],[5800,0,6000,200]]+[[x-150,y-150,x+150,y+150] for x,y in nominal]
 active=[];solid=[]
 for x in range(nx):
  for row in range(ny):
   cx=(x+.5)*h;cy=(ny-row-.5)*h;e=x*ny+row
   if cy<=roof(cx)+1e-8:
    active.append(e)
    if any(x0-1e-8<=cx<=x1+1e-8 and y0-1e-8<=cy<=y1+1e-8 for x0,y0,x1,y1 in keepboxes):solid.append(e)
 available=sorted({n for e in active for n in [e//ny*(ny+1)+e%ny,e//ny*(ny+1)+e%ny+1,(e//ny+1)*(ny+1)+e%ny,(e//ny+1)*(ny+1)+e%ny+1]})
 def nodepoint(n):return np.array([n//(ny+1)*h,(ny-n%(ny+1))*h])
 def nearest(p):
  n=min(available,key=lambda n:np.linalg.norm(nodepoint(n)-p));assert np.linalg.norm(nodepoint(n)-p)<=h*.76+1e-8;return n
 stations=[nearest(p) for p in nominal]
 d=dict(nx=nx,ny=ny,cell=h,origin=[0.,0.],frame=[[0,0,0],[1,0,0],[0,1,0]],active=active,solid=solid)
 supports=[dict(nodes=[nearest([0,0])],fix_x=True,fix_y=True),dict(nodes=[nearest([6000,0])],fix_x=False,fix_y=True)]
 return d,supports,stations,nominal,keepboxes,[nodepoint(n).tolist() for n in stations]

def forces(case):
 values=[]
 for j in range(6):
  if case==0:fx=0;fy=-3000*(.15+.6+.8)
  elif case in (1,2,3):
   snow=.8 if case==1 or case==2 and j<3 or case==3 and j>=3 else .4
   fx=0;fy=-3000*(1.3*.15+1.5*.6+1.5*snow)
  else:fx=(-1 if j<3 else 1)*1.5*1.0*3000*.5;fy=3000*(1.5*1.0-.15-.8*.6)
  values.append([fx,fy])
 return values

def request(h=100,mode='fem',fraction=.3,iterations=100):
 d,supports,stations,nominal,boxes,applied=geometry(h)
 cases=[]
 for i,name in enumerate(CASE_NAMES):
  loads=[dict(nodes=[n],force=f) for n,f in zip(stations,forces(i))]
  loads.append(dict(kind='gravity',acceleration=[0,-G*(1.3 if i in (1,2,3) else 1)]))
  cases.append(dict(name=name,weight=1,loads=loads))
 return dict(schema='topoptlab-gh-request-v1',engineering=True,dimension=2,mode=mode,job_id='roof-2d-'+mode,domain=d,supports=supports,loads=[],load_cases=cases,material=dict(preset='steel',length_unit='mm',force_unit='N',stock_thickness_mm=12,safety_factor=1.5),settings=dict(backend='cpu-direct',threads=4,volume=fraction,iterations=iterations,radius=180/h,thickness=THICKNESS,young=210000,poisson=.3,preserve_attachments=True,objective_tolerance=.001,design_tolerance=.01,convergence_window=5,minimum_iterations=10),manufacturing=dict(symmetry='x',extrusion='none',process='unspecified',threshold=.4,minimum_feature=0),design_limits=dict(max_displacement=0,max_stress_mpa=0,enforce=False))

