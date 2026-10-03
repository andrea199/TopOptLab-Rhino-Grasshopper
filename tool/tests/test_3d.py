# SPDX-License-Identifier: GPL-3.0-or-later
import copy,json
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from worker3d import Model3D
from worker import run
from sample3d import cantilever

def tension():
    nx,ny,nz=4,2,2
    def node(x,y,z):return z*(nx+1)*(ny+1)+x*(ny+1)+ny-y
    supports=[]
    for axis in range(3):
        ids=[node(x,y,z) for z in range(nz+1) for x in range(nx+1) for y in range(ny+1) if [x,y,z][axis]==0]
        supports.append(dict(nodes=ids,fix_x=axis==0,fix_y=axis==1,fix_z=axis==2))
    loads=[dict(nodes=[node(nx,y,z)],force=[(.5 if y in (0,ny) else 1)*(.5 if z in (0,nz) else 1),0,0]) for z in range(nz+1) for y in range(ny+1)]
    return dict(schema='topoptlab-gh-request-v1',dimension=3,mode='fem',job_id='tension3d',domain=dict(nx=nx,ny=ny,nz=nz,cell=1,origin=[0,0,0],active=list(range(nx*ny*nz)),solid=[]),supports=supports,loads=loads,settings=dict(young=1000,poisson=.3))

def test_3d_uniaxial_analytic(tmp_path):
    r=tension();m=Model3D(r);out=run(r,tmp_path)
    expected=m.nodes*np.array([.001,-.0003,-.0003])
    assert np.allclose(out['displacement'],expected,atol=1e-12)
    assert np.allclose(out['stress_gauss'],[1,0,0,0,0,0],atol=1e-10)
    assert np.allclose(out['von_mises'],1)
    assert np.allclose(np.sum(out['reactions'],axis=0),[-4,0,0],atol=1e-10)
    assert out['metrics']['equilibrium']<1e-10

def test_3d_affine_patch_and_rigid_motion():
    m=Model3D(tension());x,y,z=m.nodes.T
    u=np.column_stack((.001*x+.004*y+.005*z,.002*y+.006*z,.003*z))
    stress,_=m.stress(u);mu=m.young/(2*(1+m.nu));lam=m.young*m.nu/((1+m.nu)*(1-2*m.nu))
    expected=np.r_[lam*.006+2*mu*np.array([.001,.002,.003]),mu*np.array([.006,.005,.004])]
    assert np.allclose(stress,expected)
    rigid=np.cross([.02,.03,.04],m.nodes)+[1,2,3]
    assert np.max(abs(m.stress(rigid)[0]))<1e-9

def test_3d_gauss_energy_equals_upstream_stiffness():
    m=Model3D(tension());u=np.random.default_rng(3).normal(size=(len(m.nodes),3));stress,_=m.stress(u)
    normal=stress[:,:,:3];trace=normal.sum(axis=2,keepdims=True)
    strain=(1+m.nu)/m.young*normal-m.nu/m.young*trace
    shear=stress[:,:,3:]*2*(1+m.nu)/m.young
    energy=(np.sum(normal*strain,axis=2)+np.sum(stress[:,:,3:]*shear,axis=2)).sum(axis=1)*m.h**3/8
    ue=u[m.hexes].reshape(m.n,24)
    assert np.allclose(energy,np.einsum('ei,ij,ej->e',ue,m.KE,ue),rtol=1e-11)

def test_3d_gradients_budget_and_optimization(tmp_path):
    r=cantilever('optimize',8,4,2,8);m=Model3D(r);x=m.initial();v=np.random.default_rng(9).normal(size=len(x));v/=np.linalg.norm(v);eps=1e-5
    a=m.solve(m.density(x));plus=m.density(x+eps*v);minus=m.density(x-eps*v)
    assert (m.solve(plus)['compliance']-m.solve(minus)['compliance'])/(2*eps)==pytest.approx(a['gradient']@v,rel=1e-4)
    assert (plus.sum()-minus.sum())/(2*eps)==pytest.approx(m.dv@v,rel=1e-6)
    out=run(r,tmp_path);assert out['metrics']['improvement_percent']>0
    assert all(h['volume']<=.35+1e-10 for h in out['history'])
    assert np.all(np.array(out['density'])[m.keep]==1)
    assert out['metrics']['equilibrium']<1e-6

def test_3d_scaling_and_holes():
    r=tension();a=Model3D(r);ar=a.solve(np.ones(a.n));r['settings']['young']*=3;b=Model3D(r);br=b.solve(np.ones(b.n))
    assert np.allclose(br['displacement'],ar['displacement']/3)
    assert np.allclose(a.stress(ar['displacement'])[1],b.stress(br['displacement'])[1])
    r=cantilever('fem',8,4,2);r['domain']['active'].remove(13);m=Model3D(r);assert m.n==63;assert m.solve(np.ones(m.n))['balance']<1e-7

@pytest.mark.parametrize('kind',['rigid','disconnected','force','limit'])
def test_3d_invalid(kind):
    r=tension()
    if kind=='rigid':r['supports']=r['supports'][:1]
    elif kind=='disconnected':r['domain']['active']=[0,15]
    elif kind=='force':r['loads']=[dict(nodes=[2],force=[1,0,0])]
    else:r['domain'].update(nx=200,ny=200,nz=200)
    with pytest.raises(ValueError):Model3D(r)

def test_3d_cancel_after_fem(tmp_path,monkeypatch):
    original=Model3D.solve
    def cancel(self,rho):
        response=original(self,rho);(tmp_path/'cancel').touch();return response
    monkeypatch.setattr(Model3D,'solve',cancel)
    assert run(tension(),tmp_path)['status']=='cancelled'
    assert not (tmp_path/'result.json').exists()


@pytest.mark.parametrize('prefix',['fem','opt'])
def test_3d_archives(prefix):
    import xml.etree.ElementTree as ET
    root=ET.parse(Path(__file__).resolve().parents[1]/'examples'/f'{prefix}_cantilever_3d.ghx')
    ids=[i.text for i in root.iter('item') if i.get('name')=='InstanceGuid']
    assert len(ids)==len(set(ids))
    assert set(i.text for i in root.iter('item') if i.get('name')=='Source')<=set(ids)
    assert len([i for i in root.iter('item') if i.get('name')=='ExpressionNormal' and i.text=='False'])==(3 if prefix=='fem' else 4)
    assert root.find("./chunks/chunk[@name='Definition']/chunks/chunk[@name='DefinitionProperties']/items/item[@name='Date']") is not None


def test_3d_pure_torque_equilibrium():
    r=cantilever('fem',8,4,2)
    nx,ny,nz=8,4,2
    def node(x,y,z):return z*(nx+1)*(ny+1)+x*(ny+1)+ny-y
    r['loads']=[dict(nodes=[node(nx,0,1)],force=[0,0,-10]),dict(nodes=[node(nx,ny,1)],force=[0,0,10])]
    m=Model3D(r);response=m.solve(np.ones(m.n))
    assert np.allclose(response['reactions'].sum(axis=0),0,atol=1e-8)
    assert np.allclose(np.cross(m.nodes,response['reactions']).sum(axis=0),[-600,0,0],atol=1e-7)


def test_3d_bending_refines_toward_beam_solution():
    # Slender square cantilever, nu=0, end shear. HEX8 discretization should
    # approach Euler-Bernoulli compliance from below as bending is resolved.
    def case(nx,ny,nz):
        h=12/nx
        def node(x,y,z):return z*(nx+1)*(ny+1)+x*(ny+1)+ny-y
        return dict(schema='topoptlab-gh-request-v1',dimension=3,mode='fem',job_id='bend',domain=dict(nx=nx,ny=ny,nz=nz,cell=h,origin=[0,0,0],active=list(range(nx*ny*nz)),solid=[]),supports=[dict(nodes=[node(0,y,z) for y in range(ny+1) for z in range(nz+1)],fix_x=True,fix_y=True,fix_z=True)],loads=[dict(nodes=[node(nx,y,z) for y in range(ny+1) for z in range(nz+1)],force=[0,0,-1])],settings=dict(young=1000,poisson=0))
    values=[]
    for dims in [(12,1,1),(24,2,2)]:
        m=Model3D(case(*dims));values.append(m.solve(np.ones(m.n))['compliance'])
    reference=12**3/(3*1000*(1/12))
    assert abs(values[1]-reference)<abs(values[0]-reference)
    assert values[1]==pytest.approx(reference,rel=.15)


def test_3d_filter_bound_roundoff():
    m=Model3D(cantilever('optimize'))
    rho=m.density(np.ones(int(m.design.sum())))
    assert np.max(rho)<=1
    assert np.allclose(rho,1)
    with pytest.raises(ValueError):m.density(np.full(int(m.design.sum()),1.01))
