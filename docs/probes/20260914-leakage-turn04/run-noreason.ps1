$ev = "C:\Users\testc\AppData\Local\Temp\opencode\gemmamonster-leakage-20260914"
$td = "$ev\deep-dive\noreason-turn-04"
New-Item -ItemType Directory -Path $td -Force | Out-Null
Copy-Item "$ev\sweep-long-context\turn-04\request.json" "$td\request.json"
$log = "$ev\deep-dive\noreason-graph\logs\server.stdout.log"
$start = (Get-Content $log | Measure-Object -Line).Lines
$body = Get-Content "$td\request.json" -Raw
try {
  $r = Invoke-WebRequest -Uri "http://127.0.0.1:18091/v3/chat/completions" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 600
  $r.Content | Set-Content "$td\response.raw.json"
  "HTTP $($r.StatusCode)" | Set-Content "$td\http.txt"
} catch {
  "FAIL: $($_.Exception.Message)" | Set-Content "$td\http.txt"
  if ($_.ErrorDetails) { $_.ErrorDetails.Message | Set-Content "$td\response.raw.json" }
}
$total = (Get-Content $log | Measure-Object -Line).Lines
Get-Content $log | Select-Object -Skip $start | Set-Content "$td\server-window.log"
$raw = Get-Content "$td\server-window.log" -Raw
$re = [regex]'parseChunk\[PROCESSING_PHASE=(\w+)\] called with (\d+) tokens, text="(.*?)", finish_reason=(\d+), token IDs=\[(.*?)\]'
$ms = [regex]::Matches($raw, $re.ToString(), [System.Text.RegularExpressions.RegexOptions]::Singleline)
$out = @()
foreach ($m in $ms) {
  $txt = $m.Groups[3].Value -replace "`r", '\r' -replace "`n", '\n'
  $out += ("{0} ntok={1} fin={2} text=[{3}] ids=[{4}]" -f $m.Groups[1].Value, $m.Groups[2].Value, $m.Groups[4].Value, $txt, $m.Groups[5].Value)
}
$out | Set-Content "$td\parsechunks-parsed.txt"
$resp = Get-Content "$td\response.raw.json" -Raw | ConvertFrom-Json
$msg = $resp.choices[0].message
$s = [ordered]@{
  http = (Get-Content "$td\http.txt")
  finish_reason = $resp.choices[0].finish_reason
  tool_calls_count = @($msg.tool_calls).Count
  tool_arguments = ((@($msg.tool_calls) | ForEach-Object { $_.function.arguments }) -join " | ")
  prompt_tokens = $resp.usage.prompt_tokens
  completion_tokens = $resp.usage.completion_tokens
  parsechunk_count = $out.Count
}
$s | ConvertTo-Json -Depth 5 | Set-Content "$td\summary.json"
Get-Content "$td\summary.json"
Write-Output "--- OutputParser init line ---"
Select-String -Path "$td\server-window.log" -Pattern "OutputParser initialized" | ForEach-Object { $_.Line } | Out-String
Write-Output "--- chunks ---"
$out | ForEach-Object { Write-Output $_ }
