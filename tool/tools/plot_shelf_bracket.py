# SPDX-License-Identifier: GPL-3.0-or-later
"""Plot computed bracket density and extracted geometry; no rendered design is invented."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
p=argparse.ArgumentParser();p.add_argument("run",type=Path);p.add_argument("output",type=Path);p.add_argument("--design-dir",type=Path);a=p.parse_args()
design_dir=a.design_dir or a.run/"optimize"
project=json.loads((design_dir/"project.json").read_text());design=json.loads((design_dir/"result.json").read_text());surface=json.loads((a.run/"surface/result.json").read_text())
d=project["domain"];rho=np.full(d["nx"]*d["ny"]*d["nz"],np.nan);rho[d["active"]]=design["density"]
rho=rho.reshape(d["nz"],d["nx"],d["ny"]);projection=np.max(np.nan_to_num(rho,nan=0),axis=2)
fig=plt.figure(figsize=(13,5.5),layout="constrained",facecolor="#f6f8fb");ax=fig.add_subplot(121)
im=ax.imshow(projection,origin="lower",extent=[0,d["nx"]*d["cell"],0,d["nz"]*d["cell"]],vmin=0,vmax=1,cmap="Greys",aspect="equal")
ax.set_title(f"Computed density / {d['cell']:g} mm cells",loc="left",fontweight="bold");ax.set_xlabel("Projection from wall X / mm");ax.set_ylabel("Height Z / mm");fig.colorbar(im,ax=ax,shrink=.55,label="Maximum density across width")
ax=fig.add_subplot(122,projection="3d");v=np.array(surface["nodes"]);f=np.array(surface["triangles"]);mesh=Poly3DCollection(v[f],facecolor="#15999d",edgecolor="#126775",linewidth=.05,alpha=1);ax.add_collection3d(mesh)
lo=v.min(axis=0);hi=v.max(axis=0);ax.set_xlim(lo[0],hi[0]);ax.set_ylim(lo[1],hi[1]);ax.set_zlim(lo[2],hi[2]);ax.set_box_aspect(hi-lo);ax.view_init(elev=19,azim=-62)
ax.set_title("Extracted surface / inspect and reanalyse",loc="left",fontweight="bold");ax.set_xlabel("X / mm");ax.set_ylabel("");ax.set_yticks([]);ax.set_zlabel("");ax.text2D(.02,.08,"Z upward / width Y = 25 mm",transform=ax.transAxes,fontsize=9)
fig.suptitle("Shelf bracket / 250 mm / four alternative 4 kg payload cases",fontweight="bold",fontsize=16)
cad=surface.get("cad_interfaces") or surface.get("geometry",{}).get("cad_interfaces")
footer="ABS reference • rigid wall pads • " + ("CAD clearance reconstruction" if cad else "voxel interfaces") + " • not a qualified printed-part load rating"
fig.text(.5,.005,footer,ha="center",fontsize=9,color="#455463")
a.output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(a.output,dpi=170);plt.close(fig);print(a.output)
