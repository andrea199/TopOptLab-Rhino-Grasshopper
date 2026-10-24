# Hosting the unified English manual

The canonical site is `docs/manual/`. The same component reference, eight lessons,
slides and files work offline and on Read the Docs. Do not create a separate
Sphinx copy or rewrite the lessons for hosting.

## Reproduce the hosting build

Only Python's standard library is needed; Rhino, the numerical dependencies and
the bundled solver are not imported during this build.

```
python tools/manual/build.py
python tools/manual/check.py
python tools/manual/check_course.py
python tools/manual/export_site.py --output tool/build/fresh-manual-site
```

The output must be new or empty. The exporter does not delete/overwrite an
existing site. Open its `index.html` locally. GitHub's Manual validation workflow
runs these steps on Linux and retains the validated static site as an artifact.

## Connect Read the Docs

The repository-root `.readthedocs.yaml` uses the supported custom HTML build jobs
and writes the existing site to `$READTHEDOCS_OUTPUT/html`. No second site or
documentation dependency installation is required.

1. Sign in to the intended Read the Docs account and import this GitHub repository.
2. Grant that service access to this repository through its own authorization flow.
3. Select `.readthedocs.yaml`, the approved documentation branch and intended
   visibility. A private GitHub repository does not by itself authorize public docs.
4. Trigger a build and check the home, component reference, lesson navigation,
   slides, images and exercise downloads at the assigned URL.
5. Add the real successful URL to the README only after the hosted build succeeds.

This source configuration does not create a hosted account/project, authorize a
new service or change GitHub repository visibility. Those account actions must
be completed by an authorized account owner. No hosted URL is claimed yet.

Official configuration reference:
https://docs.readthedocs.com/platform/stable/build-customization.html

## Readiness and scope

- Release status remains experimental alpha, independent of documentation hosting.
- Native Rhino acceptance, second-PC installation and Mac validation are separate
  from a successful HTML build or CPU numerical regression run.
- The upstream snapshot remains unchanged; use the provenance manifest and the
  controlled update procedure in CONTRIBUTING.md when evaluating upstream changes.
