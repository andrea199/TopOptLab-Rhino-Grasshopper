# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit FEM checks and differentiable density-design constraints.
Stress during optimization is sqrt(rho) * VM(C B u), a relaxed surrogate.
It is never presented as a verification of a thresholded final shape.
"""
from itertools import product
import numpy as np
from topoptlab.material_interpolation import simp, simp_dx
from topoptlab.elements.bilinear_quadrilateral import bmatrix_rectangle
from topoptlab.elements.trilinear_hexahedron import bmatrix_cuboid
from worker import number


def resolve_limits(spec, material):
    if spec is None: spec = {}
    if not isinstance(spec, dict): raise ValueError('Design Limits must be an object')
    u = number(spec.get('max_displacement', 0), 'displacement limit', 0, 1e12)
    stress_mpa = number(spec.get('max_stress_mpa', 0), 'stress limit MPa', 0, 1e12)
    use_material = spec.get('use_material_allowable', False)
    enforce = spec.get('enforce', True)
    if not isinstance(use_material, bool) or not isinstance(enforce, bool):
        raise ValueError('Design limit switches must be booleans')
    if stress_mpa and use_material: raise ValueError('Choose explicit stress limit OR material allowable, not both')
    stress = stress_mpa*1e6*material['length_m']**2/material['force_n']
    if use_material:
        if material['allowable'] is None:
            raise ValueError('Material allowable unavailable; specify stock data or an explicit stress limit')
        stress = material['allowable']
        stress_mpa = stress*material['force_n']/material['length_m']**2/1e6
    tolerance = number(spec.get('tolerance', .001), 'constraint tolerance', 1e-8, .01)
    aggregation = number(spec.get('aggregation', 50), 'KS aggregation', 10, 200)
    return dict(max_displacement=u, max_stress=stress, max_stress_mpa=stress_mpa,
                stress_source='material_screening_allowable' if use_material else 'user_limit',
                enforce=enforce, active=bool(u or stress), tolerance=tolerance, aggregation=aggregation)


def ks_upper(values, sharpness):
    """Unnormalised log-sum-exp: a conservative upper bound of the sampled maximum."""
    values = np.asarray(values, float)
    if not values.size or not np.isfinite(values).all(): raise ValueError('Invalid constraint field')
    maximum = float(values.max()); exp = np.exp(sharpness*(values-maximum)); total = float(exp.sum())
    return maximum+np.log(total)/sharpness, exp/total


def stress_operator(model):
    if hasattr(model, '_stress_operator'): return model._stress_operator
    q = 1/np.sqrt(3)
    if model.nodes.shape[1] == 2:
        B = bmatrix_rectangle(np.array([-q,q,q,-q]), np.array([-q,-q,q,q]), model.h, model.h)
        C = model.young/(1-model.nu**2)*np.array([[1,model.nu,0],[model.nu,1,0],[0,0,(1-model.nu)/2]])
    else:
        points = np.array(list(product([-q,q], repeat=3)))
        B = bmatrix_cuboid(points[:,0],points[:,1],points[:,2],model.h,model.h,model.h)
        C = model.constitutive()
    model._stress_operator = np.einsum('ij,qjk->qik', C, B)
    return model._stress_operator


def von_mises_gradient(stress, vm):
    result = np.zeros_like(stress)
    if stress.shape[-1] == 3:
        result[...,0] = stress[...,0]-.5*stress[...,1]
        result[...,1] = stress[...,1]-.5*stress[...,0]
        result[...,2] = 3*stress[...,2]
    else:
        result[...,:3] = 1.5*stress[...,:3]-.5*stress[...,:3].sum(axis=-1, keepdims=True)
        result[...,3:] = 3*stress[...,3:]
    return np.divide(result, vm[...,None], out=np.zeros_like(result), where=vm[...,None]>0)


def adjoint_gradient(model, case, rho, response, rhs, explicit, constraint_kind=None):
    scale = simp(rho, eps=1e-6, penal=model.penal)
    if np.any(rhs[model.free]):
        key=None if constraint_kind is None else ('adjoint',case['name'],constraint_kind)
        adjoint, _, _ = model.engine.solve(scale, rhs,cache_key=key)
    else: adjoint = np.zeros(model.ndof)
    ue = response['displacement'].ravel()[model.edof]; le = adjoint[model.edof]
    cross = np.einsum('ei,ij,ej->e', le, model.KE, ue)
    physical = explicit-simp_dx(rho, eps=1e-6, penal=model.penal)*cross
    if case['body'] is not None: physical += np.asarray(case['body'].T@adjoint).ravel()
    return np.asarray(model.filter.T@physical[model.design]).ravel()


def evaluate_limits(model, case, rho, response, limits, gradients=False):
    dim = model.nodes.shape[1]; optimized = model.mode == 'optimize'
    values = []; jacobian = []; checks = []
    displacement = response['displacement']; magnitudes = np.linalg.norm(displacement, axis=1)
    stress, vm = model.stress(displacement)
    relaxation = np.sqrt(rho) if optimized else np.ones(model.n)
    sampled_stress = vm*relaxation[:,None]
    response['von_mises_relaxed' if optimized else 'von_mises'] = sampled_stress.max(axis=1)
    for kind, field, limit in [('displacement', magnitudes, limits['max_displacement']),
                               ('stress', sampled_stress, limits['max_stress'])]:
        if not limit: continue
        ratios = field/limit; aggregate, weights = ks_upper(ratios, limits['aggregation'])
        index = np.unravel_index(np.argmax(field), field.shape); maximum = float(field[index]); ratio = maximum/limit
        check = dict(kind=kind, value=maximum, limit=limit, utilization=ratio,
                     status='within_limit' if ratio<=1 else 'within_tolerance' if ratio<=1+limits['tolerance'] else 'exceeded',
                     aggregated_utilization=aggregate)
        if kind == 'displacement':
            check['grid_node_id'] = int(model.grid_node_ids[index[0]])
        else:
            check.update(cell_id=int(model.active[index[0]]), gauss_point=int(index[1]),
                         field='sqrt-density relaxed von Mises' if optimized else 'full-material von Mises')
        checks.append(check); values.append(aggregate-1)
        if gradients:
            explicit = np.zeros(model.n)
            if kind == 'displacement':
                derivative = np.divide(displacement, magnitudes[:,None], out=np.zeros_like(displacement), where=magnitudes[:,None]>0)
                rhs = (derivative*(weights/limit)[:,None]).ravel()
            else:
                dvm = von_mises_gradient(stress, vm)
                derivative = dvm*(weights*relaxation[:,None]/limit)[...,None]
                element_rhs = np.einsum('qij,eqi->ej', stress_operator(model), derivative)
                rhs = np.bincount(model.edof.ravel(), weights=element_rhs.ravel(), minlength=model.ndof)
                if optimized:
                    explicit = np.sum(weights*vm, axis=1)*.5/(np.sqrt(rho)*limit)
            jacobian.append(adjoint_gradient(model, case, rho, response, rhs, explicit, constraint_kind=kind))
    return dict(values=np.asarray(values), jacobian=np.asarray(jacobian), checks=checks,
                scope='relaxed_density_model_only' if optimized else 'full_material_fem',
                max_stress=float(sampled_stress.max()))


def summarize_limits(limits, case_checks, mode):
    checks = [check for case in case_checks for check in case['checks']]
    worst = max((c['utilization'] for c in checks), default=None)
    status = 'not_requested' if not checks else ('exceeded' if worst>1+limits['tolerance'] else 'within_tolerance' if worst>1 else 'within_limits')
    return dict(status=status, requested=limits, cases=case_checks, worst_utilization=worst,
                scope='relaxed_density_model_only' if mode=='optimize' else 'binary_voxel_fem' if mode=='verify' else 'full_solid_fem',
                enforced_during_optimization=bool(limits['enforce'] and limits['active'] and mode=='optimize'),
                final_shape_reanalysed=mode=='verify',
                final_shape_verified=mode=='verify' and bool(checks) and status in ('within_limits','within_tolerance'),
                note='Numerical limits on this model, not code compliance. Relaxed design stress is not final-shape stress.')
