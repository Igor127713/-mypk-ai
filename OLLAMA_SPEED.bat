@echo off
chcp 65001 >nul
echo Ускорение Ollama: flash attention и сжатый кэш контекста (меньше памяти, быстрее на длинных диалогах).
setx OLLAMA_FLASH_ATTENTION 1 >nul
setx OLLAMA_KV_CACHE_TYPE q8_0 >nul
setx OLLAMA_KEEP_ALIVE -1 >nul
echo Готово. Теперь полностью закрой Ollama (значок в трее - Quit) и запусти её снова, потом START.bat.
pause
