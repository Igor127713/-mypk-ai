@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title MYPK AI - первый запуск (всё автоматически)

echo ============================================================
echo  Первый запуск делает всё сам: окружение, движок llama.cpp,
echo  модель (разово ~2 ГБ) и саму программу. Не закрывай окно.
echo ============================================================

rem ---- 1. Python и виртуальное окружение (как в START.bat) ----
set "PY="
where py >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if not defined PY (
  where python >nul 2>&1
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  echo ОШИБКА: не найден Python 3.11+. Поставь с python.org и запусти снова.
  pause & exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo [1/5] Создаю окружение Python...
  %PY% -m venv .venv
  if errorlevel 1 (echo ОШИБКА создания окружения. & pause & exit /b 1)
)
echo [2/5] Проверяю зависимости Python...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (echo ОШИБКА установки зависимостей. & pause & exit /b 1)

rem ---- 2. Скачиваем движок и модель, если их ещё нет ----
echo [3/5] Проверяю движок llama.cpp и модель (если уже скачаны - пропустится)...
powershell -NoProfile -ExecutionPolicy Bypass -File "llama_autoinstall.ps1"
if errorlevel 1 (
  echo ОШИБКА автоустановки. Подробности выше. Можно поставить вручную по LLAMACPP_SETUP.txt.
  pause & exit /b 1
)

rem ---- 3. Запускаем движок (мост) в отдельном окне и ждём его готовности ----
echo [4/5] Запускаю движок llama.cpp...
start "MYPK AI - движок llama.cpp" /min ".venv\Scripts\python.exe" llama_bridge.py
set READY=
for /l %%i in (1,1,150) do (
  ".venv\Scripts\python.exe" -c "import sys,urllib.request;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8090/health',timeout=1).status==200 else 1)" 2>nul
  if not errorlevel 1 (set READY=1 & goto ENGINE_UP)
  timeout /t 1 /nobreak >nul
)
:ENGINE_UP
if not defined READY (
  echo Движок долго не отвечает - большая модель грузится дольше. Смотри окно движка и data\llamacpp_bridge.log.
  echo Запускаю программу всё равно, она сама дождётся движка при первом вопросе.
)

rem ---- 4. Запускаем саму программу ----
echo [5/5] Запускаю MYPK AI...
".venv\Scripts\python.exe" launcher.py
if errorlevel 1 (echo ОШИБКА запуска программы. См. startup.log. & pause & exit /b 1)
echo READY
exit /b 0
