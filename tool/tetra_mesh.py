# SPDX-License-Identifier: GPL-3.0-or-later
"""Gmsh tetrahedral remeshing in an isolated process so Stop can interrupt it."""
import json,math,sys,time,subprocess
from pathlib import Path
import numpy as np

def generate(nodes,triangles,size,directory,max_tets=250000,cad_surface=False):
    import gmsh
    from final_geometry import from_mesh,mesh_arrays
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    solid=from_mesh(nodes,triangles)
    if cad_surface:
        if not math.isfinite(size) or size<=0:raise ValueError('Final mesh size must be positive and finite')
        if len(triangles)>200000 or solid.volume()/size**3>40000:raise ValueError('CAD meshing allocation budget exceeded; increase final mesh size or simplify surface')
    shells=solid.decompose()
    outer=[s for s in shells if s.volume()>0];inner=[s for s in shells if s.volume()<0]
    if len(outer)!=1:raise ValueError('Final FEM requires one connected solid; extraction contains disconnected pieces')
    gmsh.initialize();gmsh.option.setNumber('General.Terminal',0)
    try:
        gmsh.model.add('Final geometry');loops=[];offset=0
        # Each shell is independently classified and parameterized by Gmsh.
        for shell in outer+inner:
            v,f=mesh_arrays(shell);tag=gmsh.model.addDiscreteEntity(2)
            ns=np.arange(offset+1,offset+len(v)+1,dtype=np.int64);offset+=len(v)
            gmsh.model.mesh.addNodes(2,tag,ns.tolist(),v.ravel().tolist());gmsh.model.mesh.addElementsByType(tag,2,[],ns[f].ravel().tolist())
        gmsh.model.mesh.classifySurfaces(math.radians(.5 if cad_surface else 40),True,True,math.pi)
        gmsh.model.mesh.createGeometry()
        # Group classified surfaces by connectivity through their bounding curves.
        surfaces=[tag for dim,tag in gmsh.model.getEntities(2)];groups=[]
        curves={tag:{abs(t) for dim,t in gmsh.model.getBoundary([(2,tag)],oriented=False)} for tag in surfaces}
        left=set(surfaces)
        while left:
            group={left.pop()};front=list(group)
            while front:
                q=front.pop();neighbors={p for p in left if curves[q]&curves[p]};left-=neighbors;group|=neighbors;front+=list(neighbors)
            groups.append(sorted(group))
        # Determine signed shell volumes from the preserved oriented surface triangles.
        node_tags,coords,_=gmsh.model.mesh.getNodes();xyz={int(t):p for t,p in zip(node_tags,np.asarray(coords).reshape(-1,3))}
        ranked=[]
        for group in groups:
            signed=0
            for tag in group:
                _,ns=gmsh.model.mesh.getElementsByType(2,tag);pts=np.array([xyz[int(t)] for t in ns]).reshape(-1,3,3)
                signed+=np.einsum('ij,ij->i',pts[:,0],np.cross(pts[:,1],pts[:,2])).sum()/6
            ranked.append((signed,gmsh.model.geo.addSurfaceLoop(group)))
        ranked.sort(reverse=True);gmsh.model.geo.addVolume([loop for _,loop in ranked]);gmsh.model.geo.synchronize()
        gmsh.option.setNumber('Mesh.MeshSizeMin',size);gmsh.option.setNumber('Mesh.MeshSizeMax',size)
        gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',0);gmsh.option.setNumber('Mesh.ElementOrder',1)
        gmsh.option.setNumber('General.NumThreads',1)
        print('Generating tetrahedra with '+('CAD planar patches at 0.5 degrees' if cad_surface else 'generic surface patches'),flush=True)
        gmsh.model.mesh.generate(3);gmsh.model.mesh.optimize('Netgen')
        tags,coords,_=gmsh.model.mesh.getNodes();coords=np.asarray(coords).reshape(-1,3);mapping={int(t):i for i,t in enumerate(tags)}
        _,tetnodes=gmsh.model.mesh.getElementsByType(4)
        if len(tetnodes)//4>max_tets:raise ValueError('Final tetrahedral mesh exceeds element limit; increase mesh size')
        tets=np.array([mapping[int(t)] for t in tetnodes],int).reshape(-1,4)
        used=np.unique(tets);remap=np.full(len(coords),-1);remap[used]=np.arange(len(used));coords=coords[used];tets=remap[tets]
        if len(tets)==0:raise ValueError('Gmsh produced no tetrahedra')
        if cad_surface:
            (directory/'boundary-meshing.json').write_text(json.dumps(dict(method='CAD_planar_patch_reparameterization',classification_angle_degrees=.5,target_size=size,surface_vertices=len(nodes),surface_triangles=len(triangles),tetrahedra=len(tets),optimizer='Netgen',cad_postchecks_required=True),indent=2))
        gmsh.write(str(directory/'final.msh'));return coords,tets
    finally:gmsh.finalize()

def remesh(nodes,triangles,size,directory,cancel=lambda:None,cad_surface=False):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    spec=directory/'mesh-request.json';spec.write_text(json.dumps(dict(nodes=np.asarray(nodes).tolist(),triangles=np.asarray(triangles).tolist(),size=size,cad_surface=bool(cad_surface))))
    flags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
    with (directory/'mesher.log').open('w') as log:
        process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),str(spec)],stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
        try:
            start=time.monotonic()
            while process.poll() is None:
                cancel()
                if time.monotonic()-start>300:raise ValueError('Surface remeshing exceeded 300 seconds; increase mesh size or simplify extraction')
                time.sleep(.1)
            cancel()
            if process.returncode:raise ValueError('Gmsh remeshing failed: '+(directory/'mesher.log').read_text()[-1800:])
        finally:
            if process.poll() is None:process.kill();process.wait()
    data=np.load(directory/'mesh.npz');return data['nodes'],data['tets']

if __name__=='__main__':
    path=Path(sys.argv[1]);d=json.loads(path.read_text());v,t=generate(d['nodes'],d['triangles'],d['size'],path.parent,cad_surface=d.get('cad_surface',False));np.savez(path.parent/'mesh.npz',nodes=v,tets=t)
