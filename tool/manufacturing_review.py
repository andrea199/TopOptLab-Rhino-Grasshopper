# SPDX-License-Identifier: GPL-3.0-or-later
"""Additive geometry screening. Explicitly sampled; not a printability certificate."""
import numpy as np
from final_geometry import from_mesh
from worker import number,integer

def inspect(nodes,triangles,spec,cancel=lambda:None):
    if not spec or not spec.get('enabled',False):return dict(status='not_requested')
    axis=np.asarray(spec.get('build_direction',[0,0,1]),float)
    if axis.shape!=(3,) or not np.isfinite(axis).all() or np.linalg.norm(axis)==0:raise ValueError('Use a finite nonzero build direction')
    axis/=np.linalg.norm(axis);angle=number(spec.get('overhang_angle',45),'overhang angle from vertical',1,89)
    minimum=number(spec.get('minimum_wall',0),'minimum sampled wall',0,1e9);count=integer(spec.get('samples',500),'wall samples',20,2000)
    v=np.asarray(nodes,float);f=np.asarray(triangles,int);p=v[f];cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);areas=np.linalg.norm(cross,axis=1)/2;normals=cross/np.maximum(2*areas[:,None],1e-300)
    projection=v@axis;span=np.ptp(v,axis=0).max();eps=max(span*1e-7,1e-12);bed=np.all(abs(projection[f]-projection.min())<=eps,axis=1)
    overhang=(normals@axis < -np.sin(np.deg2rad(angle))-1e-10)&~bed
    weights=np.cumsum(areas)/areas.sum();sample=np.unique(np.searchsorted(weights,(np.arange(count)+.5)/count));solid=from_mesh(v,f);thickness=[];thin=[];missing=0
    for k in sample:
        cancel();center=p[k].mean(axis=0);direction=-normals[k]
        hits=solid.ray_cast(tuple(center+eps*direction),tuple(center+4*span*direction));exits=[hit for hit in hits if np.dot(np.asarray(hit.normal),direction)>1e-8 and np.linalg.norm(np.asarray(hit.position)-center)>eps]
        if not exits:missing+=1;continue
        distance=float(np.linalg.norm(np.asarray(exits[0].position)-center));thickness.append(distance)
        if minimum and distance<minimum:thin.append(int(k))
    flags=bool(np.any(overhang) or thin)
    return dict(process='additive_geometric_screening',status='incomplete_samples' if missing else 'flags_present' if flags else 'no_flags_at_samples',build_direction=axis.tolist(),overhang_angle_from_vertical=angle,overhang_faces=np.where(overhang)[0].tolist(),overhang_area=float(areas[overhang].sum()),overhang_area_fraction=float(areas[overhang].sum()/areas.sum()),bed_contact_area=float(areas[bed].sum()),minimum_wall_requested=minimum,sampled_wall_minimum=min(thickness) if thickness else None,sampled_faces=len(sample),missing_exit_rays=missing,thin_sample_faces=thin,note='Normal-ray thickness is sampled, not a guaranteed global minimum. Overhang flags do not model support reach, material, process anisotropy or enclosed support removal. No printability certification.')
