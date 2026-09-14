$ev = "C:\Users\testc\AppData\Local\Temp\opencode\gemmamonster-leakage-20260914"
$dd = "$ev\deep-dive"
$vd = "$dd\variants-ABCD"
New-Item -ItemType Directory -Path $vd -Force | Out-Null
$base = Get-Content "$ev\sweep-long-context\turn-04\request.json" -Raw | ConvertFrom-Json
function Send-Var($subdir, $toolsMode, $choice) {
  $td = "$vd\$subdir"
  New-Item -ItemType Directory -Path $td -Force | Out-Null
  $req = [ordered]@{ model = "gemma4"; messages = $base.messages; max_tokens = 256; temperature = 0 }
  if ($toolsMode -eq "with") { $req.tools = $base.tools; $req.tool_choice = $choice }
  elseif ($toolsMode -eq "none-choice") { $req.tools = $base.tools; $req.tool_choice = "none" }
  $req | ConvertTo-Json -Depth 14 | Set-Content "$td\request.json"
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
  $npc = 0; $m2 = Select-String -Path "$td\server-window.log" -Pattern "parseChunk\[PROCESSING_PHASE"
  if ($m2) { $npc = @($m2).Count }
  $line = "{0}: {1} finish={2} calls={3} names={4} content_len={5} ptok={6} ctok={7} pchunks={8}" -f $subdir, (Get-Content "$td\http.txt"), $resp.choices[0].finish_reason, @($msg.tool_calls).Count, ((@($msg.tool_calls) | ForEach-Object { $_.function.name }) -join ","), "$c".Length, $resp.usage.prompt_tokens, $resp.usage.completion_tokens, $npc
  $line | Set-Content "$td\summary.txt"
  Write-Output $line
}
Send-Var "A-no-tools" "without" $null
Send-Var "B-choice-none" "none-choice" $null
Send-Var "C-auto" "with" "auto"
Send-Var "D-required" "with" "required"
