from pathlib import Path
import json,re,html
ROOT=Path(__file__).resolve().parents[2];SITE=ROOT/'docs/manual'
E=lambda s:html.escape(str(s),quote=True)
CONTENT=json.loads((SITE/'data/lesson-content.json').read_text(encoding='utf8'))['lessons']
COURSE=json.loads((SITE/'data/course.json').read_text(encoding='utf8'))['lessons']
COMP={c['class']:c for c in json.loads((SITE/'data/components.json').read_text(encoding='utf8'))['components']}

def svg(body,label):return '<svg class="diagram course-diagram" viewBox="0 0 640 300" role="img" aria-label="'+E(label)+'">'+body+'</svg>'
def card(title,text):return '<div class="checkpoint"><b>'+E(title)+'</b><p>'+E(text)+'</p></div>'
def visuals(key):
 if key in COMP:return '<figure class="component-visual"><img src="../../assets/components/'+key+'.png" alt="Native Grasshopper rendering of '+E(COMP[key]['name'])+'"><figcaption>Actual component ports · rendered with Grasshopper</figcaption></figure>'
 if key in ['fem-shape','optimize-shape','verify-shape']:
  stage=key.split('-')[0];return '<figure class="computed-visual"><img src="../../assets/course/intro-'+stage+'.svg" alt="Calculated reference '+stage+' cell geometry for the introductory plate"><figcaption>Computed reference · h = 6 mm · undeformed geometry</figcaption></figure>'
 if key in ['conditions','support-diagram']:
  dots=''.join(f'<circle cx="100" cy="{40+i*20}" r="5" fill="#b65225"/>' for i in range(11))
  return svg('<rect x="100" y="40" width="400" height="200" fill="#dcebe4" stroke="#217267" stroke-width="2"/>'+dots+'<circle cx="500" cy="140" r="7" fill="#b65225"/><path d="M500 150V220l-10 -18m10 18 10 -18" fill="none" stroke="#b65225" stroke-width="4"/><g fill="#183d42" font-family="system-ui" font-size="19"><text x="100" y="25">11 constrained nodes</text><text x="390" y="275">1 loaded node · -100 N</text></g>','Schematic: 11 left-edge nodes constrained in X/Y and one right-midpoint loaded node')
 if key=='roof-diagram':
  return svg('<path d="M50 245V205L320 55 590 205V245Z" fill="#dcebe4" stroke="#217267" stroke-width="3"/><path d="M50 245l-15 25h30Z M590 245l-15 25h30Z" fill="#b65225"/><path d="M575 278H605" stroke="#183d42" stroke-width="3"/><g font-family="system-ui" font-size="21" fill="#183d42"><text x="320" y="287" text-anchor="middle">6,000 mm span</text><text x="50" y="30">Schematic · pin + anchored roller</text></g>','Schematic outline of the 6 metre roof rib, with pin and anchored roller')
 cards={
 'force-card':('Total force = (0, -100, 0) N','If n unique nodes are selected, each receives one nth of this total.'),
 'units-card':('mm · N · MPa','Stress units: N/mm² = MPa. Physical thickness: 2 mm.'),
 'balance-card':('Applied + reactions ≈ 0','Vertical forces: -100 N + 100 N ≈ 0 N.'),
 'budget-card':('Volume fraction = 0.40','Continuous-density mass: 40% of the active full-material domain, including preserved material.'),
 'status-card':('Read the termination reason','Converged, iteration limit, cancelled and error describe different outcomes.'),
 'mass-card':('0.113040 kg → 0.045216 kg','Baseline full plate → continuous-density design. Their stiffness distributions differ.'),
 'threshold-card':('Keep cells with density ≥ 0.40','The threshold changes the binary shape, its mass and its stiffness.'),
 'failure-card':('Threshold 0.50: disconnected','This is an observed rejection of the supplied reference design. Restore 0.40 for the guided calculation.'),
 'roof-card':('630 cells · 44 Keep cells','h = 100 mm · thickness = 12 mm · spacing = 3,000 mm.'),
 'roof-results':('Binary roof reference','199.704 kg · SLS U = 1.229039 mm · uplift reaction ≈ -6.850786 kN per support.'),
 'comparison-card':('52% lighter than the full plate','Introductory binary candidate: 0.0542592 kg; maximum U ≈ 0.018660 mm.'),
 'scope-card':('The conclusion has a scope','2D plane stress, linear elasticity and the declared loads/supports. State what remains uncertain.'),
 'next-card':('One question → one check','Choose an uncertainty, hold other factors fixed and decide what evidence to collect.'),
 'conclusion-card':('Claim → evidence → limitation → next check','Use units and stage names. Distinguish your own computation from supplied reference values.'),
 'checkpoint':('Explain your model and evidence','State the important settings, the observed result and what you would investigate next.')}
 return card(*cards[key])

def links(l):return '<ul>'+''.join('<li><a href="'+E(path)+'">'+E(title)+'</a></li>' for title,path in l['files'])+'</ul>'
def sequence(l):
 i=int(l['id'])-1;parts=[]
 if i:parts.append('<a href="../'+COURSE[i-1]['path']+'">← Lesson '+COURSE[i-1]['id']+'</a>')
 if i<len(COURSE)-1:parts.append('<a href="../'+COURSE[i+1]['path']+'">Lesson '+COURSE[i+1]['id']+' →</a>')
 else:parts.append('<a href="../index.html">Return to the learning path</a>')
 return '<div class="manual-related"><strong>Your learning path</strong><p>'+' · '.join(parts)+'</p></div>'
def connection_help(l):
 step={'03':2,'04':6,'05':9,'06':11,'07':14,'08':13}[l['id']]
 return '<div class="manual-related"><strong>Follow the connections</strong><p><a href="../connections/index.html#step-'+str(step)+'">Illustrated connections for this lesson</a> · <a href="../../examples/index.html">All prepared examples</a></p></div>'

def page(l,name,title,body,script=''):
 folder=SITE/'learnings'/l['slug'];folder.mkdir(parents=True,exist_ok=True)
 text='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Lesson '+l['id']+' — '+E(title)+' · TopOptLab</title><link rel="stylesheet" href="../../assets/lesson.css"></head><body><main class="manual-content"><header>TOP OPT LAB / LESSON '+l['id']+' / '+str(l['minutes'])+' MINUTES</header>'+body+connection_help(l)+sequence(l)+'<footer><a href="index.html">Lesson home</a> · <a href="teacher-guide.html">Teacher guide</a> · <a href="student-sheet.html">Student worksheet</a> · <a href="slides.html">Slides</a></footer></main>'+script+'</body></html>'
 (folder/name).write_text(text,encoding='utf8')
def list_(items):return '<ul>'+''.join('<li>'+E(s)+'</li>' for s in items)+'</ul>'
def steps(l):return '<ol>'+''.join('<li>'+E(s)+'</li>' for s in l['steps'])+'</ol>'
def refs(l):return '<div class="manual-grid two component-gallery">'+''.join('<figure class="manual-card"><img src="../../assets/components/'+c+'.png" alt="Native Grasshopper rendering of '+E(COMP[c]['name'])+'"><figcaption><a href="../../components/index.html#'+c+'">'+E(COMP[c]['name'])+' → full component reference</a></figcaption></figure>' for c in l['components'])+'</div><p class="manual-small">These are native Grasshopper capsule renderings of the actual components, not screenshots of a running solve.</p>'
def wiring(l):return '<div class="table-wrap"><table><thead><tr><th>From</th><th>To / meaning</th></tr></thead><tbody>'+''.join('<tr><td>'+E(a)+'</td><td>'+E(b)+'</td></tr>' for a,b in l['wires'])+'</tbody></table></div>'
def reference(l):
 if l['id'] in ['04','05','06','08']:
  d=json.loads((SITE/'data/intro-reference.json').read_text(encoding='utf8'))['results'];rows=[]
  for key,label in [('fem','Full-material baseline'),('optimize','Continuous-density design'),('verify','Binary verification T = 0.40')]:
   e=d[key];c=e['cases'][0];stress='relaxed design surrogate' if key=='optimize' else f"{c['max_von_mises']:.6f}"
   rows.append(f'<tr><td>{label}</td><td>{e["mass_kg"]:.7f}</td><td>{c["max_displacement"]:.7f}</td><td>{stress}</td></tr>')
  return '<h2>Computed reference — introductory plate</h2><p>120 × 60 × 2 mm; h = 6 mm; steel; 100 N downward; left edge fixed. This table records a Python-worker run of the declared model, not a classroom Rhino UI test.</p><div class="table-wrap"><table><tr><th>Stage</th><th>Mass (kg)</th><th>Maximum U (mm)</th><th>Maximum von Mises (MPa)</th></tr>'+''.join(rows)+'</table></div><p><a href="../../data/intro-reference.json">Inputs and numerical reference</a>. Relaxed optimisation stress is deliberately not presented as a comparable full-material stress value.</p>'
 if l['id']=='07':
  return '''<h2>Existing roof reference — h = 100 mm</h2><p>Fixed teaching assumptions: steel, 12 mm thickness, Volume 0.30, Threshold 0.40. Values below come from the existing roof course reference.</p><div class="table-wrap"><table><tr><th>Metric</th><th>Full plate</th><th>Density design</th><th>Binary plate</th></tr><tr><td>Mass (kg)</td><td>593.460</td><td>178.038</td><td>199.704</td></tr><tr><td>SLS maximum U (mm)</td><td>0.446785</td><td>2.455073</td><td>1.229039</td></tr><tr><td>Left-snow ULS peak stress (MPa)</td><td>39.794733</td><td>74.499572 (relaxed)</td><td>57.027307</td></tr><tr><td>Uplift reaction per support (kN)</td><td>-4.920073</td><td>Read case report</td><td>-6.850786</td></tr></table></div><p>On the same binary shape, refinement h = 100 → 50 → 25 mm gives SLS U ≈ 1.2290 → 1.4521 → 1.5787 mm, while peak stress rises ≈ 57.03 → 86.64 → 141.16 MPa. The peak has not converged. These are grid-study observations, not a complete design acceptance.</p>'''
 return ''

def experiment(l):
 if l['id']=='03':return '<section class="experiment"><h2>Explore total versus per-node force</h2><label for="nodes">Number of selected unique nodes (schematic)</label><select id="nodes"><option>1</option><option>2</option><option>5</option><option>10</option></select><output id="node-force" aria-live="polite">Total -100 N → -100 N per node</output><p class="manual-small">Arithmetic illustration of the Load component convention. It does not change your Grasshopper selection or solve the model.</p></section>',"document.querySelector('#nodes').onchange=e=>document.querySelector('#node-force').textContent='Total -100 N → '+(-100/Number(e.target.value))+' N per node';"
 if l['id']=='05':return '<section class="experiment"><h2>Explore the material budget</h2><label for="budget">Continuous-density target fraction</label><select id="budget"><option value="0.30">0.30</option><option value="0.40" selected>0.40</option><option value="0.50">0.50</option></select><output id="budget-mass" aria-live="polite">Target density mass ≈ 0.045216 kg</output><p class="manual-small">Budget arithmetic for this full 0.113040 kg plate. This does not predict topology, convergence, displacement or binary mass. Rerun the solver to calculate those.</p></section>',"document.querySelector('#budget').onchange=e=>document.querySelector('#budget-mass').textContent='Target density mass ≈ '+(.11304*Number(e.target.value)).toFixed(6)+' kg';"
 if l['id']=='06':
  return '<section class="experiment"><h2>Try a threshold on the computed density</h2><label for="threshold">Threshold for the reference density result</label><select id="threshold"><option value="0.3">0.30</option><option value="0.4" selected>0.40 — guided example</option><option value="0.5">0.50 — disconnected in reference</option><option value="0.6">0.60</option></select><output id="threshold-output" aria-live="polite"></output><p class="manual-small">Counts and binary mass use the saved density values. This browser calculation does not reanalyse stiffness or validate connectivity. Only the 0.40 and 0.50 cases were checked with the worker; use Mode 2 for a new verification.</p></section>',"const rho="+json.dumps(json.loads((SITE/'data/intro-visuals.json').read_text())['density'])+";const t=document.querySelector('#threshold');function updateThreshold(){let n=rho.filter(v=>v>=Number(t.value)).length;document.querySelector('#threshold-output').textContent=n+' retained cells · binary mass '+(n*6*6*2*7.85e-6).toFixed(7)+' kg';}t.onchange=updateThreshold;updateThreshold();"
 return '', ''

def build():
 style=(SITE/'learnings/02-build-the-domain/index.html').read_text(encoding='utf8');css=re.search(r'<style>(.*?)</style>',style,re.S).group(1)
 css+=''' figure{margin:0} .component-gallery{margin:22px 0}.component-gallery figure{text-align:center;display:flex;flex-direction:column;align-items:center;justify-content:space-between;gap:20px}.component-gallery img{max-width:100%;height:240px;object-fit:contain}.component-gallery figcaption{font-size:15px}.experiment{margin:30px 0;padding:24px;border:1px solid #d1ded7;border-radius:12px;background:white}.experiment output{display:block;font-weight:700;margin:15px 0}.lesson-controls{display:flex;gap:12px;flex-wrap:wrap}.lesson-visual{max-width:800px;margin:24px auto}.lesson-visual img{width:100%;max-height:400px;object-fit:contain}.lesson-visual figcaption{font-size:13px;color:#526970}.manual-content .experiment h2{margin-top:0}.manual-content h2{margin-top:32px}.worksheet-note{font-size:14px;color:#526970} .manual-content textarea{margin-bottom:20px} @media print{.experiment{display:none}.component-gallery{display:block}.component-gallery img{height:180px}header{font-size:10pt}}'''
 (SITE/'assets/lesson.css').write_text(css,encoding='utf8')
 old=(SITE/'learnings/02-build-the-domain/slides.html').read_text(encoding='utf8');slidecss=re.search(r'<style>(.*?)</style>',old,re.S).group(1);controller=re.search(r'<script>(.*?)</script>',old,re.S).group(1)
 slidecss+='''.component-visual,.computed-visual{margin:0;min-height:0;height:clamp(120px,31vh,330px);display:flex;flex-direction:column;align-items:center;gap:5px}.component-visual img,.computed-visual img{display:block;max-width:100%;max-height:calc(100% - 24px);object-fit:contain;min-height:0}.component-visual figcaption,.computed-visual figcaption{font-size:clamp(10px,1vw,13px);line-height:1.2;color:#526970}.checkpoint p{line-height:1.4}.course-diagram{max-height:30vh}@media(max-height:700px){.slide-content{gap:clamp(8px,1.5vh,16px)}.component-visual,.computed-visual{height:28vh}.checkpoint{padding:clamp(12px,2vw,22px)}}@media(max-height:600px){.component-visual,.computed-visual{height:25vh}}@media(max-height:500px){.component-visual,.computed-visual{height:23vh}.checkpoint p{font-size:15px}.checkpoint{padding:12px}.component-visual figcaption,.computed-visual figcaption{display:none}.component-visual img,.computed-visual img{max-height:100%}}'''
 for l in CONTENT:
  experiment_html,experiment_js=experiment(l)
  controls='<div class="lesson-controls"><a class="button" href="slides.html">Open the slides</a><a class="button" href="teacher-guide.html">Teacher guide</a><a class="button" href="student-sheet.html">Student worksheet</a></div>'
  keyvisual={'03':'conditions','04':'fem-shape','05':'optimize-shape','06':'verify-shape','07':'roof-diagram','08':'comparison-card'}[l['id']]
  start='<p class="eyebrow">STEP BY STEP / '+str(l['minutes'])+' MINUTES</p><h1>'+E(l['title'])+'.</h1><p class="lead">'+E(l['question'])+'</p><p>'+E(l['goal'])+'</p>'+controls+'<div class="lesson-visual">'+visuals(keyvisual)+'</div>'
  run_note='' if l['id']=='03' else '<p class="note"><strong>Before starting:</strong> teaching archives contain the definition, not completed runtime jobs. Select the shared Rhino geometry where needed and run the required stages in order. Keep job folders in place for reports and case selection.</p>'
  page(l,'index.html',l['title'],start+'<h2>Files and starting point</h2>'+links(l)+run_note+'<h2>Build and observe</h2>'+steps(l)+'<h2>Follow the data</h2>'+wiring(l)+experiment_html+'<h2>Understand the result</h2>'+l['notes']+reference(l)+'<h2>Components in this lesson</h2>'+refs(l)+'<h2>Checkpoint</h2>'+list_(l['checkpoint']),'<script>'+experiment_js+'</script>' if experiment_js else '')
  rows=''.join('<tr><td>'+E(t)+'</td><td>'+E(a)+'</td><td>'+E(b)+'</td></tr>' for t,a,b in l['activities'])
  errors=''.join('<tr><td>'+E(a)+'</td><td>'+E(b)+'</td></tr>' for a,b in l['problems'])
  prep='<ul><li>Open the exact lesson files before class; check plugin loading, geometry, units and preview.</li><li>For calculation lessons, test Run, Stop, Reset and save/reopen on the actual classroom installation. Native archive checks and Python reference solves do not replace this interactive acceptance.</li><li>Keep the wired solution and reference table available. Where a student cannot calculate, use paired work or supplied evidence and label its provenance.</li><li>Introduce only the new concepts for this block. Keep the component reference available for detailed port questions.</li></ul>'
  page(l,'teacher-guide.html','Teacher guide — '+l['title'],'<p class="eyebrow">TEACHER GUIDE</p><h1>'+E(l['title'])+'.</h1><p class="lead">'+E(l['goal'])+'</p><h2>Prepare before class</h2>'+prep+'<h2>Teaching script</h2><div class="table-wrap"><table><tr><th>Time</th><th>Explain / demonstrate</th><th>Student evidence</th></tr>'+rows+'</table></div><h2>Demonstration recipe</h2>'+steps(l)+'<h2>Questions, errors and recovery</h2><div class="table-wrap"><table><tr><th>Observation</th><th>Response</th></tr>'+errors+'</table></div>'+reference(l)+'<h2>Expected checkpoint</h2>'+list_(l['checkpoint'])+'<h2>Conceptual scope</h2>'+l['notes'])
  fields=''.join('<div class="field"><label for="'+key+'">'+str(i+1)+'. '+E(prompt)+'</label><textarea id="'+key+'" data-save></textarea></div>' for i,(key,prompt) in enumerate(l['prompts']))
  worksheet='<p class="eyebrow">STUDENT WORKSHEET / PREDICT → OBSERVE → EXPLAIN</p><h1>'+E(l['title'])+'.</h1><p class="lead">'+E(l['goal'])+'</p><h2>Start here</h2>'+links(l)+'<p><a href="index.html">Open the full step-by-step exercise</a></p><h2>Your observations</h2>'+fields+'<h2>Ready to continue?</h2>'+list_(l['checkpoint'])+'<p><button onclick="window.print()">Print / Save as PDF</button></p><p class="worksheet-note" id="save-status" role="status">Answers stay in this browser when local storage is available. Print a copy to keep your work. Label supplied reference numbers clearly.</p>'
  js="const prefix='topopt-lesson"+l['id']+"-';for(const e of document.querySelectorAll('[data-save]')){try{e.value=localStorage.getItem(prefix+e.id)||''}catch{}e.addEventListener('input',()=>{try{localStorage.setItem(prefix+e.id,e.value)}catch{document.querySelector('#save-status').textContent='Browser storage is unavailable. Print a copy to keep your answers.'}})}"
  page(l,'student-sheet.html','Student worksheet — '+l['title'],worksheet,'<script>'+js+'</script>')
  sections=''.join('<section class="slide" id="slide-'+str(i+1)+'" aria-label="Slide '+str(i+1)+'"><div class="slide-content"><p class="eyebrow">LESSON '+l['id']+' / '+E(timing)+'</p><h1>'+E(title)+'</h1><p class="lead">'+E(lead)+'</p>'+visuals(visual)+'<p class="prompt">'+E(prompt)+'</p></div></section>' for i,(timing,title,lead,visual,prompt) in enumerate(l['slides']))
  deck='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Lesson '+l['id']+' — '+E(l['title'])+'</title><style>'+slidecss+'</style></head><body>'+sections+'<nav aria-label="Presentation controls"><button id="prev">← Previous</button><span id="progress" aria-live="polite">1 / '+str(len(l['slides']))+'</span><button id="next">Next →</button><a href="teacher-guide.html">Teacher notes</a><a href="index.html">Back to lesson</a></nav><script>'+controller+'</script></body></html>'
  (SITE/'learnings'/l['slug']/'slides.html').write_text(deck,encoding='utf8')
 print('Built lessons 03–08 in the unified manual (42 slides).')

if __name__=='__main__':build()
