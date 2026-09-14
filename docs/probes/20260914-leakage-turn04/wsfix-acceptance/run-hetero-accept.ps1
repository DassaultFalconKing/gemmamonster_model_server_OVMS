param([string]$RestBase = "http://127.0.0.1:18091", [string]$OutDir = "")
# Heterogeneous grammar acceptance: 100-150 MIXED requests on ONE live instance.
# Mixes schemas, tool sets, choices, roundtrips, prompt lengths, sampling.
# PASS = all served, no CL_OUT_OF_RESOURCES/death, soft anomalies (length+empty) counted.
# Run ONLY against the binary under acceptance (row 3/XGrammar-A first).
$ev = "C:\Users\testc\AppData\Local\Temp\opencode\wsfix-acceptance-20260914"
if ($OutDir -eq "") { $OutDir = "$ev\hetero-accept" }
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$script:softAnomalies = @()
$script:n = 0
function Send-Mixed($tag, $messages, $tools, $choice, $temp, $topP, $topK, $maxTok) {
  $script:n++
  $d = "$OutDir\{0:D3}-{1}" -f $script:n, $tag
  New-Item -ItemType Directory -Path $d -Force | Out-Null
  $req = [ordered]@{ model = "gemma4"; messages = $messages; tool_choice = $choice; max_tokens = $maxTok; temperature = $temp }
  if ($null -ne $topP) { $req.top_p = $topP }
  if ($null -ne $topK) { $req.top_k = $topK }
  if ($tools) { $req.tools = $tools }
  $req | ConvertTo-Json -Depth 14 | Set-Content "$d\request.json"
  $body = Get-Content "$d\request.json" -Raw
  $outcome = ""
  try {
    $r = Invoke-WebRequest -Uri "$RestBase/v3/chat/completions" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 600
    $r.Content | Set-Content "$d\response.raw.json"
    $j = $r.Content | ConvertFrom-Json
    $m = $j.choices[0].message; $c = $m.content; if ($null -eq $c) { $c = "" }
    $fin = $j.choices[0].finish_reason; $nc = @($m.tool_calls).Count
    $outcome = "finish={0} calls={1} clen={2} calltag={3} ptok={4} ctok={5}" -f $fin, $nc, "$c".Length, ($c -match "<call:"), $j.usage.prompt_tokens, $j.usage.completion_tokens
    if (($fin -eq "length" -and "$c" -eq "" -and $nc -eq 0) -or ($c -match "<call:")) {
      $script:softAnomalies += ("{0:D3}-{1}: {2}" -f $script:n, $tag, $outcome)
      $outcome += " SOFT_ANOMALY"
    }
  } catch { $outcome = "HARD_FAIL: $($_.Exception.Message)"; $r.Content 2>$null | Out-Null; if ($_.ErrorDetails) { $_.ErrorDetails.Message | Set-Content "$d\response.raw.json" } }
  $p = Get-Process ovms -ErrorAction SilentlyContinue
  $mem = if ($p) { [math]::Round(($p | Measure-Object WorkingSet64 -Sum).Sum / 1MB) } else { -1 }
  $free = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory
  $line = "{0:D3} {1} memMB={2} freeKB={3} alive={4} :: {5}" -f $script:n, $tag, $mem, $free, ($null -ne $p), $outcome
  $line | Set-Content "$d\result.txt"
  Add-Content "$OutDir\hetero-accept.log" $line
  if (($script:n % 10) -eq 0 -or $outcome -match "FAIL|ANOMALY") { Write-Output $line }
  if ($outcome -match "HARD_FAIL" -or $null -eq $p) { Write-Output "STOPPING on hard failure"; return $false }
  return $true
}
function EchoTool() { return [ordered]@{ type = "function"; function = [ordered]@{ name = "echo"; description = "Echo back the given text."; parameters = [ordered]@{ type = "object"; properties = [ordered]@{ text = [ordered]@{ type = "string"; description = "Text to echo." } }; required = @("text"); additionalProperties = $false } } } }
function ExaToolFull() { return [ordered]@{ type = "function"; function = [ordered]@{ name = "exa_web_search_exa"; description = "Search the web."; parameters = [ordered]@{ type = "object"; properties = [ordered]@{ query = [ordered]@{ type = "string"; description = "Natural language search query." }; objective = [ordered]@{ type = "string"; description = "Goal." }; numResults = [ordered]@{ type = "integer"; description = "Count." } }; required = @("query"); additionalProperties = $false } } } }
function ExaToolMin() { return [ordered]@{ type = "function"; function = [ordered]@{ name = "exa_web_search_exa"; description = "Search the web."; parameters = [ordered]@{ type = "object"; properties = [ordered]@{ query = [ordered]@{ type = "string" } }; required = @("query") } } } }
function U($t) { return [ordered]@{ role = "user"; content = $t } }
$go = $true
# Phase 1: short mix x30 (schemas x choices x toolsets x plain)
$queries = @("winner of the 2026 Eurovision Song Contest", "capital city of Kazakhstan", "current price of crude oil", "tallest building in the world 2026", "latest stable OpenVINO release")
$qi = 0
foreach ($ch in @("auto", "auto", "required", "named", "none")) {
  foreach ($ts in @("echo", "exafull", "examin", "both")) {
    if (-not $go) { break }
    $tools = $null
    if ($ts -eq "echo") { $tools = @(EchoTool) }
    elseif ($ts -eq "exafull") { $tools = @(ExaToolFull) }
    elseif ($ts -eq "examin") { $tools = @(ExaToolMin) }
    else { $tools = @(EchoTool; ExaToolFull) }
    $choice = $ch
    if ($ch -eq "named") { $choice = ([ordered]@{ type = "function"; function = [ordered]@{ name = "exa_web_search_exa" } }) }
    $q = $queries[$qi % $queries.Count]; $qi++
    $txt = if ($ts -eq "echo" -and $ch -eq "auto") { "Echo this exactly: hetero-probe-$qi" } else { "Search the internet for $q." }
    if ($ch -eq "none" -or $null -eq $tools) { $txt = "What is $((3+$qi)) plus $((4+$qi))? Answer directly." }
    $go = Send-Mixed "p1-$ts-$ch" @(U $txt) $tools $choice 0 $null $null 256
  }
}
# Phase 2: roundtrips x20 (call -> synthetic result -> synthesize), alternating tools/temp
for ($k = 1; $k -le 10 -and $go; $k++) {
  $t = if (($k % 2) -eq 0) { 1.0 } else { 0 }
  $go = Send-Mixed "p2-call-$k" @(U "Search the internet for hetero roundtrip fact number $k.") @((ExaToolFull)) "auto" $t 0.95 64 256
  if (-not $go) { break }
  $prev = Get-Content "$OutDir\{0:D3}-p2-call-$k\response.raw.json" -Raw | ConvertFrom-Json
  if (@($prev.choices[0].message.tool_calls).Count -gt 0) {
    $tc = $prev.choices[0].message.tool_calls[0]
    $hist = @(
      (U "Search the internet for hetero roundtrip fact number $k."),
      [ordered]@{ role = "assistant"; content = $prev.choices[0].message.content; tool_calls = @([ordered]@{ id = $tc.id; type = $tc.type; function = [ordered]@{ name = $tc.function.name; arguments = $tc.function.arguments } }) },
      [ordered]@{ role = "tool"; tool_call_id = $tc.id; content = ('{"results":[{"text":"Hetero fact ' + $k + ' is value-' + $k + '."}]}') },
      (U "Report hetero fact number $k in one short sentence.")
    )
    $go = Send-Mixed "p2-synth-$k" $hist @((ExaToolFull)) "auto" $t 0.95 64 256
  }
}
# Phase 3: growing-history sweeps (t0 greedy 16 turns + t1 sampling 16 turns)
$msgs = @((U "Call the echo tool once per turn with the next item, starting hetero-sweep-1. Continue after each tool result. Items: hetero-sweep-1 .. hetero-sweep-16."))
for ($k = 1; $k -le 16 -and $go; $k++) {
  $go = Send-Mixed "p3-t0-$k" $msgs @((EchoTool)) "auto" 0 $null $null 256
  if (-not $go) { break }
  $pr = Get-Content "$OutDir\{0:D3}-p3-t0-$k\response.raw.json" -Raw | ConvertFrom-Json
  if (@($pr.choices[0].message.tool_calls).Count -gt 0) {
    $t2 = $pr.choices[0].message.tool_calls[0]
    $msgs += [ordered]@{ role = "assistant"; content = $pr.choices[0].message.content; tool_calls = @([ordered]@{ id = $t2.id; type = $t2.type; function = [ordered]@{ name = $t2.function.name; arguments = $t2.function.arguments } }) }
    $msgs += [ordered]@{ role = "tool"; tool_call_id = $t2.id; content = '{"echoed":"x"}' }
  } else { $msgs += [ordered]@{ role = "assistant"; content = "noted" }; $msgs += (U "Continue with the next item via echo.") }
}
$msgs2 = @((U "Call the echo tool once per turn with the next item, starting hetero-samp-1. Items hetero-samp-1 .. hetero-samp-16."))
for ($k = 1; $k -le 16 -and $go; $k++) {
  $go = Send-Mixed "p3-t1-$k" $msgs2 @((EchoTool)) "auto" 1.0 0.95 64 256
  if (-not $go) { break }
  $pr = Get-Content "$OutDir\{0:D3}-p3-t1-$k\response.raw.json" -Raw | ConvertFrom-Json
  if (@($pr.choices[0].message.tool_calls).Count -gt 0) {
    $t2 = $pr.choices[0].message.tool_calls[0]
    $msgs2 += [ordered]@{ role = "assistant"; content = $pr.choices[0].message.content; tool_calls = @([ordered]@{ id = $t2.id; type = $t2.type; function = [ordered]@{ name = $t2.function.name; arguments = $t2.function.arguments } }) }
    $msgs2 += [ordered]@{ role = "tool"; tool_call_id = $t2.id; content = '{"echoed":"x"}' }
  } else { $msgs2 += [ordered]@{ role = "assistant"; content = "noted" }; $msgs2 += (U "Continue with the next item via echo.") }
}
# Phase 4: long-prompt + big-budget tail x12
for ($k = 1; $k -le 12 -and $go; $k++) {
  $pad = ("Background context sentence $k. " * (20 + 10 * $k))
  $go = Send-Mixed "p4-long-$k" @(U ("$pad Search the internet for hetero long-prompt fact $k and report it.")) @((ExaToolFull)) "auto" 0 $null $null 512
}
Write-Output ("HETERO DONE n=" + $script:n + " softAnomalies=" + $script:softAnomalies.Count)
$script:softAnomalies | Set-Content "$OutDir\soft-anomalies.txt"
tasklist /FI "IMAGENAME eq ovms.exe" | Out-String
