# SPDX-License-Identifier: GPL-3.0-or-later
"""Nominal shelf interfaces rebuilt independently of the density voxel grid.

Planar dimensions are nominal. Circular voids use circumscribed polygons, so
clearances are never narrower than their nominal circle; radial overcut is bounded.
This is a watertight triangle surface, not an exact BRep or a manufacturing fit.
"""
import copy,hashlib,json,math
import numpy as np
import manifold3d as md

SCHEMA='topoptlab-shelf-bracket-v1'
LOAD_SCHEMA='topoptlab-shelf-load-summary-v1'
GRAVITY=9.80665

def contract_hash(config):
    return hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def _number(data,key,positive=True):
    try:value=float(data[key])
    except (KeyError,TypeError,ValueError):raise ValueError('CAD '+key+' must be finite') from None
    if not math.isfinite(value):raise ValueError('CAD '+key+' must be finite')
    if positive and value<=0:raise ValueError('CAD '+key+' must be positive')
    return value

def dimensions(config):
    if not isinstance(config,dict) or not isinstance(config.get('specification'),dict):raise ValueError('Connect the CAD bracket specification')
    s=config['specification']
    if s.get('schema')!=SCHEMA:raise ValueError('Unsupported CAD interface specification')
    names=('length_mm','height_mm','width_mm','plate_mm','hole_diameter_mm','wall_pitch_mm','top_inset_mm','access_diameter_mm','access_depth_mm')
    L,H,W,p,d,pitch,inset,tool,depth=[_number(s,k,k!='access_depth_mm') for k in names]
    try:o=np.asarray(s['origin'],float)
    except (KeyError,ValueError,TypeError):raise ValueError('CAD origin must contain three finite coordinates') from None
    if o.shape!=(3,) or not np.isfinite(o).all():raise ValueError('CAD origin must contain three finite coordinates')
    if depth<0 or p>=min(L,H)/3 or d>=W or tool<d or tool>=W:raise ValueError('CAD plate, hole and access dimensions overlap')
    low,high=(H-pitch)/2,(H+pitch)/2;r=tool/2
    if low<=r or high+r>=H-p or pitch<=tool or inset<=p+r or L-2*inset<=tool or inset>=L/2 or depth>=min(L,H)-p:raise ValueError('CAD holes/tool access overlap or reach a plate edge')
    tolerance=_number(config,'chord_tolerance_mm')
    if tolerance>min(d,tool)/20:raise ValueError('CAD chord tolerance must be at most 5 percent of the hole diameter')
    expected_z=np.array([low,high])+o[2]
    if not np.allclose(np.asarray(s.get('wall_hole_z',[])),expected_z,rtol=0,atol=1e-7):raise ValueError('CAD wall hole coordinates differ from dimensions')
    return s,(L,H,W,p,d,pitch,inset,tool,depth),o,tolerance

def sampled_domain(domain,config):
    _,(L,H,W,p,d,pitch,inset,tool,depth),o,_=dimensions(config)
    h=float(domain['cell']);sizes=np.array([domain['nx'],domain['ny'],domain['nz']],int)
    if not np.isfinite(h) or h<=0 or np.any(sizes<1):raise ValueError('Invalid CAD source domain')
    if not np.array_equal(sizes,np.ceil(np.array([L,W,H])/h).astype(int)) or not np.allclose(domain['origin'],o+[0,-W/2,0],rtol=0,atol=1e-7):raise ValueError('CAD specification and source domain differ')
    nx,ny,nz=sizes;ids=np.arange(nx*ny*nz)
    xyz=np.column_stack(((ids//ny)%nx+.5,ny-ids%ny-.5,ids//(nx*ny)+.5))*h+np.array(domain['origin'])-o
    x,y,z=xyz.T;inside=(x>=0)&(x<=L)&(abs(y)<=W/2)&(z>=0)&(z<=H)
    for cz in ((H-pitch)/2,(H+pitch)/2):
        inside &= ~((x>=-1)&(x<=p)&(y*y+(z-cz)**2<=d*d/4+1e-8))
        if depth:inside &= ~((x>=p)&(x<=p+depth)&(y*y+(z-cz)**2<=tool*tool/4+1e-8))
    for cx in (inset,L-inset):
        inside &= ~((z>=H-p)&(z<=H+1)&((x-cx)**2+y*y<=d*d/4+1e-8))
        if depth:inside &= ~((z>=H-p-depth)&(z<=H-p)&((x-cx)**2+y*y<=tool*tool/4+1e-8))
    return ids[inside],ids[inside&((x<=p)|(z>=H-p))]

def validate_domain(domain,config):
    active,kept=sampled_domain(domain,config)
    if not np.array_equal(active,domain['active']):raise ValueError('CAD source domain differs from nominal sampled holes/envelope')
    if not set(kept)<=set(domain.get('solid',[])):raise ValueError('CAD attachment plates are not protected in the source domain')

def validate_loading(config):
    _,(L,H,W,p,d,pitch,inset,tool,depth),o,_=dimensions(config)
    c=config.get('loading')
    if not isinstance(c,dict) or c.get('schema')!=LOAD_SCHEMA:raise ValueError('Connect the bracket physical loading contract')
    payload=_number(c,'payload_kg');shelf=_number(c,'shelf_kg_per_bracket',False)
    front=_number(c,'front_depth_mm');side=_number(c,'lateral_offset_fraction');g=_number(c,'gravity_m_s2')
    if shelf<0 or front>=L-p or not 0<side<1 or not np.isclose(g,GRAVITY,rtol=0,atol=1e-12):raise ValueError('Invalid CAD payload, shelf mass, load patch or gravity')
    if not np.allclose(c.get('origin_mm',[]),o,rtol=0,atol=1e-7):raise ValueError('CAD loading origin differs')
    if c.get('support_model')!='rigid_wall_pads' or not np.isclose(_number(c,'support_pad_height_mm'),tool+p,rtol=0,atol=1e-7) or tool+p>=pitch:raise ValueError('Unsupported CAD wall support pads')
    names=c.get('case_names');records=c.get('cases')
    if not isinstance(names,list) or len(names)!=4 or len(set(names))!=4 or not isinstance(records,list) or [r.get('name') for r in records]!=names:raise ValueError('CAD requires the four independent original cases')
    return c

def _raster_patch_faces(domain,loading):
    h=domain['cell'];nx,ny=domain['nx'],domain['ny'];a=np.asarray(domain['active']);x=(a//ny)%nx;y=a%ny;z=a//(nx*ny)
    top=a[z==z.max()];tx=(top//ny)%nx;ty=top%ny
    front=top[(tx+.5)*h>(x.max()+1)*h-loading['front_depth_mm']-1e-7]
    fy=front%ny;right=front[(ny-fy-.5)*h>(ny-y.max()-1)*h+(y.max()-y.min()+1)*h*loading['lateral_offset_fraction']-1e-7]
    left=front[(ny-fy-.5)*h<(ny-y.min())*h-(y.max()-y.min()+1)*h*loading['lateral_offset_fraction']+1e-7]
    return [top,front,right,left]

def validate_contract(request,config):
    validate_domain(request['domain'],config);loading=validate_loading(config)
    material=request.get('material',{})
    if material.get('length_unit','mm')!='mm' or material.get('force_unit','N')!='N':raise ValueError('CAD bracket interfaces require mm and N')
    cases=request.get('load_cases',[])
    if [c.get('name') for c in cases]!=loading['case_names']:raise ValueError('CAD load case names/order differ from optimization')
    expected=_raster_patch_faces(request['domain'],loading);h=request['domain']['cell']
    for i,case in enumerate(cases):
        loads=case.get('loads',[]);mass=[loading['payload_kg']]+([loading['shelf_kg_per_bracket']] if loading['shelf_kg_per_bracket'] else [])
        if len(loads)!=len(mass)+1:raise ValueError('CAD payload/shelf/gravity contract differs from source loads')
        for j,kg in enumerate(mass):
            load=loads[j];faces=load.get('faces',[]);ids=expected[i] if j==0 else expected[0]
            if load.get('kind')!='traction' or any(f.get('axis')!=2 or f.get('side')!=1 for f in faces) or sorted(f['cell'] for f in faces)!=sorted(ids.tolist()):raise ValueError('CAD load patch differs from source raster patch')
            force=np.asarray(load.get('traction',[]))*len(faces)*h*h
            if force.shape!=(3,) or not np.allclose(force,[0,0,-kg*GRAVITY],rtol=1e-9,atol=1e-9):raise ValueError('CAD payload/shelf total force differs from source')
        if loads[-1].get('kind')!='gravity' or not np.allclose(loads[-1].get('acceleration',[]),[0,0,-GRAVITY],rtol=0,atol=1e-9):raise ValueError('CAD gravity differs from source')
    # The dedicated wall-pad model cannot silently replace other support physics.
    supports=request.get('supports',[])
    if len(supports)!=1 or any(supports[0].get(k) is not True for k in ('fix_x','fix_y','fix_z')):raise ValueError('CAD final supports require the original rigid wall pads')
    from engineering_loads import face_geometry
    origin=np.asarray(config['specification']['origin']);zs=config['specification']['wall_hole_z'];half=loading['support_pad_height_mm']/2
    domain=request['domain'];a=np.asarray(domain['active']);nx,ny=domain['nx'],domain['ny']
    z=origin[2]+(a//(nx*ny)+.5)*h
    selected=a[((a//ny)%nx==0)&np.any(abs(z[:,None]-np.asarray(zs))<=half,axis=1)]
    active_set=set(domain['active'])
    faces=[face_geometry(domain,3,dict(cell=int(e),axis=0,side=-1),active_set)[0] for e in selected]
    if set(supports[0]['nodes'])!=set(n for ns in faces for n in ns):raise ValueError('CAD rigid wall support patches differ from source')
    return copy.deepcopy(config)

def build(config):
    s,(L,H,W,p,d,pitch,inset,tool,depth),o,tolerance=dimensions(config)
    def box(x,y,z,dx,dy,dz):return md.Manifold.cube((dx,dy,dz)).translate(tuple(o+[x,y,z]))
    envelope=box(0,-W/2,0,L,W,H)
    plates=box(0,-W/2,0,p,W,H)+box(0,-W/2,H-p,L,W,p)
    voids=[];overcuts=[];segments=[]
    def cylinder(base,axis,r,length):
        # Circumscription guarantees the analytic nominal void is included.
        n=max(12,int(math.ceil(math.pi/math.acos(r/(r+tolerance)))))
        n=4*int(math.ceil(n/4))
        if n>4096:raise ValueError('CAD chord tolerance requires more than 4096 segments per circle')
        outer=r/math.cos(math.pi/n);shape=md.Manifold.cylinder(length,outer,circular_segments=n)
        if axis==0:shape=shape.rotate((0,90,0))
        voids.append(shape.translate(tuple(o+np.array(base))));overcuts.append(outer-r);segments.append(n)
    for z in ((H-pitch)/2,(H+pitch)/2):
        cylinder((-1,0,z),0,d/2,p+1)
        if depth:cylinder((p,0,z),0,tool/2,depth)
    for x in (inset,L-inset):
        cylinder((x,0,H-p),2,d/2,p+1)
        if depth:cylinder((x,0,H-p-depth),2,tool/2,depth)
    forbidden=md.Manifold.batch_boolean(voids,md.OpType.Add)
    return dict(envelope=envelope,voids=forbidden,protected=plates-forbidden,allowed=envelope-forbidden,max_radial_overcut_mm=max(overcuts),segments=segments)

def check_mesh(solid,config,extra_protected=None):
    cad=build(config);protected=cad['protected']
    if extra_protected is not None:protected=protected+(extra_protected^cad['allowed'])
    tolerance=max(1e-7,cad['envelope'].volume()*1e-10)
    outside=max(0.,(solid-cad['envelope']).volume());intrusion=max(0.,(solid^cad['voids']).volume());loss=max(0.,(protected-solid).volume())
    if outside>tolerance:raise ValueError('CAD surface extends outside the nominal envelope')
    if intrusion>tolerance:raise ValueError('CAD surface fills forbidden screw/tool space')
    if loss>tolerance:raise ValueError('CAD surface removes protected nominal attachment material')
    return dict(mode='nominal_cad_interfaces',planar_dimensions='nominal',circular_geometry='circumscribed polygon; nominal clearance never narrowed',chord_tolerance_mm=config['chord_tolerance_mm'],radial_overcut_bound_mm=cad['max_radial_overcut_mm'],circle_segments=cad['segments'],protected_volume_mm3=float(protected.volume()),protected_volume_loss_mm3=loss,forbidden_intrusion_mm3=intrusion,outside_envelope_mm3=outside,exact_brep=False)

def restore(solid,config,extra_protected=None):
    cad=build(config);protected=cad['protected']
    if extra_protected is not None:protected=protected+(extra_protected^cad['allowed'])
    _,(L,H,W,p,d,pitch,inset,tool,depth),origin,tolerance=dimensions(config)
    snap=float(config.get('envelope_snap_mm',0));web=float(config.get('web_cleanup_mm',.01))
    if any(not math.isfinite(t) or t<0 or t>min(.25,min(L,H,W)/10) for t in (snap,web)):raise ValueError('Envelope cleanup and web cleanup must be between 0 and 0.25 mm and below 10 percent of envelope size')
    cleanup=min(1e-7,tolerance*1e-4)
    def clean(shape):
        mesh=shape.to_mesh64()
        return md.Manifold(md.Mesh64(np.array(mesh.vert_properties[:,:3],dtype=np.float64,order='C',copy=True),np.array(mesh.tri_verts,dtype=np.uint64,order='C',copy=True))).simplify(cleanup)
    result=clean((solid+protected)^cad['allowed'])
    if web:result=result.simplify(web)
    # Reconstruct nominal interfaces after any explicit web simplification.
    result=clean((result+protected)^cad['allowed'])
    mesh=result.to_mesh64();coords=np.array(mesh.vert_properties[:,:3],dtype=np.float64,order='C',copy=True);before=coords.copy()
    if snap:
        lower=origin+[0,-W/2,0];upper=origin+[L,W/2,H]
        for axis in range(3):
            for plane in (lower[axis],upper[axis]):coords[abs(coords[:,axis]-plane)<=snap,axis]=plane
        result=md.Manifold(md.Mesh64(coords,np.array(mesh.tri_verts,dtype=np.uint64,order='C',copy=True)))
        result=clean((result+protected)^cad['allowed'])
    moved=np.linalg.norm(coords-before,axis=1)
    if result.status()!=md.Error.NoError or result.is_empty():raise ValueError('CAD interface reconstruction failed')
    info=check_mesh(result,config,extra_protected)
    info.update(boolean_cleanup_tolerance_mm=cleanup,web_cleanup_tolerance_mm=web,envelope_snap_tolerance_mm=snap,envelope_snapped_vertices=int(np.count_nonzero(moved)),maximum_snapped_vertex_displacement_mm=float(moved.max(initial=0)))
    return result,info


def physical_regions(config):
    c=validate_loading(config);s,(L,H,W,p,d,pitch,inset,tool,depth),o,_=dimensions(config)
    front=c['front_depth_mm'];side=c['lateral_offset_fraction'];top=(o+[0,-W/2,H],o+[L,W/2,H])
    region=[top,(o+[L-front,-W/2,H],o+[L,W/2,H]),(o+[L-front,-W/2+W*side,H],o+[L,W/2,H]),(o+[L-front,-W/2,H],o+[L,W/2-W*side,H])]
    half=c['support_pad_height_mm']/2
    wall=[(o+[0,-W/2,z-half],o+[0,W/2,z+half]) for z in ((H-pitch)/2,(H+pitch)/2)]
    return region,wall

