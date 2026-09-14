$ev = "C:\Users\testc\AppData\Local\Temp\opencode\wsfix-acceptance-20260914"
$td = "$ev\wsfix-sweep-t1"
New-Item -ItemType Directory -Path $td -Force | Out-Null
$logf = "$ev\server.stdout.log"
"graph=standard-prefix-true max_num_seqs=256 device=GPU VLM_CB temp=1.0 top_p=0.95 top_k=64 max_tokens=256 parallel_tool_calls=false candidate=17064400" | Set-Content "$td\conditions.txt"

$tool = [ordered]@{
  type = "function"
  function = [ordered]@{
    name = "echo"
    description = "Echo back the given text."
    parameters = [ordered]@{
      type = "object"
      properties = [ordered]@{
        text = [ordered]@{ type = "string"; description = "Text to echo." }
      }
      required = @("text")
      additionalProperties = $false
    }
  }
}
$items = 1..32 | ForEach-Object { "sweep-item-$_" }
$taskText = "Call the echo tool exactly once per turn with the next list item as text, in order, starting with sweep-item-1. After each tool result, continue with the next item on the following turn. Do not write any text, only call the tool. List: " + ($items -join ", ") + "."
$messages = @([ordered]@{ role = "user"; content = $taskText })
$checkpoints = @(1, 4, 8, 16, 24, 32)
$results = @()
$prevSig = $null; $toolTurns = 0; $firstDeviation = $null; $stopSweep = $false
function Norm-Args($a) {
  try { $o = $a | ConvertFrom-Json; return ($o | ConvertTo-Json -Compress -Depth 12) }
  catch { return "$a" }
}
for ($iter = 1; $iter -le 45 -and -not $stopSweep; $iter++) {
  $itd = "$td\turn-$("{0:D2}" -f $iter)"
  New-Item -ItemType Directory -Path $itd -Force | Out-Null
  $req = [ordered]@{
    model = "gemma4"; messages = $messages; tools = @($tool)
    tool_choice = "auto"; parallel_tool_calls = $false
    max_tokens = 256; temperature = 1.0; top_p = 0.95; top_k = 64
  }
  $req | ConvertTo-Json -Depth 14 | Set-Content "$itd\request.json"
  $start = (Get-Content $logf | Measure-Object -Line).Lines
  $body = Get-Content "$itd\request.json" -Raw
  $http = "HTTP ?"
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:18091/v3/chat/completions" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 600
    $r.Content | Set-Content "$itd\response.raw.json"
    $http = "HTTP $($r.StatusCode)"
  } catch {
    $http = "FAIL: $($_.Exception.Message)"
    if ($_.ErrorDetails) { $_.ErrorDetails.Message | Set-Content "$itd\response.raw.json" }
    else { "{}" | Set-Content "$itd\response.raw.json" }
  }
  $total = (Get-Content $logf | Measure-Object -Line).Lines
  Get-Content $logf | Select-Object -Skip $start | Set-Content "$itd\server-window.log"
  $resp = Get-Content "$itd\response.raw.json" -Raw | ConvertFrom-Json
  $choice = $resp.choices[0]; $msg = $choice.message
  $content = $msg.content; if ($null -eq $content) { $content = "" }
  $tcs = @($msg.tool_calls)
  $hasCalls = ($tcs.Count -gt 0 -and $null -ne $tcs[0])
  $names = ($tcs | ForEach-Object { $_.function.name }) -join ","
  $argList = @($tcs | ForEach-Object { $_.function.arguments })
  $sig = if ($hasCalls) { ($tcs | ForEach-Object { $_.function.name + "|" + (Norm-Args $_.function.arguments) }) -join " || " } else { "" }
  $isRepeat = ($hasCalls -and $sig -eq $prevSig)
  if ($hasCalls) { $toolTurns++ }
  $hasOpen = ($content -match "<call:")
  $isEmpty = ((-not $hasCalls) -and ($content -eq ""))
  $isLength = ($choice.finish_reason -eq "length")
  $row = [ordered]@{
    iter = $iter; tool_turn = $toolTurns; http = $http
    prompt_tokens = $resp.usage.prompt_tokens
    completion_tokens = $resp.usage.completion_tokens
    finish_reason = $choice.finish_reason; tool_calls_count = $tcs.Count
    tool_names = $names; tool_arguments = ($argList -join " | ")
    sig = $sig; literal_call_open = $hasOpen; repeat_prev_sig = $isRepeat
    empty_turn = $isEmpty; finish_length = $isLength
    content_excerpt = "$content".Substring(0, [Math]::Min(200, "$content".Length))
  }
  $results += [pscustomobject]$row
  ($row | ConvertTo-Json -Depth 6) | Set-Content "$itd\summary.json"
  Write-Output ("iter={0} toolturn={1} finish={2} calls={3} args=[{4}] <call:={5} repeat={6} empty={7} len={8} ptok={9} ctok={10}" -f $iter, $toolTurns, $choice.finish_reason, $tcs.Count, ($argList -join " | "), $hasOpen, $isRepeat, $isEmpty, $isLength, $resp.usage.prompt_tokens, $resp.usage.completion_tokens)
  $dev = $null
  if ($hasOpen) { $dev = "DIALECT_DRIFT_CALL_TAG" }
  elseif ($isEmpty -and $iter -gt 1) { $dev = "EMPTY_POST_TOOL_TURN" }
  elseif ($isLength) { $dev = "GRAMMAR_THRASH_LENGTH" }
  elseif ($isRepeat) { $dev = "REPEATED_CANONICAL_TOOL_CALL" }
  if ($dev -and (-not $firstDeviation)) {
    $firstDeviation = [ordered]@{ iter = $iter; tool_turn = $toolTurns; class = $dev }
    $firstDeviation | ConvertTo-Json | Set-Content "$td\first-deviation.json"
    Write-Output ("FIRST_DEVIATION: {0} at iter={1} toolturn={2}" -f $dev, $iter, $toolTurns)
    if ($dev -ne "REPEATED_CANONICAL_TOOL_CALL") { $stopSweep = $true }
  }
  if ($firstDeviation -and $firstDeviation.class -eq "REPEATED_CANONICAL_TOOL_CALL" -and ($iter -ge ($firstDeviation.iter + 6))) { $stopSweep = $true }
  if ($hasCalls) {
    $prevSig = $sig
    $messages += [ordered]@{ role = "assistant"; content = $msg.content; tool_calls = @($tcs | ForEach-Object { [ordered]@{ id = $_.id; type = $_.type; function = [ordered]@{ name = $_.function.name; arguments = $_.function.arguments } } }) }
    foreach ($tc in $tcs) {
      $echoed = ""
      try { $echoed = (($tc.function.arguments | ConvertFrom-Json).text) } catch { $echoed = $tc.function.arguments }
      $messages += [ordered]@{ role = "tool"; tool_call_id = $tc.id; content = ('{"echoed":"' + $echoed + '"}') }
    }
    if ($toolTurns -ge 32) { $stopSweep = $true }
  } else {
    if ($isEmpty) { $stopSweep = $true }
    else {
      $messages += [ordered]@{ role = "assistant"; content = "$content" }
      $messages += [ordered]@{ role = "user"; content = "Continue with the next list item via the echo tool. Only call the tool, no text." }
    }
  }
}
$results | ConvertTo-Json -Depth 6 | Set-Content "$td\sweep-summary.json"
if (-not $firstDeviation) { ([ordered]@{ class = "NO_LONG_CONTEXT_REGRESSION"; tool_turns = $toolTurns } | ConvertTo-Json) | Set-Content "$td\first-deviation.json" }
Write-Output "=== KG SWEEP DONE: toolturns=$toolTurns ==="
Get-Content "$td\first-deviation.json"
