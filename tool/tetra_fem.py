# SPDX-License-Identifier: GPL-3.0-or-later
"""Conforming linear TET4 elasticity with explicit force/moment/energy checks."""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from fem_backends import ElasticSolver

def constitutive(young,nu):
    mu=young/(2*(1+nu));lam=young*nu/((1+nu)*(1-2*nu))
    C=np.zeros((6,6));C[:3,:3]=lam;C[:3,:3]+=2*mu*np.eye(3);C[3:,3:]=mu*np.eye(3);return C

def rigid_modes(nodes):
    xyz=(nodes-nodes.mean(axis=0))/np.ptp(nodes,axis=0).max();r=np.zeros((len(nodes),3,6));r[:,:,:3]=np.eye(3);x,y,z=xyz.T
    r[:,1,3]=-z;r[:,2,3]=y;r[:,0,4]=z;r[:,2,4]=-x;r[:,0,5]=-y;r[:,1,5]=x;return r.reshape(-1,6)

def boundary(nodes,tets):
    faces={};adj=[]
    for e,tet in enumerate(tets):
        for opposite in range(4):
            f=np.delete(tet,opposite);p=nodes[f]
            if np.dot(np.cross(p[1]-p[0],p[2]-p[0]),nodes[tet[opposite]]-p[0])>0:f=f[::-1]
            key=tuple(sorted(f))
            if key in faces:
                other,_,count=faces[key]
                if count!=1:raise ValueError('Nonmanifold tetrahedral mesh')
                adj.append((other,e));faces[key]=(other,f,2)
            else:faces[key]=(e,f,1)
    if len(tets)>1:
        if not adj:raise ValueError('Disconnected tetrahedral mesh')
        rows,cols=np.array(adj).T;graph=coo_matrix((np.ones(len(adj)),(rows,cols)),shape=(len(tets),len(tets)))
        if connected_components(graph,directed=False,return_labels=False)!=1:raise ValueError('Disconnected tetrahedral mesh')
    items=[(e,f) for e,f,count in faces.values() if count==1]
    return np.array([f for e,f in items],int),np.array([e for e,f in items],int)

class TetraModel:
    def __init__(self,nodes,tets,material,settings):
        self.nodes=np.asarray(nodes,float);self.tets=np.asarray(tets,int).copy()
        if self.nodes.ndim!=2 or self.nodes.shape[1]!=3 or not np.isfinite(self.nodes).all() or self.tets.ndim!=2 or self.tets.shape[1]!=4 or not self.tets.size or self.tets.min()<0 or self.tets.max()>=len(nodes):raise ValueError('Invalid tetrahedral mesh')
        self.n=len(tets);self.ndof=3*len(nodes);self.material=material
        delta=self.nodes[self.tets[:,1:]]-self.nodes[self.tets[:,:1]];det=np.linalg.det(delta)
        span=np.ptp(self.nodes,axis=0).max()
        if np.any(abs(det)<span**3*1e-14):raise ValueError('Degenerate tetrahedron')
        bad=det<0;self.tets[bad,1:3]=self.tets[bad,1:3][:,::-1]
        delta=self.nodes[self.tets[:,1:]]-self.nodes[self.tets[:,:1]];self.volumes=np.linalg.det(delta)/6
        g=np.zeros((self.n,4,3));g[:,1:]=np.linalg.inv(delta).transpose(0,2,1);g[:,0]=-g[:,1:].sum(axis=1)
        B=np.zeros((self.n,6,12));B[:,0,0::3]=g[:,:,0];B[:,1,1::3]=g[:,:,1];B[:,2,2::3]=g[:,:,2]
        B[:,3,1::3]=g[:,:,2];B[:,3,2::3]=g[:,:,1];B[:,4,0::3]=g[:,:,2];B[:,4,2::3]=g[:,:,0];B[:,5,0::3]=g[:,:,1];B[:,5,1::3]=g[:,:,0]
        self.B=B;self.C=constitutive(material['young'],material['poisson']);self.KE=np.einsum('eji,jk,ekl,e->eil',B,self.C,B,self.volumes)
        self.edof=(3*self.tets[:,:,None]+np.arange(3)).reshape(self.n,12)
        self.triangles,self.owners=boundary(self.nodes,self.tets)
        edge2=sum(np.sum((self.nodes[self.tets[:,i]]-self.nodes[self.tets[:,j]])**2,axis=1) for i in range(4) for j in range(i))
        self.quality=12*(3*self.volumes)**(2/3)/edge2
        if self.quality.min()<1e-4:raise ValueError('Very poor tetrahedral quality; remesh before solving')
        self.settings=settings;self.engine=None
    def supports(self,fixed,cancel=lambda:None):
        self.fixed=np.unique(fixed).astype(int);self.free=np.setdiff1d(np.arange(self.ndof),self.fixed)
        if not len(self.free) or len(self.fixed)<6 or np.linalg.matrix_rank(rigid_modes(self.nodes)[self.fixed])<6:raise ValueError('Final supports do not restrain all rigid modes')
        self.engine=ElasticSolver(self,self.settings);self.engine.cancel=cancel
    def solve(self,force):
        f=np.asarray(force,float).ravel()
        if f.shape!=(self.ndof,) or not np.isfinite(f).all() or not np.any(f[self.free]):raise ValueError('No finite nonzero free load remains')
        u,internal,stats=self.engine.solve(np.ones(self.n),f);reaction=internal-f;reactions=np.zeros(self.ndof);reactions[self.fixed]=reaction[self.fixed]
        force_scale=max(np.linalg.norm(f.reshape(-1,3),axis=1).sum(),1e-30);center=self.nodes-self.nodes.mean(axis=0);span=np.ptp(self.nodes,axis=0).max()
        total=(reactions+f).reshape(-1,3);balance=max(np.linalg.norm(total.sum(axis=0)),np.linalg.norm(np.cross(center,total).sum(axis=0))/span)/force_scale
        residual=np.linalg.norm(reaction[self.free])/max(np.linalg.norm(f[self.free]),1e-30)
        compliance=float(f@u);energy=float(np.einsum('ei,eij,ej->',u[self.edof],self.KE,u[self.edof]))
        if max(balance,residual)>1e-5 or compliance<=0 or not np.isclose(compliance,energy,rtol=1e-6):raise ValueError('Final tetrahedral force/moment/energy check failed')
        strain=np.einsum('eij,ej->ei',self.B,u[self.edof]);stress=strain@self.C.T;x,y,z,yz,xz,xy=stress.T
        vm=np.sqrt(np.maximum(0,.5*((x-y)**2+(y-z)**2+(z-x)**2)+3*(xy**2+xz**2+yz**2)))
        return dict(displacement=u.reshape(-1,3),reactions=reactions.reshape(-1,3),stress=stress,von_mises=vm,compliance=compliance,max_displacement=float(np.linalg.norm(u.reshape(-1,3),axis=1).max()),max_von_mises=float(vm.max()),residual=float(residual),equilibrium=float(balance),performance=stats)
