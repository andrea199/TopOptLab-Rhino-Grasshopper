# SPDX-License-Identifier: GPL-3.0-or-later
"""Numerical fixtures from the same catalog embedded in the GHA."""
import json
from pathlib import Path
CATALOG=json.loads(Path(__file__).with_name('scenarios.json').read_text(encoding='utf8'))
def request(index, mode='optimize'):
    c=CATALOG[index];h=c['cell'];nx=round(c['width']/h);ny=round(c['height']/h)
    active=[];solid=[]
    for col in range(nx):
        for row in range(ny):
            x,y=(col+.5)*h,(ny-row-.5)*h
            if any((x-cx)**2+(y-cy)**2<rad**2 for cx,cy,rad in c['holes']):continue
            e=col*ny+row;active.append(e)
            if any(x0<x<x1 and y0<y<y1 for x0,y0,x1,y1 in c['keep']):solid.append(e)
    def node(x,y):return round(x/h)*(ny+1)+ny-round(y/h)
    supports=[]
    for s in c['supports']:
        nodes=[node(s['x'],s['y'])] if s['kind']=='point' else [node(s['x'],row*h) for row in range(round(s['y']/h),round(s['y2']/h)+1)]
        supports.append(dict(nodes=nodes,fix_x=s['fix_x'],fix_y=s['fix_y']))
    return dict(schema='topoptlab-gh-request-v1',mode=mode,job_id=c['id']+'-'+mode,
        domain=dict(nx=nx,ny=ny,cell=h,origin=[0,0],frame=[[0,0,0],[1,0,0],[0,1,0]],active=active,solid=solid),
        supports=supports,loads=[dict(nodes=[node(x,y)],force=c['force'][:2]) for x,y in c['loads']],
        settings={key:c[key] for key in ['young','poisson','thickness','volume','iterations','radius']})
