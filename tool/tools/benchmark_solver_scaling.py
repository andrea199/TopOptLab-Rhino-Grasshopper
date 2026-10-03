# SPDX-License-Identifier: GPL-3.0-or-later
"""Isolated repeatable old/new assembly and FEM benchmarks; emits JSON evidence."""
import argparse,importlib.util,json,sys,time
from pathlib import Path
import numpy as np
import psutil
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tool'))
from worker3d import Model3D
from sample3d import cantilever
from threadpoolctl import threadpool_limits


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--implementation',choices=['baseline','current'],required=True)
    parser.add_argument('--shape',type=int,nargs=3,default=[40,20,10])
    parser.add_argument('--backend',default='cpu-cg')
    parser.add_argument('--solve',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    path=ROOT/('tool/build/solver-scaling-baseline/fem_backends.py' if args.implementation=='baseline' else 'tool/fem_backends.py')
    spec=importlib.util.spec_from_file_location('measured_backend',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    r=cantilever('fem',*args.shape);r['settings'].update(backend=args.backend,threads=4)
    model=Model3D(r);engine=module.ElasticSolver(model,r['settings']);records=[]
    scales=[np.ones(model.n),.25+.75*(.5+.5*np.sin(np.arange(model.n)*.027)),.4+.6*(.5+.5*np.cos(np.arange(model.n)*.019))]
    for index,scale in enumerate(scales):
        start=time.perf_counter()
        with threadpool_limits(limits=4):
            if args.solve:
                u,internal,stats=engine.solve(scale,model.forces)
                # Equilibrium and work independently checked for every density update.
                reaction=internal-model.forces.ravel();residual=np.linalg.norm(reaction[model.free])/np.linalg.norm(model.forces[model.free])
                energy=np.einsum('ei,ij,ej->e',u[model.edof],model.KE,u[model.edof]);work=float(model.forces.ravel()@u)
                assert residual<=5e-9 and np.isclose(work,scale@energy,rtol=1e-7)
                extra=dict(compliance=work,residual=float(residual),iterations=stats['linear_iterations'])
            else:engine.prepare(scale);extra={}
        records.append(dict(step=index,seconds=time.perf_counter()-start,**extra))
    mem=psutil.Process().memory_info()
    report=dict(implementation=args.implementation,backend=args.backend,solve=args.solve,shape=args.shape,cells=model.n,dofs=model.ndof,records=records,peak_rss_bytes=getattr(mem,'peak_wset',mem.rss),rss_bytes=mem.rss,nnz=int(engine.A.nnz),versions=dict(numpy=np.__version__))
    if hasattr(engine,'assembly'):report['assembly_pattern_bytes']=engine.assembly.memory_bytes
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))

if __name__=='__main__':main()
