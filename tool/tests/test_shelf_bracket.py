# SPDX-License-Identifier: GPL-3.0-or-later
"""Independent checks of the native C#/Rhino-exported shelf bracket fixtures."""
import copy,json,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from worker3d import Model3D
from engineering_materials import resolve
from engineering_loads import prepare_cases,preserve_interfaces,apply_case,face_geometry
FIX=Path(__file__).parent/"fixtures"/"shelf_bracket"
def fixture(k=0):
    return json.loads((FIX/f"variant-{k}.json").read_text()),json.loads((FIX/f"summary-{k}.json").read_text())

@pytest.mark.parametrize("k",range(4))
def test_native_raster_matches_analytic_circular_holes_and_tool_spaces(k):
    r,_=fixture(k);d=r["domain"];s=r["example_geometry"];h=d["cell"];ids=np.arange(d["nx"]*d["ny"]*d["nz"])
    xyz=np.column_stack(((ids//d["ny"])%d["nx"]+.5,d["ny"]-ids%d["ny"]-.5,ids//(d["nx"]*d["ny"])+.5))*h+np.array(d["origin"])-np.array(s["origin"])
    x,y,z=xyz.T;L,H,W,t=s["length_mm"],s["height_mm"],s["width_mm"],s["plate_mm"]
    inside=(x>=0)&(x<=L)&(abs(y)<=W/2)&(z>=0)&(z<=H)
    hole=s["hole_diameter_mm"]/2;tool=s["access_diameter_mm"]/2;reach=s["access_depth_mm"]
    for cz in ((H-s["wall_pitch_mm"])/2,(H+s["wall_pitch_mm"])/2):
        inside &= ~((x>=-1)&(x<=t)&(y*y+(z-cz)**2<=hole*hole+1e-8))
        inside &= ~((x>=t)&(x<=t+reach)&(y*y+(z-cz)**2<=tool*tool+1e-8))
    for cx in (s["top_inset_mm"],L-s["top_inset_mm"]):
        inside &= ~((z>=H-t)&(z<=H+1)&((x-cx)**2+y*y<=hole*hole+1e-8))
        inside &= ~((z>=H-t-reach)&(z<=H-t)&((x-cx)**2+y*y<=tool*tool+1e-8))
    assert d["active"]==ids[inside].tolist()
    assert d["solid"]==ids[inside&((x<=t)|(z>=H-t))].tolist()

@pytest.mark.parametrize("k",range(4))
def test_total_payload_and_moment_survive_resize_translation_and_remeshing(k):
    r,summary=fixture(k);r=copy.deepcopy(r);material=resolve(r["material"])
    r["settings"].update(young=material["young"],poisson=material["poisson"]);r["loads"]=[]
    preserve_interfaces(r);model=Model3D(r);cases=prepare_cases(model,r["load_cases"],material)
    assert len(cases)==4
    origin=np.asarray(summary["origin_mm"]);active=set(r["domain"]["active"]);all_supported=set(r["supports"][0]["nodes"])
    assert all_supported
    for i,(case,description) in enumerate(zip(cases,summary["cases"])):
        # Independently integrate only payload facets using Python HEX8 face geometry.
        load=r["load_cases"][i]["loads"][0];payload=np.zeros_like(model.nodes);mapping={int(n):j for j,n in enumerate(model.grid_node_ids)}
        for face in load["faces"]:
            ns,_=face_geometry(r["domain"],3,face,active)
            assert set(ns).isdisjoint(all_supported)
            for n in ns:payload[mapping[n]]+=np.asarray(load["traction"])*model.h**2/4
        assert payload.sum(axis=0)==pytest.approx([0,0,-summary["payload_kg"]*9.80665],abs=1e-10)
        moment=np.cross(model.nodes-origin,payload).sum(axis=0)
        assert moment==pytest.approx(description["payload_moment_about_wall_origin_nmm"],abs=1e-7)
        full=apply_case(model,case,np.ones(model.n)).reshape(-1,3)
        mass=model.n*model.h**3*1e-9*material["density_kg_m3"]
        expected=-(summary["payload_kg"]+summary["shelf_kg_per_bracket"]+mass)*9.80665
        assert full.sum(axis=0)==pytest.approx([0,0,expected],abs=1e-9)
    # Opposite eccentric loads are separate cases, never summed into cancellation.
    moments=np.array([x["payload_moment_about_wall_origin_nmm"] for x in summary["cases"]])
    assert moments[2,0]<moments[3,0]
    assert len({c["name"] for c in cases})==4

def test_default_lateral_symmetry_and_reference_load():
    r,s=fixture();a=np.array([x["payload_moment_about_wall_origin_nmm"] for x in s["cases"]])
    assert a[2,0]==pytest.approx(-a[3,0]);assert a[0,0]==pytest.approx(0,abs=1e-8)
    assert a[2,1]==pytest.approx(a[3,1])
    assert s["payload_kg"]==4 and s["shelf_kg_per_bracket"]==.5
    assert s["cases"][0]["payload_force_n"]==pytest.approx(39.2266)
    assert r["material"]["preset"]=="abs"
    assert r["design_limits"]["max_stress_mpa"]==0

def test_archive_bracket_connections_and_four_case_selection():
    import xml.etree.ElementTree as ET
    root=ET.parse(Path(__file__).resolve().parents[1]/"examples/engineering_shelf_bracket_3d.ghx")
    names=[i.text for i in root.iter("item") if i.get("name")=="Name"]
    assert "TopOpt Shelf Bracket 3D" in names and "TopOpt Bracket Conditions 3D" in names
    ids=[i.text for i in root.iter("item") if i.get("name")=="InstanceGuid"]
    assert len(ids)==len(set(ids))
    assert set(i.text for i in root.iter("item") if i.get("name")=="Source")<=set(ids)
    for items in root.iter("items"):
        count=next((i for i in items if i.get("name")=="SourceCount"),None)
        if count is not None:assert int(count.text)==sum(i.get("name")=="Source" for i in items)


def test_fine_archive_cad_wiring_and_physical_filter():
    import xml.etree.ElementTree as ET
    root=ET.parse(Path(__file__).resolve().parents[1]/"examples/engineering_shelf_bracket_3d.ghx")
    objects=root.findall('.//chunk[@name="Object"]/chunks/chunk[@name="Container"]')
    def named(name):return next(c for c in objects if c.find('./items/item[@name="Name"]').text==name)
    def sources(component,index):return component.findall(f'./chunks/chunk[@name="param_input"][@index="{index}"]/items/item[@name="Source"]')
    final=named('TopOpt Final Geometry 3D')
    assert len(sources(final,8))==1 and len(sources(final,9))==1 and len(sources(final,10))==1 and len(sources(final,11))==1 and len(sources(final,12))==1
    settings=named('TopOpt Engineering Settings')
    assert len(sources(settings,16))==1 and len(sources(settings,17))==1
    sliders={c.find('./items/item[@name="NickName"]').text:c for c in objects if c.find('./items/item[@name="Name"]').text=='Number Slider'}
    def value(name):return float(sliders[name].find('./chunks/chunk[@name="Slider"]/items/item[@name="Value"]').text)
    assert value('Cell size')==2.5
    assert value('Voxel limit')>=121875
    assert value('Physical filter radius / mm')==9
    assert value('CAD hole chord tolerance / mm')==.05

    assert value('CAD envelope cleanup / mm / 0 off')==0

    assert value('CAD web cleanup / mm / 0 off')==.01

    assert value('Verification threshold')==.32
