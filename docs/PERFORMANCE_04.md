# Performance evidence — 0.4.0-dev

Measured on 2026-09-19 on the development PC: Core Ultra 9 285H, 64 GB RAM,
RTX 5070 Laptop GPU. Float64 arithmetic, relative linear tolerance 1e-9.

The constrained workload is a 120 x 60 x 30 mm steel cantilever, fixed left face,
protected end layers, independent downward/sideways 100 N loads, 60% volume budget,
0.03 mm displacement limit and 10 MPa relaxed stress limit. Each job performs four
MMA updates, not a converged production optimization. All measured jobs completed
and passed their configured discrete-model limits.

## Short constrained optimization

| Voxels | Backend | CPU thread limit | Seconds | Peak host RSS, MiB |
|---:|---|---:|---:|---:|
| 1,728 | cpu-cg | 1 | 4.52 | 136.4 |
| 1,728 | cpu-cg | 4 | 4.43 | 135.2 |
| 1,728 | cpu-matrixfree | 4 | 7.09 | 90.9 |
| 13,824 | cpu-cg | 1 | 92.32 | 551.1 |
| 13,824 | cpu-cg | 4 | 113.98 | 536.6 |
| 13,824 | cpu-matrixfree | 4 | 101.65 | 160.7 |
| 1,728 | cuda-cg | 4 | 8.84 | 538.4 |
| 13,824 | cuda-cg | 4 | 21.74 | 993.6 |

CUDA was faster at 13,824 voxels on this short constrained run; CPU CG was faster
at 1,728 voxels. Matrix-free CPU reduced host memory substantially. CPU thread limits
apply to numerical libraries, not every stage; these single samples do not establish
parallel scaling or promised speedups.

## Conforming final FEM

Same extracted surface, target size 4.5 mm, two cases: 4,168 nodes and 14,553 TET4.
Includes Gmsh meshing, load transfer, FEM, result serialization and reports. Meshing
remains a CPU operation with one thread.

| Backend | Seconds | Peak host RSS including mesher, MiB |
|---|---:|---:|
| cpu-cg | 10.51 | 209.7 |
| cpu-matrixfree | 24.41 | 190.8 |
| cuda-cg | 10.01 | 548.5 |

CPU CG and CUDA were close for total final-FEM time. Across tested backends, case
compliance, displacement and stress maxima agreed within 5e-11 relative on these
workloads. Agreement on the same discrete model does not establish mesh accuracy.

## Measurement scope

Fresh process per job. Internal time includes GPU context startup but excludes host
Python imports; `fresh_process_seconds` includes those imports/startup. Disk kernel
caches may be warm. No other project numerical tests ran concurrently. System
background load, temperature and power modes were not controlled. Single samples
are not a robust speedup study or a worst-case memory guarantee.

Host RSS was sampled every 25 ms, including Gmsh children. CuPy pool used/reserved
memory was also sampled: large constrained CUDA case approximately 43.3/82.4 MiB.
These exclude driver/context and external-library allocations and are **not total
GPU VRAM**. That run used approximately 994 MiB peak host RSS.

Raw records: [performance-04.json](performance-04.json). Complete development job
outputs remain in `tool/build/performance-04-reference`. The final surface derives
from the default constrained 3D example, threshold 0.4, smoothing 0.5.

Reproduce using the project Python, into a fresh output directory:

```
python tool/tools/benchmark_final_workflows.py --cuda --surface PATH/TO/surface/result.json
```

Omit `--cuda` for CPU-only tests and `--surface` for constrained voxel tests only.
Repeated high-contrast/converged workloads, total VRAM and second-PC measurements
remain qualification work. The experimental voxel cap has not been raised.

## Later resolution increment

The measurements above are historical. See [Resolution validation](RESOLUTION_VALIDATION.md) and [Solver scaling](SOLVER_SCALING_EVIDENCE.md) for the subsequent assembly/filter/AMG changes. Do not mix timings from different revisions or workloads.
