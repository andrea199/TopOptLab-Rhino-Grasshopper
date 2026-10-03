# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate numerical reference, preview PNG and open CAD files without Rhino."""
import argparse
import json
from pathlib import Path
import time
import uuid

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np
import rhino3dm as rhino

from sample_problem import example
from worker import Model, run, write_json


def cad_files(folder, model, result):
    inputs = rhino.File3dm()
    inputs.Settings.ModelUnitSystem = getattr(rhino.UnitSystem, 'None')
    def layer(name):
        item = rhino.Layer(); item.Name = name
        return inputs.Layers.Add(item)
    def add_curve(points, name):
        attr = rhino.ObjectAttributes(); attr.LayerIndex = layer(name)
        inputs.Objects.AddCurve(rhino.PolylineCurve([rhino.Point3d(x, y, 0) for x, y in points]), attr)
    add_curve([(0, 0), (12, 0), (12, 6), (0, 6), (0, 0)], '01 Boundary')
    attr = rhino.ObjectAttributes(); attr.LayerIndex = layer('02 Hole')
    inputs.Objects.AddCircle(rhino.Circle(rhino.Point3d(6, 3, 0), 1), attr)
    for x in (0, 11):
        add_curve([(x, 0), (x+1, 0), (x+1, 6), (x, 6), (x, 0)], '03 Keep ' + str(x))
    for x, y, name in [(0, 0, '04 Pin XY'), (12, 0, '05 Roller Y'), (6, 6, '06 Load')]:
        attr = rhino.ObjectAttributes(); attr.LayerIndex = layer(name)
        inputs.Objects.AddPoint(rhino.Point3d(x, y, 0), attr)
    if not inputs.Write(str(folder / 'input_geometry.3dm'), 8):
        raise RuntimeError('Could not write input CAD file')
    output = rhino.File3dm()
    output.Settings.ModelUnitSystem = getattr(rhino.UnitSystem, 'None')
    mesh = rhino.Mesh()
    for p in model.nodes:
        mesh.Vertices.Add(float(p[0]), float(p[1]), 0)
    for face, rho in zip(model.faces, result['density']):
        if rho >= .5:
            mesh.Faces.AddFace(*map(int, face))
    mesh.Normals.ComputeNormals(); mesh.Compact()
    if not mesh.IsValid:
        raise RuntimeError('Invalid threshold mesh')
    attr = rhino.ObjectAttributes(); attr.Name = 'Threshold 0.5 - planar mesh, not reanalysed'
    output.Objects.AddMesh(mesh, attr)
    if not output.Write(str(folder / 'optimized_shape.3dm'), 8):
        raise RuntimeError('Could not write output CAD file')


def demo(folder, render_only=False):
    request = example()
    started = time.perf_counter()
    if render_only:
        if json.loads((folder / 'request.json').read_text()) != request:
            raise ValueError('The reference request has changed; run in a new directory')
        result = json.loads((folder / 'result.json').read_text())
        elapsed = None
    else:
        result = run(request, folder)
        elapsed = time.perf_counter() - started
    model = Model(request)
    initial = json.loads((folder / 'initial.json').read_text())
    write_json(folder / 'request.json', request)
    cad_files(folder, model, result)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11})
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), facecolor='#f5f7fa')
    polys = model.nodes[model.faces]
    entries = [(model.keep.astype(float), '01  Dominio e zone conservate'),
               (np.array(initial['density']), '02  Densita iniziale'),
               (np.array(result['density']), '03  Densita ottimizzata')]
    for ax, (values, title) in zip(axes, entries):
        ax.set_facecolor('#f5f7fa')
        ax.add_collection(PolyCollection(polys, array=values, cmap='Blues', clim=(0, 1), edgecolor='none'))
        ax.set(xlim=(-.4, 12.4), ylim=(-.65, 7), aspect='equal', title=title)
        ax.plot([0, 12], [0, 0], '^', color='#d37329', markersize=9)
        ax.annotate('', xy=(6, 6), xytext=(6, 6.85), arrowprops=dict(arrowstyle='-|>', color='#b53b43', lw=2))
        ax.axis('off')
    m = result['metrics']
    fig.suptitle('TopOptLab + Grasshopper | Piastra 2D con foro', x=.035, ha='left', fontsize=19, fontweight='bold')
    fig.text(.035, .08, f"80 iterazioni  |  materiale {m['volume']:.0%}  |  riduzione della compliance {m['improvement_percent']:.1f}%", fontsize=13)
    fig.text(.035, .025, 'Stesso budget di materiale; zone laterali conservate. Anteprima numerica: il collaudo interattivo in Rhino resta da completare.', color='#536172', fontsize=10)
    fig.subplots_adjust(left=.025, right=.985, top=.78, bottom=.2, wspace=.12)
    fig.savefig(folder / 'preview.png', dpi=150, facecolor=fig.get_facecolor()); plt.close(fig)
    summary = dict(metrics=m, elements=model.n, kept_elements=int(model.keep.sum()), iterations=80,
                   solve_seconds=elapsed, python_environment='Python 3.13 / tested requirements',
                   rhino_ui_validation='Pending on a Rhino installation with active license')
    write_json(folder / 'summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('runs') / uuid.uuid4().hex)
    parser.add_argument('--render-only', action='store_true')
    args = parser.parse_args()
    demo(args.output.resolve(), args.render_only)
