# SPDX-License-Identifier: GPL-3.0-or-later
"""External-worker workflow for extracted 3D surfaces and independent TET4 reanalysis."""
import copy,json,time,html
from pathlib import Path
import numpy as np
from worker import write_json,number,integer
from fem_backends import Cancelled
from engineering import signature
from engineering_materials import resolve
from design_limits import resolve_limits,summarize_limits
from final_geometry import extract,inspect_surface,surface_hash,export_stl,from_mesh,grid_mask,voxel_solid
from tetra_mesh import remesh
from tetra_fem import TetraModel
from final_loads import transfer_supports,transfer_case
from manufacturing_review import inspect as manufacture
from cad_interfaces import validate_contract,check_mesh,contract_hash


def source_project(source):
    if source.get('status')!='completed' or source.get('dimension')!=3 or source.get('engineering',{}).get('mode')!='optimize':raise ValueError('Connect a completed 3D Engineering optimization')
    report=source['engineering'].get('report_file')
    if not report:raise ValueError('Source job location missing; recompute optimization')
    project=json.loads((Path(report).parent/'project.json').read_text(encoding='utf-8-sig'))
    if project.get('job_id')!=source.get('job_id') or signature(project)!=source['engineering']['input_signature']:raise ValueError('Source job and saved physical inputs do not match')
    return project


def limit_checks(result,limits):
    checks=[]
    for kind,key,limit in [('displacement','max_displacement',limits['max_displacement']),('stress','max_von_mises',limits['max_stress'])]:
        if limit:
            value=result[key];ratio=value/limit;checks.append(dict(kind=kind,value=value,limit=limit,utilization=ratio,status='within_limit' if ratio<=1 else 'within_tolerance' if ratio<=1+limits['tolerance'] else 'exceeded',field='full-material TET4 von Mises' if kind=='stress' else 'nodal displacement'))
    return checks


def accuracy(levels,tolerance):
    comparisons=[]
    for a,b in zip(levels,levels[1:]):
        changes=[]
        for ca,cb in zip(a['cases'],b['cases']):
            changes.append(dict(name=cb['name'],**{key:abs(cb[key]-ca[key])/max(abs(cb[key]),1e-30) for key in ['compliance','max_displacement','max_von_mises']}))
        comparisons.append(dict(coarse_size=a['mesh_size'],fine_size=b['mesh_size'],relative_changes=changes,within_tolerance=all(c[key]<=tolerance for c in changes for key in ['compliance','max_displacement','max_von_mises'])))
    stable=len(comparisons)>=2 and all(c['within_tolerance'] for c in comparisons[-2:])
    return dict(status='not_studied' if not comparisons else 'stable_over_two_refinements' if stable else 'not_established',tolerance=tolerance,levels=levels,comparisons=comparisons,note='Three meshes and two stable successive refinements are required by this screen. TET4 stress is constant within an element; concentrated-load peaks can remain mesh dependent. This is a discretization study, not code certification.')


def write_report(path,data):
    esc=lambda x:html.escape(str(x));e=data.get('engineering',{});text='<!doctype html><meta charset="utf-8"><title>TopOptLab final geometry</title><style>body{font:16px system-ui;max-width:1080px;margin:35px auto;padding:20px}th,td{padding:10px;border-bottom:1px solid #ccc}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>TopOptLab final geometry and FEM</h1>'
    text+='<p>'+esc(data['mode'])+' | '+esc(data['status'])+' | '+esc(e.get('material',{}).get('name',''))+'</p>'
    geometry=data['geometry'];text+='<p>Closed surface: '+esc(geometry['closed'])+'; connected material components: '+esc(geometry['solid_components'])+'. Preserved voxel volume loss: '+esc(geometry.get('protected_volume_loss','n/a'))+'.</p>'
    if geometry.get('cad_interfaces'):
        cad=geometry['cad_interfaces'];text+='<p>Nominal CAD attachment plates and circular clearances restored. Circular surfaces are polygons with maximum radial overcut '+esc(cad['radial_overcut_bound_mm'])+' mm. This is a triangle surface, not an exact BRep. Final loads use nominal CAD contact regions; changes of moment from the original voxel contact area are recorded per load below.</p>'
    if data['mode']=='surface':text+='<p><strong>Extracted geometry has not been structurally reanalysed.</strong> Run Final FEM before evaluating its structural response.</p>'
    if e.get('cases'):
        m=e['material'];text+='<p>Mass: '+esc(e['mass_kg'])+' kg. Length: '+esc(m['length_unit'])+'; force: '+esc(m['force_unit'])+'. Stress: force/length squared.</p><table><tr><th>Case</th><th>Compliance</th><th>Max displacement</th><th>Max von Mises</th><th>Force transfer error</th><th>Moment transfer error</th></tr>'
        for c in e['cases']:
            text+='<tr>'+''.join('<td>'+esc(x)+'</td>' for x in [c['name'],format(c['compliance'],'.6g'),format(c['max_displacement'],'.6g'),format(c['max_von_mises'],'.6g'),format(c['transfer']['force_relative_error'],'.3g'),format(c['transfer']['moment_relative_error'],'.3g')])+'</tr>'
        text+='</table><p>Mesh quality: '+esc(e.get('mesh_quality_status'))+'. Final shape numerically verified: '+esc(e['design_limits'].get('final_shape_verified'))+'. Passing load limits alone does not establish mesh accuracy.</p><h2>Limits</h2><p>'+esc(e['design_limits']['status'])+' | conforming tetrahedral FEM</p>'
        for case in e['design_limits']['cases']:
            for c in case['checks']:text+='<p>'+esc(case['name'])+' / '+esc(c['kind'])+': '+esc(format(c['value'],'.6g'))+' / limit '+esc(format(c['limit'],'.6g'))+' — '+esc(c['status'])+'</p>'
        a=e['accuracy'];text+='<h2>Mesh study</h2><p>'+esc(a['status'])+'; relative tolerance '+esc(a['tolerance'])+'</p><table><tr><th>Size</th><th>Nodes</th><th>Tetrahedra</th><th>Min quality</th><th>Surface volume difference</th></tr>'
        for level in a['levels']:text+='<tr>'+''.join('<td>'+esc(level[k])+'</td>' for k in ['mesh_size','nodes','elements','minimum_quality','surface_volume_relative_error'])+'</tr>'
        text+='</table><p>'+esc(a['note'])+'</p>'
    manufacturing=data.get('manufacturing_review',{});text+='<h2>Manufacturing geometry screen</h2><p>'+esc(manufacturing.get('status','not_requested'))+'</p>'
    if manufacturing.get('status')=='see_extraction_report':text+='<p>Print flags belong to the source surface, before tetrahedral remeshing. See extraction report: '+esc(manufacturing.get('source_report_file'))+'</p>'
    elif manufacturing.get('status')!='not_requested':text+='<p>Overhang area fraction: '+esc(manufacturing.get('overhang_area_fraction'))+'; sampled minimum normal thickness: '+esc(manufacturing.get('sampled_wall_minimum'))+'. '+esc(manufacturing.get('note',''))+'</p>'
    text+='<p>Linear isotropic small-strain FEM. A pass is limited to the stated model and sampling. No buckling, fatigue, contact or process qualification.</p><details><summary>Calculation record</summary><pre>'+esc(json.dumps(dict(engineering=e,geometry=geometry,manufacturing=manufacturing),indent=2))+'</pre></details>'
    path.write_text(text,encoding='utf-8')


def run_final(request,out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);job=request['job_id'];started=time.perf_counter()
    if (out/'progress.json').exists() or (out/'result.json').exists():raise ValueError('Use a fresh final-geometry job directory')
    def cancel():
        if (out/'cancel').exists():raise Cancelled()
    def progress(stage):cancel();write_json(out/'progress.json',dict(job_id=job,status='running',stage=stage))
    try:
        progress('Validating source');action=request.get('action');settings=request.get('settings',{});source=request['source_result']
        if action=='extract':
            project=source_project(source);material=resolve(project.get('material',{}));progress('Extracting and preserving interfaces')
            cad_config=settings.get('cad_interfaces')
            if cad_config is not None:cad_config=validate_contract(project,cad_config)
            if request.get('edited_mesh') is None:
                nodes,triangles,geometry=extract(source,project['domain'],settings,cancel)
            else:
                edited=request['edited_mesh'];nodes=np.asarray(edited['nodes'],float);triangles=np.asarray(edited['triangles'],int);d=project['domain'];h=d['cell'];o=np.asarray(d['origin']);solid=from_mesh((nodes-o)/h,triangles)
                protected=voxel_solid(grid_mask(d,np.asarray(d['active'])[np.asarray(source['kept'],bool)]),cancel);original=voxel_solid(grid_mask(d,d['active']),cancel)
                if cad_config is not None:
                    cad_info=check_mesh(from_mesh(nodes,triangles),cad_config,protected.scale((h,h,h)).translate(tuple(o)))
                    geometry=inspect_surface(nodes,triangles);geometry.update(construction='user edited mesh checked against nominal CAD',cad_interfaces=cad_info,protected_volume_loss=cad_info['protected_volume_loss_mm3'],structurally_verified=False)
                else:
                    loss=(protected-solid).volume();outside=(solid-original).volume();tol=max(1e-8,len(d['active'])*1e-8)
                    if loss>tol:raise ValueError('Edited mesh removes protected material; restore load/support interfaces')
                    if outside>tol:raise ValueError('Edited mesh extends outside the original voxel design envelope')
                    geometry=inspect_surface(nodes,triangles);geometry.update(construction='user edited mesh',protected_volume_loss=float(loss*h**3),structurally_verified=False)

            progress('Manufacturing geometry checks');review=manufacture(nodes,triangles,request.get('manufacturing_review',{}),cancel)
            data=dict(schema='topoptlab-gh-surface-result-v1',dimension=3,mode='surface',job_id=job,status='completed',nodes=nodes.tolist(),triangles=triangles.tolist(),geometry=geometry,geometry_hash=surface_hash(nodes,triangles),source_project=project,manufacturing_review=review,source_optimization_job=source['job_id'],engineering=dict(mode='surface',material=material,input_signature=signature(project),report_file=str(out/'report.html'),mass_kg=geometry['volume']*material['length_m']**3*material['density_kg_m3']))
            if cad_config is not None:
                data['cad_interfaces']=cad_config;data['cad_interface_signature']=contract_hash(cad_config)
            export_stl(out/'final-surface.stl',nodes,triangles);data['surface_file']=str(out/'final-surface.stl')
        elif action=='analyze':
            if source.get('schema')!='topoptlab-gh-surface-result-v1' or source.get('mode')!='surface' or source.get('status')!='completed':raise ValueError('Connect a completed Final Geometry surface')
            nodes=np.asarray(source['nodes'],float);triangles=np.asarray(source['triangles'],int)
            if surface_hash(nodes,triangles)!=source['geometry_hash']:raise ValueError('Surface geometry changed without a new extraction record')
            project=source['source_project']
            if signature(project)!=source['engineering']['input_signature']:raise ValueError('Source material/loads/supports changed')
            cad_config=source.get('cad_interfaces')
            transfer_project=project
            if cad_config is not None:
                if contract_hash(cad_config)!=source.get('cad_interface_signature'):raise ValueError('CAD interface contract changed without a new extraction record')
                validate_contract(project,cad_config);check_mesh(from_mesh(nodes,triangles),cad_config)
                transfer_project=dict(project,cad_interfaces=cad_config)
            elif source.get('geometry',{}).get('cad_interfaces') is not None:raise ValueError('CAD interface contract is missing from the extracted surface')
            geometry=inspect_surface(nodes,triangles)
            if geometry['solid_components']!=1:raise ValueError('Final FEM requires a single connected material component')
            material=resolve(project.get('material',{}));limits=resolve_limits(request.get('design_limits',project.get('design_limits',{})),material)
            mesh_size=number(settings.get('mesh_size',project['domain']['cell']),'final mesh size',1e-9,1e9)
            if geometry['volume']/mesh_size**3>40000:raise ValueError('Requested final mesh is too dense; increase final mesh size')
            levels=integer(settings.get('levels',1),'mesh study levels',1,3);tolerance=number(settings.get('accuracy_tolerance',.05),'mesh study tolerance',.001,.2);level_records=[]
            for level in range(levels):
                size=mesh_size*.75**level
                if geometry['volume']/size**3>40000:raise ValueError('Mesh refinement exceeds the current size budget; increase final mesh size')
                progress('Meshing level '+str(level+1))
                v,t=remesh(nodes,triangles,size,out/('mesh-'+str(level+1)),cancel,cad_surface=cad_config is not None);cancel()
                try:model=TetraModel(v,t,material,settings)
                except ValueError as error:
                    if cad_config is not None:raise ValueError('CAD Final FEM rejected the automatic mesh: '+str(error)+'. Inspect or clean the interface surface and remesh; the extracted geometry is not structurally verified.') from error
                    raise
                cad_remesh_checks=check_mesh(from_mesh(model.nodes,model.triangles),cad_config) if cad_config is not None else None
                volume_error=abs(model.volumes.sum()-geometry['volume'])/geometry['volume']
                if volume_error>.02:raise ValueError('Remeshed volume differs from extracted surface by more than 2%; refine final mesh')
                fixed,support_info=transfer_supports(model,transfer_project);model.supports(fixed,cancel);responses=[];cases=[];check_cases=[]
                for case in project['load_cases']:
                    progress('FEM level '+str(level+1)+' / '+case['name']);force,transfer=transfer_case(model,transfer_project,case);r=model.solve(force)
                    responses.append(r);info=dict(name=case['name'],weight=case.get('weight',1),compliance=r['compliance'],max_displacement=r['max_displacement'],max_von_mises=r['max_von_mises'],performance=r['performance'],residual=r['residual'],equilibrium=r['equilibrium'],transfer=transfer,applied_force=force.sum(axis=0).tolist(),reaction_force=r['reactions'].sum(axis=0).tolist());cases.append(info);check_cases.append(dict(name=case['name'],checks=limit_checks(r,limits)))
                level_records.append(dict(mesh_size=size,boundary_meshing='CAD_planar_patch_reparameterization' if cad_config is not None else 'surface_reparameterization',nodes=len(v),elements=len(t),minimum_quality=float(model.quality.min()),elements_below_quality_005=int(np.count_nonzero(model.quality<.05)),surface_volume_relative_error=float(volume_error),cases=cases))
                boundary_record=out/('mesh-'+str(level+1))/'boundary-meshing.json'
                if boundary_record.exists():level_records[-1]['boundary_meshing_details']=json.loads(boundary_record.read_text())
                if cad_remesh_checks is not None:level_records[-1]['cad_interface_checks']=cad_remesh_checks
                write_json(out/('level-%02d.json'%(level+1)),level_records[-1])
            e=dict(version='0.4.0-dev',mode='final_fem',input_signature=signature(project),display_case=cases[0]['name'],material=material,cases=cases,weighted_compliance=sum(c['weight']*c['compliance'] for c in cases),mass_kg=float(model.volumes.sum()*material['length_m']**3*material['density_kg_m3']),termination_reason='conforming_fem_completed',converged=False,verification='Gmsh remeshed TET4 FEM on extracted surface',source_geometry_hash=source['geometry_hash'],support_transfer=support_info,accuracy=accuracy(level_records,tolerance),elapsed_seconds=time.perf_counter()-started,report_file=str(out/'report.html'),case_files=['case-%02d.json'%(i+1) for i in range(len(cases))])
            e['design_limits']=summarize_limits(limits,check_cases,'verify');e['design_limits']['scope']='conforming_tetrahedral_fem'
            e['mesh_quality_status']='poor_elements_present' if np.any(model.quality<.05) else 'no_poor_elements'
            e['design_limits']['numerical_limits_passed']=e['design_limits']['status'] in ('within_limits','within_tolerance')
            e['design_limits']['final_shape_verified']=bool(e['design_limits']['numerical_limits_passed'] and e['accuracy']['status']=='stable_over_two_refinements' and e['mesh_quality_status']=='no_poor_elements')
            e['design_limits']['note']='Limits apply to this discrete model. Final shape verification additionally requires stable mesh refinements and no flagged poor tetrahedra; it is not code compliance.'
            def payload(r,index):
                return dict(schema='topoptlab-gh-surface-result-v1',dimension=3,mode='final_fem',status='completed',job_id=job,nodes=model.nodes.tolist(),triangles=model.triangles.tolist(),tets=model.tets.tolist(),boundary_owners=model.owners.tolist(),displacement=r['displacement'].tolist(),reactions=r['reactions'].tolist(),von_mises=r['von_mises'].tolist(),stress_mean=r['stress'].tolist(),geometry=dict(source['geometry'],structurally_reanalysed=True,structurally_verified=e['design_limits']['final_shape_verified']),geometry_hash=source['geometry_hash'],manufacturing_review={'status':'see_extraction_report','source_report_file':source['engineering']['report_file']},metrics={k:r[k] for k in ['compliance','max_displacement','max_von_mises','residual','equilibrium']},engineering=dict(e,display_case=cases[index]['name'],selected_case_index=index+1),load_case=dict(name=cases[index]['name'],weight=cases[index]['weight']))
            data=payload(responses[0],0)
            for i,r in enumerate(responses):cancel();write_json(out/e['case_files'][i],payload(r,i))
        else:raise ValueError('Final workflow action must be extract or analyze')
        cancel();write_json(out/'project.json',request);write_report(out/'report.html',data);write_json(out/'result.json',data);write_json(out/'progress.json',data);return data
    except Cancelled:
        data=dict(job_id=job,status='cancelled');write_json(out/'progress.json',data);return data
    except Exception as error:
        write_json(out/'progress.json',dict(job_id=job,status='error',message=str(error)));raise
