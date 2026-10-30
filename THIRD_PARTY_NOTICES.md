# Third-party notices

TopOptLab for Rhino is an integration built on **topoptlab by Stefan Hiemer**.
The bundled upstream source snapshot is in vendor/topoptlab, with its original
LICENSE and metadata. No upstream files were edited by this integration.
The integration source carries GPL-3.0-or-later SPDX notices; see LICENSE.

The transferred upstream snapshot contains no Git metadata, so an upstream commit
cannot be claimed. vendor/upstream-sha256.json records the exact bundled files.
Resolve its correspondence to the original repository before an upstream contribution.

Python dependencies are installed from their distributions with their own license
metadata. CUDA dependencies are optional downloads from PyPI; NVIDIA runtime
binaries are not bundled in the source release. Rhino/Grasshopper are external
prerequisites and their SDK binaries are not redistributed in this repository.

The optional engineering constraint path uses mmapy 0.3.1 (GPL-3.0-or-later),
Arjen Deetman's Python implementation of Krister Svanberg's MMA/GCMMA algorithms:
https://github.com/arjendeetman/GCMMA-MMA-Python . The integration calls MMA (`mmasub`),
not the GCMMA outer algorithm. Method: K. Svanberg, The method of moving asymptotes,
IJNME 24 (1987), DOI 10.1002/nme.1620240207. Original dependency license notices
remain in the installed distribution; no MMA source files are vendored here.

The final-geometry path uses scikit-image 0.26.0 (primarily BSD-3-Clause, with
per-file notices retained in its distribution), Manifold/manifold3d 3.5.2
(Apache-2.0), Gmsh 4.15.2 (GPL-2.0-or-later), and meshio 5.3.5 (MIT).
The numerical comparison tests use scikit-fem 12.0.2 (BSD-3-Clause). These packages
are installed as external distributions; their code is not copied into this tool.
See the dependency license files, requirements-tested.txt and runtime lock for
exact versions. Implementation/API references are in docs/FINAL_GEOMETRY.md.

## EU emblem and European Innovation Council identity

The English funding lockup in `docs/manual/assets/funding/eic-funded-by-eu.png`
is supplied unchanged by the [European Innovation Council](https://eic.ec.europa.eu/communication-toolkit_en).
The EU emblem and EIC identity retain their official use conditions; the GPL
licence for the software does not relicense these marks. Their display acknowledges
ARCHIBIOFOAM funding and does not imply EU or EIC endorsement of the software.
See the [asset provenance](docs/manual/assets/funding/README.md) and the
[EU legal notice](https://european-union.europa.eu/legal-notice_en).
