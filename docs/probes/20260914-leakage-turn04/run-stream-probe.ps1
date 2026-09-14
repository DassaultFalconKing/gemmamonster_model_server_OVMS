$ev = "C:\Users\testc\AppData\Local\Temp\opencode\gemmamonster-leakage-20260914"
$vd = "$ev\sweep-long-context\turn-04-stream-probe"
New-Item -ItemType Directory -Path $vd -Force | Out-Null
$base = Get-Content "$ev\sweep-long-context\turn-04\request.json" -Raw | ConvertFrom-Json
$req = [ordered]@{
  model = "gemma4"
  messages = $base.messages
  tools = $base.tools
  tool_choice = "auto"
  max_tokens = 256
  temperature = 0
  stream = $true
}
$req | ConvertTo-Json -Depth 14 | Set-Content "$vd\request.json"
$start = (Get-Content "$ev\server-fresh\server.stdout.log" | Measure-Object -Line).Lines
$body = Get-Content "$vd\request.json" -Raw
try {
  $r = Invoke-WebRequest -Uri "http://127.0.0.1:18091/v3/chat/completions" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 600
  $r.Content | Set-Content "$vd\response.sse.txt"
  "HTTP $($r.StatusCode)" | Set-Content "$vd\http.txt"
} catch {
  "FAIL: $($_.Exception.Message)" | Set-Content "$vd\http.txt"
}
$total = (Get-Content "$ev\server-fresh\server.stdout.log" | Measure-Object -Line).Lines
Get-Content "$ev\server-fresh\server.stdout.log" | Select-Object -Skip $start | Set-Content "$vd\server-window.log"
$raw = Get-Content "$vd\response.sse.txt" -Raw
$lines = $raw -split "`n" | Where-Object { $_ -match "^data:" }
"chunks=$($lines.Count)" | Set-Content "$vd\summary.txt"
$lines | Select-Object -First 8 | Set-Content "$vd\first-chunks.txt"
$lines | Select-Object -Last 8 | Set-Content "$vd\last-chunks.txt"
Get-Content "$vd\http.txt"
Get-Content "$vd\summary.txt"
"--- first chunks ---"
Get-Content "$vd\first-chunks.txt"
"--- last chunks ---"
Get-Content "$vd\last-chunks.txt"
