# Install on Windows

## Requirements

- Windows 64 bit, Rhino 8 with a working license, and Grasshopper.
- Python **3.13, 64 bit**, available through the Windows Python launcher.
- Internet access to download the pinned Python dependencies.
- A writable permanent project folder, such as your Documents folder.
- For CUDA only: a supported NVIDIA GPU/driver. CPU operation needs no CUDA.

The source installer builds the Grasshopper plugin against your installed Rhino
SDK. Rhino SDK binaries and the Python environment are not in this repository.

## Get the complete project

While the repository is private, sign in to GitHub with an account that has access.
Use **Code → Download ZIP** and extract the entire archive, or clone:

```powershell
git clone https://github.com/andrea199/TopOptLab-Rhino.git
cd TopOptLab-Rhino
```

Do not copy only the GHA, an example, or the teaching folder to install the software.
The numerical worker and its environment must remain available.

## Install

1. Save your work and close **all** Rhino windows.
2. In the project folder, double-click `INSTALL.cmd`.
3. Wait for dependency installation and compilation to finish.
4. Reopen Rhino, run `Grasshopper`, and find the **TopOptLab** tab.
5. Open the [first example](QUICKSTART.md).

From PowerShell in the project root, the equivalent command is:

```powershell
py -3.13 install_windows.py
```

For the optional CUDA backend:

```powershell
.\INSTALL.cmd --cuda
```

For a nonstandard Rhino location:

```powershell
py -3.13 install_windows.py --rhino "D:\Applications\Rhino 8"
```

To download dependencies and compile while Rhino is still open:

```powershell
py -3.13 install_windows.py --prepare-only
```

This last command does not update the loaded plugin. Close Rhino and rerun the
installer to finish. Add `--cuda` if you also need the optional GPU dependencies.

`setup.py` remains a compatibility entry point for older instructions, not a
setuptools installer. Do not use `pip install .` at the project root.
The root `pyproject.toml` configures tests, not native plugin installation.

## What is installed

- `.venv/`: Python runtime environment inside this project.
- `tool/build/TopoptLab.GH.gha`: compiled plugin.
- `%APPDATA%\Grasshopper\Libraries\TopoptLabExample`: installed plugin and
  machine-specific `local-settings.json`.
- `tool/build/installation-backups/`: previous plugin/configuration saved on update.

Keep the project in place. If you move it, rerun the installer to update the worker
path. Local settings and generated calculation jobs are excluded from Git.

## Update and rollback

With Rhino closed, update your clone or extract a new complete copy, then run
`INSTALL.cmd` in that copy. If you have local changes, inspect `git status` and save
them before pulling. A previously saved GH document keeps its own slider values;
open the updated example to see new defaults.

To roll back, close Rhino and restore the matching GHA and configuration from a
backup, together with the corresponding source/runtime version. An old GHA paired
with an incompatible new worker is not a complete rollback.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `py -3.13` not found | Install Python 3.13 64 bit and the Python launcher; reopen the terminal. |
| Missing TopOptLab components | Check the installer output, the Rhino SDK location and the installed GHA; restart Rhino. |
| Worker not found | Rerun setup from the permanent project folder. |
| Duplicate components | Check Grasshopper Libraries for an older manually copied TopOptLab GHA. Keep one installed version. |
| Archive error | Open the current supplied GH file with the current plugin; record the full archive message if it persists. |
| CUDA unavailable | Install optional CUDA dependencies and check the driver, or explicitly select a CPU backend. |
| Grid rejected | Read Domain Resources, Cell size and Voxel limit together; see the resolution guide. |

The installer is currently a source installer, not a standalone EXE with an
uninstaller. Latest-build interactive Run/Stop/Reset/Bake/Undo acceptance remains
part of the [validation checklist](USER_GUIDE.md).
