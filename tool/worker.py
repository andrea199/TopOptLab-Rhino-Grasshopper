# SPDX-License-Identifier: GPL-3.0-or-later
"""Rhino-independent 2D worker for the Grasshopper example.

Run with external Python >=3.12.4. Geometry is discretized by Rhino; the
request contains explicit cell/node indices, so the solved grid is the preview.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import traceback
import warnings

import numpy as np
from scipy.ndimage import label
from scipy.sparse import diags
from scipy.sparse.linalg import MatrixRankWarning
from topoptlab.elements.bilinear_quadrilateral import create_edofMat, bmatrix_rectangle
from topoptlab.elements.linear_elasticity_2d import lk_linear_elast_2d
from topoptlab.fem import create_matrixinds, assemble_matrix, apply_bc
from topoptlab.filter.matrix_filter import assemble_matrix_filter
from topoptlab.material_interpolation import simp, simp_dx
from topoptlab.optimizer.optimality_criterion import oc_top88
from topoptlab.solve_linsystem import solve_lin


def write_json(path, value):
    path = Path(path)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')), encoding='utf8')
    # A Rhino reader may hold the previous snapshot briefly on Windows.
    for attempt in range(20):
        try:
            temp.replace(path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(.025)


def number(value, name, low, high):
    if isinstance(value, bool) or not np.isscalar(value):
        raise ValueError(f'{name}: expected a number')
    value = float(value)
    if not np.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name}: expected {low} .. {high}')
    return value


def integer(value, name, low, high):
    result = number(value, name, low, high)
    if result != int(result):
        raise ValueError(f'{name}: expected an integer')
    return int(result)


def indices(values, name, size, allow_empty=False):
    raw = np.asarray(values)
    if raw.ndim != 1 or (not allow_empty and not raw.size):
        raise ValueError(f'{name}: expected a nonempty list of indices')
    if raw.size and (raw.dtype.kind not in 'iu' or np.any(raw < 0) or np.any(raw >= size)):
        raise ValueError(f'{name}: invalid grid index')
    a = raw.astype(int)
    if len(np.unique(a)) != len(a):
        raise ValueError(f'{name}: duplicate indices')
    return a


class Model:
    def __init__(self, request):
        if request.get('schema') != 'topoptlab-gh-request-v1':
            raise ValueError('Unsupported request schema')
        self.request = request
        self.mode = request.get('mode', 'optimize')
        if self.mode not in ('optimize', 'fem'):
            raise ValueError('Unknown analysis mode')
        d, s = request['domain'], request['settings']
        nx = integer(d['nx'], 'nx', 2, 500)
        ny = integer(d['ny'], 'ny', 2, 500)
        if nx * ny > 60000:
            raise ValueError('Use at most 60000 bounding-box cells')
        h = number(d['cell'], 'cell size', 1e-9, 1e9)
        if number(s.get('memory_budget_gib', 0), 'RAM budget', 0, 1e9) > 0:
            raise ValueError('Explicit RAM budget is currently supported for 3D only; use 0 for 2D')
        radius_length = number(s.get('radius_length', 0), 'physical filter radius', 0, 1e9)
        origin = np.asarray(d['origin'], float)
        if origin.shape != (2,) or not np.isfinite(origin).all():
            raise ValueError('Invalid local grid origin')
        frame = np.asarray(d['frame'], float)
        if frame.shape != (3, 3) or not np.isfinite(frame).all() or not np.allclose(frame[1:] @ frame[1:].T, np.eye(2), atol=1e-8):
            raise ValueError('Frame must contain an origin and two orthonormal axes')
        self.frame = frame
        self.active = indices(d['active'], 'active cells', nx * ny)
        solids = indices(d.get('solid', []), 'solid cells', nx * ny, True)
        if not np.isin(solids, self.active).all():
            raise ValueError('Preserved cells must belong to the domain')
        mask = np.zeros(nx * ny, bool)
        mask[self.active] = True
        if label(mask.reshape(nx, ny))[1] != 1:
            raise ValueError('The grid has disconnected pieces. Increase resolution or connect the domain.')
        self.n = len(self.active)
        self.keep = np.isin(self.active, solids)
        self.design = ~self.keep
        if self.mode == 'optimize':
            if not self.design.any():
                raise ValueError('No cells remain available for optimization')
            self.target = number(s['volume'], 'volume fraction', .05, .95)
            self.design_budget = self.target * self.n - self.keep.sum()
            if self.design_budget <= 1e-6:
                raise ValueError('Preserved material already consumes the budget. Increase Volume or reduce Keep.')
            self.iterations = integer(s['iterations'], 'iterations', 1, 1000)
            self.radius = number(radius_length / h if radius_length else s['radius'],
                                 'filter radius in cells (physical radius / cell size)', 1, min(10, nx, ny))
        young = number(s.get('young', 1), 'Young modulus', 1e-12, 1e15)
        nu = number(s.get('poisson', .3), 'Poisson ratio', 0, .49)
        thickness = number(s.get('thickness', 1), 'thickness', 1e-9, 1e9)
        self.penal = number(s.get('penal', 3), 'SIMP exponent', 1, 5)
        self.young, self.nu, self.thickness, self.h = young, nu, thickness, h
        xx, yy = np.meshgrid(origin[0] + np.arange(nx + 1) * h,
                             origin[1] + np.arange(ny, -1, -1) * h, indexing='ij')
        fullnodes = np.column_stack((xx.ravel(), yy.ravel()))
        edof, *_ = create_edofMat(nx, ny, nnode_dof=2)
        fullfaces = edof[self.active, ::2] // 2
        self.grid_node_ids = np.unique(fullfaces)
        remap = np.full(len(fullnodes), -1, int)
        remap[self.grid_node_ids] = np.arange(len(self.grid_node_ids))
        self.nodes = fullnodes[self.grid_node_ids]
        self.faces = remap[fullfaces]
        self.edof = (2 * self.faces[:, :, None] + np.arange(2)).reshape(self.n, 8)
        self.ndof = 2 * len(self.nodes)
        self.iK, self.jK = create_matrixinds(self.edof)
        self.KE = lk_linear_elast_2d(E=young, nu=nu, plane_stress=True, l=np.array([h, h]), t=thickness)
        # Filter only variable cells. Holes are absent from FEM, and preserved
        # material is a constant term in both density and volume derivatives.
        if self.mode == 'optimize':
            H, _ = assemble_matrix_filter(nx, ny, rmin=float(self.radius))
            variable = self.active[self.design]
            H = H.tocsr()[variable][:, variable]
            self.filter = (diags(1 / np.asarray(H.sum(axis=1)).ravel()) @ H).tocsr()
            self.dv = np.asarray(self.filter.T @ np.ones(len(variable))).ravel()

        def mapped(group):
            ids = indices(group['nodes'], 'selected nodes', len(fullnodes))
            if np.any(remap[ids] < 0):
                raise ValueError('A selected node does not belong to an active element')
            return remap[ids]

        fixed = []
        for support in request['supports']:
            ids = mapped(support)
            if not isinstance(support['fix_x'], bool) or not isinstance(support['fix_y'], bool):
                raise ValueError('Support directions must be booleans')
            if not support['fix_x'] and not support['fix_y']:
                raise ValueError('A support must constrain at least one direction')
            if support['fix_x']:
                fixed.extend(2 * ids)
            if support['fix_y']:
                fixed.extend(2 * ids + 1)
        self.fixed = np.unique(fixed).astype(int)
        self.free = np.setdiff1d(np.arange(self.ndof), self.fixed)
        if not self.free.size:
            raise ValueError('All degrees of freedom are constrained')
        xy = (self.nodes - self.nodes.mean(axis=0)) / max(np.ptp(self.nodes, axis=0))
        rigid = np.zeros((self.ndof, 3))
        rigid[::2, 0], rigid[1::2, 1] = 1, 1
        rigid[::2, 2], rigid[1::2, 2] = -xy[:, 1], xy[:, 0]
        if len(self.fixed) < 3 or np.linalg.matrix_rank(rigid[self.fixed]) < 3:
            raise ValueError('Supports permit rigid translation or rotation. Add or move supports.')
        self.forces = np.zeros((self.ndof, 1))
        for load in request['loads']:
            ids = mapped(load)
            force = np.asarray(load['force'], float)
            if force.shape != (2,) or not np.isfinite(force).all() or np.linalg.norm(force) == 0:
                raise ValueError('Load force must be a finite, nonzero in-plane vector')
            # One load component specifies TOTAL force, independent of resolution.
            for axis in (0, 1):
                dofs = 2 * ids + axis
                if force[axis] != 0 and np.isin(dofs, self.fixed).any():
                    raise ValueError('A force acts in a constrained direction. Move the load or support.')
                self.forces[dofs, 0] += force[axis] / len(ids)
        self.force_scale = float(np.max(np.abs(self.forces)))
        if not self.force_scale and not request.get('engineering'):
            raise ValueError('Apply at least one nonzero resulting force')

    def density(self, x):
        rho = np.ones(self.n)
        rho[self.design] = np.asarray(self.filter @ x).ravel()
        if np.any((rho < -1e-12) | (rho > 1+1e-12)):
            raise ValueError('Filtered density outside physical bounds')
        return np.clip(rho,0,1)

    def initial(self):
        return np.full(int(self.design.sum()), self.design_budget / self.design.sum())

    def solve(self, rho):
        if self.request['settings'].get('backend'):
            from fem_backends import solve_model
            return solve_model(self,rho)
        rho = np.asarray(rho)
        if rho.shape != (self.n,) or not np.isfinite(rho).all() or np.any((rho < 0) | (rho > 1)):
            raise ValueError('Invalid density array')
        scale = simp(rho, eps=1e-6, penal=self.penal)
        K = assemble_matrix((scale[:, None, None] * self.KE).ravel(), self.iK, self.jK,
                            ndof=self.ndof, solver='scipy-direct', springs=None)
        reduced = apply_bc(K, solver='scipy-direct', free=self.free, fixed=self.fixed)
        u = np.zeros_like(self.forces)
        with warnings.catch_warnings():
            warnings.simplefilter('error', MatrixRankWarning)
            u[self.free], _, _ = solve_lin(reduced, self.forces[self.free], solver='scipy-direct')
        if not np.isfinite(u).all():
            raise ValueError('The mechanical system is singular')
        reactions = K @ u - self.forces
        residual = float(np.max(abs(reactions[self.free])) / self.force_scale)
        # Only constrained reactions enter equilibrium; free residuals must not
        # be included or this check would cancel the numerical error by definition.
        supported = np.zeros_like(reactions)
        supported[self.fixed] = reactions[self.fixed]
        total = (supported + self.forces).reshape(-1, 2)
        centered = self.nodes - self.nodes.mean(axis=0)
        moment = np.sum(centered[:, 0] * total[:, 1] - centered[:, 1] * total[:, 0])
        span = max(np.ptp(self.nodes, axis=0))
        balance = max(np.max(abs(total.sum(axis=0))) / self.force_scale, abs(moment) / (self.force_scale * span))
        if max(residual, balance) > 1e-5:
            raise ValueError('Force balance failed. Check connectivity and supports.')
        ue = u[self.edof, 0]
        energy = np.einsum('ei,ij,ej->e', ue, self.KE, ue)
        compliance = float(np.sum(self.forces * u))
        if compliance <= 0 or not np.isclose(compliance, scale @ energy, rtol=1e-5):
            raise ValueError('Work/energy verification failed')
        dc = (np.asarray(self.filter.T @ (-simp_dx(rho, eps=1e-6, penal=self.penal) * energy)[self.design]).ravel()
              if self.mode == 'optimize' else None)
        return dict(compliance=compliance, displacement=u.reshape(-1, 2), gradient=dc,
                    reactions=supported.reshape(-1, 2), residual=residual, balance=float(balance))

    def stress(self, displacement):
        """Plane-stress tensor in DOMAIN axes at four 2x2 Gauss points.

        Q4 order and B matrix come from topoptlab; shear strain is engineering
        gamma_xy. No nodal smoothing or density interpolation in full-solid FEM.
        """
        q = 1 / np.sqrt(3)
        B = bmatrix_rectangle(np.array([-q, q, q, -q]),
                              np.array([-q, -q, q, q]), self.h, self.h)
        ue = np.asarray(displacement)[self.faces].reshape(self.n, 8)
        strain = np.einsum('qij,ej->eqi', B, ue)
        C = self.young / (1 - self.nu**2) * np.array(
            [[1, self.nu, 0], [self.nu, 1, 0], [0, 0, (1-self.nu)/2]])
        stress = np.einsum('ij,eqj->eqi', C, strain)
        sx, sy, tau = np.moveaxis(stress, -1, 0)
        vm = np.sqrt(np.maximum(0, sx*sx - sx*sy + sy*sy + 3*tau*tau))
        return stress, vm

    def fem_payload(self, response, job_id):
        stress, vm = self.stress(response['displacement'])
        origin, ax, ay = self.frame
        world = origin + self.nodes[:, :1] * ax + self.nodes[:, 1:] * ay
        def vectors(v):
            return (v[:, :1] * ax + v[:, 1:] * ay).tolist()
        return dict(schema='topoptlab-gh-fem-result-v1', mode='fem', job_id=job_id,
                    status='completed', nodes=world.tolist(), faces=self.faces.tolist(),
                    frame=self.frame.tolist(), cell_ids=self.active.tolist(),
                    grid_node_ids=self.grid_node_ids.tolist(),
                    displacement=vectors(response['displacement']),
                    reactions=vectors(response['reactions']),
                    stress_gauss=stress.tolist(), stress_mean=stress.mean(axis=1).tolist(),
                    von_mises=vm.max(axis=1).tolist(),
                    material=dict(young=self.young, poisson=self.nu, thickness=self.thickness),
                    metrics=dict(compliance=response['compliance'],
                                 max_displacement=float(np.linalg.norm(response['displacement'], axis=1).max()),
                                 max_von_mises=float(vm.max()),
                                 residual=response['residual'], equilibrium=response['balance']),
                    notes='Full active domain; holes absent; Keep ignored. Plane stress, small strain. '
                          'Stress in domain axes, force/length^2; VM is max of 4 Gauss points per cell. '
                          'Point loads and sharp restraints can create mesh-dependent stress peaks.')

    def step(self, x, response, baseline):
        rho = self.density(x)
        proposed, _ = oc_top88(x=x, volfrac=self.target,
                              dc=np.minimum(response['gradient'] / baseline, -1e-30),
                              dv=self.dv, g=float(rho.sum() - self.target * self.n),
                              el_flags=None, move=.15)
        used = float(self.dv @ proposed)
        # Conservative correction for the upstream OC bisection tolerance.
        if used > self.design_budget:
            proposed *= self.design_budget / used
        return proposed

    def payload(self, rho, response, iteration, baseline, status, history, job_id):
        origin, ax, ay = self.frame
        world = origin + self.nodes[:, :1] * ax + self.nodes[:, 1:] * ay
        u = response['displacement']
        world_u = u[:, :1] * ax + u[:, 1:] * ay
        return dict(schema='topoptlab-gh-result-v1', job_id=job_id, status=status,
                    iteration=iteration, completed_iterations=len(history) - 1,
                    nodes=world.tolist(), faces=self.faces.tolist(), density=rho.tolist(),
                    displacement=world_u.tolist(), kept=self.keep.tolist(),
                    metrics=dict(compliance=response['compliance'], initial_compliance=baseline,
                                 improvement_percent=100 * (1 - response['compliance'] / baseline),
                                 volume=float(rho.mean()), target_volume=self.target,
                                 max_displacement=float(np.linalg.norm(u, axis=1).max()),
                                 residual=response['residual'], equilibrium=response['balance']),
                    history=history)


def run(request, out):
    if request.get("workflow")=="final_geometry":
        from final_workflow import run_final
        return run_final(request,out)
    if request.get("engineering"):
        from engineering import run_engineering
        return run_engineering(request,out)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    job_id = str(request['job_id'])
    if (out / 'result.json').exists() or (out / 'progress.json').exists():
        raise ValueError('Each job requires a fresh output directory')
    last = None
    try:
        if (out / 'cancel').exists():
            write_json(out / 'progress.json', dict(job_id=job_id, status='cancelled'))
            return None
        dimension = request.get('dimension', 2)
        if dimension not in (2, 3):
            raise ValueError('Dimension must be 2 or 3')
        if dimension == 3:
            from worker3d import Model3D
            model = Model3D(request)
        else:
            model = Model(request)
        if model.mode == 'fem':
            write_json(out / 'progress.json', dict(job_id=job_id, status='running'))
            response = model.solve(np.ones(model.n))
            if (out / 'cancel').exists():
                stopped = dict(job_id=job_id, status='cancelled')
                write_json(out / 'progress.json', stopped)
                return stopped
            final = model.fem_payload(response, job_id)
            if final.get('stress_storage') == 'gauss_npz_in_case_folder':
                model.save_stress(response, out / 'stress.npz')
                final['stress_file'] = str(out / 'stress.npz')
            write_json(out / 'result.json', final)
            write_json(out / 'progress.json', final)
            return final
        x = model.initial()
        history = []
        best = None
        for iteration in range(model.iterations + 1):
            if (out / 'cancel').exists():
                stopped = last or dict(job_id=job_id)
                stopped['status'] = 'cancelled'
                write_json(out / 'progress.json', stopped)
                return stopped
            rho = model.density(x)
            response = model.solve(rho)
            if iteration == 0:
                baseline = response['compliance']
            history.append(dict(iteration=iteration, compliance=response['compliance'], volume=float(rho.mean())))
            if best is None or response['compliance'] < best[1]['compliance']:
                best = (rho.copy(), response, iteration)
            last = model.payload(rho, response, iteration, baseline, 'running', history, job_id)
            if iteration == 0:
                write_json(out / 'initial.json', last)
            if iteration % 5 == 0 or iteration == model.iterations:
                write_json(out / 'progress.json', last)
            if iteration < model.iterations:
                x = model.step(x, response, baseline)
        if (out / 'cancel').exists():
            last['status'] = 'cancelled'
            write_json(out / 'progress.json', last)
            return last
        rho, response, iteration = best
        final = model.payload(rho, response, iteration, baseline, 'completed', history, job_id)
        write_json(out / 'history.json', history)
        write_json(out / 'result.json', final)
        write_json(out / 'progress.json', final)
        return final
    except Exception as exc:
        write_json(out / 'progress.json', dict(job_id=job_id, status='error', message=str(exc)))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        request = json.loads(args.request.read_text(encoding='utf-8-sig'))
        run(request, args.output)
    except Exception:
        (args.output / 'error.log').write_text(traceback.format_exc(), encoding='utf8')
        raise


if __name__ == '__main__':
    main()
