import copy,sys,json
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from worker import Model,run
from worker3d import Model3D
from sample3d import cantilever
from sample_problem import example
from engineering import case_forces,constrain_design,signature
from engineering_materials import resolve
from fem_backends import ElasticSolver,Cancelled

def project(dim=3,mode='fem'):
    r=cantilever(mode,8,4,2,12) if dim==3 else example(12,6,12)
    r.update(mode=mode,dimension=dim,engineering=True,material={'preset':'steel','stock_thickness_mm':10})
    r['load_cases']=[dict(name='Down',weight=1,loads=r['loads'])]
    r['settings']['backend']='cpu-cg'
    return r

@pytest.mark.parametrize('dim',[2,3])
@pytest.mark.parametrize('backend',['cpu-direct','cpu-cg','cpu-amg','cpu-matrixfree','cuda-cg'])
def test_backend_matches_legacy(dim,backend):
    if backend=='cuda-cg':pytest.importorskip('cupy',reason='Optional CUDA package not installed')
    r=cantilever('fem',8,4,2) if dim==3 else example(12,6)
    r['mode']='fem';cls=Model3D if dim==3 else Model
    old=cls(r);expected=old.solve(np.ones(old.n));r['settings']['backend']=backend
    m=cls(r);actual=m.solve(np.ones(m.n))
    assert actual['compliance']==pytest.approx(expected['compliance'],rel=1e-7)
    assert np.allclose(actual['displacement'],expected['displacement'],rtol=1e-6,atol=1e-9)
    assert actual['balance']<1e-5

def test_explicit_units_and_material_sources():
    mm=resolve({'preset':'steel','stock_thickness_mm':12});meter=resolve({'preset':'steel','length_unit':'m','force_unit':'kN'})
    assert mm['young']==210000
    assert meter['young']==210000000
    assert mm['allowable']==pytest.approx(235/1.5)
    assert resolve({'preset':'steel','stock_thickness_mm':30})['allowable'] is None
    assert resolve({'preset':'abs'})['density_kg_m3']==1040
    assert 'assumption' in ' '.join(resolve({'preset':'abs'})['notes'])
    with pytest.raises(ValueError):resolve({'length_unit':'in'})

def test_independent_opposite_cases_do_not_cancel(tmp_path):
    r=project();one=run(r,tmp_path/'one')
    other=copy.deepcopy(r['load_cases'][0]);other['name']='Up';other['loads'][0]['force']=[0,0,100];r['load_cases'].append(other)
    two=run(r,tmp_path/'two');e=two['engineering']
    assert two['metrics']['compliance']==pytest.approx(2*one['metrics']['compliance'],rel=1e-7)
    assert len(e['cases'])==2
    assert e['cases'][-1]['performance']['matrix_preparations']==1
    assert e['mass_kg']==pytest.approx(120*60*30*1e-9*7850)
    assert (tmp_path/'two/report.html').exists()
    assert (tmp_path/'two/case-02.json').exists()

def test_convergence_and_iteration_limit_are_distinct(tmp_path):
    r=project(mode='optimize');r['settings'].update(iterations=2)
    a=run(r,tmp_path/'limited');assert a['engineering']['termination_reason']=='iteration_limit'
    r['settings'].update(iterations=80,minimum_iterations=1,convergence_window=2,objective_tolerance=.1,design_tolerance=.2)
    b=run(r,tmp_path/'converged');assert b['engineering']['termination_reason']=='converged'
    assert b['completed_iterations']<80

def test_project_reanalysis_and_changed_input_rejection(tmp_path):
    r=project(mode='optimize');r['settings'].update(volume=.8,iterations=1)
    source=run(r,tmp_path/'source');v=copy.deepcopy(r);v.update(mode='verify',source_result=source,manufacturing={'threshold':.01})
    result=run(v,tmp_path/'verify')
    assert result['engineering']['termination_reason']=='voxel_reanalysis_completed'
    assert result['engineering']['cases'][0]['max_von_mises']>0
    v['material']['preset']='abs'
    with pytest.raises(ValueError,match='changed'):run(v,tmp_path/'changed')

def test_threshold_disconnection_rejected(tmp_path):
    r=project(mode='optimize');r['settings'].update(iterations=1)
    source=run(r,tmp_path/'source');nx,ny=r['domain']['nx'],r['domain']['ny']
    source['density']=[0 if (i//ny)%nx==nx//2 else 1 for i in r['domain']['active']]
    r.update(mode='verify',source_result=source)
    with pytest.raises(ValueError,match='Disconnected'):run(r,tmp_path/'broken')

@pytest.mark.parametrize('constraint',[{'symmetry':'y'},{'extrusion':'z'}])
def test_manufacturing_projected_gradient(constraint):
    r=project(mode='optimize');m=Model3D(r);constrain_design(m,constraint)
    x=m.initial();v=np.random.default_rng(9).normal(size=len(x));v/=np.linalg.norm(v);eps=1e-5
    response=m.solve(m.density(x));num=(m.solve(m.density(x+eps*v))['compliance']-m.solve(m.density(x-eps*v))['compliance'])/(2*eps)
    assert num==pytest.approx(response['gradient']@v,rel=1e-4)
    rho=m.density(x+.01*v).reshape(2,8,4)
    if 'symmetry' in constraint:assert np.allclose(rho,rho[:,:,::-1])
    else:assert np.allclose(rho[0],rho[1])

def test_cancel_inside_iterative_solver():
    r=project();m=Model3D(r);m.engine=ElasticSolver(m,r['settings']);m.engine.cancel=lambda:True
    with pytest.raises(Cancelled):m.solve(np.ones(m.n))

def test_linear_nonconvergence_is_error():
    r=project();r['settings']['linear_iterations']=1;m=Model3D(r)
    with pytest.raises(ValueError,match='did not converge'):m.solve(np.ones(m.n))

def test_cancel_has_no_final_result(tmp_path):
    (tmp_path/'cancel').touch();data=run(project(),tmp_path)
    assert data['status']=='cancelled';assert not (tmp_path/'result.json').exists()

def test_no_implicit_backend_fallback():
    r=project();r['settings']['backend']='automatic_magic'
    with pytest.raises(ValueError,match='Unknown backend'):Model3D(r)


def test_unit_conversion_preserves_physical_response(tmp_path):
    mm=project();a=run(mm,tmp_path/'mm')
    metre=copy.deepcopy(mm);metre['domain']['cell']/=1000;metre['domain']['origin']=[x/1000 for x in metre['domain']['origin']]
    metre['material'].update(length_unit='m',force_unit='kN')
    for case in metre['load_cases']:
        for load in case['loads']:load['force']=[f/1000 for f in load['force']]
    b=run(metre,tmp_path/'metre')
    assert b['engineering']['mass_kg']==pytest.approx(a['engineering']['mass_kg'])
    assert np.asarray(b['displacement'])==pytest.approx(np.asarray(a['displacement'])/1000,rel=1e-6,abs=1e-12)
    assert b['metrics']['max_von_mises']==pytest.approx(a['metrics']['max_von_mises']*1000,rel=1e-7)

def test_engineering_graphs_have_three_idle_stages():
    import xml.etree.ElementTree as ET
    for dim in (2,3):
        root=ET.parse(Path(__file__).resolve().parents[1]/'examples'/f'engineering_workflow_{dim}d.ghx')
        containers=root.findall('.//chunk[@name="Object"]/chunks/chunk[@name="Container"]')
        stages=[c for c in containers if c.find('./items/item[@name="Name"]').text=='TopOpt Engineering']
        assert len(stages)==3
        for stage,c in enumerate(stages):
            values=c.findall('./chunks/chunk[@name="param_input"][@index="5"]/chunks/chunk[@name="PersistentData"]//chunk[@name="Item"]/items/item')
            assert [v.text for v in values]==[str(stage)]
        ids=[i.text for i in root.iter('item') if i.get('name')=='InstanceGuid']
        assert len(ids)==len(set(ids))
        assert set(i.text for i in root.iter('item') if i.get('name')=='Source')<=set(ids)
        assert sum(i.text=='False' for i in root.iter('item') if i.get('name')=='ExpressionNormal')==9
