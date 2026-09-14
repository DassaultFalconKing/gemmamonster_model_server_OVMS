$ev = "C:\Users\testc\AppData\Local\Temp\opencode\gemmamonster-leakage-20260914"
$dd = "$ev\deep-dive"
$wd = "$dd\repro-warm"
New-Item -ItemType Directory -Path $wd -Force | Out-Null
function Send-Warm($subdir, $srcRequest) {
  $td = "$wd\$subdir"
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
  $resp = Get-Content "$td\response.raw.json" -Raw | ConvertFrom-Json
  $msg = $resp.choices[0].message; $c = $msg.content; if ($null -eq $c) { $c = "" }
  $npc = 0
  $m2 = Select-String -Path "$td\server-window.log" -Pattern "parseChunk\[PROCESSING_PHASE"
  if ($m2) { $npc = @($m2).Count }
  $s = [ordered]@{
    http = (Get-Content "$td\http.txt")
    finish_reason = $resp.choices[0].finish_reason
    tool_calls_count = @($msg.tool_calls).Count
    tool_arguments = ((@($msg.tool_calls) | ForEach-Object { $_.function.arguments }) -join " | ")
    prompt_tokens = $resp.usage.prompt_tokens
    completion_tokens = $resp.usage.completion_tokens
    parsechunk_lines = $npc
  }
  $s | ConvertTo-Json -Depth 5 | Set-Content "$td\summary.json"
  Write-Output ("=== " + $subdir + " ===")
  Get-Content "$td\summary.json"
}
Send-Warm "w01-turn-01" "$ev\sweep-long-context\turn-01\request.json"
Send-Warm "w02-turn-02" "$ev\sweep-long-context\turn-02\request.json"
Send-Warm "w03-turn-03" "$ev\sweep-long-context\turn-03\request.json"
Send-Warm "w04-turn-04" "$ev\sweep-long-context\turn-04\request.json"
