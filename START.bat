@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title MYPK AI 9
set "PY="
where py >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if not defined PY (
  where python >nul 2>&1
  if not errorlevel 1 set "PY=python"
)
if not defined PY goto NO_PY
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating environment...
  %PY% -m venv .venv
  if errorlevel 1 goto VENV_FAIL
)
echo [2/3] Checking dependencies...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto PIP_FAIL
echo [3/3] Starting MYPK AI 9...
".venv\Scripts\python.exe" launcher.py
if errorlevel 1 goto RUN_FAIL
echo READY
exit /b 0
:NO_PY
echo ERROR: Python 3.11+ not found.
pause
exit /b 1
:VENV_FAIL
echo ERROR: Could not create virtual environment.
pause
exit /b 1
:PIP_FAIL
echo ERROR: Dependency installation failed.
pause
exit /b 1
:RUN_FAIL
echo ERROR: Server failed to start. See startup.log.
pause
exit /b 1
