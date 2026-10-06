@echo off
chcp 65001 >nul
cd /d "%~dp0"
title MYPK AI - llama.cpp (замена Ollama)
if not exist ".venv\Scripts\python.exe" (
  echo Сначала один раз запусти START.bat - он создаст окружение и поставит зависимости.
  pause & exit /b 1
)
if not exist "llamacpp\llama-server.exe" (
  echo Не найден llamacpp\llama-server.exe
  echo Смотри инструкцию: LLAMACPP_SETUP.txt
  pause & exit /b 1
)
if not exist "models\model.gguf" if not exist "data\llamacpp.json" (
  echo Не найдена модель models\model.gguf
  echo Смотри инструкцию: LLAMACPP_SETUP.txt
  pause & exit /b 1
)
echo Запускаю движок llama.cpp (без Ollama)...
".venv\Scripts\python.exe" llama_bridge.py
pause
