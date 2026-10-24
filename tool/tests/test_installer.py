# SPDX-License-Identifier: GPL-3.0-or-later
"""Installer contract tests: never install dependencies or touch a real Rhino."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("installer_under_test", ROOT / "install_windows.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def test_both_entry_points_support_help(self):
        for entry in ("install_windows.py", "setup.py"):
            result = subprocess.run(
                [sys.executable, str(ROOT / entry), "--help"],
                capture_output=True, text=True, check=True,
            )
            for option in ("--cuda", "--prepare-only", "--rhino"):
                self.assertIn(option, result.stdout)

    def test_launcher_uses_new_entry_point(self):
        self.assertIn('"%~dp0install_windows.py" %*', (ROOT / "INSTALL.cmd").read_text())

    def test_prepare_only_does_not_install_or_check_running_rhino(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sdk = root / "Rhino/System"
            sdk.mkdir(parents=True)
            (sdk / "RhinoCommon.dll").touch()
            python = root / ".venv/Scripts/python.exe"
            python.parent.mkdir(parents=True)
            python.touch()
            (root / "tool/build").mkdir(parents=True)
            argv = ["installer", "--prepare-only", "--cuda", "--rhino", str(sdk.parent)]
            with patch.object(installer, "ROOT", root), \
                 patch.object(installer.sys, "argv", argv), \
                 patch.object(installer.sys, "version_info", (3, 13)), \
                 patch.object(installer.os, "name", "nt"), \
                 patch.object(installer, "run") as run, \
                 patch.object(installer.subprocess, "check_output") as tasks, \
                 patch.object(installer.shutil, "copy2") as copy:
                installer.main()
            tasks.assert_not_called()
            copy.assert_not_called()
            self.assertEqual(run.call_count, 4)
            self.assertTrue((root / "tool/build/local-settings.json").is_file())
            self.assertFalse((root / "tool/build/installation-backups").exists())

    def test_wrong_python_rejected_before_install(self):
        with patch.object(installer.sys, "argv", ["installer"]), \
             patch.object(installer.sys, "version_info", (3, 12)), \
             patch.object(installer.os, "name", "nt"), \
             patch.object(installer, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "Python 3.13"):
                installer.main()
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
