# SPDX-License-Identifier: GPL-3.0-or-later
"""Transfer surface supports and loads with checked original force and moment."""
import numpy as np
from engineering_loads import face_geometry

def grid_points(domain,ids):
    ids=np.asarray(ids,int);nx,ny=domain['nx'],domain['ny'];h=domain['cell'];o=np.asarray(domain['origin'])
    return o+np.column_stack(((ids//(ny+1))%(nx+1),ny-ids%(ny+1),ids//((nx+1)*(ny+1))))*h

def patches(domain):
    active=set(domain['active']);result=[]
    for e in domain['active']:
        x,y,z=(e//domain['ny'])%domain['nx'],e%domain['ny'],e//(domain['nx']*domain['ny'])
        for axis in range(3):
            for side in (-1,1):
                nb=[x,y,z];nb[axis]+= -side if axis==1 else side
                if all(0<=n<size for n,size in zip(nb,(domain['nx'],domain['ny'],domain['nz']))) and nb[2]*domain['nx']*domain['ny']+nb[0]*domain['ny']+nb[1] in active:continue
                face=dict(cell=e,axis=axis,side=side);ns,normal=face_geometry(domain,3,face,active);result.append((face,ns,grid_points(domain,ns),normal))
    return result

def transfer_supports(model,request):
    if request.get('cad_interfaces') is not None:return _cad_supports(model,request)
    d=request['domain'];tol=d['cell']*1e-6;boundary_nodes=np.unique(model.triangles);xyz=model.nodes[boundary_nodes];fixed=[];summaries=[];allpatches=patches(d)
    for group in request['supports']:
        selected=set(group['nodes']);faces=[p for p in allpatches if set(p[1])<=selected]
        covered=set(n for p in faces for n in p[1])
        if not faces or not selected<=covered:raise ValueError('Final FEM supports must select complete original boundary faces; point/line supports need explicit surface patches')
        keep=np.zeros(len(xyz),bool)
        for face,ns,points,normal in faces:
            keep|=np.all((xyz>=points.min(axis=0)-tol)&(xyz<=points.max(axis=0)+tol),axis=1)
        ids=boundary_nodes[keep]
        if not len(ids):raise ValueError('A support patch is missing from the extracted shape')
        for axis,key in enumerate(('fix_x','fix_y','fix_z')):
            if group[key]:fixed.extend(3*ids+axis)
        summaries.append(dict(original_nodes=len(selected),original_faces=len(faces),mapped_nodes=len(ids)))
    return fixed,summaries

def closest_weights(point,triangles):
    """Exact closest point over all triangles, including edge/vertex regions."""
    a,b,c=triangles[:,0],triangles[:,1],triangles[:,2];v0=b-a;v1=c-a;v2=point-a
    aa=np.einsum('ij,ij->i',v0,v0);ab=np.einsum('ij,ij->i',v0,v1);bb=np.einsum('ij,ij->i',v1,v1);av=np.einsum('ij,ij->i',v0,v2);bv=np.einsum('ij,ij->i',v1,v2);den=aa*bb-ab*ab
    good=den>0;u=np.divide(bb*av-ab*bv,den,out=np.zeros_like(den),where=good);v=np.divide(aa*bv-ab*av,den,out=np.zeros_like(den),where=good)
    weights=np.column_stack((1-u-v,u,v));points=np.einsum('ei,eij->ej',weights,triangles);dist=np.sum((points-point)**2,axis=1);dist[~good|np.any(weights<0,axis=1)]=np.inf
    for i,j in [(0,1),(1,2),(2,0)]:
        edge=triangles[:,j]-triangles[:,i];length2=np.einsum('ij,ij->i',edge,edge);t=np.clip(np.einsum('ij,ij->i',point-triangles[:,i],edge)/np.maximum(length2,1e-300),0,1)
        p=triangles[:,i]+t[:,None]*edge;ds=np.sum((p-point)**2,axis=1);better=ds<dist
        w=np.zeros_like(weights);w[:,i]=1-t;w[:,j]=t;weights[better]=w[better];dist[better]=ds[better]
    k=int(dist.argmin());return k,weights[k],float(np.sqrt(dist[k]))

def clipped_weights(triangle,lo,hi,axes):
    """Integral of triangle barycentric weights over its intersection with a rectangle."""
    polygon=[(p[axes],w) for p,w in zip(triangle,np.eye(3))]
    for j in range(2):
        for bound,sign in [(lo[axes[j]],1),(hi[axes[j]],-1)]:
            clipped=[]
            if not polygon:return np.zeros(3)
            for a,b in zip(polygon,polygon[1:]+polygon[:1]):
                va=sign*(a[0][j]-bound);vb=sign*(b[0][j]-bound);ina=va>=0;inb=vb>=0
                if ina:clipped.append(a)
                if ina!=inb:
                    t=va/(va-vb);clipped.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])))
            polygon=clipped
    result=np.zeros(3)
    for i in range(1,len(polygon)-1):
        a,b,c=polygon[0],polygon[i],polygon[i+1];ab=b[0]-a[0];ac=c[0]-a[0];area=abs(ab[0]*ac[1]-ab[1]*ac[0])/2
        result+=area*(a[1]+b[1]+c[1])/3
    return result

def transfer_case(model,request,case):
    if request.get('cad_interfaces') is not None:return _cad_case(model,request,case)
    d=request['domain'];active_set=set(d['active']);h=d['cell'];origin=model.nodes.mean(axis=0);span=np.ptp(model.nodes,axis=0).max();tol=h*1e-5
    force=np.zeros((len(model.nodes),3));target_force=np.zeros(3);target_moment=np.zeros(3);tris=model.nodes[model.triangles];details=[];m=model.material
    for load in case['loads']:
        kind=load.get('kind','nodal')
        if kind=='nodal':
            pts=grid_points(d,load['nodes']);v=np.asarray(load['force'],float)/len(pts);max_distance=0
            for point in pts:
                k,w,distance=closest_weights(point,tris)
                if distance>tol:raise ValueError('A load point is missing from the extracted boundary; preserve its interface')
                np.add.at(force,model.triangles[k],w[:,None]*v);target_force+=v;target_moment+=np.cross(point-origin,v);max_distance=max(max_distance,distance)
            details.append(dict(kind=kind,points=len(pts),max_projection_distance=max_distance))
        elif kind in ('pressure','traction'):
            transferred=0
            for face in load['faces']:
                ns,normal=face_geometry(d,3,face,active_set);points=grid_points(d,ns);lo,hi=points.min(axis=0),points.max(axis=0);axis=face['axis'];axes=[j for j in range(3) if j!=axis]
                v=-float(load['pressure'])*normal if kind=='pressure' else np.asarray(load['traction'],float)
                candidates=np.where(np.max(abs(tris[:,:,axis]-lo[axis]),axis=1)<=tol)[0];area=0
                for k in candidates:
                    if np.any(tris[k].max(axis=0)<lo-tol) or np.any(tris[k].min(axis=0)>hi+tol):continue
                    weights=clipped_weights(tris[k],lo,hi,axes);area+=weights.sum();np.add.at(force,model.triangles[k],weights[:,None]*v)
                if not np.isclose(area,h*h,rtol=1e-5,atol=h*h*1e-8):raise ValueError('Loaded face is incomplete after extraction/remeshing')
                transferred+=area;target_force+=v*h*h;target_moment+=np.cross(points.mean(axis=0)-origin,v*h*h)
            details.append(dict(kind=kind,faces=len(load['faces']),mapped_area=float(transferred)))
        elif kind=='gravity':
            acc=np.asarray(load['acceleration'],float);element_force=model.volumes[:,None]*m['length_m']**3*m['density_kg_m3']*acc/m['force_n']
            for j in range(4):np.add.at(force,model.tets[:,j],element_force/4)
            target_force+=element_force.sum(axis=0);target_moment+=np.cross(model.nodes[model.tets].mean(axis=1)-origin,element_force).sum(axis=0)
            details.append(dict(kind=kind,acceleration_m_s2=acc.tolist(),mass_kg=float(model.volumes.sum()*m['length_m']**3*m['density_kg_m3'])))
        else:raise ValueError('Unknown final load kind: '+kind)
    denominator=max(np.linalg.norm(force,axis=1).sum(),1e-30);ferror=np.linalg.norm(force.sum(axis=0)-target_force)/denominator;merror=np.linalg.norm(np.cross(model.nodes-origin,force).sum(axis=0)-target_moment)/(denominator*span)
    if max(ferror,merror)>1e-5:raise ValueError('Force or moment changed while transferring the loads')
    return force,dict(force_relative_error=float(ferror),moment_relative_error=float(merror),moment_reference=origin.tolist(),loads=details)


def _cad_patch(model,lo,hi,axis,tolerance):
    """Integrate FE shape functions over a nominal rectangle on a planar face.

    Plane candidate lists are reused across cases; rectangular clipping retains
    circular holes because only triangles actually present are integrated.
    """
    lo=np.asarray(lo);hi=np.asarray(hi);axes=[a for a in range(3) if a!=axis]
    cache=getattr(model,'_cad_plane_cache',None)
    if cache is None:cache={};model._cad_plane_cache=cache
    key=(axis,float(lo[axis]),float(tolerance))
    if key not in cache:
        triangles=model.nodes[model.triangles]
        ids=np.where(np.max(abs(triangles[:,:,axis]-lo[axis]),axis=1)<=tolerance)[0]
        cross=np.cross(triangles[ids,1]-triangles[ids,0],triangles[ids,2]-triangles[ids,0])
        desired=1 if axis==2 else -1
        ids=ids[cross[:,axis]*desired>0]
        cache[key]=(ids,triangles[ids])
    ids,triangles=cache[key];weights=np.zeros(len(model.nodes))
    overlap=~(np.any(triangles.max(axis=1)<lo-tolerance,axis=1)|np.any(triangles.min(axis=1)>hi+tolerance,axis=1))
    for k,triangle in zip(ids[overlap],triangles[overlap]):
        w=clipped_weights(triangle,lo,hi,axes)
        np.add.at(weights,model.triangles[k],w)
    area=float(weights.sum())
    centroid=weights@model.nodes/area if area>0 else np.zeros(3)
    return weights,area,centroid

def _cad_reference(model,config,lo,hi,axis,tolerance):
    """Independent nominal CAD area/centroid for missing-face detection."""
    from types import SimpleNamespace
    from cad_interfaces import build,contract_hash
    from final_geometry import mesh_arrays
    cache=getattr(model,'_cad_nominal_cache',None)
    fingerprint=contract_hash(config)
    if cache is None or cache[0]!=fingerprint:
        v,f=mesh_arrays(build(config)['protected']);cache=(fingerprint,SimpleNamespace(nodes=v,triangles=f));model._cad_nominal_cache=cache
    _,area,centroid=_cad_patch(cache[1],lo,hi,axis,tolerance)
    return area,centroid

def _cad_supports(model,request):
    from cad_interfaces import physical_regions
    config=request['cad_interfaces'];_,wall=physical_regions(config);tol=request['domain']['cell']*1e-6
    fixed=set();records=[]
    for lo,hi in wall:
        weights,area,centroid=_cad_patch(model,lo,hi,0,tol);target_area,_=_cad_reference(model,config,lo,hi,0,tol)
        if area<=0 or not np.isclose(area,target_area,rtol=.005,atol=1e-7):raise ValueError('CAD wall support patch is incomplete after remeshing')
        ids=np.where((weights>0)&np.all((model.nodes>=lo-tol)&(model.nodes<=hi+tol),axis=1))[0]
        if len(ids)<3:raise ValueError('CAD wall support patch has too few mesh nodes; refine Final FEM mesh')
        for node in ids:fixed.update(range(3*int(node),3*int(node)+3))
        records.append(dict(mapping='nominal_cad_wall_pads',mapped_nodes=len(ids),mapped_area_mm2=area,nominal_polygon_area_mm2=target_area,rigid_directions=['X','Y','Z']))
    return sorted(fixed),records

def _cad_case(model,request,case):
    from cad_interfaces import physical_regions,validate_loading
    from engineering_loads import face_geometry
    config=request['cad_interfaces'];loading=validate_loading(config);regions,_=physical_regions(config)
    try:index=loading['case_names'].index(case['name'])
    except ValueError:raise ValueError('CAD physical load case is missing from the contract') from None
    force=np.zeros_like(model.nodes);target_force=np.zeros(3);target_moment=np.zeros(3);details=[]
    origin=np.asarray(config['specification']['origin']);h=request['domain']['cell'];tol=h*1e-6;active_set=set(request['domain']['active'])
    pairs=[('payload',loading['payload_kg'],regions[index],0)]
    if loading['shelf_kg_per_bracket']>0:pairs.append(('shelf',loading['shelf_kg_per_bracket'],regions[0],1))
    for kind,mass,(lo,hi),original_index in pairs:
        weights,area,centroid=_cad_patch(model,lo,hi,2,tol)
        expected_area,expected_centroid=_cad_reference(model,config,lo,hi,2,tol)
        if area<=0 or not np.isclose(area,expected_area,rtol=.005,atol=1e-7):raise ValueError('CAD load patch is missing or incomplete after remeshing')
        # A remesher may approximate the polygon edges slightly; reject material
        # drift rather than quietly moving an intended physical contact region.
        if np.linalg.norm(centroid-expected_centroid)>max(.01,h*.005):raise ValueError('CAD load patch centroid changed excessively after remeshing; refine Final FEM mesh')
        vector=np.array([0.,0.,-mass*loading['gravity_m_s2']]);nodal=weights[:,None]*vector/area
        force+=nodal;target_force+=vector;moment=np.cross(centroid-origin,vector);target_moment+=moment
        original=case['loads'][original_index];raster_force=np.zeros(3);raster_moment=np.zeros(3)
        for face in original.get('faces',[]):
            ns,_=face_geometry(request['domain'],3,face,active_set);points=grid_points(request['domain'],ns);value=np.asarray(original['traction'])*h*h
            raster_force+=value;raster_moment+=np.cross(points.mean(axis=0)-origin,value)
        details.append(dict(kind=kind,mapping='uniform_traction_on_nominal_cad_patch',mass_kg=mass,total_force_n=vector.tolist(),mapped_area_mm2=area,nominal_polygon_area_mm2=expected_area,centroid_mm=centroid.tolist(),nominal_polygon_centroid_mm=expected_centroid.tolist(),moment_about_wall_origin_nmm=moment.tolist(),original_raster_force_n=raster_force.tolist(),original_raster_moment_nmm=raster_moment.tolist(),moment_change_from_raster_nmm=(moment-raster_moment).tolist(),note='Force is preserved. CAD contact geometry replaces the voxel contact area; any resulting moment change is explicitly reported.'))
    for load in case['loads']:
        if load.get('kind')!='gravity':continue
        m=model.material;acc=np.asarray(load['acceleration'],float);ef=model.volumes[:,None]*m['length_m']**3*m['density_kg_m3']*acc/m['force_n']
        for j in range(4):np.add.at(force,model.tets[:,j],ef/4)
        target_force+=ef.sum(axis=0);target_moment+=np.cross(model.nodes[model.tets].mean(axis=1)-origin,ef).sum(axis=0)
        details.append(dict(kind='gravity',acceleration_m_s2=acc.tolist(),mass_kg=float(model.volumes.sum()*m['length_m']**3*m['density_kg_m3'])))
    denominator=max(np.linalg.norm(force,axis=1).sum(),1e-30);span=max(np.ptp(model.nodes,axis=0).max(),1e-30)
    ferror=np.linalg.norm(force.sum(axis=0)-target_force)/denominator;merror=np.linalg.norm(np.cross(model.nodes-origin,force).sum(axis=0)-target_moment)/(denominator*span)
    if max(ferror,merror)>1e-8:raise ValueError('CAD physical force or moment changed during transfer')
    return force,dict(mapping='nominal_cad_patches',force_relative_error=float(ferror),moment_relative_error=float(merror),moment_reference=origin.tolist(),loads=details)
