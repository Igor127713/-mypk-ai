@echo off
cd /d "%~dp0"
echo Adding MYPK AI to Windows startup and disabling sleep while on AC power...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Startup')+'\MYPK_AI.lnk'); $s.TargetPath='%~dp0START_QUIET.bat'; $s.WorkingDirectory='%~dp0'; $s.WindowStyle=7; $s.Save()"
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
echo Done. The AI now starts automatically when you log in to Windows.
pause
