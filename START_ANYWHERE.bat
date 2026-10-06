@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title MYPK AI 9 - ANYWHERE
call START.bat
if errorlevel 1 exit /b 1
set "PORT=7860"
if exist "data\runtime_port.txt" set /p PORT=<"data\runtime_port.txt"
if "%PORT%"=="" set "PORT=7860"
if not exist "cloudflared.exe" (
  echo Downloading tunnel client...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'cloudflared.exe'"
)
if not exist "cloudflared.exe" (
  echo ERROR: cloudflared download failed.
  echo Try: winget install Cloudflare.cloudflared
  pause
  exit /b 1
)
echo Starting public HTTPS tunnel to local port %PORT%...
echo Keep this window open while using the phone.
".venv\Scripts\python.exe" tunnel.py %PORT%
pause
