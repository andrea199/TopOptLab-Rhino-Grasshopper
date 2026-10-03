# SPDX-License-Identifier: GPL-3.0-or-later
"""Consistent loads on Q4 edges / HEX8 faces and density-dependent self-weight.
Pressure is positive inward on fixed, preserved grid interfaces, not a follower load.
Gravity acceleration is SI m/s^2; pressure and traction use model force/length^2.
"""
import numpy as np
from scipy.sparse import coo_matrix
from worker import indices, number, integer


def face_geometry(domain, dim, face, active=None):
    nx, ny, nz = domain['nx'], domain['ny'], domain.get('nz', 1)
    e = integer(face['cell'], 'face cell', 0, nx*ny*nz-1)
    axis = integer(face['axis'], 'face axis', 0, dim-1)
    side = integer(face['side'], 'face side', -1, 1)
    if side == 0:
        raise ValueError('Face side must be -1 or +1')
    active = set(domain['active']) if active is None else active
    if e not in active:
        raise ValueError('A loaded face was removed; preserve the loading interface')
    x, y, z = (e//ny) % nx, e % ny, e//(nx*ny)
    neighbor = [x, y, z]
    neighbor[axis] += -side if axis == 1 else side
    if all(0 <= n < size for n, size in zip(neighbor, (nx, ny, nz))):
        other = neighbor[2]*nx*ny + neighbor[0]*ny + neighbor[1]
        if other in active:
            raise ValueError('Pressure/traction requires exposed boundary faces, not an internal interface')
    nodes = []
    for dz in range(2 if dim == 3 else 1):
        for dx in range(2):
            for dy in range(2):
                offset = (dx, dy, dz)[axis]
                wanted = (0 if side > 0 else 1) if axis == 1 else (1 if side > 0 else 0)
                if offset == wanted:
                    nodes.append((z+dz)*(nx+1)*(ny+1)+(x+dx)*(ny+1)+y+dy)
    normal = np.zeros(dim); normal[axis] = side
    return nodes, normal


def preserve_interfaces(request):
    """Preserve the original pressure/traction boundary during optimization."""
    d = request['domain']; active = set(d['active']); keep = set(d.get('solid', [])); original = set(keep)
    for case in request.get('load_cases', []):
        for load in case.get('loads', []):
            if load.get('kind') in ('pressure', 'traction'):
                faces = load.get('faces')
                if not isinstance(faces, list) or not faces:
                    raise ValueError('Surface load has no faces')
                seen = set()
                for face in faces:
                    face_geometry(d, request['dimension'], face, active)
                    key = (face['cell'], face['axis'], face['side'])
                    if key in seen:
                        raise ValueError('Duplicate face in one surface load')
                    seen.add(key); keep.add(face['cell'])
    if request.get('settings', {}).get('preserve_attachments', False):
        dim = request['dimension']; nx, ny, nz = d['nx'], d['ny'], d.get('nz', 1)
        full = (nx+1)*(ny+1)*(nz+1 if dim == 3 else 1)
        groups = list(request.get('supports', []))
        groups += [load for case in request.get('load_cases', []) for load in case.get('loads', []) if load.get('kind', 'nodal') == 'nodal']
        for group in groups:
            for node in indices(group['nodes'], 'attachment nodes', full):
                x, y, z = (node//(ny+1))%(nx+1), node%(ny+1), node//((nx+1)*(ny+1))
                for dz in (-1, 0) if dim == 3 else (0,):
                    for dx in (-1, 0):
                        for dy in (-1, 0):
                            a, b, c = x+dx, y+dy, z+dz
                            if 0<=a<nx and 0<=b<ny and 0<=c<nz:
                                e = c*nx*ny+a*ny+b
                                if e in active: keep.add(e)
    d['solid'] = sorted(keep)
    return len(keep-original)


def prepare_cases(model, cases, material):
    dim = model.nodes.shape[1]; d = model.request['domain']
    full = (d['nx']+1)*(d['ny']+1)*(d.get('nz', 0)+1)
    remap = np.full(full, -1, int); remap[model.grid_node_ids] = np.arange(len(model.nodes))
    active = set(model.active.tolist()); conn = model.hexes if dim == 3 else model.faces
    if not isinstance(cases, list) or not 1 <= len(cases) <= 16:
        raise ValueError('Connect between 1 and 16 load cases')
    result = []; names = set()
    for k, case in enumerate(cases):
        name = str(case.get('name', 'Case '+str(k+1)))
        if not name.strip() or name in names:
            raise ValueError('Load case names must be unique and nonempty')
        names.add(name); weight = number(case.get('weight', 1), 'case weight', 1e-9, 1e9)
        force = np.zeros((model.ndof, 1)); gravity = np.zeros(dim); summaries = []
        if not isinstance(case.get('loads'), list) or not case['loads']:
            raise ValueError(name+': no loads')
        for load in case['loads']:
            kind = load.get('kind', 'nodal')
            if kind == 'gravity':
                acc = np.asarray(load['acceleration'], float)
                if acc.shape != (dim,) or not np.isfinite(acc).all() or np.linalg.norm(acc) == 0:
                    raise ValueError(name+': invalid gravity acceleration')
                gravity += acc
                summaries.append(dict(kind=kind, acceleration_m_s2=acc.tolist()))
            elif kind == 'nodal':
                ids = indices(load['nodes'], 'load nodes', full)
                if np.any(remap[ids] < 0):
                    raise ValueError(name+': a loaded node was removed; preserve its surrounding material')
                ids = remap[ids]; v = np.asarray(load['force'], float)
                if v.shape != (dim,) or not np.isfinite(v).all() or np.linalg.norm(v) == 0:
                    raise ValueError(name+': invalid force')
                for axis in range(dim):
                    dofs = dim*ids+axis
                    if v[axis] and np.isin(dofs, model.fixed).any():
                        raise ValueError(name+': force on constrained direction')
                    force[dofs, 0] += v[axis]/len(ids)
                summaries.append(dict(kind=kind, total_force=v.tolist(), nodes=len(ids)))
            elif kind in ('pressure', 'traction'):
                if not isinstance(load.get('faces'), list) or not load['faces']:
                    raise ValueError(name+': surface load has no faces')
                if kind == 'pressure':
                    pressure = number(load['pressure'], 'pressure', -1e15, 1e15)
                    if not pressure: raise ValueError('Pressure must be nonzero')
                else:
                    traction = np.asarray(load['traction'], float)
                    if traction.shape != (dim,) or not np.isfinite(traction).all() or np.linalg.norm(traction) == 0:
                        raise ValueError('Use a nonzero finite traction vector')
                area = model.h**2 if dim == 3 else model.h*model.thickness
                seen = set(); resultant = np.zeros(dim)
                for face in load['faces']:
                    ns, normal = face_geometry(d, dim, face, active)
                    key = (face['cell'], face['axis'], face['side'])
                    if key in seen: raise ValueError('Duplicate face in one surface load')
                    seen.add(key)
                    ids = remap[ns]
                    if np.any(ids < 0): raise ValueError('Loaded boundary nodes were removed')
                    v = (-pressure*normal if kind == 'pressure' else traction)*area
                    for axis in range(dim): force[dim*ids+axis, 0] += v[axis]/len(ids)
                    resultant += v
                summaries.append(dict(kind=kind, faces=len(seen), area=len(seen)*area,
                                      total_force=resultant.tolist(), interface='fixed grid boundary; preserved in optimization'))
            else:
                raise ValueError('Unknown load kind: '+str(kind))
        body = None
        if np.any(gravity):
            volume = model.h**dim*(model.thickness if dim == 2 else 1)
            element_mass = volume*material['length_m']**3*material['density_kg_m3']
            nodal = element_mass*gravity/(material['force_n']*conn.shape[1])
            values = np.broadcast_to(nodal, (model.n, conn.shape[1], dim)).ravel()
            columns = np.repeat(np.arange(model.n), conn.shape[1]*dim)
            body = coo_matrix((values, (model.edof.ravel(), columns)), shape=(model.ndof, model.n)).tocsr()
        result.append(dict(name=name, weight=weight, force=force, body=body, loads=summaries))
    return result


def apply_case(model, case, rho):
    force = case['force'].copy()
    if case['body'] is not None: force[:, 0] += case['body'] @ rho
    if not np.any(force[model.free]):
        raise ValueError(case['name']+': no nonzero load remains on free directions (loads cancel or are fully supported)')
    model.forces = force
    model.force_scale = float(np.max(abs(force)))
    return force


def solve_case(model, case, rho):
    force = apply_case(model, case, rho)
    if model.request['settings'].get('backend'):
        from fem_backends import solve_model
        response = solve_model(model,rho,cache_key=('forward',case['name']))
    else:
        response = model.solve(rho)
    if response['gradient'] is not None and case['body'] is not None:
        # C=f(rho)^T u, Ku=f -> dC = 2 u^T df - u^T dK u.
        physical = 2*np.asarray(case['body'].T @ response['displacement'].ravel()).ravel()
        response['gradient'] += np.asarray(model.filter.T @ physical[model.design]).ravel()
    response['applied_forces'] = force.reshape(-1, model.nodes.shape[1])
    return response
