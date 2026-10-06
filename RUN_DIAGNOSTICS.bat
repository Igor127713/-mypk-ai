@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (set "PY=.venv\Scripts\python.exe") else (set "PY=py -3")
echo === MYPK AI 7_9 DIAGNOSTICS ===
%PY% --version
%PY% -m py_compile app.py launcher.py
if errorlevel 1 echo Python syntax check FAILED
%PY% -c "import requests; print('requests OK')"
%PY% -c "import flask; print('flask OK')"
%PY% -c "import PIL; print('Pillow OK')"
%PY% -c "import json, pathlib; p=pathlib.Path('data/config.json'); print('model=',json.loads(p.read_text(encoding='utf-8')).get('model') if p.exists() else 'default')"
echo.
echo === OLLAMA ===
curl -s http://127.0.0.1:11434/api/tags
echo.
echo === STARTUP LOG ===
if exist startup.log powershell -NoProfile -Command "Get-Content startup.log -Tail 80"
pause
