"""Build the manual navigation and component catalogue. No exports or ZIPs."""
from pathlib import Path
import html,json,re,runpy,os
from release_links import release_downloads
from funding import funding_html, update_readme
REPO=Path(__file__).resolve().parents[2]
SITE=REPO/'docs/manual'
E=lambda s:html.escape(str(s))

def relative(page,target):
 return os.path.relpath(SITE/target,page.parent).replace('\\','/')

def chrome(page,section):
 links=[('home','Home','index.html'),('components','Components','components/index.html'),('learnings','Learnings','learnings/index.html'),('setup','Getting Started','getting-started/index.html')]
 nav=''.join('<a '+('aria-current="page" ' if section==key else '')+'href="'+relative(page,path)+'">'+label+'</a>' for key,label,path in links)
 return '<!-- MANUAL NAV START --><div class="manual-bar"><a class="manual-brand" href="'+relative(page,'index.html')+'">TOP OPT LAB <span>/ MANUAL</span></a><div class="manual-links" role="navigation" aria-label="Main manual navigation">'+nav+'</div></div><!-- MANUAL NAV END -->'

def integrate(page,section):
 text=page.read_text(encoding='utf8')
 text=re.sub(r'<!-- MANUAL NAV START -->.*?<!-- MANUAL NAV END -->','',text,flags=re.S)
 text=re.sub(r'<!-- FUNDING ACKNOWLEDGEMENT START -->.*?<!-- FUNDING ACKNOWLEDGEMENT END -->','',text,flags=re.S)
 text=re.sub(r'<link[^>]*data-manual-style[^>]*>','',text)
 style='<link data-manual-style rel="stylesheet" href="'+relative(page,'assets/manual.css')+'">'
 if '</head>' in text:text=text.replace('</head>',style+'</head>',1)
 else:text=text.replace('<main>',style+'<main>',1)
 text=re.sub(r'<main\b[^>]*>',lambda m:chrome(page,section)+m.group(0),text,count=1)
 text=re.sub(r'<!-- RELATED START -->.*?<!-- RELATED END -->','',text,flags=re.S)
 text=re.sub(r'<!-- CONNECTIONS START -->.*?<!-- CONNECTIONS END -->','',text,flags=re.S)
 if '01-understand-the-problem' in page.parts:
  related='<div class="manual-related"><strong>Continue learning</strong><p><a href="'+relative(page,'components/index.html')+'#DomainComponent">Component reference: TopOpt Domain</a> · <a href="'+relative(page,'learnings/02-build-the-domain/index.html')+'">Next: Build the domain</a> · <a href="'+relative(page,'learnings/index.html')+'">Full learning path</a></p></div>'
  text=text.replace('</main>','<!-- RELATED START -->'+related+'<!-- RELATED END --></main>')
 if section=='learnings' and page.parent.name.startswith(('01-','02-')):
  help='<div class="manual-related"><strong>Follow the connections</strong><p><a href="'+relative(page,'learnings/connections/index.html')+'#step-1">Domain connections, one step at a time</a> · <a href="'+relative(page,'examples/index.html')+'">All prepared examples</a></p></div>'
  text=text.replace('</main>','<!-- CONNECTIONS START -->'+help+'<!-- CONNECTIONS END --></main>')
 text=text.replace('</main>',funding_html(page,SITE)+'</main>',1)
 page.write_text(text,encoding='utf8')

def connection_resources(page):
 links=[('Illustrated installation','getting-started/installation/index.html'),('Components before the example','learnings/component-primer/index.html'),('Connection walkthrough','learnings/connections/index.html'),('All 21 examples','examples/index.html')]
 buttons=''.join('<a class="manual-button secondary" href="'+relative(page,target)+'">'+label+'</a>' for label,target in links)
 return release_downloads()+'<section class="manual-related"><h2>Installation, components and course files</h2><p>Install before class, learn the component inputs and outputs, then follow the worked examples and their 18 illustrated connection steps. All 21 prepared examples are linked here. PowerPoint presentations are maintained separately by the instructor. Each lesson also keeps its own HTML slides and practice files.</p><div class="manual-actions">'+buttons+'</div></section>'

def sync_example_archives():
 sources=sorted((REPO/'tool/examples').glob('*.ghx'))+[REPO/'teaching/roof_2d/output/case/roof_2d_classroom.ghx']
 destination=SITE/'components/examples';destination.mkdir(parents=True,exist_ok=True)
 for source in sources:
  target=destination/source.name;data=source.read_bytes()
  if not target.exists() or target.read_bytes()!=data:target.write_bytes(data)

def page(path,title,body,section):
 p=SITE/path;p.parent.mkdir(parents=True,exist_ok=True)
 resources=connection_resources(p)
 if section=='home':body=body.replace('<div class="manual-grid">',resources+'<div class="manual-grid">',1)
 elif section=='learnings':body=body.replace('<div class="manual-lesson-list">',resources+'<div class="manual-lesson-list">',1)
 elif section=='setup':body=body.replace('<h2>Teacher checklist</h2>',resources+'<h2>Teacher checklist</h2>',1)
 p.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+' · TopOptLab Manual</title></head><body><main class="manual-content">'+body+'<footer class="manual-page-footer">TopOptLab 0.4.0-dev · English teaching manual · <a href="'+relative(p,'LICENSE.txt')+'">License</a></footer></main></body></html>',encoding='utf8')
 integrate(p,section)

def build():
 update_readme(REPO)
 sync_example_archives()
 runpy.run_path(str(Path(__file__).with_name('build_intro.py')),run_name='__main__')
 runpy.run_path(str(Path(__file__).with_name('build_components.py')),run_name='__main__')
 integrate(SITE/'components/index.html','components')
 runpy.run_path(str(Path(__file__).with_name('build_lessons.py')),run_name='__main__')
 course=json.loads((SITE/'data/course.json').read_text(encoding='utf8'))
 catalogue=SITE/'components/index.html';catalogue_text=catalogue.read_text(encoding='utf8')
 for component in json.loads((SITE/'data/components.json').read_text(encoding='utf8'))['components']:
  uses=[entry for entry in course['lessons'] if component['class'] in entry['components'] and entry['status']=='available']
  if uses:
   links=' · '.join('<a href="../learnings/'+entry['path']+'">Lesson '+entry['id']+'</a>' for entry in uses)
   marker='id="'+component['class']+'"';start=catalogue_text.find(marker)
   if start>=0:
    end=catalogue_text.find('</h2>',start)
    if end>=0:catalogue_text=catalogue_text[:end+5]+'<p class="manual-small">Learn this in: '+links+'</p>'+catalogue_text[end+5:]
 catalogue.write_text(catalogue_text,encoding='utf8')

 lesson_cards=[]
 for l in course['lessons']:
  ready=l['status']=='available'
  refs=' · '.join('<a href="../components/index.html#'+c+'">'+E(c.replace('Component',''))+'</a>' for c in l['components'])
  lesson_cards.append('<article class="manual-card lesson-card" id="lesson-'+l['id']+'"><p class="manual-kicker">LESSON '+l['id']+' / '+str(l['minutes'])+' MINUTES <span class="manual-status '+('ready' if ready else 'planned')+'">'+('Available' if ready else 'Planned')+'</span></p><h2>'+E(l['title'])+'</h2><p>'+E(l['description'])+'</p><p class="manual-small">Component references: '+refs+'</p>'+('<a class="manual-button" href="'+l['path']+'">Open lesson '+l['id']+' →</a>' if ready else '<p class="manual-small">This lesson will be added here as the course develops.</p>')+'</article>')
 lesson_cards.insert(4,'<aside class="manual-related"><strong>10-minute break</strong><p>Save the completed baseline after lesson 04. Resume with the material-budget question in lesson 05.</p></aside>')
 page('learnings/index.html','Learnings','<p class="manual-kicker">STEP BY STEP / THREE-HOUR COURSE</p><h1>The learning path.</h1><p class="manual-lead">Start with a prediction. Build a model, solve it, then check what the result means. Every lesson connects back to the component reference.</p><p>The course includes 170 minutes of teaching and exercises, with a 10-minute break after lesson 04. All eight lessons are available, with slides, teacher guides, student worksheets and linked practice files. Start with lesson 01 and continue in order.</p><div class="manual-lesson-list">'+''.join(lesson_cards)+'</div>','learnings')
 page('index.html','Home','''<p class="manual-kicker">ONE MANUAL / ONE LEARNING PATH</p><div class="manual-hero"><div><h1>Learn TopOptLab.<br>One step at a time.</h1><p class="manual-lead">An English guide to modelling, FEM and topology optimisation in Rhino and Grasshopper.</p><p>Use the lessons to learn in sequence and the component guide to understand each input, output and connection.</p><div class="manual-actions"><a class="manual-button" href="learnings/01-understand-the-problem/index.html">Start lesson 01 →</a><a class="manual-button secondary" href="components/index.html">Explore components</a></div></div><figure><img src="assets/components/DomainComponent.png" alt="TopOpt Domain rendered with Grasshopper’s native capsule renderer"><figcaption>Actual component layout and ports, rendered for the guide.</figcaption></figure></div><div class="manual-grid"><article class="manual-card"><p class="manual-kicker">REFERENCE</p><h2>Component Guide</h2><p>33 components, 346 ports, rendered component images, exact defaults and verified wiring examples.</p><a href="components/index.html">Find a component →</a></article><article class="manual-card"><p class="manual-kicker">PRACTICE</p><h2>Learnings</h2><p>A progressive course: questions, actions, expected observations and checkpoints. Each lesson keeps its slides and files together.</p><a href="learnings/index.html">Follow the learning path →</a></article><article class="manual-card"><p class="manual-kicker">PREPARATION</p><h2>Getting Started</h2><p>Software preparation, Windows and Mac status, classroom checks and how to use this manual offline.</p><a href="getting-started/index.html">Prepare your computer →</a></article></div><section class="manual-section"><h2>The complete course is connected.</h2><p>All eight lessons are available: from the first prediction to a three-stage calculation, the roof-rib transfer exercise and an evidence-based conclusion. Teaching and exercises total 170 minutes, plus a 10-minute break.</p><p><a class="manual-button" href="learnings/index.html">Open all eight lessons →</a></p><p><strong>Lesson 01 — Understand the problem</strong> is ready: seven slides, teacher notes, a prediction sheet and the native Rhino/Grasshopper starter files.</p><p><a href="learnings/01-understand-the-problem/index.html">Open the complete lesson page →</a></p><p><strong>Lesson 02 — Build the domain</strong> is ready: interactive grid, seven slides, teacher guide, student worksheet and Grasshopper starter/solution.</p><p><a href="learnings/02-build-the-domain/index.html">Continue with lesson 02 →</a></p></section>''','home')
 page('getting-started/index.html','Getting Started','''<p class="manual-kicker">BEFORE CLASS</p><h1>Prepare once.<br>Learn in sequence.</h1><p class="manual-lead">This manual opens directly in a browser and works offline. Keep the manual folder intact so images, examples and lesson files stay connected.</p><h2>For the first lesson</h2><ol><li>Use Rhino 8 with a working license and Grasshopper.</li><li>Open the Rhino model and Grasshopper starter from the lesson page. The starter contains native parameters and instructions.</li><li>Use the slides for the explanation, the teacher guide for timing and the student sheet for predictions.</li></ol><a class="manual-button" href="../learnings/01-understand-the-problem/index.html">Open lesson 01</a><h2>For the later FEM and optimisation blocks</h2><p>Install the complete TopOptLab project before class. The Grasshopper plugin uses an external Python worker: the environment and worker must remain in their configured location.</p><div class="manual-grid two"><article class="manual-card"><h3>Windows / Rhino 8</h3><p>The source installer currently supports Windows x64 and Python 3.13. Save and close Rhino, then run <code>INSTALL.cmd</code> from the complete project checkout.</p><p>For the course, use the complete Windows ZIP linked below. It contains <code>software/windows/TopOptLab-Students-Windows-0.4.0-Setup.exe</code> and its CPU Python runtime. The source-installation route above is an alternative for developers and requires Python 3.13 and internet access.</p></article><article class="manual-card"><h3>Mac / classroom pilot</h3><p>A universal Mac Yak candidate is being prepared for Apple Silicon and Intel. CPU-worker tests pass on both architectures; native Rhino/Grasshopper acceptance remains pending. See <a href="#mac-yak-candidate">Mac candidate status and remaining checks</a>. This is not a public Mac Package Manager release.</p><p>Download the Apple Silicon or Intel ZIP matching Apple menu → About This Mac. Both packages remain pilots for macOS 15 or later. Each includes native dependencies and the official Python 3.13 installer. Native plugin loading, worker execution, preview and controls still require a teacher test on a real Mac.</p><p>Reading the manual, viewing the slides and completing the prediction sheet work in a browser on either platform. Arrange a prepared Windows workstation for group calculations where necessary.</p></article></div><h2>Teacher checklist</h2><ul><li>Open the exact lesson file before class.</li><li>Check units, Top view, layer visibility and geometry selection.</li><li>For calculation lessons, test Run, Stop, Reset, reports and preview on the classroom installation.</li><li>Check save/reopen and Bake/Undo before using those operations in class.</li></ul><section id="mac-yak-candidate" class="manual-section"><h2>Mac Yak candidate: Apple Silicon and Intel</h2><p>A single Mac package is being prepared for native arm64 and x86_64 Python. It requires macOS 15 or later, Rhino 8 SR37+ and native Python 3.13. It is not yet a public Mac Package Manager release.</p><p>The CPU worker, dependency setup, runtime reuse and host memory/path checks pass on both native Mac architectures. Each architecture passed 263 integration tests, with 11 expected CUDA/Windows test exclusions. Loading all components and using the menus, Rhino geometry, preview, Run/Stop/Reset, save/reopen and Bake/Undo inside Rhino for Mac remain pending.</p><p>For a supervised local trial, use the candidate package’s own README and <code>SETUP-PYTHON.command</code>. Keep the source folder intact: it contains this same manual and all examples. Do not use the Windows <code>.cmd</code> launcher or Rosetta Python on a Mac.</p></section><h2>Source and publication</h2><p>The manual is maintained inside <code>docs/manual/</code> in the <a href="https://github.com/andrea199/TopOptLab-Rhino-Grasshopper">TopOptLab-Rhino repository</a>. Internal navigation uses relative links so the same manual can be viewed locally or hosted. Installer downloads point to the new GitHub Release; this repository remains private during publication review and currently requires repository access. Publishing a Release does not activate a hosted manual site.</p><p><a href="../AUTHORING.md">How to add the next lesson</a> · <a href="../LICENSE.txt">License</a></p>''','setup')
 lesson=SITE/'learnings/01-understand-the-problem'
 for name in ['index.html','teacher-guide.html','student-sheet.html']:integrate(lesson/name,'learnings')
 # Presentation mode keeps its viewport-safe controls and returns to the lesson.
 slides=lesson/'slides.html';text=slides.read_text(encoding='utf8').replace('>Lesson home</a>','>Back to lesson</a>')
 def unique_svg(match):
  part=match.group(0);sid=re.search(r'id="(slide-\d+)"',part).group(1)
  for name in ['arrow','hatch']:
   part=part.replace('id="'+name+'"','id="'+name+'-'+sid+'"').replace('url(#'+name+')','url(#'+name+'-'+sid+')')
  return part
 text=re.sub(r'<section class="slide".*?</section>',unique_svg,text,flags=re.S)
 slides.write_text(text,encoding='utf8')
 for entry in course['lessons'][1:]:
  folder=SITE/'learnings'/Path(entry['path']).parent
  for name in ['index.html','teacher-guide.html','student-sheet.html']:integrate(folder/name,'learnings')
 for extra,section in [('examples/index.html','examples'),('learnings/connections/index.html','learnings'),('learnings/component-primer/index.html','learnings'),('getting-started/installation/index.html','setup')]:
  if (SITE/extra).is_file():integrate(SITE/extra,section)
 print('Built one English manual: home, component guide, eight lessons, connection walkthrough, example gallery and setup.')

if __name__=='__main__':build()
