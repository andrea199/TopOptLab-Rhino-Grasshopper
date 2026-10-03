# SPDX-License-Identifier: GPL-3.0-or-later
import sys,copy
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from final_geometry import extract,mesh_arrays,from_mesh,inspect_surface
from tetra_mesh import generate
from tetra_fem import TetraModel,constitutive
from engineering_materials import resolve
from final_loads import transfer_supports,transfer_case
from manufacturing_review import inspect as manufacturing
import manifold3d as md


def box_request():
    from sample3d import cantilever
    r=cantilever('fem',8,4,2);d=r['domain'];d['cell']=1;d['origin']=[0,0,0]
    r['material']={'preset':'steel','poisson':0};r['dimension']=3
    faces=[dict(cell=e,axis=0,side=1) for e in d['active'] if (e//d['ny'])%d['nx']==d['nx']-1]
    r['load_cases']=[dict(name='Tension',weight=1,loads=[dict(kind='pressure',pressure=-2,faces=faces)])]
    return r

@pytest.fixture(scope='module')
def box_mesh(tmp_path_factory):
    v,f=mesh_arrays(md.Manifold.cube((8,4,2)));return generate(v,f,1.2,tmp_path_factory.mktemp('tet-box'))


def test_extract_is_closed_bounded_and_keeps_all_protected_voxels():
    r=box_request();d=r['domain'];source=dict(status='completed',dimension=3,engineering={'mode':'optimize'},density=np.full(len(d['active']),.7).tolist(),kept=np.isin(d['active'],d['solid']).tolist(),cell_ids=d['active'])
    v,f,info=extract(source,d,dict(threshold=.5,smoothing=.5))
    assert info['closed'];assert info['solid_components']==1;assert info['protected_volume_loss']<1e-8
    assert np.all(v.min(axis=0)>=-1e-8);assert np.all(v.max(axis=0)<=[8+1e-8,4+1e-8,2+1e-8])
    assert not info['structurally_verified'];assert info['volume']<64


def test_open_surface_and_disconnected_material_are_detected():
    v,f=mesh_arrays(md.Manifold.cube())
    with pytest.raises(ValueError,match='closed'):from_mesh(v,f[:-1])
    v,f=mesh_arrays(md.Manifold.cube()+md.Manifold.cube().translate((2,0,0)))
    assert inspect_surface(v,f)['solid_components']==2


@pytest.mark.parametrize('backend',['cpu-direct','cpu-cg','cpu-amg','cpu-matrixfree','cuda-cg'])
def test_tetra_uniform_tension_exact_and_backend_parity(box_mesh,backend):
    if backend=='cuda-cg':pytest.importorskip('cupy')
    r=box_request();m=TetraModel(*box_mesh,resolve(r['material']),dict(backend=backend));fixed,info=transfer_supports(m,r);m.supports(fixed)
    force,transfer=transfer_case(m,r,r['load_cases'][0]);result=m.solve(force)
    assert result['displacement'][:,0]==pytest.approx(m.nodes[:,0]*2/210000,rel=1e-6,abs=1e-10)
    assert result['von_mises']==pytest.approx(np.full(m.n,2),rel=1e-6,abs=1e-8)
    assert transfer['force_relative_error']<1e-10;assert transfer['moment_relative_error']<1e-10
    assert result['equilibrium']<1e-8


def test_independent_scikit_fem_assembly_and_response(box_mesh):
    from skfem import MeshTet,ElementTetP1,ElementVector,Basis,asm,condense,solve
    from skfem.models.elasticity import linear_elasticity,lame_parameters
    r=box_request();r['material']['poisson']=.3
    r['load_cases'][0]['loads'][0]=dict(kind='nodal',nodes=[8*5+2],force=[0,0,-1])
    m=TetraModel(*box_mesh,resolve(r['material']),{'backend':'cpu-direct'});fixed,_=transfer_supports(m,r);m.supports(fixed);force,_=transfer_case(m,r,r['load_cases'][0]);actual=m.solve(force)
    basis=Basis(MeshTet(m.nodes.T,m.tets.T),ElementVector(ElementTetP1()));K=asm(linear_elasticity(*lame_parameters(m.material['young'],m.material['poisson'])),basis)
    # Explicit DOF map, rather than assuming an undocumented vector ordering.
    order=basis.nodal_dofs.T.ravel();F=np.zeros(basis.N);F[order]=force.ravel();U=solve(*condense(K,F,D=order[m.fixed]));reference=U[order].reshape(-1,3)
    assert actual['displacement']==pytest.approx(reference,rel=1e-8,abs=1e-12)
    assert actual['compliance']==pytest.approx(float(F@U),rel=1e-10)
    delta=(m.engine.K-K[order][:,order]).toarray();assert np.max(abs(delta))<1e-8*m.material['young']


def test_gravity_and_surface_traction_conserve_force_moment(box_mesh):
    r=box_request();r['load_cases'][0]['loads'][0].update(kind='traction',traction=[.2,-.1,-.3]);r['load_cases'][0]['loads'].append(dict(kind='gravity',acceleration=[0,0,-9.80665]))
    m=TetraModel(*box_mesh,resolve(r['material']),{'backend':'cpu-direct'});fixed,_=transfer_supports(m,r);m.supports(fixed);force,transfer=transfer_case(m,r,r['load_cases'][0]);result=m.solve(force)
    expected=np.array([.2,-.1,-.3])*8;expected[2]-=64*1e-9*7850*9.80665
    assert force.sum(axis=0)==pytest.approx(expected);assert transfer['moment_relative_error']<1e-12;assert result['equilibrium']<1e-10


def test_missing_load_and_unsupported_point_support_are_rejected(box_mesh):
    r=box_request();m=TetraModel(*box_mesh,resolve(r['material']),{'backend':'cpu-direct'})
    r['load_cases'][0]['loads']=[dict(kind='nodal',nodes=[4*5+2+1*9*5],force=[0,0,-1])]
    with pytest.raises(ValueError,match='missing'):transfer_case(m,r,r['load_cases'][0])
    r['supports'][0]['nodes']=[0]
    with pytest.raises(ValueError,match='complete original boundary faces'):transfer_supports(m,r)


def test_partial_pressure_patch_preserves_original_resultant(box_mesh):
    r=box_request();r['load_cases'][0]['loads'][0]['faces']=r['load_cases'][0]['loads'][0]['faces'][1:3]
    m=TetraModel(*box_mesh,resolve(r['material']),{'backend':'cpu-direct'});force,transfer=transfer_case(m,r,r['load_cases'][0])
    assert force.sum(axis=0)==pytest.approx([4,0,0]);assert transfer['moment_relative_error']<1e-10


def test_print_orientation_bed_and_sampled_thickness():
    v,f=mesh_arrays(md.Manifold.cube((8,4,2)));a=manufacturing(v,f,dict(enabled=True,minimum_wall=3,samples=100))
    assert a['bed_contact_area']==pytest.approx(32);assert a['overhang_area']==0;assert a['sampled_wall_minimum']==pytest.approx(2)
    assert a['thin_sample_faces'];assert a['status']=='flags_present'
    # Elevated shelf has a genuine unsupported downward-facing patch above the bed.
    shape=md.Manifold.cube((1,1,3))+md.Manifold.cube((4,1,1)).translate((0,0,2));v,f=mesh_arrays(shape)
    b=manufacturing(v,f,dict(enabled=True));assert b['overhang_area']>2.9


def test_accuracy_needs_two_successive_refinements():
    from final_workflow import accuracy
    def level(h,value):return dict(mesh_size=h,cases=[dict(name='a',compliance=value,max_displacement=value,max_von_mises=value)])
    assert accuracy([level(1,1)],.05)['status']=='not_studied'
    assert accuracy([level(1,1),level(.75,1)],.05)['status']=='not_established'
    assert accuracy([level(1,1),level(.75,1),level(.5,1.01)],.05)['status']=='stable_over_two_refinements'
    assert accuracy([level(1,1),level(.75,1),level(.5,2)],.05)['status']=='not_established'


def test_tetra_units_mm_n_to_m_kn(box_mesh):
    r=box_request();r['load_cases'][0]['loads'].append(dict(kind='gravity',acceleration=[0,0,-9.80665]))
    def solve(request,nodes,tets):
        model=TetraModel(nodes,tets,resolve(request['material']),{'backend':'cpu-direct'});fixed,_=transfer_supports(model,request);model.supports(fixed);force,transfer=transfer_case(model,request,request['load_cases'][0]);return model.solve(force),force,transfer
    a,fa,ta=solve(r,*box_mesh);r['domain']['cell']/=1000;r['material'].update(length_unit='m',force_unit='kN');r['load_cases'][0]['loads'][0]['pressure']*=1000
    b,fb,tb=solve(r,box_mesh[0]/1000,box_mesh[1]);assert b['displacement']==pytest.approx(a['displacement']/1000,rel=1e-7,abs=1e-13)
    assert b['von_mises']==pytest.approx(a['von_mises']*1000,rel=1e-7);assert fb==pytest.approx(fa/1000,abs=1e-12);assert tb['moment_relative_error']<1e-10


@pytest.fixture(scope='module')
def optimized_source(tmp_path_factory):
    from test_distributed_loads import rectangle
    from worker import run
    r=rectangle(3,'optimize');r['settings'].update(iterations=2,preserve_attachments=True);r['job_id']='final-integration-source'
    other=copy.deepcopy(r['load_cases'][0]);other['name']='Half load';other['loads'][0]['pressure']/=2;r['load_cases'].append(other)
    return run(r,tmp_path_factory.mktemp('final-source')/'job')


def test_final_worker_pipeline_limits_and_saved_cases(optimized_source,tmp_path):
    from worker import run
    import json
    v,f=mesh_arrays(md.Manifold.cube((8,4,2)))
    surface=run(dict(workflow='final_geometry',action='extract',source_result=optimized_source,job_id='extract',settings=dict(threshold=.4),edited_mesh=dict(nodes=v.tolist(),triangles=f.tolist()),manufacturing_review={'enabled':True}),tmp_path/'surface')
    assert surface['geometry']['protected_volume_loss']==0;assert Path(surface['surface_file']).is_file()
    result=run(dict(workflow='final_geometry',action='analyze',source_result=surface,job_id='final-fem',settings=dict(mesh_size=1.2,backend='cpu-cg'),design_limits=dict(max_stress_mpa=1)),tmp_path/'fem')
    assert result['mode']=='final_fem';assert result['engineering']['design_limits']['status']=='exceeded'
    assert result['engineering']['accuracy']['status']=='not_studied';assert not result['engineering']['design_limits']['final_shape_verified'];assert result['geometry']['structurally_reanalysed'];assert result['engineering']['cases'][0]['max_von_mises']==pytest.approx(2,rel=1e-6)
    second=json.loads((tmp_path/'fem/case-02.json').read_text());assert second['load_case']['name']=='Half load'
    assert second['metrics']['compliance']==pytest.approx(result['metrics']['compliance']/4,rel=1e-7)
    assert Path(result['engineering']['report_file']).is_file();assert result['engineering']['source_geometry_hash']==surface['geometry_hash']
    verified=run(dict(workflow='final_geometry',action='analyze',source_result=surface,job_id='stable-fem',settings=dict(mesh_size=1.5,levels=3,backend='cpu-cg'),design_limits=dict(max_stress_mpa=3)),tmp_path/'stable-fem')
    assert verified['engineering']['accuracy']['status']=='stable_over_two_refinements';assert verified['engineering']['mesh_quality_status']=='no_poor_elements'
    assert verified['engineering']['design_limits']['final_shape_verified'];assert verified['geometry']['structurally_verified']



def test_edited_mesh_rejects_removed_keep_and_outside_envelope(optimized_source,tmp_path):
    from worker import run
    for name,solid,message in [('removed',md.Manifold.cube((7,4,2)),'protected material'),('outside',md.Manifold.cube((9,4,2)),'outside')]:
        v,f=mesh_arrays(solid)
        with pytest.raises(ValueError,match=message):run(dict(workflow='final_geometry',action='extract',source_result=optimized_source,job_id=name,edited_mesh=dict(nodes=v.tolist(),triangles=f.tolist())),tmp_path/name)
        assert not (tmp_path/name/'result.json').exists()


def test_final_source_signature_and_surface_hash_rejections(optimized_source,tmp_path):
    from worker import run
    broken=copy.deepcopy(optimized_source);broken['job_id']='unrelated'
    with pytest.raises(ValueError,match='do not match'):run(dict(workflow='final_geometry',action='extract',source_result=broken,job_id='badsource'),tmp_path/'badsource')
    surface=run(dict(workflow='final_geometry',action='extract',source_result=optimized_source,job_id='surface',settings=dict(threshold=.1,smoothing=0)),tmp_path/'surface')
    surface['nodes'][0][0]+=.1
    with pytest.raises(ValueError,match='geometry changed'):run(dict(workflow='final_geometry',action='analyze',source_result=surface,job_id='badhash'),tmp_path/'badhash')


def test_cancel_before_final_work_and_during_mesher(tmp_path):
    from worker import run
    from tetra_mesh import remesh
    from fem_backends import Cancelled
    import time
    directory=tmp_path/'cancelled';directory.mkdir();(directory/'cancel').touch()
    result=run(dict(workflow='final_geometry',action='extract',job_id='cancelled'),directory)
    assert result['status']=='cancelled';assert not (directory/'result.json').exists()
    v,f=mesh_arrays(md.Manifold.cube());start=time.monotonic()
    def stop():raise Cancelled()
    with pytest.raises(Cancelled):remesh(v,f,.001,tmp_path/'mesher',stop)
    assert time.monotonic()-start<10;assert not (tmp_path/'mesher/mesh.npz').exists()


def test_final_example_archive_links_controls_and_new_icons():
    import xml.etree.ElementTree as ET
    root=ET.parse(Path(__file__).resolve().parents[1]/'examples/engineering_final_geometry_3d.ghx')
    names=[i.text for i in root.findall('.//chunk[@name="Object"]/items/item[@name="Name"]')]
    assert names.count('TopOpt Final Geometry 3D')==1;assert names.count('TopOpt Final FEM 3D')==1;assert names.count('TopOpt Final Results 3D')==2;assert names.count('TopOpt Print Review')==1
    ids=[i.text for i in root.iter('item') if i.get('name')=='InstanceGuid'];assert len(ids)==len(set(ids))
    assert set(i.text for i in root.iter('item') if i.get('name')=='Source')<=set(ids)
    assert sum(i.text=='False' for i in root.iter('item') if i.get('name')=='ExpressionNormal')==17
    for name in ['FinalGeometry3DComponent','FinalFem3DComponent','FinalResults3DComponent','PrintReviewComponent']:assert (Path(__file__).resolve().parents[1]/'icons'/(name+'.png')).is_file()
