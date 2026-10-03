# SPDX-License-Identifier: GPL-3.0-or-later
"""Conservative admission estimates, not a promise of measured peak RAM or runtime."""
import math
import psutil

MAX_GRID_CELLS = 2_000_000
MAX_GRID_AXIS = 2048


def _integer(value, label, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or int(value) != value or not 1 <= value <= maximum:
        raise ValueError(f"{label} must be an integer from 1 to {maximum:,}")
    return int(value)


def grid_resources(request, available_bytes=None, gpu_available_bytes=None):
    """Check before allocating connectivity/filter/matrices; keep 40% of free RAM aside."""
    d=request['domain'];s=request.get('settings',{})
    dims=[_integer(d[k],k,MAX_GRID_AXIS) for k in ('nx','ny','nz')]
    bounding=math.prod(dims)
    if bounding>MAX_GRID_CELLS:
        raise ValueError(f"Grid has {bounding:,} bounding cells; absolute input guard is {MAX_GRID_CELLS:,}. Increase Cell size.")
    active=len(d.get('active',[])) or bounding
    nodes=math.prod(v+1 for v in dims);dofs=3*nodes
    cases=max(1,len(request.get('load_cases',[])))
    backend=s.get('backend','cpu-direct')
    if backend not in ('cpu-direct','cpu-cg','cpu-amg','cpu-matrixfree','cuda-cg'):
        raise ValueError('Unknown backend')
    compact=s.get('compact_results',active>32768)
    # Includes simultaneous Python/JSON results, load/adjoint vectors and conservative sparse assembly workspace.
    base=512*2**20+bounding*600+dofs*8*(12+4*cases)
    fields=active*(2400+1200*cases+(0 if compact else 2400*(cases+1)))
    assembly=active*(1000 if backend=='cpu-matrixfree' else 16000)
    if backend=='cpu-amg':assembly+=dofs*2500
    if backend=='cpu-direct':assembly+=int(32*dofs**1.5)
    cell=float(d.get('cell',1))
    if not math.isfinite(cell) or cell<=0:raise ValueError('Cell size must be finite and positive')
    radius_length=float(s.get('radius_length',0))
    if not math.isfinite(radius_length) or radius_length<0:
        raise ValueError('Physical filter radius must be finite and nonnegative')
    radius=radius_length/float(d.get('cell',1)) if radius_length else float(s.get('radius',1.8))
    if not math.isfinite(radius):raise ValueError('Filter radius must be finite')
    if request.get('mode','optimize')=='optimize' and not 1<=radius<=64:
        raise ValueError('Filter radius must span 1..64 cells; check physical radius and Cell size')
    pad=2*math.ceil(radius)+2 if request.get('mode','optimize')=='optimize' else 0
    filter_bytes=0 if request.get('mode','optimize')!='optimize' else 64*math.prod(v+pad for v in dims)
    estimate=int(base+fields+assembly+filter_bytes)
    available=int(psutil.virtual_memory().available if available_bytes is None else available_bytes)
    chosen=float(s.get('memory_budget_gib',0))
    if not math.isfinite(chosen) or chosen<0:
        raise ValueError('RAM budget must be finite and nonnegative (0 = automatic)')
    budget=int(min(.6*available,chosen*2**30)) if chosen else int(.6*available)
    info=dict(bounding_cells=bounding,active_cells=active,grid_nodes_upper_bound=nodes,
              estimated_host_bytes=estimate,host_budget_bytes=budget,available_host_bytes=available,
              backend=backend,filter_radius_cells=radius,filter_radius_length=radius*float(d.get('cell',1)),
              compact_results=bool(compact),estimate_policy='conservative admission estimate; 40% free RAM reserved; not a peak guarantee',
              qualification='larger grids require numerical and performance verification')
    if estimate>budget:
        raise ValueError(f"Estimated memory {estimate/2**30:.2f} GiB exceeds usable memory budget {budget/2**30:.2f} GiB for {bounding:,} cells / {backend}. Increase Cell size, close other jobs, or select an iterative solver. No calculation started.")
    if backend=='cuda-cg':
        if gpu_available_bytes is None:
            try:
                import cupy as cp
                gpu_available_bytes=int(cp.cuda.runtime.memGetInfo()[0])
            except Exception as exc:
                raise ValueError('CUDA memory check unavailable; select CPU explicitly or repair CUDA: '+str(exc)) from exc
        
        # Assignment can temporarily retain both previous and new device CSR matrices.
        gpu_estimate=int(256*2**20+active*5600+dofs*8*12)
        info.update(estimated_gpu_bytes=gpu_estimate,available_gpu_bytes=int(gpu_available_bytes))
        if gpu_estimate>.7*gpu_available_bytes:
            raise ValueError(f"Estimated GPU memory {gpu_estimate/2**30:.2f} GiB exceeds 70% of free GPU memory ({gpu_available_bytes/2**30:.2f} GiB). Select CPU or increase Cell size.")
    return info
