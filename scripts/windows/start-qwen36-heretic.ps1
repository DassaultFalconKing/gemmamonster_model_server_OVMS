<#
ИНСТРУКЦИЯ ПО АДАПТАЦИИ СКРИПТОВ ЗАПУСКА
1. package — каталог распакованного релиза с ovms.exe и MANIFEST.json.
   modelPath — каталог OpenVINO IR; modelName — имя модели в API и карточке OMP.
   Здесь выбран tvall43-Qwen3.6-35B-A3B-heretic-int4-ov; отдельные API/config/cache.
2. WEIGHTS_PATH вычисляется из modelPath: не копируйте .bin от другой модели.
   JSON создаётся через ConvertTo-Json; пути в нём используют прямые слеши.
   Отдельное экранирование кавычек ниже нужно для native args PowerShell 5.1.
3. Каталоги offload и logs создаются этим скриптом автоматически, вместе
   с родительскими папками. Вручную создавать их не нужно. Нужны права записи
   и свободное место. Повторный запуск использует тот же собственный кэш.
4. Для другой модели/runtime/конфигурации задавайте новый cacheKey. После замены
   весов также смените cacheKey. Не очищайте кэш работающего сервера.
   CACHE_DIR на диске и общий KV-пул cache_size — разные виды кэша.
5. offloadRatio=20 — исторически рабочая точка для Qwen MoE; для отключения
   задайте 0. У dense-моделей offload не включайте. Значения 30+ раньше зависали.
   Новая комбинация runtime, u4, двух слотов и eviction требует отдельной проверки.
6. Pipeline и парсеры выбирайте под семейство. Здесь VLM_CB, qwen3coder и qwen3.
   Не переносите чужой chat_template. MTP/speculative здесь не включается.
7. Параметры scheduler находятся внизу: 2 слота, батч 4096,
   динамический KV-кэш (cache_size=0). Кэш выделяется по потребности; это не
   гарантия ограничения всей RAM процесса. После изменения настроек обновите cacheKey.
   cache_size не ограничивает всю RAM процесса; батч не равен длине контекста.
   Основной профиль: prefix caching и interval 256, без token eviction.
   На этой машине eviction-профили исчерпывали RAM на входе 40К токенов.
   -EnableEviction — экспериментальный режим, не принятый для такого входа:
   65536 KV-токенов на последовательность, первые 40960 и последние 8192
   защищены от eviction; prefix caching в этом режиме отключён.
   Настройки записываются в configs\qwen36-heretic-long-2slots-eviction рядом со скриптом.
   -ConfigureOnly создаёт конфиги без загрузки модели и без остановки серверов.
8. Порт 8137 также использует Ornith: запускать по очереди либо менять порт
   вместе с SSH-туннелем/клиентом. Скрипт не завершает другие процессы.
   rest_workers=1 — обход воспроизведённой ошибки параллельного VLM_CB ввода
   (empty chat history / перепутанные ответы). Слотов scheduler два, но это
   не подтверждает реальную параллельную обработку двух длинных запросов.
9. Файл сохранять как UTF-8 с BOM для русских комментариев в PowerShell 5.1.
   Логи OVMS — в logs рядом со скриптом. Отдельный stderr библиотек может
   не попасть в этот файл. Это запуск сервера, не автоматический тест.
#>
param([switch]$ConfigureOnly, [switch]$EnableEviction)
$ErrorActionPreference = 'Stop'
$package = 'C:\gm\qwenmonster\releases\gemmamonster-2026.4-rc4\extracted-py_off\ovms'
$modelPath = 'C:\llm\models\tvall43-Qwen3.6-35B-A3B-heretic-int4-ov'
$modelName = 'qwen36-35b-a3b-heretic-int4'
$offloadRatio = 20
$kvPrecision = 'u4'
$cacheKey = 'qwen36-heretic-rc4-offload20-u4-seqs2-batch4096-long-v1'
$cacheRoot = 'C:\gm\qwenmonster\cache'
$weightsPath = Join-Path $modelPath 'openvino_language_model.bin'
foreach ($requiredFile in @($weightsPath,
    (Join-Path $modelPath 'config.json'),
    (Join-Path $modelPath 'openvino_language_model.xml'),
    (Join-Path $modelPath 'openvino_tokenizer.xml'),
    (Join-Path $modelPath 'openvino_tokenizer.bin'))) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw ('Required model file missing: ' + $requiredFile)
    }
}
if ($offloadRatio -lt 0 -or $offloadRatio -gt 100) {
    throw 'OFFLOAD_RATIO must be between 0 and 100.'
}
# Runtime pin (not a benchmark claim for this model): gemmamonster-2026.4-rc4 362b1d293b0461fa6b8772f1cf34d075c7ee23e4
$manifest = Get-Content (Join-Path $package 'MANIFEST.json') -Raw | ConvertFrom-Json
foreach ($row in $manifest.files) {
    if ($row.path -match '\.(dll|exe)$') {
        $file = Join-Path $package $row.path
        $stream = [IO.File]::OpenRead($file)
        $hash = [Security.Cryptography.SHA256]::Create()
        try {$actual=[BitConverter]::ToString($hash.ComputeHash($stream)).Replace('-','').ToLower()} finally {$stream.Dispose();$hash.Dispose()}
        if ($actual -ne $row.sha256) {throw ('Release file changed: ' + $file)}
    }
}
$env:PYTHONHOME=$null
$env:PYTHONPATH=$null
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PATH="$package;$env:SystemRoot\System32;$env:SystemRoot"
$exe=Join-Path $package 'ovms.exe'
$pluginConfig = [ordered]@{ KV_CACHE_PRECISION = $kvPrecision }
if ($offloadRatio -gt 0) {
    $offloadCache = Join-Path $cacheRoot $cacheKey
    [void][IO.Directory]::CreateDirectory($offloadCache)
    $pluginConfig['OFFLOAD_RATIO'] = $offloadRatio
    $pluginConfig['WEIGHTS_PATH'] = $weightsPath.Replace('\', '/')
    $pluginConfig['CACHE_DIR'] = $offloadCache.Replace('\', '/')
    Write-Host ('Offload cache: ' + $offloadCache)
}
$gpuPluginConfig = $pluginConfig | ConvertTo-Json -Compress
# Eviction is exposed through graph node options in RC4, not a CLI flag.
# JSON string encoding also produces valid protobuf text string escaping.
$configDir = Join-Path $PSScriptRoot 'configs\qwen36-heretic-long-2slots-eviction'
[void][IO.Directory]::CreateDirectory($configDir)
$graphPath = Join-Path $configDir 'graph.pbtxt'
$serverConfigPath = Join-Path $configDir 'config.json'
$modelLiteral = ConvertTo-Json -InputObject $modelPath.Replace('\', '/') -Compress
$pluginLiteral = ConvertTo-Json -InputObject $gpuPluginConfig -Compress
$prefixCaching = 'true'
$intervalOption = 'cache_interval_multiplier: 256'
$evictionOptions = ''
if ($EnableEviction) {
    Write-Warning 'Experimental eviction failed 40K-prompt memory probes on this machine.'
    $prefixCaching = 'false'
    $intervalOption = ''
    $evictionOptions = @'
      cache_eviction_config {
        aggregation_mode: NORM_SUM
        start_size: 40960
        recent_size: 8192
        max_cache_size: 65536
        apply_rotation: false
        snapkv_window_size: 0
      }
'@
}
$graph = @"
input_stream: "HTTP_REQUEST_PAYLOAD:input"
output_stream: "HTTP_RESPONSE_PAYLOAD:output"
node {
  name: "LLMExecutor"
  calculator: "HttpLLMCalculator"
  input_stream: "LOOPBACK:loopback"
  input_stream: "HTTP_REQUEST_PAYLOAD:input"
  input_side_packet: "LLM_NODE_RESOURCES:llm"
  input_side_packet: "LLM_NODE_EXECUTION_CONTEXTS:llm_ctx"
  output_stream: "LOOPBACK:loopback"
  output_stream: "HTTP_RESPONSE_PAYLOAD:output"
  input_stream_info { tag_index: "LOOPBACK:0" back_edge: true }
  node_options {
    [type.googleapis.com/mediapipe.LLMCalculatorOptions] {
      models_path: $modelLiteral
      plugin_config: $pluginLiteral
      device: "GPU"
      pipeline_type: VLM_CB
      tool_parser: "qwen3coder"
      reasoning_parser: "qwen3"
      enable_tool_guided_generation: true
      max_num_seqs: 2
      max_num_batched_tokens: 4096
      dynamic_split_fuse: true
      cache_size: 0
      enable_prefix_caching: $prefixCaching
      $intervalOption
$evictionOptions
    }
  }
  input_stream_handler {
    input_stream_handler: "SyncSetInputStreamHandler"
    options {
      [mediapipe.SyncSetInputStreamHandlerOptions.ext] {
        sync_set { tag_index: "LOOPBACK:0" }
      }
    }
  }
}
"@
$utf8 = New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText($graphPath, $graph, $utf8)
$serverConfig = @{
    model_config_list = @()
    mediapipe_config_list = @(@{ name = $modelName; graph_path = $graphPath.Replace('\', '/') })
} | ConvertTo-Json -Depth 6
[IO.File]::WriteAllText($serverConfigPath, $serverConfig, $utf8)
Write-Host ('Server configuration: ' + $serverConfigPath)
if ($ConfigureOnly) { exit 0 }
if (Get-NetTCPConnection -LocalPort 8137 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 8137 is occupied. Stop the current model before starting Qwen; no processes were stopped.'
}
$logDir = Join-Path $PSScriptRoot 'logs'
[void][IO.Directory]::CreateDirectory($logDir)
$logPath = Join-Path $logDir ($modelName + '-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ') + '.log')
Write-Host ('Model: ' + $modelName + ' -> ' + $modelPath)
Write-Host ('OVMS log: ' + $logPath)
& $exe `
    --rest_port 8137 `
    --rest_bind_address 127.0.0.1 `
    --rest_workers 1 `
    --config_path $serverConfigPath `
    --log_path $logPath
exit $LASTEXITCODE
