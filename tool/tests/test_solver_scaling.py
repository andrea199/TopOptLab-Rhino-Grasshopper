# SPDX-License-Identifier: GPL-3.0-or-later
"""Numerical invariants for cached element-block assembly and elastic AMG."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pytest
from scipy.sparse import coo_matrix
from types import SimpleNamespace
from fem_backends import BlockAssembly, elastic_candidates, ElasticSolver


def miniature(dim, varying=False):
    # Overlapping, irregularly ordered elements; local matrices may differ (TET4).
    enodes=np.array([[2,0,1],[1,3,2],[3,4,2]])
    ed=(dim*enodes[:,:,None]+np.arange(dim)).reshape(3,-1)
    rng=np.random.default_rng(19);a=rng.normal(size=(3,3*dim,3*dim))
    ke=np.einsum('eji,ejk->eik',a,a)
    nodes=rng.normal(size=(5,dim))
    return SimpleNamespace(edof=ed,ndof=5*dim,n=3,KE=ke if varying else ke[0],nodes=nodes,free=np.arange(dim,5*dim))


@pytest.mark.parametrize('dim',[2,3])
@pytest.mark.parametrize('varying',[False,True])
def test_cached_block_assembly_matches_independent_coo(dim,varying):
    m=miniature(dim,varying);pattern=BlockAssembly(m);mapping=pattern.element_blocks
    for scale in [np.array([1.,.12,.03]),np.array([.7,.3,1.]),np.array([0.,1.,0.])]:
        actual=pattern.assemble(scale)
        width=m.edof.shape[1]
        expected=coo_matrix(((scale[:,None,None]*m.KE).ravel(),(np.repeat(m.edof,width,axis=1).ravel(),np.tile(m.edof,(1,width)).ravel())),shape=(m.ndof,m.ndof)).tocsr()
        assert actual.toarray()==pytest.approx(expected.toarray(),rel=1e-13,abs=1e-13)
        assert pattern.element_blocks is mapping
    # Node-block mapping uses one integer per node pair, not two per DOF pair.
    assert mapping.nbytes < 2*m.n*m.edof.shape[1]**2*8/8


@pytest.mark.parametrize('dim',[2,3])
def test_elastic_amg_candidates_span_physical_rigid_modes(dim):
    m=miniature(dim);b=elastic_candidates(m)
    assert b.shape==(len(m.free),3 if dim==2 else 6)
    assert b.T@b==pytest.approx(np.eye(b.shape[1]),abs=1e-12)
    translated=m.nodes+np.arange(dim)*100
    other=elastic_candidates(SimpleNamespace(nodes=translated,free=m.free,ndof=m.ndof))
    assert b@b.T==pytest.approx(other@other.T,abs=1e-12)


def test_block_assembly_can_cancel_before_work():
    def cancelled():raise RuntimeError('test cancellation')
    with pytest.raises(RuntimeError,match='test cancellation'):BlockAssembly(miniature(3),cancelled)


@pytest.mark.parametrize('backend',['cpu-cg','cpu-amg'])
def test_density_updates_and_multiple_loads_match_direct(backend):
    from worker3d import Model3D
    from sample3d import cantilever
    request=cantilever('fem',8,4,2);request['settings']['backend']=backend
    model=Model3D(request);actual=ElasticSolver(model,request['settings']);direct=ElasticSolver(model,dict(backend='cpu-direct'))
    rng=np.random.default_rng(26)
    for scale in [np.ones(model.n),.05+.95*rng.random(model.n)]:
        for factor in [1.,-.7]:
            got,reactions,stats=actual.solve(scale,factor*model.forces)
            expected,expected_reactions,_=direct.solve(scale,factor*model.forces)
            assert got==pytest.approx(expected,rel=1e-6,abs=1e-10)
            assert reactions==pytest.approx(expected_reactions,abs=1e-7)
            assert stats['linear_residual']<=5e-9
    assert actual.preparations==2
    assert actual.assembly_pattern_builds==1



def test_stable_rhs_slots_use_current_equation_and_are_isolated():
    from worker3d import Model3D
    from sample3d import cantilever
    request=cantilever('fem',8,4,2);request['settings']['backend']='cpu-cg'
    m=Model3D(request);engine=ElasticSolver(m,request['settings']);direct=ElasticSolver(m,dict(backend='cpu-direct'))
    scale=np.full(m.n,.8)
    _,_,first=engine.solve(scale,m.forces,cache_key=('forward','A'))
    _,_,other=engine.solve(scale,-m.forces,cache_key=('forward','B'))
    assert not first['warm_start'] and not other['warm_start']
    new_force=m.forces*1.0001;new_scale=scale*1.0002
    actual,internal,stats=engine.solve(new_scale,new_force,cache_key=('forward','A'))
    expected,reference,_=direct.solve(new_scale,new_force)
    assert stats['warm_start'] and stats['initial_relative_residual']<1
    assert actual==pytest.approx(expected,rel=1e-6,abs=1e-10)
    assert internal==pytest.approx(reference,abs=1e-7)
    assert stats['linear_residual']<=5e-9
    _,_,adjoint=engine.solve(new_scale,new_force,cache_key=('adjoint','A','displacement'))
    assert not adjoint['warm_start']
    assert len(engine.guess)==3


def test_unhelpful_guess_rejected_and_cache_remains_bounded():
    from worker3d import Model3D
    from sample3d import cantilever
    request=cantilever('fem',4,2,1);request['settings']['backend']='cpu-cg'
    m=Model3D(request);engine=ElasticSolver(m,request['settings']);scale=np.ones(m.n)
    engine.solve(scale,m.forces,cache_key='same')
    _,_,stats=engine.solve(scale,-m.forces,cache_key='same')
    assert not stats['warm_start']
    for i in range(20):engine.solve(scale,m.forces,cache_key=('case',i))
    assert len(engine.guess)==16


def test_selfweight_case_and_adjoint_warm_start_namespaces():
    from test_distributed_loads import rectangle,model_cases
    from engineering_loads import solve_case
    from design_limits import evaluate_limits,resolve_limits
    from engineering_materials import resolve
    r=rectangle(3,'optimize');r['settings']['backend']='cpu-cg'
    r['load_cases'][0]['loads'].append(dict(kind='gravity',acceleration=[0,0,-9.80665]))
    m,cases=model_cases(r);limits=resolve_limits(dict(max_displacement=1,max_stress_mpa=1000),resolve(r['material']))
    for density in [.8,.80001]:
        rho=np.full(m.n,density);response=solve_case(m,cases[0],rho)
        evaluate_limits(m,cases[0],rho,response,limits,True)
    assert response['performance']['warm_start']
    slots={key[1] for key in m.engine.guess}
    assert slots=={('forward','Pressure'),('adjoint','Pressure','displacement'),('adjoint','Pressure','stress')}
