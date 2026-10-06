@echo off
powershell -NoProfile -ExecutionPolicy Bypass -Command "Remove-Item ([Environment]::GetFolderPath('Startup')+'\MYPK_AI.lnk') -ErrorAction SilentlyContinue"
echo Autostart removed.
pause
