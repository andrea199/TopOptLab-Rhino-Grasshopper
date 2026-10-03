# SPDX-License-Identifier: GPL-3.0-or-later
"""CAD interfaces are geometric constraints, independent of optimization voxels."""
import copy,json,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import manifold3d as md
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cad_interfaces import build,validate_contract,restore,check_mesh,contract_hash
from final_geometry import extract,mesh_arrays,from_mesh
from final_loads import transfer_case,transfer_supports
FIX=Path(__file__).parent/'fixtures'/'shelf_bracket'

def contract():
    request=json.loads((FIX/'variant-0.json').read_text())
    loading=json.loads((FIX/'summary-0.json').read_text())
    loading.update(front_depth_mm=20,lateral_offset_fraction=.6,support_model='rigid_wall_pads',support_pad_height_mm=26,case_names=[c['name'] for c in request['load_cases']])
    cfg=dict(specification=request['example_geometry'],loading=loading,chord_tolerance_mm=.05)
    return request,cfg

def test_nominal_plates_and_circular_clearances_are_independent_of_grid():
    request,cfg=contract();cad=build(cfg);s=cfg['specification']
    nominal=(250*25*10+10*25*140)-4*np.pi*4**2*10
    assert cad['protected'].volume()<=nominal
    assert cad['protected'].volume()>nominal-4*np.pi*((4+.05)**2-4**2)*10
    assert cad['max_radial_overcut_mm']<=.05
    # Circle cylinders are circumscribed: the nominal screw is never obstructed.
    dense=md.Manifold.cylinder(10,4,circular_segments=256).rotate((0,90,0)).translate((0,0,25))
    assert (cad['protected']^dense).volume()<1e-6
    v,f=mesh_arrays(cad['protected']);near=v[(v[:,0]>-.001)&(v[:,0]<10.001)&(abs(v[:,2]-25)<4.1)&(abs(v[:,1])<4.1)]
    radius=np.linalg.norm(near[:,[1,2]]-[0,25],axis=1)
    assert len(radius)>20 and radius.min()>=4-1e-7 and radius.max()<=4.05+1e-7
    assert contract_hash(cfg)==contract_hash(copy.deepcopy(cfg))

@pytest.mark.parametrize('change,message',[
    (lambda c:c['specification'].update(hole_diameter_mm=0),'positive'),
    (lambda c:c.update(chord_tolerance_mm=0),'tolerance'),
    (lambda c:c['specification'].update(origin=[0,0,float('nan')]),'finite'),
    (lambda c:c['loading'].update(payload_kg=5),'payload'),
    (lambda c:c['loading'].update(front_depth_mm=30),'patch'),
    (lambda c:c['loading'].update(origin_mm=[1,0,0]),'origin'),
])
def test_invalid_or_mismatched_cad_contract_fails(change,message):
    request,cfg=contract();change(cfg)
    with pytest.raises(ValueError,match=message):validate_contract(request,cfg)

def test_rejects_nonmatching_domain_and_source_case_changes():
    request,cfg=contract();validate_contract(request,cfg)
    request['domain']['active']=request['domain']['active'][1:]
    with pytest.raises(ValueError,match='domain'):validate_contract(request,cfg)
    request,cfg=contract();request['load_cases'][2]['loads'][0]['traction'][2]*=2
    with pytest.raises(ValueError,match='payload'):validate_contract(request,cfg)

def test_extraction_restores_plates_and_keeps_nominal_voids_empty():
    r,cfg=contract();d=r['domain'];active=np.array(d['active']);kept=np.isin(active,d['solid'])
    source=dict(status='completed',dimension=3,engineering=dict(mode='optimize'),density=np.full(len(active),.65).tolist(),kept=kept.tolist(),cell_ids=active.tolist())
    nodes,triangles,info=extract(source,d,dict(threshold=.4,smoothing=.5,cad_interfaces=cfg))
    cad=build(cfg);solid=from_mesh(nodes,triangles)
    assert (cad['protected']-solid).volume()<1e-6
    assert (solid^cad['voids']).volume()<1e-6
    assert (solid-cad['envelope']).volume()<1e-6
    assert info['cad_interfaces']['radial_overcut_bound_mm']<=.05
    assert info['solid_components']==1
    xyz=nodes[triangles];assert np.all(np.linalg.norm(np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),axis=1)>0)
    assert not info['structurally_verified']

def test_edited_mesh_fails_when_forbidden_space_is_filled_or_plate_lost():
    r,cfg=contract();cad=build(cfg)
    with pytest.raises(ValueError,match='forbidden'):check_mesh(cad['envelope'],cfg)
    cut=md.Manifold.cube((20,40,20)).translate((235,-20,135))
    with pytest.raises(ValueError,match='protected'):check_mesh(cad['protected']-cut,cfg)

def test_cad_patch_transfer_matches_nominal_forces_and_reports_raster_difference():
    r,cfg=contract();cad=build(cfg);v,f=mesh_arrays(cad['protected'])
    model=SimpleNamespace(nodes=v,triangles=f,material={})
    r['cad_interfaces']=cfg
    # Exclude gravity in this surface-only integration test.
    for case in r['load_cases']:case['loads']=[load for load in case['loads'] if load['kind']!='gravity']
    forces=[];moments=[]
    for case in r['load_cases']:
        force,info=transfer_case(model,r,case);forces.append(force.sum(axis=0));moments.append(np.cross(v,force).sum(axis=0))
        assert force.sum(axis=0)==pytest.approx([0,0,-4.5*9.80665],abs=1e-9)
        assert info['force_relative_error']<1e-12 and info['moment_relative_error']<1e-12
        assert info['mapping']=='nominal_cad_patches'
        assert 'original_raster_moment_nmm' in info['loads'][0]
    assert moments[2][0]==pytest.approx(-moments[3][0],abs=1e-8)
    assert moments[2][1]==pytest.approx(moments[3][1],abs=1e-8)
    # Continuous right rectangle y=2.5..12.5 has centroid7.5; total force 4kg.
    assert moments[2][0]==pytest.approx(-4*9.80665*7.5,abs=1e-6)
    fixed,records=transfer_supports(model,r)
    assert len(fixed)>0 and all(abs(v[i//3,0])<1e-7 for i in fixed)
    assert records[0]['mapping']=='nominal_cad_wall_pads'

def test_missing_cad_load_patch_is_rejected():
    r,cfg=contract();r['cad_interfaces']=cfg
    v,f=mesh_arrays(md.Manifold.cube((250,25,10)).translate((0,-12.5,100)))
    model=SimpleNamespace(nodes=v,triangles=f,material={})
    with pytest.raises(ValueError,match='CAD load patch'):transfer_case(model,r,r['load_cases'][0])


def test_cad_workflow_contract_provenance_and_edited_geometry(tmp_path):
    from engineering import signature
    from worker import run
    request,cfg=contract();request['job_id']='cad-source'
    directory=tmp_path/'source';directory.mkdir();(directory/'project.json').write_text(json.dumps(request))
    d=request['domain'];source=dict(status='completed',dimension=3,job_id='cad-source',engineering=dict(mode='optimize',report_file=str(directory/'report.html'),input_signature=signature(request)),density=[.7]*len(d['active']),kept=np.isin(d['active'],d['solid']).tolist(),cell_ids=d['active'])
    surface=run(dict(workflow='final_geometry',action='extract',source_result=source,job_id='cad-extract',settings=dict(cad_interfaces=cfg,threshold=.4,smoothing=.5)),tmp_path/'surface')
    assert surface['cad_interface_signature']==contract_hash(cfg)
    assert surface['geometry']['cad_interfaces']['exact_brep'] is False
    corrupt=copy.deepcopy(surface);corrupt['cad_interfaces']['loading']['payload_kg']=5
    with pytest.raises(ValueError,match='CAD interface contract changed'):run(dict(workflow='final_geometry',action='analyze',source_result=corrupt,job_id='cad-tamper'),tmp_path/'tamper')
    corrupt=copy.deepcopy(surface);del corrupt['cad_interfaces']
    with pytest.raises(ValueError,match='CAD interface contract is missing'):run(dict(workflow='final_geometry',action='analyze',source_result=corrupt,job_id='cad-missing'),tmp_path/'missing')
    # A closed but forbidden filled envelope is not accepted as an edited result.
    v,f=mesh_arrays(build(cfg)['envelope'])
    with pytest.raises(ValueError,match='forbidden'):run(dict(workflow='final_geometry',action='extract',source_result=source,job_id='cad-fill',settings=dict(cad_interfaces=cfg),edited_mesh=dict(nodes=v.tolist(),triangles=f.tolist())),tmp_path/'filled')


def test_cad_planar_mesher_keeps_hole_volume_and_refines(tmp_path):
    from tetra_mesh import remesh
    from tetra_fem import TetraModel
    from engineering_materials import resolve
    shape=md.Manifold.cube((8,6,4))-md.Manifold.cylinder(6,1,circular_segments=20).translate((4,3,-1))
    v,f=mesh_arrays(shape);records=[]
    for index,size in enumerate((2,1)):
        nodes,tets=remesh(v,f,size,tmp_path/str(index),cad_surface=True)
        model=TetraModel(nodes,tets,resolve({'preset':'steel'}),{'backend':'cpu-direct'})
        assert model.volumes.sum()==pytest.approx(shape.volume(),rel=1e-10)
        boundary_nodes=model.nodes[np.unique(model.triangles)]
        on_wall=boundary_nodes[(boundary_nodes[:,2]>1e-8)&(boundary_nodes[:,2]<4-1e-8)]
        assert not np.any(np.linalg.norm(on_wall[:,0:2]-[4,3],axis=1)<np.cos(np.pi/20)-1e-8)
        records.append((len(model.triangles),len(tets)))
    assert records[1][0]>records[0][0] and records[1][1]>records[0][1]


def test_cad_meshing_budget_rejects_before_allocating(tmp_path):
    from tetra_mesh import generate
    v,f=mesh_arrays(md.Manifold.cube((8,6,4)))
    with pytest.raises(ValueError,match='allocation budget'):generate(v,f,1e-8,tmp_path,cad_surface=True)


def test_envelope_cleanup_is_explicit_bounded_and_can_be_disabled():
    r,cfg=contract();shape=md.Manifold.cube((250,24.98,150)).translate((0,-12.49,0))
    cleaned,info=restore(shape,dict(cfg,envelope_snap_mm=.05))
    assert info['envelope_snapped_vertices']>0
    assert info['maximum_snapped_vertex_displacement_mm']<=np.sqrt(3)*.05
    unchanged,disabled=restore(shape,dict(cfg,envelope_snap_mm=0))
    assert disabled['envelope_snapped_vertices']==0
    assert cleaned.volume()>=unchanged.volume()
    with pytest.raises(ValueError,match='Envelope cleanup'):restore(shape,dict(cfg,envelope_snap_mm=-1))
