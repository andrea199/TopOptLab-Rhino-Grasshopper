# SPDX-License-Identifier: GPL-3.0-or-later
def cantilever(mode='fem',nx=24,ny=12,nz=6,iterations=40):
    h=120/nx
    def node(x,y,z):return z*(nx+1)*(ny+1)+x*(ny+1)+ny-y
    fixed=[node(0,y,z) for z in range(nz+1) for y in range(ny+1)]
    load=[node(nx,y,z) for z in range(nz+1) for y in range(ny+1) if abs(y*h-30)<=h+1e-9 and abs(z*h-15)<=h+1e-9]
    solid=[z*nx*ny+x*ny+y for z in range(nz) for x in (0,nx-1) for y in range(ny)]
    return dict(schema='topoptlab-gh-request-v1',dimension=3,mode=mode,job_id='cantilever3d',
        domain=dict(nx=nx,ny=ny,nz=nz,cell=h,origin=[0,0,0],active=list(range(nx*ny*nz)),solid=solid),
        supports=[dict(nodes=fixed,fix_x=True,fix_y=True,fix_z=True)],
        loads=[dict(nodes=load,force=[0,0,-100])],settings=dict(young=210000,poisson=.3,volume=.35,iterations=iterations,radius=1.8))
