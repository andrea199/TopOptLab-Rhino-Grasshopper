# SPDX-License-Identifier: GPL-3.0-or-later
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scenarios import CATALOG,request
from worker import Model,run

@pytest.mark.parametrize('index',range(4))
@pytest.mark.parametrize('mode',['fem','optimize'])
def test_scenario_full_run(index,mode,tmp_path):
    r=request(index,mode);m=Model(r);c=CATALOG[index]
    assert np.sum(m.forces[1::2])==pytest.approx(-len(c['loads']))
    if index in (0,3):assert len(r['supports'][0]['nodes'])==25
    result=run(r,tmp_path)
    assert result['status']=='completed'
    assert result['metrics']['equilibrium']<1e-6
    assert np.isfinite(result['displacement']).all()
    if mode=='fem':
        assert np.min(result['von_mises'])>=0
        assert np.max(result['von_mises'])>0
        assert np.allclose(np.sum(result['reactions'],axis=0),[0,len(c['loads']),0],atol=1e-7)
    else:
        assert result['completed_iterations']==80
        assert result['metrics']['volume']<=c['volume']+1e-10
        assert result['metrics']['improvement_percent']>0
        assert all(np.array(result['density'])[m.keep]==1)

@pytest.mark.parametrize('index',range(4))
@pytest.mark.parametrize('prefix',['fem','opt'])
def test_scenario_archive(index,prefix):
    root=ET.parse(Path(__file__).resolve().parents[1]/'examples'/f'{prefix}_{CATALOG[index]["id"]}.ghx')
    ids=[i.text for i in root.iter('item') if i.get('name')=='InstanceGuid']
    assert len(ids)==len(set(ids))
    assert set(i.text for i in root.iter('item') if i.get('name')=='Source')<=set(ids)
    assert len([i for i in root.iter('item') if i.get('name')=='ExpressionNormal' and i.text=='False'])==(3 if prefix=='fem' else 4)
    assert root.find("./chunks/chunk[@name='Definition']/chunks/chunk[@name='DefinitionProperties']/items/item[@name='Date']") is not None
    for items in root.iter('items'):
        counts=[int(i.text) for i in items if i.get('name')=='SourceCount']
        if counts:assert counts[0]==sum(i.get('name')=='Source' for i in items)

@pytest.mark.parametrize('index',range(4))
@pytest.mark.parametrize('prefix',['fem','opt'])
def test_scenario_persistent_inputs_replace_defaults(index,prefix):
    root=ET.parse(Path(__file__).resolve().parents[1]/'examples'/f'{prefix}_{CATALOG[index]["id"]}.ghx')
    objects=root.findall('.//chunk[@name="Object"]/chunks/chunk[@name="Container"]')
    def named(name):
        return [c for c in objects if c.find('./items/item[@name="Name"]').text==name]
    def values(c,index):
        return [i.text for i in c.findall(f'./chunks/chunk[@name="param_input"][@index="{index}"]/chunks/chunk[@name="PersistentData"]//chunk[@name="Item"]/items/item')]
    assert values(named('TopOpt Scenario Geometry')[0],0)==[str(index)]
    for component,support in zip(named('TopOpt Support'),CATALOG[index]['supports']):
        assert values(component,2)==[str(support['fix_x']).lower()]
        assert values(component,3)==[str(support['fix_y']).lower()]

@pytest.mark.parametrize('filename',sorted(p.name for p in (Path(__file__).resolve().parents[1]/'examples').glob('*.ghx')))
def test_geometry_dimension_and_position_sliders(filename):
    root=ET.parse(Path(__file__).resolve().parents[1]/'examples'/filename)
    objects=root.findall('.//chunk[@name="Object"]/chunks/chunk[@name="Container"]')
    targets=[c for c in objects if c.find('./items/item[@name="Name"]').text in ['TopOpt Scenario Geometry','TopOpt Example Geometry','TopOpt Example 3D','TopOpt Shelf Bracket 3D']]
    assert len(targets)==1
    component=targets[0]
    inputs=component.findall('./chunks/chunk[@name="param_input"]')
    if 'Case'==inputs[0].find('./items/item[@name="Name"]').text:inputs=inputs[1:]
    if component.find('./items/item[@name="Name"]').text == 'TopOpt Shelf Bracket 3D':
        names=['Length / mm','Height / mm','Width / mm','Keep plate thickness / mm',
               'Nominal hole diameter / mm','Wall hole pitch / mm','Top hole inset / mm',
               'Tool access diameter / mm','Tool access depth / mm',
               'Position X / mm','Position Y / mm','Position Z / mm']
    else:
        names=['Length X','Height Y']+(['Depth Z'] if '3d' in filename else [])+['Position X','Position Y','Position Z']
    assert len(inputs)==len(names)
    by_id={c.find('./items/item[@name="InstanceGuid"]').text:c for c in objects}
    for param,name in zip(inputs,names):
        sources=param.findall('./items/item[@name="Source"]')
        assert len(sources)==1
        slider=by_id[sources[0].text]
        assert slider.find('./items/item[@name="Name"]').text=='Number Slider'
        assert slider.find('./items/item[@name="NickName"]').text==name
