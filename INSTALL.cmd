@echo off
setlocal
py -3.13 "%~dp0install_windows.py" %*
if errorlevel 1 echo Setup failed. Read the message above. Python 3.13 and Rhino 8 are required.
pause
