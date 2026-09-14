$ev = "C:\Users\testc\AppData\Local\Temp\opencode\gemmamonster-leakage-20260914"
$dd = "$ev\deep-dive"
New-Item -ItemType Directory -Path $dd -Force | Out-Null
"PID 16708 single TRACE instance; restarted after dual-instance OOM risk; same binary/SHA/graph/ports" | Set-Content "$dd\instance-note.txt"

function Send-Trace($subdir, $srcRequest) {
  $td = "$dd\$subdir"
  New-Item -ItemType Directory -Path $td -Force | Out-Null
  Copy-Item $srcRequest "$td\request.json"
  $start = (Get-Content "$ev\server-fresh\server.stdout.log" | Measure-Object -Line).Lines
  $body = Get-Content "$td\request.json" -Raw
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:18091/v3/chat/completions" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 600
    $r.Content | Set-Content "$td\response.raw.json"
    "HTTP $($r.StatusCode)" | Set-Content "$td\http.txt"
  } catch {
    "FAIL: $($_.Exception.Message)" | Set-Content "$td\http.txt"
    if ($_.ErrorDetails) { $_.ErrorDetails.Message | Set-Content "$td\response.raw.json" }
  }
  $total = (Get-Content "$ev\server-fresh\server.stdout.log" | Measure-Object -Line).Lines
  Get-Content "$ev\server-fresh\server.stdout.log" | Select-Object -Skip $start | Set-Content "$td\server-window.log"
  Select-String -Path "$td\server-window.log" -Pattern "parseChunk\[PROCESSING_PHASE" | ForEach-Object { $_.Line } | Set-Content "$td\parsechunks.txt"
  $n = 0; try { $n = (Get-Content "$td\parsechunks.txt" | Measure-Object -Line).Lines } catch { $n = 0 }
  $resp = Get-Content "$td\response.raw.json" -Raw | ConvertFrom-Json
  $msg = $resp.choices[0].message; $c = $msg.content; if ($null -eq $c) { $c = "" }
  $s = [ordered]@{
    http = (Get-Content "$td\http.txt")
    finish_reason = $resp.choices[0].finish_reason
    tool_calls_count = @($msg.tool_calls).Count
    tool_names = ((@($msg.tool_calls) | ForEach-Object { $_.function.name }) -join ",")
    tool_arguments = ((@($msg.tool_calls) | ForEach-Object { $_.function.arguments }) -join " | ")
    content_len = "$c".Length
    prompt_tokens = $resp.usage.prompt_tokens
    completion_tokens = $resp.usage.completion_tokens
    parsechunk_lines = $n
  }
  $s | ConvertTo-Json -Depth 5 | Set-Content "$td\summary.json"
  Write-Output "=== $subdir ==="
  Get-Content "$td\summary.json"
}
Send-Trace "turn-03-trace" "$ev\sweep-long-context\turn-03\request.json"
Send-Trace "turn-04-trace" "$ev\sweep-long-context\turn-04\request.json"
