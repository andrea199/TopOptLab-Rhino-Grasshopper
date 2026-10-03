# SPDX-License-Identifier: GPL-3.0-or-later
import copy
import json
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from worker import Model, run
from sample_problem import example as plate_example


def example(nx=24, ny=12, iterations=15):
    r = plate_example(nx, ny, iterations)
    r['job_id'] = 'test'
    return r


def test_holes_removed_and_kept_material_constant():
    model = Model(example())
    centers = model.nodes[model.faces].mean(axis=1)
    assert np.all(np.linalg.norm(centers - [6, 3], axis=1) >= 1)
    rho = model.density(model.initial())
    assert np.all(rho[model.keep] == 1)
    assert rho.mean() == pytest.approx(model.target)
    assert len(model.nodes) < 25 * 13  # Unused hole nodes have no artificial stiffness.


def test_filtered_gradient_and_volume_with_hole_and_keep():
    model = Model(example())
    x = model.initial()
    rng = np.random.default_rng(56)
    direction = rng.normal(size=len(x))
    direction /= np.linalg.norm(direction)
    eps = 1e-5
    response = model.solve(model.density(x))
    plus, minus = model.density(x + eps * direction), model.density(x - eps * direction)
    numerical = (model.solve(plus)['compliance'] - model.solve(minus)['compliance']) / (2 * eps)
    assert numerical == pytest.approx(response['gradient'] @ direction, rel=2e-5)
    assert (plus.sum() - minus.sum()) / (2 * eps) == pytest.approx(model.dv @ direction, rel=1e-7)


def test_optimization_consistency_budget_and_equilibrium(tmp_path):
    request = example(iterations=25)
    result = run(request, tmp_path)
    m = Model(request)
    rho = np.array(result['density'])
    measured = m.solve(rho)
    assert result['status'] == 'completed'
    assert result['metrics']['improvement_percent'] > 40
    assert all(row['volume'] <= m.target + 1e-10 for row in result['history'])
    assert np.all(rho[m.keep] == 1)
    assert measured['compliance'] == pytest.approx(result['metrics']['compliance'])
    assert np.allclose(measured['displacement'], np.array(result['displacement'])[:, :2])
    assert measured['balance'] < 1e-6
    assert json.loads((tmp_path / 'result.json').read_text())['job_id'] == 'test'
    with pytest.raises(ValueError, match='fresh'):
        run(request, tmp_path)


def test_distributed_force_is_total():
    request = example()
    request['loads'][0]['nodes'] = [10 * 13, 11 * 13, 12 * 13]
    m = Model(request)
    assert m.forces[1::2].sum() == pytest.approx(-.001)
    assert np.count_nonzero(m.forces) == 3


@pytest.mark.parametrize('kind', ['rigid', 'budget', 'constrained_load', 'disconnected', 'unused_node', 'duplicate', 'fractional_grid', 'empty_load', 'invalid_frame'])
def test_reject_bad_inputs(kind):
    r = example()
    if kind == 'rigid':
        r['supports'] = r['supports'][:1]
    elif kind == 'budget':
        r['settings']['volume'] = .05
    elif kind == 'constrained_load':
        r['loads'][0]['nodes'] = [12]
    elif kind == 'disconnected':
        r['domain']['active'] = [i for i in r['domain']['active'] if i // 12 != 4]
    elif kind == 'unused_node':
        r['loads'][0]['nodes'] = [12 * 13 + 6]
    elif kind == 'duplicate':
        r['loads'][0]['nodes'] *= 2
    elif kind == 'fractional_grid':
        r['domain']['nx'] = 24.5
    elif kind == 'empty_load':
        r['loads'] = []
    else:
        r['domain']['frame'][1] = [2, 0, 0]
    with pytest.raises(ValueError):
        Model(r)


def test_cancel_does_not_publish_completed_result(tmp_path):
    (tmp_path / 'cancel').touch()
    assert run(example(), tmp_path) is None
    assert not (tmp_path / 'result.json').exists()
    assert json.loads((tmp_path / 'progress.json').read_text())['status'] == 'cancelled'


def test_cancel_between_iterations(tmp_path, monkeypatch):
    original = Model.solve
    def solve_and_cancel(self, rho):
        response = original(self, rho)
        (tmp_path / 'cancel').touch()
        return response
    monkeypatch.setattr(Model, 'solve', solve_and_cancel)
    result = run(example(), tmp_path)
    assert result['status'] == 'cancelled'
    assert not (tmp_path / 'result.json').exists()
    assert result['completed_iterations'] == 0


def test_error_publishes_actionable_status(tmp_path):
    r = example()
    r['supports'] = []
    with pytest.raises(ValueError):
        run(r, tmp_path)
    assert json.loads((tmp_path / 'progress.json').read_text())['status'] == 'error'
    assert not (tmp_path / 'result.json').exists()


def test_rotated_plane_changes_world_coordinates_not_mechanics():
    r = example(iterations=1)
    m = Model(r)
    rho = m.density(m.initial())
    response = m.solve(rho)
    r2 = copy.deepcopy(r)
    r2['domain']['frame'] = [[10, 20, 30], [0, 0, 1], [0, 1, 0]]
    m2 = Model(r2)
    assert m2.solve(rho)['compliance'] == pytest.approx(response['compliance'])
    p = m2.payload(rho, response, 0, response['compliance'], 'running', [{}], 'test')
    assert np.allclose(np.array(p['nodes'])[:, 0], 10)
    assert np.allclose(np.array(p['nodes'])[:, 2], m.nodes[:, 0] + 30)
    assert np.allclose(np.array(p['displacement'])[:, 2], response['displacement'][:, 0])


def test_material_and_thickness_scaling():
    r = example()
    a = Model(r)
    r['settings']['young'] = 7
    r['settings']['thickness'] = 3
    b = Model(r)
    rho = a.density(a.initial())
    assert b.solve(rho)['compliance'] == pytest.approx(a.solve(rho)['compliance'] / 21, rel=1e-7)
