$ev = "C:\Users\testc\AppData\Local\Temp\opencode\wsfix-acceptance-20260914"
$td = "$ev\agentic"
function Send-One($name, $file) {
  $d = "$td\$name"
  New-Item -ItemType Directory -Path $d -Force | Out-Null
  Copy-Item $file "$d\request.json"
  $body = Get-Content "$d\request.json" -Raw
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:18091/v3/chat/completions" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 600
    $r.Content | Set-Content "$d\response.raw.json"
  } catch { "FAIL $($_.Exception.Message)" | Set-Content "$d\response.raw.json" }
  $raw = Get-Content "$d\response.raw.json" -Raw
  if ($raw -match "^FAIL") { Write-Output "$name : $raw"; return $null }
  $resp = $raw | ConvertFrom-Json
  $msg = $resp.choices[0].message; $c = $msg.content; if ($null -eq $c) { $c = "" }
  Write-Output ("{0}: finish={1} calls={2} names={3} clen={4} calltag={5} content=[{6}]" -f $name, $resp.choices[0].finish_reason, @($msg.tool_calls).Count, ((@($msg.tool_calls) | ForEach-Object { $_.function.name }) -join ","), "$c".Length, ($c -match "<call:"), "$c".Substring(0, [Math]::Min(200, "$c".Length)))
  return $resp
}
# Rebuild B1/B2/C1 requests inline (agentic script died before writing them)
$exa = ([ordered]@{ type = "function"; function = [ordered]@{ name = "exa_web_search_exa"; description = "Search the web."; parameters = [ordered]@{ type = "object"; properties = [ordered]@{ query = [ordered]@{ type = "string" }; objective = [ordered]@{ type = "string" }; numResults = [ordered]@{ type = "integer" } }; required = @("query"); additionalProperties = $false } } })
$echo = ([ordered]@{ type = "function"; function = [ordered]@{ name = "echo"; description = "Echo."; parameters = [ordered]@{ type = "object"; properties = [ordered]@{ text = [ordered]@{ type = "string" } }; required = @("text"); additionalProperties = $false } } })
function MkReq($messages, $tools, $choice) {
  $q = [ordered]@{ model = "gemma4"; messages = $messages; tool_choice = $choice; max_tokens = 512; temperature = 0 }
  if ($tools) { $q.tools = $tools }
  return ($q | ConvertTo-Json -Depth 14)
}
MkReq @([ordered]@{ role = "user"; content = "What is 7 plus 8? Answer directly with just the number." }) @($echo, $exa) "auto" | Set-Content "$td\B1-direct\request.json" -Force
New-Item -ItemType Directory -Path "$td\B1-direct" -Force | Out-Null
MkReq @([ordered]@{ role = "user"; content = "What is 7 plus 8? Answer directly with just the number." }) @($echo, $exa) "auto" | Set-Content "$td\B1-direct\request.json"
MkReq @([ordered]@{ role = "user"; content = "Search the web for the current price of crude oil and report it." }) @($echo, $exa) "auto" | Set-Content "$td\B2-route-web\request.json" -Force
New-Item -ItemType Directory -Path "$td\B2-route-web" -Force | Out-Null
MkReq @([ordered]@{ role = "user"; content = "Search the web for the current price of crude oil and report it." }) @($echo, $exa) "auto" | Set-Content "$td\B2-route-web\request.json"
New-Item -ItemType Directory -Path "$td\C1-required" -Force | Out-Null
MkReq @([ordered]@{ role = "user"; content = "Find the capital city of Kazakhstan using web search." }) @($exa) "required" | Set-Content "$td\C1-required\request.json"
Send-One "B1-direct" "$td\B1-direct\request.json"
Send-One "B2-route-web" "$td\B2-route-web\request.json"
$rC = Send-One "C1-required" "$td\C1-required\request.json"
if ($rC -and @($rC.choices[0].message.tool_calls).Count -gt 0) {
  $tcc = $rC.choices[0].message.tool_calls[0]
  $histC = @(
    [ordered]@{ role = "user"; content = "Find the capital city of Kazakhstan using web search." },
    [ordered]@{ role = "assistant"; content = $rC.choices[0].message.content; tool_calls = @([ordered]@{ id = $tcc.id; type = $tcc.type; function = [ordered]@{ name = $tcc.function.name; arguments = $tcc.function.arguments } }) },
    [ordered]@{ role = "tool"; tool_call_id = $tcc.id; content = '{"results":[{"title":"Kazakhstan capital","text":"The capital of Kazakhstan is Astana."}]}' },
    [ordered]@{ role = "user"; content = "What is the capital? Answer in one short sentence." }
  )
  New-Item -ItemType Directory -Path "$td\C2-synthesize" -Force | Out-Null
  MkReq $histC @($exa) "auto" | Set-Content "$td\C2-synthesize\request.json"
  Send-One "C2-synthesize" "$td\C2-synthesize\request.json"
} else { Write-Output "SKIP C2" }
tasklist /FI "IMAGENAME eq ovms.exe" | Out-String
