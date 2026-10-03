import copy
import json
from pathlib import Path
import numpy as np
import pytest
from worker import Model, run
from worker3d import Model3D
from engineering_loads import prepare_cases, preserve_interfaces, solve_case
from engineering_materials import resolve
from engineering import constrain_design
from design_updates import project_budget


def rectangle(dim, mode='fem', scale=1):
    nx, ny, nz = 8*scale, 4*scale, 2*scale
    h = 1/scale
    d = dict(nx=nx, ny=ny, cell=h, origin=[0.]*dim, solid=[], active=list(range(nx*ny*(nz if dim==3 else 1))))
    if dim==3: d['nz']=nz
    else: d['frame']=[[0,0,0],[1,0,0],[0,1,0]]
    fixed=[z*(nx+1)*(ny+1)+y for z in range(nz+1 if dim==3 else 1) for y in range(ny+1)]
    support=dict(nodes=fixed,fix_x=True,fix_y=True)
    if dim==3:support['fix_z']=True
    faces=[dict(cell=z*nx*ny+(nx-1)*ny+y,axis=0,side=1) for z in range(nz if dim==3 else 1) for y in range(ny)]
    r=dict(schema='topoptlab-gh-request-v1',engineering=True,dimension=dim,mode=mode,job_id='distributed',domain=d,supports=[support],loads=[],
           material=dict(preset='steel',poisson=0,stock_thickness_mm=10),
           settings=dict(backend='cpu-direct',young=210000,poisson=0,thickness=2,volume=.6,iterations=8,radius=1.5))
    r['load_cases']=[dict(name='Pressure',weight=1,loads=[dict(kind='pressure',pressure=-2,faces=faces)])]
    return r


def model_cases(r):
    r=copy.deepcopy(r);preserve_interfaces(r)
    material=resolve(r['material']);r['settings'].update(young=material['young'],poisson=material['poisson'])
    m=(Model3D if r['dimension']==3 else Model)(r)
    return m,prepare_cases(m,r['load_cases'],material)


@pytest.mark.parametrize('dim',[2,3])
@pytest.mark.parametrize('scale',[1,2])
def test_surface_pressure_exact_tension_and_nodal_integration(dim,scale):
    r=rectangle(dim,scale=scale);m,c=model_cases(r);res=solve_case(m,c[0],np.ones(m.n))
    area=8 # 4*2 both the Q4 thickness and HEX8 cross section
    assert res['applied_forces'].sum(axis=0)==pytest.approx([2*area]+[0]*(dim-1))
    assert res['reactions'].sum(axis=0)==pytest.approx([-2*area]+[0]*(dim-1),abs=1e-10)
    assert res['displacement'][:,0]==pytest.approx(2*m.nodes[:,0]/210000,rel=1e-9,abs=1e-12)
    stress,vm=m.stress(res['displacement'])
    assert stress[:,:,0]==pytest.approx(np.full(stress.shape[:2],2),rel=1e-9)
    loaded=res['applied_forces'][:,0];loaded=loaded[loaded!=0]
    assert loaded.max()/loaded.min()==pytest.approx(4 if dim==3 else 2)
    assert res['balance']<1e-8


@pytest.mark.parametrize('dim',[2,3])
def test_traction_force_and_moment(dim):
    r=rectangle(dim);r['load_cases'][0]['loads'][0].update(kind='traction',traction=[0,-3] if dim==2 else [0,0,-3])
    m,c=model_cases(r);res=solve_case(m,c[0],np.ones(m.n));force=res['applied_forces']
    assert force.sum(axis=0)==pytest.approx([0,-24] if dim==2 else [0,0,-24])
    if dim==2:
        assert (m.nodes[:,0]*force[:,1]-m.nodes[:,1]*force[:,0]).sum()==pytest.approx(-192)
    else:assert np.cross(m.nodes,force).sum(axis=0)==pytest.approx([-48,192,0])


@pytest.mark.parametrize('dim',[2,3])
def test_gravity_mass_and_reactions_including_fixed_nodes(dim,tmp_path):
    r=rectangle(dim);g=[0,-9.80665] if dim==2 else [0,0,-9.80665]
    r['load_cases'][0]['loads']=[dict(kind='gravity',acceleration=g)]
    result=run(r,tmp_path/'gravity');case=result['engineering']['cases'][0]
    total=np.array(g)*result['engineering']['mass_kg']
    assert case['applied_force']==pytest.approx(total)
    assert case['reaction_force']==pytest.approx(-total,abs=1e-10)
    payload=json.loads((tmp_path/'gravity/case-01.json').read_text())
    assert np.asarray(payload['applied_forces']).sum(axis=0)==pytest.approx(list(total)+[0] if dim==2 else total)
    m,c=model_cases(r);res=solve_case(m,c[0],np.ones(m.n));f=res['applied_forces']
    if dim==2:assert (m.nodes[:,0]*f[:,1]).sum()==pytest.approx(4*total[1])
    else:assert np.cross(m.nodes,f).sum(axis=0)==pytest.approx(np.cross([4,2,1],total))


@pytest.mark.parametrize('dim',[2,3])
@pytest.mark.parametrize('manufacturing',[{}, {'symmetry':'y'}])
def test_gravity_gradient_with_filter_and_keep_matches_finite_difference(dim,manufacturing):
    r=rectangle(dim,'optimize');r['load_cases'][0]['loads'][0]['pressure']=-.002;g=[0,-98.0665] if dim==2 else [0,0,-98.0665]
    r['load_cases'][0]['loads'].append(dict(kind='gravity',acceleration=g))
    m,c=model_cases(r);constrain_design(m,manufacturing)
    x=m.initial()+.01*np.random.default_rng(41).normal(size=m.design.sum())
    v=np.random.default_rng(42).normal(size=len(x));v/=np.linalg.norm(v);eps=1e-5
    res=solve_case(m,c[0],m.density(x))
    numeric=(solve_case(m,c[0],m.density(x+eps*v))['compliance']-solve_case(m,c[0],m.density(x-eps*v))['compliance'])/(2*eps)
    assert res['gradient']@v==pytest.approx(numeric,rel=3e-5,abs=1e-10)


@pytest.mark.parametrize('dim',[2,3])
def test_pure_gravity_optimization_is_monotone_fixed_budget(dim,tmp_path):
    r=rectangle(dim,'optimize');g=[0,-9.80665] if dim==2 else [0,0,-9.80665]
    r['load_cases'][0]['loads']=[dict(kind='gravity',acceleration=g)]
    result=run(r,tmp_path/'optimization');e=result['engineering'];history=result['history']
    costs=np.array([h['compliance'] for h in history])
    assert len(costs)>2 and costs[-1]<costs[0]
    assert np.all(np.diff(costs)<=1e-13)
    assert [h['volume'] for h in history]==pytest.approx([.6]*len(history),abs=1e-9)
    assert e['cases'][0]['applied_force']==pytest.approx(np.array(g)*e['mass_kg'])
    assert 'projected' in e['optimization_update']
    assert np.isfinite(result['density']).all()


@pytest.mark.parametrize('dim',[2,3])
def test_units_pressure_gravity_and_thickness_are_consistent(dim,tmp_path):
    r=rectangle(dim);g=[0,-9.80665] if dim==2 else [0,0,-9.80665]
    r['load_cases'][0]['loads'].append(dict(kind='gravity',acceleration=g))
    a=run(r,tmp_path/'mm');r['domain']['cell']/=1000;r['settings']['thickness']/=1000
    r['material'].update(length_unit='m',force_unit='kN');r['load_cases'][0]['loads'][0]['pressure']*=1000
    b=run(r,tmp_path/'m')
    assert b['engineering']['mass_kg']==pytest.approx(a['engineering']['mass_kg'])
    assert np.asarray(b['displacement'])==pytest.approx(np.asarray(a['displacement'])/1000,rel=1e-7,abs=1e-13)
    assert b['engineering']['cases'][0]['applied_force']==pytest.approx(np.array(a['engineering']['cases'][0]['applied_force'])/1000)


@pytest.mark.parametrize('dim',[2,3])
def test_preserved_pressure_survives_optimization_and_verification(dim,tmp_path):
    r=rectangle(dim,'optimize');r['settings']['iterations']=2
    result=run(r,tmp_path/'opt');e=result['engineering'];faceids=[f['cell'] for f in r['load_cases'][0]['loads'][0]['faces']]
    assert e['automatically_preserved_interface_cells']==len(faceids)
    assert np.asarray(result['density'])[faceids]==pytest.approx(np.ones(len(faceids)))
    r.update(mode='verify',source_result=result,manufacturing={'threshold':.01})
    verified=run(r,tmp_path/'verify');assert verified['engineering']['cases'][0]['applied_force']==pytest.approx([16]+[0]*(dim-1))
    result['density'][faceids[0]]=0
    with pytest.raises(ValueError,match='loaded face was removed'):run(r,tmp_path/'removed')


@pytest.mark.parametrize('mutation,message',[
    ('duplicate','Duplicate face'),('internal','exposed boundary'),('zero','nonzero'),('unknown','Unknown load kind'),('axis','face axis')])
def test_invalid_surface_loads_rejected(mutation,message,tmp_path):
    r=rectangle(3);load=r['load_cases'][0]['loads'][0]
    if mutation=='duplicate':load['faces'].append(load['faces'][0])
    elif mutation=='internal':load['faces'][0]['side']=-1
    elif mutation=='zero':load['pressure']=0
    elif mutation=='axis':load['faces'][0]['axis']=3
    else:load['kind']='pressure_magic'
    with pytest.raises(ValueError,match=message):run(r,tmp_path/mutation)
    assert not (tmp_path/mutation/'result.json').exists()


def test_projection_accepts_positive_and_negative_derivatives():
    weights=np.array([1.,2.,3.]);x=project_budget(np.array([-3.,4.,.7]),weights,2.4,np.zeros(3),np.ones(3))
    assert weights@x==pytest.approx(2.4);assert np.all((x>=0)&(x<=1))
    with pytest.raises(ValueError,match='budget'):project_budget(x,weights,7,np.zeros(3),np.ones(3))


@pytest.mark.parametrize('dim',[2,3])
def test_axial_gravity_matches_exact_bar_nodal_solution(dim):
    r=rectangle(dim);g=9.80665;r['load_cases'][0]['loads']=[dict(kind='gravity',acceleration=[g]+[0]*(dim-1))]
    m,c=model_cases(r);res=solve_case(m,c[0],np.ones(m.n));b=7850*1e-9*g;x=m.nodes[:,0]
    assert res['displacement'][:,0]==pytest.approx(b*(8*x-x*x/2)/210000,rel=1e-8,abs=1e-15)
    assert res['applied_forces'].sum(axis=0)==pytest.approx([64*7850*1e-9*g]+[0]*(dim-1))


@pytest.mark.parametrize('dim',[2,3])
def test_low_density_self_weight_has_positive_exact_derivative(dim):
    r=rectangle(dim,'optimize');r['load_cases'][0]['loads']=[dict(kind='gravity',acceleration=[9.80665]+[0]*(dim-1))]
    m,c=model_cases(r);rho=.001;x=np.full(m.design.sum(),rho);res=solve_case(m,c[0],m.density(x))
    scale=1e-6+(1-1e-6)*rho**3;derivative=res['compliance']*(2/rho-3*(1-1e-6)*rho**2/scale)
    assert derivative>0
    assert res['gradient'].sum()==pytest.approx(derivative,rel=1e-8)


def test_distributed_example_archives_contain_idle_stages_and_typed_load_components():
    import xml.etree.ElementTree as ET
    for dim in (2,3):
        root=ET.parse(Path(__file__).resolve().parents[1]/'examples'/f'engineering_distributed_loads_{dim}d.ghx')
        names=[i.text for i in root.findall('.//chunk[@name="Object"]/items/item[@name="Name"]')]
        assert names.count('TopOpt Engineering')==3
        assert names.count('TopOpt Gravity')==1
        assert names.count('TopOpt Surface Load'+(' 3D' if dim==3 else ''))==1
        assert names.count('TopOpt Load Case')==2
        assert sum(i.text=='False' for i in root.iter('item') if i.get('name')=='ExpressionNormal')==9


@pytest.mark.parametrize('dim',[2,3])
def test_attachment_keep_preserves_support_interface_and_budget(dim,tmp_path):
    r=rectangle(dim,'optimize');r['settings'].update(preserve_attachments=True,iterations=2)
    preserved=copy.deepcopy(r);count=preserve_interfaces(preserved)
    d=r['domain'];expected=2*d['ny']*d.get('nz',1)
    assert count==expected
    source=run(r,tmp_path/'source');rho=np.asarray(source['density'])
    assert rho[preserved['domain']['solid']]==pytest.approx(np.ones(expected))
    assert rho.mean()==pytest.approx(.6,abs=1e-9)


@pytest.mark.parametrize('dim',[2,3])
@pytest.mark.parametrize('backend',['cpu-cg','cpu-matrixfree','cuda-cg'])
def test_distributed_load_backend_parity(dim,backend):
    if backend=='cuda-cg':pytest.importorskip('cupy')
    r=rectangle(dim);r['load_cases'][0]['loads'].append(dict(kind='gravity',acceleration=[9.80665]+[0]*(dim-1)))
    m,c=model_cases(r);a=solve_case(m,c[0],np.ones(m.n));r['settings']['backend']=backend
    m,c=model_cases(r);b=solve_case(m,c[0],np.ones(m.n))
    assert b['compliance']==pytest.approx(a['compliance'],rel=1e-8)
    assert b['reactions']==pytest.approx(a['reactions'],abs=1e-7)
