@echo off
chcp 65001 >nul
net session >nul 2>&1
if errorlevel 1 (
  echo Нужны права администратора: правой кнопкой по файлу, "Запуск от имени администратора".
  pause & exit /b 1
)
set PORT=7860
if exist "%~dp0data\runtime_port.txt" set /p PORT=<"%~dp0data\runtime_port.txt"
netsh advfirewall firewall delete rule name="MYPK AI phone" >nul 2>&1
netsh advfirewall firewall add rule name="MYPK AI phone" dir=in action=allow protocol=TCP localport=%PORT% profile=private
echo Готово: порт %PORT% открыт для телефона в домашней (частной) сети.
echo Если Wi-Fi в Windows помечен как "Общедоступная", смени на "Частная" в параметрах сети.
pause
