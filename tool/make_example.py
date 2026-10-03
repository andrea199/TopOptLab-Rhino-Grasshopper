# SPDX-License-Identifier: GPL-3.0-or-later
"""Run inside Rhino 8 with _RunPythonScript to regenerate the connected example.
Compatible with Rhino's built-in IronPython: numerical Python stays external.
"""
import os
import clr
import Rhino

Rhino.RhinoApp.RunScript('_Grasshopper', False)
clr.AddReference('Grasshopper')
import Grasshopper

folder = os.path.dirname(os.path.abspath(__file__))
assembly = os.path.join(os.environ['APPDATA'], 'Grasshopper', 'Libraries', 'TopoptLabExample', 'TopoptLab.GH.gha')
clr.AddReferenceToFileAndPath(assembly)
from TopoptLab.GH import ExampleDocument
doc = ExampleDocument.Create(os.path.join(folder, 'examples'))
Grasshopper.Instances.DocumentServer.AddDocument(doc)
Grasshopper.Instances.ActiveCanvas.Document = doc
doc.NewSolution(False)
print('Created plate_with_hole.gh and plate_with_hole.ghx')
