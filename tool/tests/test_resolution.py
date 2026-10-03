# SPDX-License-Identifier: GPL-3.0-or-later
"""Memory budgets and a matrix-free density filter must preserve the model."""
import copy, sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from resource_budget import grid_resources
from grid_filter import GridDensityFilter
from topoptlab.filter.matrix_filter import assemble_matrix_filter
from scipy.sparse import diags


def request(nx=100,ny=10,nz=60,backend="cpu-cg"):
    return dict(domain=dict(nx=nx,ny=ny,nz=nz,cell=2.5,active=list(range(nx*ny*nz))),settings=dict(backend=backend,radius=1.8),mode="fem",load_cases=[{}]*4)


@pytest.mark.parametrize("dims",[(100,10,60),(125,13,75),(250,25,150)])
def test_larger_grids_follow_available_memory_not_old_cap(dims):
    info=grid_resources(request(*dims),available_bytes=64*2**30)
    assert info["bounding_cells"]==np.prod(dims)
    assert info["estimated_host_bytes"]<info["host_budget_bytes"]


def test_low_memory_rejected_before_allocation():
    with pytest.raises(ValueError,match="memory"):
        grid_resources(request(),available_bytes=512*2**20)


def test_explicit_budget_cannot_override_available_ram():
    r=request();r["settings"]["memory_budget_gib"]=60
    with pytest.raises(ValueError,match="memory"):
        grid_resources(r,available_bytes=512*2**20)


@pytest.mark.parametrize("dims",[(0,2,2),(2049,1,1),(201,201,201),(2.5,2,2)])
def test_invalid_or_absolute_resource_bounds(dims):
    r=dict(domain=dict(nx=dims[0],ny=dims[1],nz=dims[2]),settings={},mode="fem")
    with pytest.raises(ValueError):grid_resources(r,available_bytes=64*2**30)


def test_cuda_budget_checked_independently():
    with pytest.raises(ValueError,match="GPU memory"):
        grid_resources(request(backend="cuda-cg"),available_bytes=64*2**30,gpu_available_bytes=2**20)


@pytest.mark.parametrize("radius",[1.,1.8,3.6,4.5])
def test_filter_matches_independent_sparse_reference_with_holes_and_keeps(radius):
    shape=(5,7,4);n=np.prod(shape)
    variable=np.delete(np.arange(n),[0,2,3,15,27,100])
    reference,_=assemble_matrix_filter(7,4,rmin=radius,nelz=5)
    h=reference.tocsr()[variable][:,variable]
    reference=diags(1/np.asarray(h.sum(axis=1)).ravel())@h
    f=GridDensityFilter(shape,variable,radius)
    rng=np.random.default_rng(934);x=rng.uniform(size=len(variable));y=rng.normal(size=len(variable))
    np.testing.assert_allclose(f@x,reference@x,rtol=1e-12,atol=1e-12)
    np.testing.assert_allclose(f.T@y,reference.T@y,rtol=1e-12,atol=1e-12)
    assert y@(f@x)==pytest.approx(x@(f.T@y),abs=1e-11)
    np.testing.assert_allclose(f@np.ones(len(variable)),1,atol=1e-12)
    assert f.storage_bytes<10_000_000


def test_filter_does_not_build_cell_by_neighbor_matrix():
    shape=(60,100,10);variable=np.arange(np.prod(shape))
    f=GridDensityFilter(shape,variable,3.6)
    assert f.storage_bytes<30*2**20
    np.testing.assert_allclose(f@np.ones(len(variable)),1,atol=1e-12)


def test_group_average_is_self_adjoint_and_linear_storage():
    from grid_filter import GroupAverage
    labels=np.repeat(np.arange(30),1000);f=GroupAverage(labels)
    x=np.arange(len(labels),dtype=float);y=np.cos(x)
    expected=x.reshape(30,1000).mean(axis=1).repeat(1000)
    np.testing.assert_allclose(f@x,expected)
    assert y@(f@x)==pytest.approx(x@(f.T@y),abs=1e-7)
    assert f.labels.nbytes+f.counts.nbytes<1_000_000


def test_unused_small_filter_does_not_block_fem():
    r=request();r['settings']['radius_length']=.01
    assert grid_resources(r,available_bytes=64*2**30)['bounding_cells']==60000


@pytest.mark.parametrize('engineering',[False,True])
def test_compact_stress_archive_preserves_scientific_fields(tmp_path,engineering):
    from test_3d import tension
    from worker import run
    r=tension();r['settings']['compact_results']=True
    if engineering:
        r['engineering']=True;r['material']=dict(preset='steel')
        r['load_cases']=[dict(name='Tension',weight=1,loads=r['loads'])]
    result=run(r,tmp_path)
    assert result['status']=='completed'
    assert 'stress_gauss' not in result
    archive=np.load(result['stress_file'])
    assert archive['stress_gauss'].shape==(16,8,6)
    np.testing.assert_allclose(archive['stress_gauss'],np.broadcast_to([1,0,0,0,0,0],(16,8,6)),atol=1e-8)
    np.testing.assert_allclose(archive['von_mises_gauss'].max(axis=1),result['von_mises'])


def test_2d_physical_filter_radius_matches_cell_units():
    from sample_problem import example
    from worker import Model
    r=example(24,12,2);r['settings']['radius']=2.6
    reference=Model(r)
    physical=copy.deepcopy(r);physical['settings']['radius']=1.1
    physical['settings']['radius_length']=2.6*r['domain']['cell']
    actual=Model(physical)
    assert actual.radius==pytest.approx(2.6)
    np.testing.assert_allclose(actual.filter.toarray(),reference.filter.toarray(),atol=1e-14)


def test_2d_explicit_ram_budget_is_not_silently_ignored():
    from sample_problem import example
    from worker import Model
    r=example();r['settings']['memory_budget_gib']=2
    with pytest.raises(ValueError,match='3D'):
        Model(r)


@pytest.mark.parametrize('mode',['fem','optimize'])
def test_nonfinite_radius_cannot_enter_resource_metadata(mode):
    r=request();r['mode']=mode;r['settings']['radius']=float('nan')
    with pytest.raises(ValueError,match='radius'):
        grid_resources(r,available_bytes=64*2**30)


def test_omitted_mode_budgets_default_optimization_filter():
    r=request();r.pop('mode');r['settings']['radius']=0
    with pytest.raises(ValueError,match='radius'):
        grid_resources(r,available_bytes=64*2**30)


def test_cuda_admission_includes_matrix_replacement_peak():
    # The previous GPU matrix can coexist with its replacement during preparation.
    with pytest.raises(ValueError,match='GPU memory'):
        grid_resources(request(backend='cuda-cg'),available_bytes=64*2**30,gpu_available_bytes=800*2**20)
