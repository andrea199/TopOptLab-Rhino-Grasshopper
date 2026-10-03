# SPDX-License-Identifier: GPL-3.0-or-later
"""Engineering workflow: separate load cases, convergence, manufacturing and voxel reanalysis."""
import copy, hashlib, html, json, time
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix, issparse
from scipy.sparse.linalg import aslinearoperator
from scipy.ndimage import label, distance_transform_edt
from worker import Model, write_json, number, integer, indices
from worker3d import Model3D
from fem_backends import ElasticSolver, Cancelled
from engineering_materials import resolve
from engineering_loads import prepare_cases, preserve_interfaces, solve_case
from design_updates import self_weight_step, projected_stationarity
from design_limits import resolve_limits, evaluate_limits, summarize_limits
from constrained_design import optimize_constrained
VERSION='0.4.0-dev'

def signature(request):
    fields={k:request.get(k) for k in ('domain','supports','load_cases','material','dimension')}
    fields['thickness']=request['settings'].get('thickness',1)
    if request['settings'].get('preserve_attachments'):fields['preserve_attachments']=True
    return hashlib.sha256(json.dumps(fields,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def case_forces(model, cases):
    # Compatibility entry point for existing integrations.
    return prepare_cases(model, cases, resolve(model.request.get('material', {})))

def constrain_design(model,manufacturing):
    """Apply a linear density projection, so the existing adjoint gradient remains exact."""
    symmetry=manufacturing.get('symmetry','none');extrusion=manufacturing.get('extrusion','none')
    if symmetry not in ('none','x','y','z') or extrusion not in ('none','x','y','z'):raise ValueError('Manufacturing axes must be none/x/y/z')
    if symmetry=='none' and extrusion=='none':return
    d=model.request['domain'];dim=model.nodes.shape[1]
    if dim==2 and (symmetry=='z' or extrusion!='none'):raise ValueError('2D supports X/Y symmetry only; use thickness for extrusion')
    nx,ny,nz=d['nx'],d['ny'],d.get('nz',1)
    ids=model.active;coords=np.column_stack(((ids//ny)%nx,ids%ny,ids//(nx*ny)));sizes=[nx,ny,nz]
    # Require geometric and Keep symmetry, rather than manufacturing a misleading partial constraint.
    active_set=set(ids.tolist());keep_set=set(ids[model.keep].tolist())
    if symmetry!='none':
        axis='xyz'.index(symmetry);mirror=coords.copy();mirror[:,axis]=sizes[axis]-1-mirror[:,axis];mi=mirror[:,2]*nx*ny+mirror[:,0]*ny+mirror[:,1]
        if set(mi.tolist())!=active_set or set(mi[model.keep].tolist())!=keep_set:raise ValueError('Domain and Keep must match the requested symmetry')
        coords[:,axis]=np.minimum(coords[:,axis],sizes[axis]-1-coords[:,axis])
    if extrusion!='none':
        axis='xyz'.index(extrusion)
        original=np.column_stack(((ids//ny)%nx,ids%ny,ids//(nx*ny)));groups={}
        for i,c in enumerate(original):groups.setdefault(tuple(np.delete(c,axis)),[]).append(i)
        if any(len(g)!=sizes[axis] or len(set(model.keep[g]))!=1 for g in groups.values()):raise ValueError('Extrusion requires full columns and consistent Keep through the selected axis')
        coords[:,axis]=0
    variable=coords[model.design]
    from grid_filter import GroupAverage
    _,labels=np.unique(variable,axis=0,return_inverse=True)
    model.filter=GroupAverage(labels)@aslinearoperator(model.filter)
    model.dv=np.asarray(model.filter.T@np.ones(len(variable))).ravel()

def manufacturing_report(model,rho,spec):
    d=model.request['domain'];shape=(d.get('nz',1),d['nx'],d['ny']) if model.nodes.shape[1]==3 else (d['nx'],d['ny'])
    threshold=number(spec.get('threshold',.5),'threshold',.01,.99)
    mask=np.zeros(np.prod(shape),bool);mask[model.active]=rho>=threshold;mask=mask.reshape(shape)
    components=label(mask)[1]
    # Diagnostic voxel erosion only: not a guaranteed geometric minimum-feature constraint.
    padded=np.pad(mask,1);distance=distance_transform_edt(padded)*model.h
    core=distance[tuple(slice(1,-1) for _ in shape)]
    size=number(spec.get('minimum_feature',0),'minimum feature',0,1e9)
    notes=['Feature-size erosion is diagnostic only; no certified minimum wall or tool-access check.',
           'Thresholded geometry requires FEM reanalysis; no smoothing is applied.']
    process=spec.get('process','unspecified')
    if process not in ('unspecified','machining','injection_molding','additive'):raise ValueError('Unknown manufacturing process')
    if process=='additive':notes.append('Print orientation, support material and anisotropic properties require process qualification.')
    if process=='machining':notes.append('Cutter diameter, tool reach, fixtures and toolpaths are not checked.')
    if process=='injection_molding':notes.append('Draft, undercuts, wall uniformity, filling and cooling are not checked.')
    return dict(process=process,symmetry=spec.get('symmetry','none'),extrusion=spec.get('extrusion','none'),threshold=threshold,
                connected_components=int(components),retained_cells=int(mask.sum()),minimum_feature_requested=size,
                cells_surviving_radius_erosion=int(np.count_nonzero(mask&(core>=size/2))) if size else None,notes=notes)

def write_report(path,data):
    e=data['engineering'];rows=''.join('<tr><td>'+html.escape(c['name'])+'</td><td>%.6g</td><td>%.6g</td><td>%s</td></tr>'%(c['compliance'],c['max_displacement'],c.get('max_von_mises',c.get('max_von_mises_relaxed','n/a'))) for c in e['cases'])
    history=data.get('history',[]);chart=''
    if history:
        ys=[h['compliance'] for h in history];lo,hi=min(ys),max(ys);points=' '.join('%.2f,%.2f'%(20+600*i/max(1,len(ys)-1),180-160*(v-lo)/max(hi-lo,1e-30)) for i,v in enumerate(ys))
        chart='<h2>Weighted compliance history</h2><svg viewBox="0 0 640 210" width="640"><polyline fill="none" stroke="#1565c0" stroke-width="2" points="'+points+'"/></svg>'
    text='<!doctype html><meta charset="utf-8"><title>TopOptLab engineering report</title><style>body{font:16px system-ui;max-width:1000px;margin:40px auto;padding:20px}td,th{padding:10px;border-bottom:1px solid #ccc}pre{white-space:pre-wrap;word-break:break-word}svg{max-width:100%}</style><h1>TopOptLab engineering report</h1>'
    text+='<p>Version '+VERSION+' · '+html.escape(e['termination_reason'])+' · '+html.escape(e['material']['name'])+'</p>'
    text+='<p>Preview displays case '+html.escape(e['display_case'])+'. Mass: %.6g kg. Optimization stress is a relaxed design surrogate; verify the final shape.</p>'%e['mass_kg']
    units=e['material'];lu=html.escape(units['length_unit']);fu=html.escape(units['force_unit'])
    stress_label='Max relaxed design stress' if e['mode']=='optimize' else 'Max von Mises'
    text+='<table><tr><th>Load case</th><th>Compliance ('+fu+' '+lu+')</th><th>Max displacement ('+lu+')</th><th>'+stress_label+' ('+fu+'/'+lu+'^2)</th></tr>'+rows+'</table>'+chart
    check_summary=e['design_limits'];check_rows=''
    for case in check_summary['cases']:
        for check in case['checks']:
            check_rows+='<tr><td>'+html.escape(case['name'])+'</td><td>'+html.escape(check['kind'])+'</td><td>%.6g</td><td>%.6g</td><td>%.2f%%</td><td>%s</td></tr>'%(check['value'],check['limit'],100*check['utilization'],html.escape(check['status']))
    color='#9b1c1c' if check_summary['status'] in ('exceeded','constraints_not_satisfied') else '#183f60'
    text+='<h2>Design limits</h2><p style="color:'+color+'"><strong>'+html.escape(check_summary['status'])+'</strong> | '+html.escape(check_summary['scope'])+'</p>'
    text+='<p>Numerical tolerance: %.3g%%. Each load case is checked independently. These checks are not structural-code certification.</p>'%(100*check_summary['requested']['tolerance'])
    if check_rows:text+='<table><tr><th>Case</th><th>Field</th><th>Maximum</th><th>Limit</th><th>Utilization</th><th>Status</th></tr>'+check_rows+'</table>'
    if e.get('constraint_optimizer') is not None:
        text+='<p>MMA aggregate/budget feasibility: '+str(e['constraint_optimizer']['feasible'])+'. Maximum normalized violation: %.6g.</p>'%e['constraint_optimizer']['max_constraint_violation']
    if e.get('constraint_optimizer',{}):
        failure=e['constraint_optimizer'].get('numerical_failure')
        if failure:text+='<p><strong>Optimizer stopped after a numerical failure. The saved design is for inspection:</strong> '+html.escape(failure)+'</p>'
    if e['mode']=='optimize':text+='<p><strong>Design stress = sqrt(density) times solid-material von Mises. This is not the stress in the final extracted part.</strong></p>'
    text+='<h2>Applied loads and reactions</h2><p>Vector components: '+html.escape(e['load_coordinate_system'])+'. Force unit: '+fu+'.</p>'
    for case in e['cases']:
        text+='<h3>'+html.escape(case['name'])+'</h3><p>Applied resultant: '+html.escape(str(case['applied_force']))+'; reaction resultant: '+html.escape(str(case['reaction_force']))+'.</p>'
        text+='<pre>'+html.escape(json.dumps(case['loads'],indent=2))+'</pre>'
    text+='<p>Automatically preserved interface cells: '+str(e['automatically_preserved_interface_cells'])+'. Volume policy: '+html.escape(e['volume_policy'])+'.</p>'
    text+='<details><summary>Units, provenance and full calculation record</summary><pre>'+html.escape(json.dumps(e,indent=2))+'</pre></details>'
    path.write_text(text,encoding='utf8')

def run_engineering(request,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);job=str(request['job_id']);started=time.perf_counter()
    if (out/'result.json').exists() or (out/'progress.json').exists():raise ValueError('Use a fresh job directory')
    last=None
    try:
        if (out/'cancel').exists():raise Cancelled()
        if request.get('schema')!='topoptlab-gh-request-v1':raise ValueError('Unsupported schema')
        r=copy.deepcopy(request);mode=r.get('mode','fem');dimension=r.get('dimension',2)
        if mode not in ('fem','optimize','verify') or dimension not in (2,3):raise ValueError('Invalid engineering mode/dimension')
        material=resolve(r.get('material',{}));limits=resolve_limits(r.get('design_limits',{}),material);s=r['settings'];s.update(young=material['young'],poisson=material['poisson']);s.setdefault('backend','cpu-direct')
        sig=signature(request);spec=r.get('manufacturing',{});cases=r.get('load_cases')
        if not cases:raise ValueError('Connect load cases')
        r['loads']=[]
        r['dimension']=dimension
        if dimension==3:
            from resource_budget import grid_resources
            grid_resources(r)
        preserved_interfaces=preserve_interfaces(r)
        if mode=='verify':
            source=r.get('source_result')
            if not isinstance(source,dict) or source.get('status')!='completed' or 'density' not in source:raise ValueError('Connect a completed engineering optimization result')
            if source.get('engineering',{}).get('input_signature')!=sig:raise ValueError('Geometry, supports, loads, units or material changed since optimization; recompute the source')
            if source.get('engineering',{}).get('mode')!='optimize':raise ValueError('Verification source must be optimization')
            rho=np.asarray(source['density'],float);active=np.asarray(r['domain']['active'])
            if rho.shape!=active.shape:raise ValueError('Source density does not match domain')
            threshold=number(spec.get('threshold',.5),'threshold',.01,.99);selected=active[rho>=threshold].tolist()
            if not selected:raise ValueError('Threshold removed all material')
            r['domain']['active']=selected;r['domain']['solid']=[];r['mode']='fem'
        ModelType=Model3D if dimension==3 else Model
        model=ModelType(r);model.engine=ElasticSolver(model,s);model.engine.cancel=lambda:(out/'cancel').exists();forces=prepare_cases(model,cases,material)
        has_gravity=any(c['body'] is not None for c in forces)
        if mode=='optimize':constrain_design(model,spec)
        initial_case_compliances=[]
        def evaluate(rho):
            responses=[];total=0;gradient=None
            for case in forces:
                model.engine.check_cancel()
                res=solve_case(model,case,rho);responses.append(res);total+=case['weight']*res['compliance']
                if res['gradient'] is not None:gradient=case['weight']*res['gradient'] if gradient is None else gradient+case['weight']*res['gradient']
            if not initial_case_compliances:initial_case_compliances.extend(res['compliance'] for res in responses)
            combined=dict(responses[0]);combined.update(compliance=total,gradient=gradient)
            return combined,responses
        history=[];reason='fem_completed';best=None;constraint_optimizer=None
        constrained=mode=='optimize' and limits['active'] and limits['enforce']
        if constrained:
            def progress(rho,combined,responses,iteration,baseline,history,feasibility):
                nonlocal last
                last=model.payload(rho,combined,iteration,baseline,'running',history,job)
                if 'von_mises_relaxed' in responses[0]:last['von_mises_relaxed']=responses[0]['von_mises_relaxed'].tolist()
                last['engineering']=dict(mode=mode,display_case=forces[0]['name'],termination_reason='running',material=material,constraint_optimizer=feasibility)
                write_json(out/'progress.json',last)
            rho,combined,responses,iteration,baseline,history,reason,constraint_optimizer=optimize_constrained(model,forces,limits,evaluate,progress)
            data=model.payload(rho,combined,iteration,baseline,'completed',history,job)
        elif mode=='optimize':
            x=model.initial();previous_rho=None;previous_c=None;stable=0
            if has_gravity and np.min(x)<.001:raise ValueError('Increase Volume: self-weight optimization needs density >= 0.001 in design cells')
            tol=number(s.get('objective_tolerance',1e-3),'objective tolerance',1e-8,.1);dtol=number(s.get('design_tolerance',.01),'design tolerance',1e-6,.2)
            window=integer(s.get('convergence_window',5),'convergence window',2,50);minimum=integer(s.get('minimum_iterations',10),'minimum iterations',1,1000)
            reason='iteration_limit'
            for iteration in range(model.iterations+1):
                rho=model.density(x);combined,responses=evaluate(rho)
                if iteration==0:baseline=combined['compliance']
                change=None if previous_c is None else abs(combined['compliance']-previous_c)/max(abs(previous_c),1e-30)
                dchange=None if previous_rho is None else float(np.max(abs(rho-previous_rho)))
                stationarity=projected_stationarity(model,x,combined['gradient']) if has_gravity else None
                history.append(dict(iteration=iteration,compliance=combined['compliance'],volume=float(rho.mean()),objective_change=change,design_change=dchange,projected_stationarity=stationarity))
                if best is None or combined['compliance']<best[1]['compliance']:best=(rho.copy(),combined,responses,iteration)
                last=model.payload(rho,combined,iteration,baseline,'running',history,job)
                last['engineering']=dict(mode=mode,display_case=forces[0]['name'],termination_reason='running',material=material)
                write_json(out/'progress.json',last)
                feasible=float(rho.mean())<=model.target+1e-8
                stable=stable+1 if iteration>=minimum and feasible and change is not None and change<=tol and dchange<=dtol and (not has_gravity or stationarity<=dtol) else 0
                if stable>=window:reason='converged';break
                previous_rho=rho.copy();previous_c=combined['compliance']
                if iteration<model.iterations:
                    if has_gravity:
                        updated=self_weight_step(model,x,combined,evaluate)
                        if updated is None:reason='line_search_stalled';break
                        x=updated
                    else:x=model.step(x,combined,baseline)
            # Return the converged design when convergence triggered, otherwise the best observed design.
            if reason!='converged':rho,combined,responses,iteration=best
            data=model.payload(rho,combined,iteration,baseline,'completed',history,job)
        else:
            rho=np.ones(model.n);write_json(out/'progress.json',dict(job_id=job,status='running'))
            combined,responses=evaluate(rho);data=model.fem_payload(responses[0],job)
            data['metrics']['compliance']=combined['compliance'];reason='voxel_reanalysis_completed' if mode=='verify' else 'fem_completed'
        model.engine.check_cancel();case_info=[];limit_cases=[]
        for i,(case,res) in enumerate(zip(forces,responses)):
            item=dict(loads=case['loads'],applied_force=res['applied_forces'].sum(axis=0).tolist(),reaction_force=res['reactions'].sum(axis=0).tolist(),name=case['name'],weight=case['weight'],compliance=res['compliance'],max_displacement=float(np.linalg.norm(res['displacement'],axis=1).max()),residual=res['residual'],equilibrium=res['balance'],performance=res['performance'])
            evaluation=evaluate_limits(model,case,rho,res,limits,False)
            limit_cases.append(dict(name=case['name'],checks=evaluation['checks']))
            item['max_von_mises_relaxed' if mode=='optimize' else 'max_von_mises']=evaluation['max_stress']
            if mode!='optimize':
                item['stress_utilization_screening']=None if material['allowable'] is None else evaluation['max_stress']/material['allowable']
            case_info.append(item)
        volume=float(rho.sum())*model.h**dimension*(model.thickness if dimension==2 else 1)
        metadata=dict(version=VERSION,mode=mode,input_signature=sig,termination_reason=reason,converged=reason=='converged',
                      display_case=forces[0]['name'],objective='sum(weight * compliance) over independent cases',cases=case_info,
                      load_coordinate_system='domain axes' if dimension==2 else 'world XYZ',
                      automatically_preserved_interface_cells=preserved_interfaces,
                      optimization_update=('projected gradient with Armijo line search' if has_gravity else 'optimality criteria') if mode=='optimize' else 'not applicable: FEM',
                      volume_policy=('fixed budget with self-weight; minimum design density 0.001' if has_gravity else 'upper bound') if mode=='optimize' else 'solid retained grid',
                      loading_notes=['Distributed loads on fixed DOFs contribute to reactions; nodal point loads in constrained directions remain rejected.', 'Surface loads act on preserved grid facets, not an evolving CAD boundary.', 'Self-weight optimization is experimental: low-density SIMP parasitic effects and mesh dependence require final-shape verification.'],
                      material=material,mass_kg=volume*material['length_m']**3*material['density_kg_m3'],
                      manufacturing=manufacturing_report(model,rho,spec),elapsed_seconds=time.perf_counter()-started,
                      verification='same-grid binary voxel FEM; no smoothing, remeshing or code-compliance certification' if mode=='verify' else 'not a final-shape verification',
                      report_file=str(out/'report.html'))
        if dimension==3:metadata['resources']=model.resource_estimate
        metadata['weighted_compliance']=combined['compliance']
        metadata['case_files']=['case-%02d.json'%(i+1) for i in range(len(forces))]
        metadata['design_limits']=summarize_limits(limits,limit_cases,mode)
        metadata['constraint_optimizer']=constraint_optimizer
        if constraint_optimizer is not None:
            metadata['design_limits']['sampled_checks_status']=metadata['design_limits']['status']
            metadata['design_limits']['optimizer_feasible']=constraint_optimizer['feasible']
            if not constraint_optimizer['feasible']:metadata['design_limits']['status']='constraints_not_satisfied'
        if constrained:
            metadata['optimization_update']='MMA with displacement/stress adjoints'
            metadata['volume_policy']=constraint_optimizer['volume_policy']
        if mode=='optimize':data['von_mises_relaxed']=responses[0]['von_mises_relaxed'].tolist()
        data['engineering']=metadata
        for i,(case,res) in enumerate(zip(forces,responses)):
            model.engine.check_cancel()
            if mode=='optimize':
                selected=model.payload(rho,res,iteration,initial_case_compliances[i],'completed',[],job)
                selected['completed_iterations']=data['completed_iterations']
                selected['von_mises_relaxed']=res['von_mises_relaxed'].tolist()
                selected['history_note']='Weighted objective history is stored in the parent result.'
            else:
                selected=model.fem_payload(res,job)
                if dimension==3 and model.resource_estimate['compact_results']:
                    stress_file='case-%02d-stress.npz'%(i+1)
                    model.save_stress(res,out/stress_file)
                    selected['stress_file']=str(out/stress_file)
                    if i==0:data['stress_file']=str(out/stress_file)
            applied=res['applied_forces']
            if dimension==2:applied=applied[:,0:1]*model.frame[1]+applied[:,1:2]*model.frame[2]
            selected['applied_forces']=applied.tolist()
            selected['load_case']=dict(name=case['name'],weight=case['weight'])
            selected['engineering']=dict(metadata,display_case=case['name'],selected_case_index=i+1,result_scope='single_case')
            write_json(out/metadata['case_files'][i],selected)
        write_json(out/'project.json',request);write_json(out/'history.json',history);write_report(out/'report.html',data)
        write_json(out/'result.json',data);write_json(out/'progress.json',data);return data
    except Cancelled:
        data=last or dict(job_id=job);data['status']='cancelled';write_json(out/'progress.json',data);return data
    except Exception as exc:
        write_json(out/'progress.json',dict(job_id=job,status='error',message=str(exc)));raise
