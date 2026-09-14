$ev = "C:\Users\testc\AppData\Local\Temp\opencode\gemmamonster-leakage-20260914"
$dd = "$ev\deep-dive"
$wd = "$dd\repro-full"
New-Item -ItemType Directory -Path $wd -Force | Out-Null
$pairs = @(
  @("f01-echo", "$ev\test-4-echo-auto\request.json"),
  @("f02-realexa", "$ev\test-5-real-exa-auto\request.json"),
  @("f03-minimal", "$ev\test-6-minimal-exa-auto\request.json"),
  @("f04-required", "$ev\test-7a-real-exa-required\request.json"),
  @("f05-named", "$ev\test-7b-real-exa-named\request.json"),
  @("f06-contam", "$ev\test-8-contaminated-exa-auto\request.json"),
  @("f07-t1", "$ev\sweep-long-context\turn-01\request.json"),
  @("f08-t2", "$ev\sweep-long-context\turn-02\request.json"),
  @("f09-t3", "$ev\sweep-long-context\turn-03\request.json"),
  @("f10-t4", "$ev\sweep-long-context\turn-04\request.json")
)
foreach ($p in $pairs) {
  $td = "$wd\$($p[0])"
  New-Item -ItemType Directory -Path $td -Force | Out-Null
  Copy-Item $p[1] "$td\request.json"
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
  $msg = $resp.choices[0].message
  $npc = 0; $m2 = Select-String -Path "$td\server-window.log" -Pattern "parseChunk\[PROCESSING_PHASE"
  if ($m2) { $npc = @($m2).Count }
  $line = "{0}: {1} finish={2} calls={3} args={4} ptok={5} ctok={6} pchunks={7}" -f $p[0], (Get-Content "$td\http.txt"), $resp.choices[0].finish_reason, @($msg.tool_calls).Count, ((@($msg.tool_calls) | ForEach-Object { $_.function.arguments }) -join "|"), $resp.usage.prompt_tokens, $resp.usage.completion_tokens, $npc
  $line | Set-Content "$td\summary.txt"
  Write-Output $line
}
