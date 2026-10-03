# SPDX-License-Identifier: GPL-3.0-or-later
"""Closed density isosurfaces, bounded by the design domain with exact voxel Keep union."""
import hashlib,json
import numpy as np
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes
import manifold3d as md
from worker import number

def surface_hash(nodes,triangles):
    h=hashlib.sha256();h.update(np.asarray(nodes,dtype='<f8').tobytes());h.update(np.asarray(triangles,dtype='<i8').tobytes());return h.hexdigest()

def from_mesh(nodes,triangles):
    nodes=np.asarray(nodes,float);triangles=np.asarray(triangles,np.int64)
    if nodes.ndim!=2 or nodes.shape[1]!=3 or triangles.ndim!=2 or triangles.shape[1]!=3 or len(triangles)<4 or not np.isfinite(nodes).all():raise ValueError('Invalid triangle surface')
    if triangles.min()<0 or triangles.max()>=len(nodes):raise ValueError('Invalid triangle indices')
    solid=md.Manifold(md.Mesh64(np.array(nodes,dtype=np.float64,order="C",copy=True),np.array(triangles,dtype=np.uint64,order="C",copy=True)))
    if solid.status()!=md.Error.NoError or solid.is_empty():raise ValueError('Surface must be a closed, consistently oriented manifold: '+str(solid.status()))
    return solid

def mesh_arrays(solid):
    mesh=solid.to_mesh64();return np.asarray(mesh.vert_properties[:,:3],float),np.asarray(mesh.tri_verts,np.int64)

def grid_mask(domain,ids):
    nx,ny,nz=domain['nx'],domain['ny'],domain['nz'];mask=np.zeros(nx*ny*nz,bool);mask[np.asarray(ids,int)]=True
    return mask.reshape(nz,nx,ny).transpose(1,2,0)[:,::-1,:].copy()

def voxel_solid(mask,cancel=lambda:None):
    """Greedy boxes exactly tile the requested voxels; no geometric simplification."""
    left=mask.copy();boxes=[];nx,ny,nz=left.shape
    while np.any(left):
        cancel();x,y,z=np.argwhere(left)[0];X=x+1
        while X<nx and left[X,y,z]:X+=1
        Y=y+1
        while Y<ny and left[x:X,Y,z].all():Y+=1
        Z=z+1
        while Z<nz and left[x:X,y:Y,Z].all():Z+=1
        left[x:X,y:Y,z:Z]=False
        boxes.append(md.Manifold.cube((float(X-x),float(Y-y),float(Z-z))).translate((float(x),float(y),float(z))))
    return md.Manifold.batch_boolean(boxes,md.OpType.Add)

def inspect_surface(nodes,triangles):
    solid=from_mesh(nodes,triangles);pieces=solid.decompose()
    # Negative-volume shells are cavity boundaries, not disconnected material islands.
    components=sum(p.volume()>0 for p in pieces)
    xyz=np.asarray(nodes)[np.asarray(triangles)];cross=np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]);areas=np.linalg.norm(cross,axis=1)/2
    return dict(closed=True,oriented=True,solid_components=components,boundary_shells=len(pieces),vertices=len(nodes),triangles=len(triangles),volume=float(solid.volume()),area=float(areas.sum()))

def extract(source,domain,settings,cancel=lambda:None):
    if source.get('status')!='completed' or source.get('dimension')!=3 or source.get('engineering',{}).get('mode')!='optimize':raise ValueError('Connect a completed 3D Engineering optimization')
    threshold=number(settings.get('threshold',.4),'surface threshold',.05,.95)
    sigma=number(settings.get('smoothing',.5),'density smoothing in cells',0,2)
    active=np.asarray(domain['active'],int);rho=np.asarray(source['density'],float);kept=np.asarray(source['kept'],bool)
    if rho.shape!=active.shape or kept.shape!=active.shape or not np.isfinite(rho).all() or np.any((rho<0)|(rho>1)):raise ValueError('Density/Keep does not match source domain')
    if not np.array_equal(source['cell_ids'],active):raise ValueError('Source cell identities changed')
    mask=grid_mask(domain,active);keep=grid_mask(domain,active[kept]);nx,ny,nz=mask.shape
    values=np.zeros(nx*ny*nz);values[active]=rho
    field=values.reshape(nz,nx,ny).transpose(1,2,0)[:,::-1,:].copy();field=np.pad(field,1)
    if sigma:field=gaussian_filter(field,sigma,mode='constant',cval=0)
    cancel()
    if field.max()<=threshold:raise ValueError('Threshold/smoothing removes all density material; reduce them')
    vertices,faces,_,_=marching_cubes(field,threshold,allow_degenerate=False)
    vertices=vertices.astype(float)-.5
    if np.einsum('ij,ij->i',vertices[faces[:,0]],np.cross(vertices[faces[:,1]],vertices[faces[:,2]])).sum()<0:faces=faces[:,::-1]
    solid=from_mesh(vertices,faces);original=voxel_solid(mask,cancel);protected=voxel_solid(keep,cancel)
    cancel()
    cad_config=settings.get('cad_interfaces')
    cad_info=None
    if cad_config is not None:
        from cad_interfaces import validate_domain,restore
        validate_domain(domain,cad_config)
        h=domain['cell'];origin=tuple(domain['origin'])
        solid,cad_info=restore(solid.scale((h,h,h)).translate(origin),cad_config,protected.scale((h,h,h)).translate(origin))
        vertices,faces=mesh_arrays(solid)
        info=inspect_surface(vertices,faces)
        info.update(threshold=threshold,smoothing_cells=sigma,protected_voxels=int(keep.sum()),protected_volume_loss=cad_info['protected_volume_loss_mm3'],source_density_volume=float(rho.sum()*h**3),domain='nominal CAD envelope and screw/tool voids',cad_interfaces=cad_info,structurally_verified=False)
        return vertices,faces,info
    solid=(solid+protected)^original
    if solid.status()!=md.Error.NoError or solid.is_empty():raise ValueError('Protected surface extraction failed')
    lost=(protected-solid).volume() if np.any(keep) else 0
    if lost>max(1e-8,float(keep.sum())*1e-8):raise ValueError('Protected material was lost during extraction')
    vertices,faces=mesh_arrays(solid);h=domain['cell'];vertices=vertices*h+np.asarray(domain['origin'])
    info=inspect_surface(vertices,faces);info.update(threshold=threshold,smoothing_cells=sigma,protected_voxels=int(keep.sum()),protected_volume_loss=float(lost*h**3),source_density_volume=float(rho.sum()*h**3),domain='clipped to original voxel domain',structurally_verified=False)
    return vertices,faces,info

def export_stl(path,nodes,triangles):
    import meshio
    meshio.write(path,meshio.Mesh(np.asarray(nodes),[('triangle',np.asarray(triangles))]),binary=True)
