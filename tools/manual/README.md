# Manual tools

The canonical content is `docs/manual/`.

```
python tools/manual/build.py
python tools/manual/check.py
```

The builder refreshes the component reference, home, Learnings and shared navigation. It creates no ZIP files and requires only the Python standard library.

To regenerate component illustrations on Windows after changing the GHA:

```
python tools/manual/render_images.py --assembly-dir <folder-containing-TopoptLab.GH.gha>
```

Rhino8 and the C# compiler supplied by Windows are required for image rendering; they are not required for reading or rebuilding the HTML content. Generated component images are documentation assets; compiled helper executables stay in a temporary directory.

## Lesson 02 exercise files

The canonical lesson pages are edited in `docs/manual/learnings/02-build-the-domain/`. Regenerate starter and wired solution with `python tools/manual/create_lesson02.py --assembly-dir <installed-plugin-directory>` on Windows with the Rhino 8 SDK. The tool compiles into a temporary directory, writes `.gh`/`.ghx` files and checks archive/object readback. Select the boundary from the shared lesson 01 Rhino model after opening either file. No structural solver is included.

## Complete course (lessons 03–08)

Edit English content in `docs/manual/data/lesson-content.json`; normal `build.py` invokes `build_lessons.py`. The approved lesson 01–02 HTML stays editable directly. Lesson images reuse shared component assets. Introductory cell plots come from worker results; they are not generated concept illustrations.

Optional native file regeneration on Windows:

```
python tools/manual/create_course_files.py --assembly-dir <installed-plugin-directory>
```

The C# helper writes the progressive lesson 03–06 `.gh` and `.ghx` starter/solution files and performs SDK archive/object readback. SDK libraries and the compiled helper remain in a disposable temporary directory. It does not load or alter the installed runtime configuration.

Reference reproduction (use the project Python environment and a fresh output directory):

```
python tools/manual/reproduce_intro.py --output tool/build/new-intro-run
python tools/manual/check_course.py
```

Optional browser QA requires Playwright and Chrome:

```
node tools/manual/check_course_browser.cjs
```

`TOPOPT_MANUAL_QA_DIR` can select a development output directory. The test covers 24 lesson pages, 56 slides × 5 viewports, worksheet persistence, interactive exercises and bidirectional component links. No browser test outputs, runtime jobs, SDK DLLs or ZIPs belong in the manual tree. Before teaching, complete the interactive Rhino acceptance described in the teacher guides.
