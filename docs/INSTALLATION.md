# Installation

## Complete classroom packages

Choose one [classroom release package](https://github.com/andrea199/TopOptLab-Rhino/releases/tag/v0.4.0-classroom.20261026) for your computer. The complete
English HTML manual, HTML lesson slides, examples and corresponding CPU
installer are included. PowerPoint files are not distributed through GitHub. Python dependencies are bundled; the Windows source
installation later in this document has different prerequisites.

| Computer | Download | Exact size |
| --- | --- | ---: |
| Windows x64 with Rhino 8 | [Windows ZIP](https://github.com/andrea199/TopOptLab-Rhino/releases/download/v0.4.0-classroom.20261026/Lecture_26102026_Windows.zip) | 220,632,103 bytes |
| Apple Silicon Mac, macOS 15+, Rhino 8 | [Apple Silicon ZIP — pilot](https://github.com/andrea199/TopOptLab-Rhino/releases/download/v0.4.0-classroom.20261026/Lecture_26102026_Mac_AppleSilicon.zip) | 229,400,558 bytes |
| Intel Mac, macOS 15+, Rhino 8 | [Intel ZIP — pilot](https://github.com/andrea199/TopOptLab-Rhino/releases/download/v0.4.0-classroom.20261026/Lecture_26102026_Mac_Intel.zip) | 239,289,376 bytes |

GitHub access is required while this repository is private. Download one ZIP and
extract the whole archive to a permanent writable folder. Do not merge different
platform packages. On Mac, **Apple menu → About This Mac** identifies an Apple
M-series chip or an Intel processor.

### Windows classroom setup

1. Install and license Rhino 8; open it at least once.
2. Save your work and close every Rhino window.
3. In the extracted kit, run `software/windows/TopOptLab-Students-Windows-0.4.0-Setup.exe`.
4. Select **Install** and wait for the CPU self-check to finish.
5. Reopen Rhino, start Grasshopper and check the **TopOptLab** tab.

The Windows course installer includes its Python runtime. CPU operation needs no
CUDA. Use a short extraction path, such as `C:\Users\YourName\TopOptLab`.

### Mac classroom setup — pilot

1. Use macOS 15+ and the ZIP matching the Mac's native Apple Silicon or Intel architecture.
2. In Rhino 8, open Grasshopper → **File → Special Folders → Components Folder** and note that location.
3. Save your work, close Rhino and open `software/mac-pilot` in the extracted kit.
4. Run `INSTALL_MAC_PILOT.command`. If it opens the bundled Python 3.13 installer, finish that installation and run the launcher again.
5. Select the noted Grasshopper 8 Components Folder when prompted.
6. Reopen Rhino and Grasshopper, then check a small 2D example.

The package uses native Python 3.13 and bundled CPU wheels; Rosetta is unsupported.
If Finder does not run the launcher, open Terminal in `software/mac-pilot` and run
`bash INSTALL_MAC_PILOT.command`. Follow the included Mac README for full details.
Native Rhino/Mac acceptance is still pending; test the intended Mac before class.
Windows student Rhino UI and second-PC acceptance are also pending. No verified
installer is provided for Linux, Windows ARM or older macOS.

### Opening the English HTML manual

From the extracted `TopOptLab_Students_2026-10-26` folder, open `START_HERE.html` in
a browser and click **Open the complete English manual**. The fallback file is
`software/source/TopOptLab-Rhino/docs/manual/index.html`. Keep the complete folder
structure so the images, lessons and GH/GHX downloads work offline. Reading the
manual does not require Rhino or Python.

The manual's [illustrated setup guide](manual/getting-started/installation/index.html)
shows the opening steps. PowerPoint presentations remain separate instructor material. See [release scope and checksums](RELEASE_2026-10-26.md).

## Windows source installation

The instructions below are for a repository clone or GitHub's **Code → Download ZIP**,
not the self-contained course packages above.

### Source requirements

- Windows 64 bit, Rhino 8 with a working license, and Grasshopper.
- Python **3.13, 64 bit**, available through the Windows Python launcher.
- Internet access to download the pinned Python dependencies.
- A writable permanent project folder, such as your Documents folder.
- For CUDA only: a supported NVIDIA GPU/driver. CPU operation needs no CUDA.

The source installer builds the Grasshopper plugin against your installed Rhino
SDK. Rhino SDK binaries and the Python environment are not in this repository.

### Get the complete source project

While the repository is private, sign in to GitHub with an account that has access.
Use **Code → Download ZIP** and extract the entire archive, or clone:

```powershell
git clone https://github.com/andrea199/TopOptLab-Rhino.git
cd TopOptLab-Rhino
```

Do not copy only the GHA, an example, or the teaching folder to install the software.
The numerical worker and its environment must remain available.

### Run the source installer

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

### What the source installer installs

- `.venv/`: Python runtime environment inside this project.
- `tool/build/TopoptLab.GH.gha`: compiled plugin.
- `%APPDATA%\Grasshopper\Libraries\TopoptLabExample`: installed plugin and
  machine-specific `local-settings.json`.
- `tool/build/installation-backups/`: previous plugin/configuration saved on update.

Keep the project in place. If you move it, rerun the installer to update the worker
path. Local settings and generated calculation jobs are excluded from Git.

### Source update and rollback

With Rhino closed, update your clone or extract a new complete copy, then run
`INSTALL.cmd` in that copy. If you have local changes, inspect `git status` and save
them before pulling. A previously saved GH document keeps its own slider values;
open the updated example to see new defaults.

To roll back, close Rhino and restore the matching GHA and configuration from a
backup, together with the corresponding source/runtime version. An old GHA paired
with an incompatible new worker is not a complete rollback.

### Source troubleshooting

| Symptom | Action |
| --- | --- |
| `py -3.13` not found | Install Python 3.13 64 bit and the Python launcher; reopen the terminal. |
| Missing TopOptLab components | Check the installer output, the Rhino SDK location and the installed GHA; restart Rhino. |
| Worker not found | Rerun setup from the permanent project folder. |
| Duplicate components | Check Grasshopper Libraries for an older manually copied TopOptLab GHA. Keep one installed version. |
| Archive error | Open the current supplied GH file with the current plugin; record the full archive message if it persists. |
| CUDA unavailable | Install optional CUDA dependencies and check the driver, or explicitly select a CPU backend. |
| Grid rejected | Read Domain Resources, Cell size and Voxel limit together; see the resolution guide. |

This source workflow builds the plugin locally. For the bundled Windows EXE,
use the complete classroom ZIP above. Latest-build interactive Run/Stop/Reset/Bake/Undo acceptance remains
part of the [validation checklist](USER_GUIDE.md).
