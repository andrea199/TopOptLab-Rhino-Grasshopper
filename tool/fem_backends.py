# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit verified CPU/GPU linear solvers. No silent CUDA fallback."""
import os, site, time
from pathlib import Path
import numpy as np
from scipy.sparse import bsr_matrix
from scipy.linalg import qr
from scipy.sparse.linalg import LinearOperator, cg, splu
_DEPS=Path(__file__).with_name('runtime_deps')
if _DEPS.is_dir():site.addsitedir(str(_DEPS))
_CUDA_ROOT=next((Path(p)/'nvidia/cu13' for p in [str(_DEPS)]+site.getsitepackages() if (Path(p)/'nvidia/cu13/include/cuda_runtime.h').exists()),None)
_DLL_HANDLES=[]
if _CUDA_ROOT is not None:
    os.environ['CUDA_PATH']=str(_CUDA_ROOT)
    if os.name=='nt':
        for directory in sorted({p.parent for p in _CUDA_ROOT.rglob('*.dll')}):
            _DLL_HANDLES.append(os.add_dll_directory(str(directory)))
            os.environ['PATH']=str(directory)+os.pathsep+os.environ.get('PATH','')
class Cancelled(RuntimeError):pass
class BlockAssembly:
    """Cache connectivity once and sum dense nodal stiffness blocks in bounded memory.

    A HEX8 needs 64 node-pair indices instead of 576 DOF pairs.  In particular,
    density updates never rebuild the two large COO row/column arrays.  Both
    shared Q4/HEX8 matrices and element-specific TET4 matrices are supported.
    """
    def __init__(self, model, check_cancel=lambda:None):
        check_cancel()
        self.model=model;self.check_cancel=check_cancel
        self.dim=model.nodes.shape[1]
        element_nodes=model.edof[:,::self.dim]//self.dim
        expected=(self.dim*element_nodes[:,:,None]+np.arange(self.dim)).reshape(model.edof.shape)
        if not np.array_equal(expected,model.edof):
            raise ValueError('Block assembly requires node-major displacement DOFs')
        self.width=element_nodes.shape[1];node_count=model.ndof//self.dim
        # Each pair is encoded in int64; unique() simultaneously builds a stable
        # scatter map.  These temporary keys are released before numeric assembly.
        keys=(element_nodes[:,:,None]*np.int64(node_count)+element_nodes[:,None,:]).ravel()
        unique,inverse=np.unique(keys,return_inverse=True)
        check_cancel()
        index_type=np.int32 if max(len(unique),node_count)<np.iinfo(np.int32).max else np.int64
        self.element_blocks=inverse.astype(index_type,copy=False)
        self.indices=(unique%node_count).astype(index_type)
        counts=np.bincount(unique//node_count,minlength=node_count)
        self.indptr=np.empty(node_count+1,dtype=index_type);self.indptr[0]=0
        np.cumsum(counts,out=self.indptr[1:])
        self.block_count=len(unique)
        self.memory_bytes=self.element_blocks.nbytes+self.indices.nbytes+self.indptr.nbytes

    def assemble(self,scale):
        self.check_cancel();m=self.model;dim=self.dim
        blocks=np.empty((self.block_count,dim,dim))
        # One scalar component at a time bounds temporaries to n * nodes**2.
        # bincount sums duplicate contributions deterministically in element order.
        for i in range(dim):
            for j in range(dim):
                self.check_cancel()
                local=m.KE[:,i::dim,j::dim] if m.KE.ndim==3 else m.KE[i::dim,j::dim]
                weights=(scale[:,None,None]*local).ravel()
                blocks[:,i,j]=np.bincount(self.element_blocks,weights=weights,minlength=self.block_count)
        return bsr_matrix((blocks,self.indices,self.indptr),shape=(m.ndof,m.ndof))


def elastic_candidates(model):
    """Orthonormal translations/rotations restricted to unconstrained DOFs.

    Supplying physical near-nullspace modes is essential for elasticity AMG;
    the scalar default constant vector omits bending and torsion modes.
    """
    nodes=model.nodes;dim=nodes.shape[1]
    center=nodes-nodes.mean(axis=0);span=np.ptp(nodes,axis=0).max()
    if not span>0:raise ValueError('Invalid spatial extent for elastic AMG')
    xyz=center/span
    modes=np.zeros((len(nodes),dim,3 if dim==2 else 6))
    modes[:,:,:dim]=np.eye(dim)
    if dim==2:
        modes[:,0,2]=-xyz[:,1];modes[:,1,2]=xyz[:,0]
    else:
        x,y,z=xyz.T
        modes[:,1,3]=-z;modes[:,2,3]=y
        modes[:,0,4]=z;modes[:,2,4]=-x
        modes[:,0,5]=-y;modes[:,1,5]=x
    restricted=modes.reshape(model.ndof,-1)[model.free]
    basis,r,_=qr(restricted,mode='economic',pivoting=True)
    diag=abs(np.diag(r));rank=np.count_nonzero(diag>diag.max()*1e-12)
    return np.ascontiguousarray(basis[:,:rank])


class ElasticSolver:
    def __init__(self,model,settings):
        self.model=model;self.backend=settings.get('backend','cpu-direct')
        if self.backend not in ('cpu-direct','cpu-cg','cpu-amg','cpu-matrixfree','cuda-cg'):raise ValueError('Unknown backend')
        self.rtol=float(settings.get('linear_tolerance',1e-9));self.maxiter=int(settings.get('linear_iterations',5000))
        self.threads=int(settings.get('threads',min(4,os.cpu_count() or 1)))
        if not 1e-12<=self.rtol<=1e-6 or not 1<=self.maxiter<=50000 or not 1<=self.threads<=(os.cpu_count() or 1):raise ValueError('Invalid solver tolerance, iterations or CPU threads')
        self.last_scale=None;self.guess={};self.cancel=lambda:False;self.setup_seconds=0;self.solve_seconds=0;self.preparations=0;self.assembly_pattern_builds=0
        try:from threadpoolctl import threadpool_limits
        except ImportError as exc:raise RuntimeError('Install threadpoolctl with setup_engineering.py') from exc
        self.limits=threadpool_limits
    def check_cancel(self):
        if self.cancel():raise Cancelled('Cancelled during linear solve')
    def prepare(self,scale):
        if self.last_scale is not None and np.array_equal(scale,self.last_scale):return
        self.check_cancel();t=time.perf_counter();m=self.model;n=m.ndof
        if self.backend=='cpu-matrixfree':
            ed=m.edof
            def matvec(v):
                self.check_cancel();out=np.zeros(n)
                for start in range(0,m.n,4096):
                    ids=ed[start:start+4096];local=(np.einsum("eij,ej->ei",m.KE[start:start+4096],v[ids]) if m.KE.ndim==3 else v[ids]@m.KE.T)*scale[start:start+4096,None]
                    out+=np.bincount(ids.ravel(),weights=local.ravel(),minlength=n)
                return out
            self.K=LinearOperator((n,n),matvec=matvec,dtype=float)
            diagonal=np.bincount(ed.ravel(),weights=(scale[:,None]*(np.diagonal(m.KE,axis1=1,axis2=2) if m.KE.ndim==3 else np.diag(m.KE))).ravel(),minlength=n)[m.free]
            def reduced(v):
                full=np.zeros(n);full[m.free]=v;return (self.K@full)[m.free]
            self.A=LinearOperator((len(m.free),len(m.free)),matvec=reduced,dtype=float)
        else:
            if not hasattr(self,'assembly'):
                self.assembly=BlockAssembly(m,self.check_cancel);self.assembly_pattern_builds+=1
            self.K=self.assembly.assemble(scale)
            full=self.K.tocsr();self.A=full[m.free][:,m.free].tocsr();del full
            diagonal=self.A.diagonal()
        if not np.isfinite(diagonal).all() or np.any(diagonal<=0):raise ValueError('Nonpositive stiffness diagonal')
        self.M=LinearOperator(self.A.shape,matvec=lambda v:v/diagonal,dtype=float)
        if self.backend=='cpu-direct':self.factor=splu(self.A.tocsc())
        elif self.backend=='cpu-amg':
            import pyamg
            self.M=pyamg.smoothed_aggregation_solver(self.A,B=elastic_candidates(m),symmetry='symmetric').aspreconditioner(cycle='V')
        elif self.backend=='cuda-cg':
            try:
                import cupy as cp
                from cupyx.scipy.sparse import csr_matrix
                from cupyx.scipy.sparse.linalg import LinearOperator as GPULinearOperator
                if cp.cuda.runtime.getDeviceCount()<1:raise RuntimeError('No CUDA device')
                self.cp=cp;self.gpu_A=csr_matrix(self.A);gd=cp.asarray(diagonal)
                self.gpu_M=GPULinearOperator(self.A.shape,matvec=lambda v:v/gd,dtype=cp.float64)
            except Exception as exc:raise RuntimeError('CUDA unavailable: '+str(exc)+'. Choose CPU or install CUDA dependencies.') from exc
        self.last_scale=scale.copy();self.setup_seconds+=time.perf_counter()-t;self.preparations+=1
    def solve(self,scale,force,cache_key=None):
        with self.limits(limits=self.threads):
            self.prepare(scale);self.check_cancel();t=time.perf_counter();b=np.asarray(force).ravel()[self.model.free];steps=[0]
            def callback(_):steps[0]+=1;self.check_cancel()
            # A stable, namespaced slot survives density-dependent forces. It only
            # selects an initial guess: the current RHS and residual remain exact.
            key=('rhs',b.tobytes()) if cache_key is None else ('slot',cache_key)
            x0=None if self.backend=='cpu-direct' else self.guess.get(key)
            initial_relative_residual=1.0
            if x0 is not None:
                initial_relative_residual=float(np.linalg.norm(self.A@x0-b)/np.linalg.norm(b))
                if not np.isfinite(initial_relative_residual) or initial_relative_residual>=1:
                    x0=None;initial_relative_residual=1.0
            warm_start=x0 is not None
            if self.backend=='cpu-direct':x=self.factor.solve(b);info=0
            elif self.backend=='cuda-cg':
                from cupyx.scipy.sparse.linalg import cg as gpu_cg
                cp=self.cp
                x,info=gpu_cg(self.gpu_A,cp.asarray(b),x0=None if x0 is None else cp.asarray(x0),rtol=self.rtol,atol=0,maxiter=self.maxiter,M=self.gpu_M,callback=callback)
                x=cp.asnumpy(x)
            else:x,info=cg(self.A,b,x0=x0,rtol=self.rtol,atol=0,maxiter=self.maxiter,M=self.M,callback=callback)
            self.check_cancel();self.solve_seconds+=time.perf_counter()-t;residual=float(np.linalg.norm(self.A@x-b)/np.linalg.norm(b))
            if info!=0 or not np.isfinite(x).all() or residual>max(5*self.rtol,1e-10):raise ValueError('Linear solve did not converge: %s, iterations=%s, residual=%.3g'%(self.backend,steps[0],residual))
            if key not in self.guess and len(self.guess)>=16:self.guess.pop(next(iter(self.guess)))
            self.guess.pop(key,None);self.guess[key]=x.copy();u=np.zeros(self.model.ndof);u[self.model.free]=x
            return u,self.K@u,dict(backend=self.backend,linear_iterations=steps[0],warm_start=warm_start,initial_relative_residual=initial_relative_residual,linear_residual=residual,setup_seconds=self.setup_seconds,solve_seconds=self.solve_seconds,matrix_preparations=self.preparations,assembly_pattern_builds=self.assembly_pattern_builds,assembly_pattern_bytes=getattr(getattr(self,'assembly',None),'memory_bytes',0),cpu_threads=self.threads)
def solve_model(model,rho,cache_key=None):
    from topoptlab.material_interpolation import simp,simp_dx
    rho=np.asarray(rho,float)
    if rho.shape!=(model.n,) or not np.isfinite(rho).all() or np.any((rho<0)|(rho>1)):raise ValueError('Invalid density')
    if not hasattr(model,'engine'):model.engine=ElasticSolver(model,model.request['settings'])
    scale=simp(rho,eps=1e-6,penal=model.penal);u,internal,stats=model.engine.solve(scale,model.forces,cache_key=cache_key)
    dim=model.nodes.shape[1];force=model.forces.ravel();reaction=internal-force
    residual=float(np.max(abs(reaction[model.free]))/model.force_scale);supported=np.zeros(model.ndof);supported[model.fixed]=reaction[model.fixed]
    total=(supported+force).reshape(-1,dim);center=model.nodes-model.nodes.mean(axis=0);span=max(np.ptp(model.nodes,axis=0))
    moment=np.cross(center,total).sum(axis=0) if dim==3 else np.sum(center[:,0]*total[:,1]-center[:,1]*total[:,0])
    balance=float(max(np.max(abs(total.sum(axis=0)))/model.force_scale,np.max(abs(moment))/(model.force_scale*span)))
    if max(residual,balance)>1e-5:raise ValueError('Force/moment balance failed after '+model.engine.backend)
    ue=u[model.edof];energy=np.einsum('ei,ij,ej->e',ue,model.KE,ue);compliance=float(force@u)
    if compliance<=0 or not np.isclose(compliance,scale@energy,rtol=1e-5):raise ValueError('Work/energy verification failed')
    gradient=np.asarray(model.filter.T@(-simp_dx(rho,eps=1e-6,penal=model.penal)*energy)[model.design]).ravel() if model.mode=='optimize' else None
    return dict(compliance=compliance,displacement=u.reshape(-1,dim),reactions=supported.reshape(-1,dim),gradient=gradient,residual=residual,balance=balance,performance=stats)
