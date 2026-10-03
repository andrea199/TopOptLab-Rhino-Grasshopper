# SPDX-License-Identifier: GPL-3.0-or-later
"""First 3D voxel implementation. World XYZ, HEX8, solid FEM or SIMP.
Node ordering z,x,y-descending is shared with Domain3D and upstream HEX8.
"""
import numpy as np
import warnings
from scipy.ndimage import label
from scipy.sparse import diags
from scipy.sparse.linalg import MatrixRankWarning
from topoptlab.elements.trilinear_hexahedron import create_edofMat,bmatrix_cuboid
from topoptlab.elements.linear_elasticity_3d import _lk_linear_elast_3d
from topoptlab.fem import create_matrixinds,assemble_matrix,apply_bc
from topoptlab.filter.matrix_filter import assemble_matrix_filter
from topoptlab.material_interpolation import simp,simp_dx
from topoptlab.solve_linsystem import solve_lin
from worker import Model,number,integer,indices
from resource_budget import grid_resources, MAX_GRID_AXIS
from grid_filter import GridDensityFilter

class Model3D(Model):
    def __init__(self,request):
        if request.get('schema')!='topoptlab-gh-request-v1' or request.get('dimension')!=3:
            raise ValueError('Expected a 3D request')
        self.request=request;self.mode=request.get('mode','optimize')
        if self.mode not in ('fem','optimize'):raise ValueError('Unknown analysis mode')
        d,s=request['domain'],request['settings']
        self.resource_estimate=grid_resources(request)
        nx,ny,nz=[integer(d[k],k,1,MAX_GRID_AXIS) for k in ('nx','ny','nz')]
        h=number(d['cell'],'cell size',1e-9,1e9);self.h=h
        origin=np.asarray(d['origin'],float)
        if origin.shape!=(3,) or not np.isfinite(origin).all():raise ValueError('Invalid 3D origin')
        self.active=indices(d['active'],'active voxels',nx*ny*nz)
        solid=indices(d.get('solid',[]),'Keep voxels',nx*ny*nz,True)
        if not np.isin(solid,self.active).all():raise ValueError('Keep outside active domain')
        mask=np.zeros(nx*ny*nz,bool);mask[self.active]=True
        if label(mask.reshape(nz,nx,ny))[1]!=1:raise ValueError('Disconnected voxel domain')
        self.n=len(self.active);self.keep=np.isin(self.active,solid);self.design=~self.keep
        self.young=number(s.get('young',1),'Young modulus',1e-12,1e15)
        self.nu=number(s.get('poisson',.3),'Poisson ratio',0,.49)
        self.penal=number(s.get('penal',3),'SIMP exponent',1,5)
        zz,xx,yy=np.meshgrid(origin[2]+np.arange(nz+1)*h,origin[0]+np.arange(nx+1)*h,
                             origin[1]+np.arange(ny,-1,-1)*h,indexing='ij')
        full=np.column_stack((xx.ravel(),yy.ravel(),zz.ravel()))
        edof,*_=create_edofMat(nx,ny,nz,nnode_dof=3)
        fullhex=edof[self.active,::3]//3
        self.grid_node_ids=np.unique(fullhex)
        remap=np.full(len(full),-1,int);remap[self.grid_node_ids]=np.arange(len(self.grid_node_ids))
        self.nodes=full[self.grid_node_ids];self.hexes=remap[fullhex]
        self.edof=(3*self.hexes[:,:,None]+np.arange(3)).reshape(self.n,24)
        self.ndof=3*len(self.nodes)
        if not s.get('backend'):self.iK,self.jK=create_matrixinds(self.edof)
        # Numerical upstream HEX8 integration matches B-matrix stress recovery.
        # The bundled closed-form matrix differs for non-affine displacement fields.
        self.KE=_lk_linear_elast_3d(self.nodes[self.hexes[0]],self.constitutive())[0]
        if self.mode=='optimize':
            if not self.design.any():raise ValueError('No variable voxels remain')
            self.target=number(s['volume'],'volume fraction',.05,.95)
            self.design_budget=self.target*self.n-self.keep.sum()
            if self.design_budget<=1e-6:raise ValueError('Keep consumes material budget')
            self.iterations=integer(s['iterations'],'iterations',1,300)
            physical_radius=number(s.get('radius_length',0),'physical filter radius',0,1e9)
            self.radius=number(physical_radius/h if physical_radius else s['radius'],'filter radius in cells',1,64)
            variable=self.active[self.design]
            self.filter=GridDensityFilter((nz,nx,ny),variable,self.radius)
            self.dv=np.asarray(self.filter.T@np.ones(len(variable))).ravel()
        def mapped(group):
            ids=indices(group['nodes'],'selected nodes',len(full))
            if np.any(remap[ids]<0):raise ValueError('Selection contains inactive nodes')
            return remap[ids]
        fixed=[]
        for group in request['supports']:
            ids=mapped(group);flags=[group[k] for k in ('fix_x','fix_y','fix_z')]
            if not all(isinstance(v,bool) for v in flags) or not any(flags):raise ValueError('Select at least one boolean support direction')
            for axis,flag in enumerate(flags):
                if flag:fixed.extend(3*ids+axis)
        self.fixed=np.unique(fixed).astype(int);self.free=np.setdiff1d(np.arange(self.ndof),self.fixed)
        if not self.free.size:raise ValueError('All DOFs constrained')
        xyz=(self.nodes-self.nodes.mean(axis=0))/max(np.ptp(self.nodes,axis=0))
        rigid=np.zeros((len(self.nodes),3,6));rigid[:,:,:3]=np.eye(3)
        x,y,z=xyz.T
        rigid[:,1,3]=-z;rigid[:,2,3]=y;rigid[:,0,4]=z;rigid[:,2,4]=-x;rigid[:,0,5]=-y;rigid[:,1,5]=x
        if len(self.fixed)<6 or np.linalg.matrix_rank(rigid.reshape(-1,6)[self.fixed])<6:raise ValueError('Supports permit rigid 3D translation or rotation')
        self.forces=np.zeros((self.ndof,1))
        for group in request['loads']:
            ids=mapped(group);force=np.asarray(group['force'],float)
            if force.shape!=(3,) or not np.isfinite(force).all() or np.linalg.norm(force)==0:raise ValueError('Invalid 3D force')
            for axis in range(3):
                dofs=3*ids+axis
                if force[axis]!=0 and np.isin(dofs,self.fixed).any():raise ValueError('Force acts in a constrained direction')
                self.forces[dofs,0]+=force[axis]/len(ids)
        self.force_scale=float(np.max(abs(self.forces)))
        if not self.force_scale and not request.get('engineering'):raise ValueError('Apply a nonzero total force')

    def density(self,x):
        rho=super().density(x)
        # Normalized filter sums may exceed one by a few floating-point ulps.
        if np.any((rho < -1e-12) | (rho > 1+1e-12)):
            raise ValueError('Filtered density outside physical bounds')
        return np.clip(rho,0,1)

    def solve(self,rho):
        if self.request['settings'].get('backend'):
            from fem_backends import solve_model
            return solve_model(self,rho)
        rho=np.asarray(rho)
        if rho.shape!=(self.n,) or not np.isfinite(rho).all() or np.any((rho<0)|(rho>1)):raise ValueError('Invalid density')
        scale=simp(rho,eps=1e-6,penal=self.penal)
        K=assemble_matrix((scale[:,None,None]*self.KE).ravel(),self.iK,self.jK,ndof=self.ndof,solver='scipy-direct',springs=None)
        reduced=apply_bc(K,solver='scipy-direct',free=self.free,fixed=self.fixed)
        u=np.zeros_like(self.forces)
        with warnings.catch_warnings():
            warnings.simplefilter('error',MatrixRankWarning)
            u[self.free],_,_=solve_lin(reduced,self.forces[self.free],solver='scipy-direct')
        if not np.isfinite(u).all():raise ValueError('Singular 3D system')
        reactions=K@u-self.forces;residual=float(np.max(abs(reactions[self.free]))/self.force_scale)
        supported=np.zeros_like(reactions);supported[self.fixed]=reactions[self.fixed]
        total=(supported+self.forces).reshape(-1,3);center=self.nodes-self.nodes.mean(axis=0)
        moment=np.cross(center,total).sum(axis=0);span=max(np.ptp(self.nodes,axis=0))
        balance=float(max(np.max(abs(total.sum(axis=0)))/self.force_scale,np.max(abs(moment))/(self.force_scale*span)))
        if max(balance,residual)>1e-5:raise ValueError('3D force/moment balance failed')
        ue=u[self.edof,0];energy=np.einsum('ei,ij,ej->e',ue,self.KE,ue)
        compliance=float(np.sum(self.forces*u))
        if compliance<=0 or not np.isclose(compliance,scale@energy,rtol=1e-5):raise ValueError('3D energy verification failed')
        gradient=np.asarray(self.filter.T@(-simp_dx(rho,eps=1e-6,penal=self.penal)*energy)[self.design]).ravel() if self.mode=='optimize' else None
        return dict(compliance=compliance,displacement=u.reshape(-1,3),reactions=supported.reshape(-1,3),gradient=gradient,residual=residual,balance=balance)

    def constitutive(self):
        mu=self.young/(2*(1+self.nu));lam=self.young*self.nu/((1+self.nu)*(1-2*self.nu))
        C=np.zeros((6,6));C[:3,:3]=lam;C[:3,:3]+=2*mu*np.eye(3);C[3:,3:]=mu*np.eye(3)
        return C

    def stress(self,u):
        from itertools import product
        q=np.array(list(product([-1/np.sqrt(3),1/np.sqrt(3)],repeat=3)))
        B=bmatrix_cuboid(q[:,0],q[:,1],q[:,2],self.h,self.h,self.h)
        strain=np.einsum('qij,ej->eqi',B,np.asarray(u)[self.hexes].reshape(self.n,24))
        C=self.constitutive()
        stress=np.einsum('ij,eqj->eqi',C,strain)
        x,y,z,yz,xz,xy=np.moveaxis(stress,-1,0)
        vm=np.sqrt(np.maximum(0,.5*((x-y)**2+(y-z)**2+(z-x)**2)+3*(xy**2+xz**2+yz**2)))
        return stress,vm

    def common(self,response,job_id):
        return dict(schema='topoptlab-gh-3d-result-v1',dimension=3,mode=self.mode,job_id=job_id,
                    nodes=self.nodes.tolist(),hexes=self.hexes.tolist(),cell_ids=self.active.tolist(),
                    displacement=response['displacement'].tolist(),kept=self.keep.tolist(),
                    grid_node_ids=self.grid_node_ids.tolist(),cell_size=self.h,
                    material=dict(young=self.young,poisson=self.nu),
                    metrics=dict(compliance=response['compliance'],max_displacement=float(np.linalg.norm(response['displacement'],axis=1).max()),residual=response['residual'],equilibrium=response['balance']))
    def fem_payload(self,response,job_id):
        data=self.common(response,job_id);stress,vm=self.stress(response['displacement'])
        data.update(status='completed',density=np.ones(self.n).tolist(),reactions=response['reactions'].tolist(),
                    von_mises=vm.max(axis=1).tolist(),stress_order=['xx','yy','zz','yz','xz','xy'])
        if not self.resource_estimate['compact_results']:
            data.update(stress_gauss=stress.tolist(),stress_mean=stress.mean(axis=1).tolist())
        else:
            data['stress_storage']='gauss_npz_in_case_folder'
        data['resources']=self.resource_estimate
        data['metrics']['max_von_mises']=float(vm.max())
        return data
    def save_stress(self,response,path):
        stress,vm=self.stress(response['displacement'])
        np.savez_compressed(path,stress_gauss=stress,stress_mean=stress.mean(axis=1),von_mises_gauss=vm,cell_ids=self.active)

    def payload(self,rho,response,iteration,baseline,status,history,job_id):
        data=self.common(response,job_id)
        data.update(status=status,density=rho.tolist(),iteration=iteration,completed_iterations=len(history)-1,history=history)
        data['metrics'].update(initial_compliance=baseline,improvement_percent=100*(1-response['compliance']/baseline),volume=float(rho.mean()),target_volume=self.target)
        return data
