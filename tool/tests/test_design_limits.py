import copy,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_distributed_loads import rectangle,model_cases
from engineering_loads import solve_case
from engineering import constrain_design
from engineering_materials import resolve
from design_limits import resolve_limits,evaluate_limits,ks_upper,summarize_limits,stress_operator


def test_limit_units_and_material_allowable():
    material=resolve({'preset':'steel','stock_thickness_mm':10,'length_unit':'m','force_unit':'kN'})
    limits=resolve_limits({'max_displacement':.002,'max_stress_mpa':100},material)
    assert limits['max_stress']==pytest.approx(100000)
    assert limits['max_displacement']==.002
    assert resolve_limits({'use_material_allowable':True},material)['max_stress_mpa']==pytest.approx(235/1.5)
    with pytest.raises(ValueError,match='unavailable'):resolve_limits({'use_material_allowable':True},resolve({}))
    with pytest.raises(ValueError,match='OR'):resolve_limits({'use_material_allowable':True,'max_stress_mpa':100},material)
    with pytest.raises(ValueError):resolve_limits({'max_displacement':-1},material)


def test_ks_is_conservative_and_stable():
    values=np.array([0.,1.,100000.]);aggregate,weights=ks_upper(values,50)
    assert aggregate>=values.max();assert weights.sum()==pytest.approx(1)
    assert np.isfinite(aggregate)
    aggregate,weights=ks_upper(np.ones(100),50)
    assert aggregate==pytest.approx(1+np.log(100)/50)


@pytest.mark.parametrize('dim',[2,3])
@pytest.mark.parametrize('gravity',[False,True])
@pytest.mark.parametrize('manufacturing',[{}, {'symmetry':'y'}])
def test_displacement_and_stress_adjoint_derivatives(dim,gravity,manufacturing):
    r=rectangle(dim,'optimize')
    load=r['load_cases'][0]['loads'][0];load.update(kind='traction',traction=[.002,-.003] if dim==2 else [.002,-.003,-.002])
    if gravity:r['load_cases'][0]['loads'].append(dict(kind='gravity',acceleration=[0,-98.0665] if dim==2 else [0,0,-98.0665]))
    m,c=model_cases(r);constrain_design(m,manufacturing)
    limits=resolve_limits({'max_displacement':.00001,'max_stress_mpa':.05},resolve(r['material']))
    x=m.initial()+.02*np.random.default_rng(19).normal(size=m.design.sum())
    direction=np.random.default_rng(20).normal(size=len(x));direction/=np.linalg.norm(direction);eps=1e-6
    def evaluate(x,gradient=False):
        rho=m.density(x);response=solve_case(m,c[0],rho)
        return evaluate_limits(m,c[0],rho,response,limits,gradient)
    analytic=evaluate(x,True)['jacobian']@direction
    numeric=(evaluate(x+eps*direction)['values']-evaluate(x-eps*direction)['values'])/(2*eps)
    assert analytic==pytest.approx(numeric,rel=3e-5,abs=1e-8)


@pytest.mark.parametrize('dim',[2,3])
def test_fem_limit_checks_identify_exceeded_field(dim):
    r=rectangle(dim);m,c=model_cases(r);rho=np.ones(m.n);res=solve_case(m,c[0],rho)
    limits=resolve_limits({'max_displacement':1,'max_stress_mpa':1},resolve(r['material']))
    ev=evaluate_limits(m,c[0],rho,res,limits)
    assert ev['checks'][0]['status']=='within_limit'
    assert ev['checks'][1]['status']=='exceeded'
    assert ev['checks'][1]['value']==pytest.approx(2)
    summary=summarize_limits(limits,[dict(name='Tension',checks=ev['checks'])],'fem')
    assert summary['status']=='exceeded';assert not summary['final_shape_verified']
    assert ev['checks'][1]['cell_id'] in r['domain']['active']


@pytest.mark.parametrize('dim',[2,3])
def test_adjoint_stress_operator_matches_existing_recovery(dim):
    r=rectangle(dim);m,c=model_cases(r);res=solve_case(m,c[0],np.ones(m.n))
    recovered=np.einsum('qij,ej->eqi',stress_operator(m),res['displacement'].ravel()[m.edof])
    expected,_=m.stress(res['displacement'])
    assert recovered==pytest.approx(expected,abs=1e-12)


@pytest.mark.parametrize('dim',[2,3])
def test_mma_reduces_initial_violation_and_respects_constraints(dim,tmp_path):
    from worker import run
    r=rectangle(dim);r['load_cases'][0]['loads'][0].update(kind='traction',traction=[0,-.1] if dim==2 else [0,0,-.1])
    r['settings'].update(iterations=60,preserve_attachments=True,minimum_iterations=5,convergence_window=3)
    baseline=run(r,tmp_path/'baseline');r['mode']='optimize'
    r['design_limits']=dict(max_displacement=baseline['metrics']['max_displacement']*(6 if dim==2 else 4),max_stress_mpa=baseline['metrics']['max_von_mises']*5)
    result=run(r,tmp_path/'constrained');e=result['engineering']
    assert result['history'][0]['max_constraint_violation']>0
    assert e['constraint_optimizer']['feasible']
    assert e['design_limits']['status'] in ('within_limits','within_tolerance')
    assert np.mean(result['density'])<=r['settings']['volume']*1.001
    assert 'MMA' in e['optimization_update']
    assert (tmp_path/'constrained/case-01.json').exists()
    assert len(result['von_mises_relaxed'])==len(result['density'])


def test_impossible_constraints_are_not_reported_as_converged(tmp_path):
    from worker import run
    r=rectangle(2,'optimize');r['settings']['iterations']=4;r['design_limits']=dict(max_displacement=1e-12,max_stress_mpa=1e-6)
    result=run(r,tmp_path/'impossible');e=result['engineering']
    assert not e['converged'];assert not e['constraint_optimizer']['feasible']
    assert e['design_limits']['status']=='constraints_not_satisfied'
    assert 'constraints_not_satisfied' in (tmp_path/'impossible/report.html').read_text()


def test_limits_check_every_case_regardless_of_objective_weight(tmp_path):
    from worker import run
    r=rectangle(2);heavy=copy.deepcopy(r['load_cases'][0]);heavy.update(name='Heavy',weight=1e-6);heavy['loads'][0]['pressure']=-20
    r['load_cases'].append(heavy);r['design_limits']=dict(max_stress_mpa=3)
    result=run(r,tmp_path/'cases');checks=result['engineering']['design_limits']
    assert checks['status']=='exceeded'
    assert checks['cases'][0]['checks'][0]['status']=='within_limit'
    assert checks['cases'][1]['checks'][0]['status']=='exceeded'


def test_check_only_does_not_change_optimization(tmp_path):
    from worker import run
    r=rectangle(2,'optimize');r['settings']['iterations']=3
    a=run(r,tmp_path/'without');r['design_limits']=dict(max_stress_mpa=.001,enforce=False)
    b=run(r,tmp_path/'check')
    assert a['density']==pytest.approx(b['density'])
    assert b['engineering']['constraint_optimizer'] is None
    assert b['engineering']['design_limits']['status']=='exceeded'


def test_final_verification_rechecks_physical_stress_against_new_limits(tmp_path):
    from worker import run
    r=rectangle(3,'optimize');r['settings']['iterations']=1
    a=run(r,tmp_path/'design');r.update(mode='verify',source_result=a,manufacturing={'threshold':.01},design_limits={'max_stress_mpa':.1})
    verified=run(r,tmp_path/'final');checks=verified['engineering']['design_limits']
    assert checks['scope']=='binary_voxel_fem';assert checks['status']=='exceeded'
    assert checks['cases'][0]['checks'][0]['value']==pytest.approx(2)
    assert 'von_mises_relaxed' not in verified


def test_all_optimization_cases_are_saved_with_correct_displacement(tmp_path):
    import json
    from worker import run
    r=rectangle(3,'optimize');r['settings']['iterations']=2
    case=copy.deepcopy(r['load_cases'][0]);case['name']='Opposite';case['loads'][0]['pressure']*= -1;r['load_cases'].append(case)
    result=run(r,tmp_path/'job');files=result['engineering']['case_files']
    assert files==['case-01.json','case-02.json']
    a,b=[json.loads((tmp_path/'job'/file).read_text()) for file in files]
    assert np.asarray(a['displacement'])==pytest.approx(-np.asarray(b['displacement']))
    assert a['density']==b['density'];assert b['engineering']['display_case']=='Opposite'
    assert a['metrics']['compliance']*2==pytest.approx(result['engineering']['weighted_compliance'])
    assert a['completed_iterations']==result['completed_iterations']


@pytest.mark.parametrize('dim',[2,3])
def test_cuda_constraint_adjoints_match_direct(dim):
    pytest.importorskip('cupy')
    r=rectangle(dim,'optimize');m,c=model_cases(r);rho=m.density(m.initial())
    limits=resolve_limits({'max_displacement':.001,'max_stress_mpa':5},resolve(r['material']))
    a=evaluate_limits(m,c[0],rho,solve_case(m,c[0],rho),limits,True)
    r['settings']['backend']='cuda-cg';m,c=model_cases(r)
    b=evaluate_limits(m,c[0],rho,solve_case(m,c[0],rho),limits,True)
    assert a['values']==pytest.approx(b['values'],rel=1e-7,abs=1e-9)
    assert a['jacobian']==pytest.approx(b['jacobian'],rel=1e-6,abs=1e-9)


def test_mma_numerical_failure_preserves_diagnostic_state(tmp_path,monkeypatch):
    from worker import run
    import constrained_design
    def failed_step(*args,**kwargs):raise ValueError('Synthetic MMA numerical breakdown')
    monkeypatch.setattr(constrained_design,'mmasub',failed_step)
    r=rectangle(2,'optimize');r['design_limits']=dict(max_displacement=1e-12)
    result=run(r,tmp_path/'failure');e=result['engineering']
    assert e['termination_reason']=='optimizer_failed'
    assert not e['converged'];assert not e['constraint_optimizer']['feasible']
    assert 'Synthetic' in e['constraint_optimizer']['numerical_failure']
    assert np.isfinite(result['displacement']).all()


@pytest.mark.parametrize('dim',[2,3])
def test_constrained_gravity_uses_fixed_budget_and_independent_cases(dim,tmp_path):
    from worker import run
    r=rectangle(dim,'optimize');r['settings'].update(iterations=12,volume=.7)
    r['load_cases'][0]['loads'].append(dict(kind='gravity',acceleration=[0,-9.80665] if dim==2 else [0,0,-9.80665]))
    other=copy.deepcopy(r['load_cases'][0]);other['name']='Second';other['loads'][0]['pressure']*=-2;r['load_cases'].append(other)
    r['design_limits']=dict(max_displacement=.1,max_stress_mpa=100)
    result=run(r,tmp_path/'gravity');e=result['engineering'];opt=e['constraint_optimizer']
    assert opt['feasible'];assert len(e['design_limits']['cases'])==2
    assert np.mean(result['density'])==pytest.approx(.7,abs=.7*.001)
    assert opt['volume_policy'].startswith('fixed budget')
    assert np.isfinite(result['displacement']).all()


def test_review_example_wiring_and_idle_controls():
    import xml.etree.ElementTree as ET
    for dim in (2,3):
        root=ET.parse(Path(__file__).resolve().parents[1]/'examples'/f'engineering_design_limits_{dim}d.ghx')
        containers=root.findall('.//chunk[@name="Object"]/chunks/chunk[@name="Container"]')
        names=[c.find('./items/item[@name="Name"]').text for c in containers]
        assert names.count('TopOpt Case Result')==3
        assert names.count('TopOpt Review Controls')==1
        assert names.count('TopOpt Compare Results')==2
        assert names.count('TopOpt Design Limits')==1
        ids=[i.text for i in root.iter('item') if i.get('name')=='InstanceGuid']
        assert len(ids)==len(set(ids))
        assert set(i.text for i in root.iter('item') if i.get('name')=='Source')<=set(ids)
        assert sum(i.text=='False' for i in root.iter('item') if i.get('name')=='ExpressionNormal')==9
        stages=[c for c in containers if c.find('./items/item[@name="Name"]').text=='TopOpt Engineering']
        for stage in stages:
            assert stage.find('./chunks/chunk[@name="param_input"][@index="10"]/items/item[@name="Source"]') is not None
