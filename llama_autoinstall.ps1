# Автоустановка движка llama.cpp: скачивает llama-server.exe (под нужное железо) и модель .gguf,
# настраивает data\llamacpp.json и data\config.json. Запускать не напрямую, а через RUN_EVERYTHING.bat.
# Все шаги пропускаются, если файлы уже скачаны - безопасно запускать повторно.
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # иначе Invoke-WebRequest на больших файлах ползёт в разы медленнее
$Base = $PSScriptRoot
$Engine = Join-Path $Base "llamacpp"
$Models = Join-Path $Base "models"
$Data = Join-Path $Base "data"
New-Item -ItemType Directory -Force -Path $Engine, $Models, $Data | Out-Null

function Say($msg) { Write-Host "[auto-install] $msg" }

# ---------- 1. Видеокарта NVIDIA есть или нет ----------
$hasNvidia = $false
try {
    $gpu = Get-CimInstance Win32_VideoController -ErrorAction Stop | Where-Object { $_.Name -match "NVIDIA" }
    if ($gpu) { $hasNvidia = $true }
} catch {}
Say "Видеокарта NVIDIA: $hasNvidia"

# ---------- 2. Движок llama-server.exe ----------
$exePath = Join-Path $Engine "llama-server.exe"
if (Test-Path $exePath) {
    Say "llama-server.exe уже есть, пропускаю скачивание."
} else {
    Say "Ищу последний релиз llama.cpp на GitHub..."
    $rel = Invoke-RestMethod "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest" -Headers @{ "User-Agent" = "MYPK-AI" }
    $assets = $rel.assets
    $mainAsset = $null; $cudartAsset = $null
    if ($hasNvidia) {
        $mainAsset = $assets | Where-Object { $_.name -match "bin-win-cuda-12\.\d+-x64\.zip$" } | Select-Object -First 1
        if (-not $mainAsset) { $mainAsset = $assets | Where-Object { $_.name -match "bin-win-cuda.*x64\.zip$" } | Select-Object -First 1 }
        if ($mainAsset -and ($mainAsset.name -match "cuda-(\d+\.\d+)")) {
            $ver = $Matches[1]
            $cudartAsset = $assets | Where-Object { $_.name -match "cudart.*cuda-$([regex]::Escape($ver))" } | Select-Object -First 1
        }
    }
    if (-not $mainAsset) {
        Say "Беру сборку для процессора (CPU) - медленнее GPU, но работает везде."
        $mainAsset = $assets | Where-Object { $_.name -match "bin-win-cpu-x64\.zip$|bin-cpu-win-x64\.zip$" } | Select-Object -First 1
    }
    if (-not $mainAsset) { throw "Не нашёл подходящий файл в последнем релизе llama.cpp. Зайди на https://github.com/ggml-org/llama.cpp/releases и скачай вручную (см. LLAMACPP_SETUP.txt)." }

    $tmp = Join-Path $env:TEMP "llamacpp_dl"
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    $zip1 = Join-Path $tmp $mainAsset.name
    Say "Скачиваю $($mainAsset.name) ($([math]::Round($mainAsset.size/1MB))МБ)..."
    Invoke-WebRequest $mainAsset.browser_download_url -OutFile $zip1
    Expand-Archive -Path $zip1 -DestinationPath (Join-Path $tmp "main") -Force

    if ($cudartAsset) {
        $zip2 = Join-Path $tmp $cudartAsset.name
        Say "Скачиваю $($cudartAsset.name) (библиотеки CUDA)..."
        Invoke-WebRequest $cudartAsset.browser_download_url -OutFile $zip2
        Expand-Archive -Path $zip2 -DestinationPath (Join-Path $tmp "cudart") -Force
    }

    # В зип-архивах llama.cpp файлы иногда лежат не в корне - находим llama-server.exe и копируем
    # его папку целиком, плюс все .dll из cudart, в llamacpp\.
    $found = Get-ChildItem -Path (Join-Path $tmp "main") -Filter "llama-server.exe" -Recurse | Select-Object -First 1
    if (-not $found) { throw "В скачанном архиве нет llama-server.exe - релиз изменился. Скачай вручную по LLAMACPP_SETUP.txt." }
    Copy-Item -Path (Join-Path $found.DirectoryName "*") -Destination $Engine -Recurse -Force
    if ($cudartAsset) {
        Get-ChildItem -Path (Join-Path $tmp "cudart") -Filter "*.dll" -Recurse | ForEach-Object {
            Copy-Item $_.FullName -Destination $Engine -Force
        }
    }
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    Say "Движок установлен: $exePath"
}

# ---------- 3. Модель ----------
$modelPath = Join-Path $Models "model.gguf"
if (Test-Path $modelPath) {
    Say "Модель уже скачана, пропускаю."
} else {
    $url = "https://huggingface.co/bartowski/Qwen2.5-3B-Instruct-GGUF/resolve/main/Qwen2.5-3B-Instruct-Q4_K_M.gguf"
    Say "Скачиваю модель по умолчанию Qwen2.5-3B-Instruct (~1.9 ГБ, один раз, подождать 2-10 минут)..."
    Say "Другую модель можно положить вместо неё позже - см. LLAMACPP_SETUP.txt."
    Invoke-WebRequest $url -OutFile "$modelPath.part"
    Move-Item "$modelPath.part" $modelPath -Force
    Say "Модель готова: $modelPath"
}

# ---------- 4. Настройки моста ----------
$llamacppCfgPath = Join-Path $Data "llamacpp.json"
$llamacppCfg = [ordered]@{
    exe = $exePath; model = $modelPath; model_name = "local-gguf"
    gpu_layers = $(if ($hasNvidia) { 999 } else { 0 })
    ctx = 8192; backend_port = 8081; bridge_port = 8090
}
if (Test-Path $llamacppCfgPath) {
    try {
        $existing = Get-Content $llamacppCfgPath -Raw | ConvertFrom-Json
        foreach ($p in $existing.PSObject.Properties) { $llamacppCfg[$p.Name] = $p.Value }
    } catch {}
}
($llamacppCfg | ConvertTo-Json) | Set-Content -Path $llamacppCfgPath -Encoding UTF8
Say "Настройки моста: $llamacppCfgPath (gpu_layers=$($llamacppCfg.gpu_layers))"

# ---------- 5. Переключаем программу на мост вместо настоящей Ollama ----------
$mainCfgPath = Join-Path $Data "config.json"
$mainCfg = if (Test-Path $mainCfgPath) { Get-Content $mainCfgPath -Raw | ConvertFrom-Json } else { [pscustomobject]@{} }
$bridgeUrl = "http://127.0.0.1:$($llamacppCfg.bridge_port)"
$mainCfg | Add-Member -NotePropertyName ollama_url -NotePropertyValue $bridgeUrl -Force
$mainCfg | Add-Member -NotePropertyName model -NotePropertyValue "local-gguf" -Force
($mainCfg | ConvertTo-Json -Depth 10) | Set-Content -Path $mainCfgPath -Encoding UTF8
Say "data\config.json переключён на движок llama.cpp (ollama_url=$bridgeUrl)."
Say "Готово."
