# SPDX-License-Identifier: GPL-3.0-or-later
import copy
import json
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from worker import Model, run


def tension():
    nx, ny = 8, 4
    # Uniform traction: half nodal force at the two endpoints.
    right = nx*(ny+1)
    return dict(schema='topoptlab-gh-request-v1', mode='fem', job_id='fem-test',
        domain=dict(nx=nx, ny=ny, cell=1, origin=[0,0],
                    frame=[[0,0,0],[1,0,0],[0,1,0]], active=list(range(nx*ny)), solid=[]),
        supports=[dict(nodes=list(range(ny+1)), fix_x=True, fix_y=False),
                  dict(nodes=[ny], fix_x=False, fix_y=True)],
        loads=[dict(nodes=[right,right+ny], force=[100,0]),
               dict(nodes=list(range(right+1,right+ny)), force=[300,0])],
        settings=dict(young=200000, poisson=.3, thickness=2))


def test_uniform_traction_matches_analytic_solution(tmp_path):
    r=tension(); m=Model(r)
    result=run(r,tmp_path)
    # sigma = total force / cross-section = 400/(4*2) = 50.
    exact=np.column_stack((50/200000*m.nodes[:,0], -.3*50/200000*m.nodes[:,1]))
    assert np.allclose(np.array(result['displacement'])[:,:2], exact, atol=1e-12)
    assert np.allclose(result['stress_gauss'], [50,0,0], atol=1e-8)
    assert np.allclose(result['von_mises'], 50, atol=1e-8)
    assert np.allclose(np.sum(result['reactions'],axis=0), [-400,0,0], atol=1e-8)
    assert result['metrics']['equilibrium'] < 1e-10
    assert result['schema']=='topoptlab-gh-fem-result-v1'
    assert json.loads((tmp_path/'result.json').read_text())==result
    with pytest.raises(ValueError,match='fresh'): run(r,tmp_path)


def test_affine_patch_recovers_normal_and_shear_stress():
    m=Model(tension()); x,y=m.nodes.T
    strain=np.array([.001,-.0002,.0007])
    u=np.column_stack((strain[0]*x+strain[2]*y, strain[1]*y))
    stress,vm=m.stress(u)
    C=m.young/(1-m.nu*m.nu)*np.array([[1,m.nu,0],[m.nu,1,0],[0,0,(1-m.nu)/2]])
    expected=C@strain
    assert np.allclose(stress,expected)
    sx,sy,tau=expected
    assert np.allclose(vm,np.sqrt(sx*sx-sx*sy+sy*sy+3*tau*tau))


def test_gauss_energy_matches_upstream_element_stiffness():
    m=Model(tension())
    u=np.random.default_rng(84).normal(size=(len(m.nodes),2))
    stress,_=m.stress(u)
    sx,sy,tau=np.moveaxis(stress,-1,0)
    ex=(sx-m.nu*sy)/m.young; ey=(sy-m.nu*sx)/m.young
    gamma=2*(1+m.nu)*tau/m.young
    energy=np.sum(sx*ex+sy*ey+tau*gamma,axis=1)*m.h**2*m.thickness/4
    ue=u[m.faces].reshape(m.n,8)
    assert np.allclose(energy,np.einsum('ei,ij,ej->e',ue,m.KE,ue),rtol=1e-11)


def test_fem_ignores_keep_and_has_no_volume_budget():
    r=tension(); r['domain']['solid']=r['domain']['active'][:]
    m=Model(r)
    stress,_=m.stress(m.solve(np.ones(m.n))['displacement'])
    assert np.allclose(stress,[50,0,0],atol=1e-8)


def test_force_material_thickness_scaling():
    r=tension(); a=Model(r); ar=a.solve(np.ones(a.n)); sa,va=a.stress(ar['displacement'])
    r['settings']['young']*=3
    b=Model(r); br=b.solve(np.ones(b.n)); sb,vb=b.stress(br['displacement'])
    assert np.allclose(br['displacement'],ar['displacement']/3)
    assert np.allclose(vb,va)
    r['settings']['thickness']*=2
    c=Model(r); cr=c.solve(np.ones(c.n)); sc,vc=c.stress(cr['displacement'])
    assert np.allclose(vc,va/2)
    for load in r['loads']: load['force'][0]*=4
    d=Model(r); dr=d.solve(np.ones(d.n)); sd,vd=d.stress(dr['displacement'])
    assert np.allclose(vd,va*2)


def test_rotated_frame_transforms_displacement_and_reactions(tmp_path):
    r=tension(); r['domain']['frame']=[[10,20,30],[0,0,1],[0,1,0]]
    result=run(r,tmp_path)
    assert np.allclose(np.array(result['nodes'])[:,0],10)
    assert np.allclose(np.sum(result['reactions'],axis=0),[0,0,-400],atol=1e-8)
    assert np.allclose(result['von_mises'],50)


def test_fem_cancellation_after_solve(tmp_path,monkeypatch):
    original=Model.solve
    def cancel(self,rho):
        value=original(self,rho); (tmp_path/'cancel').touch(); return value
    monkeypatch.setattr(Model,'solve',cancel)
    assert run(tension(),tmp_path)['status']=='cancelled'
    assert not (tmp_path/'result.json').exists()


def test_fem_holes_are_still_absent():
    r=tension(); r['domain']['active'].remove(14)
    m=Model(r)
    assert m.n==31
    assert m.solve(np.ones(m.n))['balance'] < 1e-8


@pytest.mark.parametrize('key,value',[('young',0),('poisson',.5),('thickness',-1)])
def test_fem_rejects_invalid_material(key,value):
    r=tension(); r['settings'][key]=value
    with pytest.raises(ValueError): Model(r)
