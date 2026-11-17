#!/bin/bash
set -e
cd -- "$(dirname -- "$0")"
if [ "$(uname -s)" != "Darwin" ]; then
  echo "This launcher is for macOS. Windows users: run SETUP-PYTHON.cmd."
  exit 1
fi
PYTHON_BIN=""
for candidate in /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 /opt/homebrew/bin/python3.13 /usr/local/bin/python3.13; do
  if [ -x "$candidate" ]; then PYTHON_BIN="$candidate"; break; fi
done
if [ -z "$PYTHON_BIN" ] && command -v python3.13 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3.13)"
fi
if [ -z "$PYTHON_BIN" ]; then
  echo "Install native Python 3.13 from python.org (including its certificates), then run this file again."
  exit 1
fi
"$PYTHON_BIN" "$PWD/configure.py" "$@"
if [ -t 0 ]; then
  read -r -p "Press Return to close. " task_answer
fi
