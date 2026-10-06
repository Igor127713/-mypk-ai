@echo off
setlocal
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":7860" ^| findstr "LISTENING"') do taskkill /PID %%P /T /F >nul 2>&1
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":7861" ^| findstr "LISTENING"') do taskkill /PID %%P /T /F >nul 2>&1
taskkill /IM cloudflared.exe /F >nul 2>&1
echo STOPPED
pause
