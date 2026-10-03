# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import xml.etree.ElementTree as ET


def test_connected_example_archive():
    path = Path(__file__).resolve().parents[1] / 'examples/plate_with_hole.ghx'
    root = ET.parse(path)
    objects = next(c for c in root.iter('chunk') if c.get('name') == 'DefinitionObjects')
    count = next(i for i in objects.find('items') if i.get('name') == 'ObjectCount')
    assert int(count.text) == len(objects.find('chunks')) == 41
    ids = [i.text for i in root.iter('item') if i.get('name') == 'InstanceGuid']
    assert len(ids) == len(set(ids))
    wires = [i.text for i in root.iter('item') if i.get('name') == 'Source']
    assert len(wires) >= 30
    assert set(wires) <= set(ids)
    assert len([i for i in root.iter('item') if i.get('name') == 'ExpressionNormal' and i.text == 'False']) == 4
    # Every local SourceCount agrees with the actual wire count.
    for items in root.iter('items'):
        counts = [int(i.text) for i in items if i.get('name') == 'SourceCount']
        if counts:
            assert counts[0] == sum(i.get('name') == 'Source' for i in items)


def test_required_document_properties():
    """Regression: missing Date crashes GH_DocumentProperties.Read on open."""
    path = Path(__file__).resolve().parents[1] / 'examples/plate_with_hole.ghx'
    root = ET.parse(path)
    properties = root.find("./chunks/chunk[@name='Definition']/chunks/chunk[@name='DefinitionProperties']")
    assert properties is not None
    for name, kind in [('Name', 'gh_string'), ('Description', 'gh_string'), ('Date', 'gh_date')]:
        item = properties.find("./items/item[@name='%s']" % name)
        assert item is not None, 'Missing required document property: ' + name
        assert item.get('type_name') == kind
    projection = properties.find("./chunks/chunk[@name='Projection']")
    assert projection is not None
    assert projection.find("./items/item[@name='Target']") is not None
    assert projection.find("./items/item[@name='Zoom']") is not None


def test_fem_example_graph_and_idle_controls():
    root = ET.parse(Path(__file__).resolve().parents[1] / 'examples/fem_plate_with_hole.ghx')
    objects = root.find("./chunks/chunk[@name='Definition']/chunks/chunk[@name='DefinitionObjects']/chunks")
    assert len(objects) == 25
    guids = [o.find("./items/item[@name='GUID']").text for o in objects]
    assert '491d2743-9bd2-4a22-b86b-1764d7121e60' in guids
    assert 'b60ce452-cb02-48ac-a917-1c047bc3dd73' in guids
    ids = [i.text for i in root.iter('item') if i.get('name') == 'InstanceGuid']
    assert len(ids) == len(set(ids))
    assert set(i.text for i in root.iter('item') if i.get('name') == 'Source') <= set(ids)
    assert len([i for i in root.iter('item') if i.get('name') == 'ExpressionNormal' and i.text == 'False']) == 3
    assert root.find("./chunks/chunk[@name='Definition']/chunks/chunk[@name='DefinitionProperties']/items/item[@name='Date']") is not None
