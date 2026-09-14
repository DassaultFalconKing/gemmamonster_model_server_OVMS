$ev = "C:\Users\testc\AppData\Local\Temp\opencode\wsfix-acceptance-20260914"
$td = "$ev\agentic"
New-Item -ItemType Directory -Path $td -Force | Out-Null
$exa = [ordered]@{
  type = "function"
  function = [ordered]@{
    name = "exa_web_search_exa"
    description = "Search the web for any topic and get clean, ready-to-use content."
    parameters = [ordered]@{
      type = "object"
      properties = [ordered]@{
        query = [ordered]@{ type = "string"; description = "Natural language search query." }
        objective = [ordered]@{ type = "string"; description = "Goal for this search turn." }
        numResults = [ordered]@{ type = "integer"; description = "Number of search results to return." }
      }
      required = @("query")
      additionalProperties = $false
    }
  }
}
$echo = [ordered]@{
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
function Send-Req($name, $messages, $tools, $choice) {
  $d = "$td\$name"
  New-Item -ItemType Directory -Path $d -Force | Out-Null
  $req = [ordered]@{ model = "gemma4"; messages = $messages; tool_choice = $choice; max_tokens = 512; temperature = 0 }
  if ($tools) { $req.tools = $tools }
  $req | ConvertTo-Json -Depth 14 | Set-Content "$d\request.json"
  $body = Get-Content "$d\request.json" -Raw
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:18091/v3/chat/completions" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 600
    $r.Content | Set-Content "$d\response.raw.json"
  } catch { "FAIL $($_.Exception.Message)" | Set-Content "$d\response.raw.json" }
  $raw = Get-Content "$d\response.raw.json" -Raw
  if ($raw -match "^FAIL") { ([ordered]@{ error = $raw } | ConvertTo-Json) | Set-Content "$d\summary.json"; Write-Output ("--- " + $name + " --- REQUEST FAILED"); return $null }
  $resp = $raw | ConvertFrom-Json
  $msg = $resp.choices[0].message; $c = $msg.content; if ($null -eq $c) { $c = "" }
  $o = [ordered]@{
    finish = $resp.choices[0].finish_reason
    calls = @($msg.tool_calls).Count
    names = ((@($msg.tool_calls) | ForEach-Object { $_.function.name }) -join ",")
    args = ((@($msg.tool_calls) | ForEach-Object { $_.function.arguments }) -join " | ")
    content_len = "$c".Length
    content = "$c".Substring(0, [Math]::Min(400, "$c".Length))
    has_call_tag = ($c -match "<call:")
    ptok = $resp.usage.prompt_tokens; ctok = $resp.usage.completion_tokens
  }
  $o | ConvertTo-Json -Depth 5 | Set-Content "$d\summary.json"
  Write-Output ("--- " + $name + " ---")
  Get-Content "$d\summary.json"
  return $resp
}
# A1: search call
$r1 = Send-Req "A1-search" @([ordered]@{ role = "user"; content = "Search the internet for the winner of the 2026 Eurovision Song Contest." }) @($exa) "auto"
if ($r1 -and @($r1.choices[0].message.tool_calls).Count -gt 0) {
$tc = $r1.choices[0].message.tool_calls[0]
# A2: consume synthetic result, synthesize answer
$histA = @(
  [ordered]@{ role = "user"; content = "Search the internet for the winner of the 2026 Eurovision Song Contest." },
  [ordered]@{ role = "assistant"; content = $r1.choices[0].message.content; tool_calls = @([ordered]@{ id = $tc.id; type = $tc.type; function = [ordered]@{ name = $tc.function.name; arguments = $tc.function.arguments } }) },
  [ordered]@{ role = "tool"; tool_call_id = $tc.id; content = '{"results":[{"title":"Eurovision 2026 winner","text":"Austria won the Eurovision Song Contest 2026 with the song Hallucination."}]}' },
  [ordered]@{ role = "user"; content = "Based on the search result, report the winning country and song title." }
)
Send-Req "A2-synthesize" $histA @($exa) "auto"
} else { Write-Output "SKIP A2 (A1 no tool call)" }
# B1: direct answer expected (both tools available)
Send-Req "B1-direct" @([ordered]@{ role = "user"; content = "What is 7 plus 8? Answer directly with just the number." }) @($echo, $exa) "auto"
# B2: routing to web expected
Send-Req "B2-route-web" @([ordered]@{ role = "user"; content = "Search the web for the current price of crude oil and report it." }) @($echo, $exa) "auto"
# C1: required search, then consume
$rC = Send-Req "C1-required" @([ordered]@{ role = "user"; content = "Find the capital city of Kazakhstan using web search." }) @($exa) "required"
if ($rC -and @($rC.choices[0].message.tool_calls).Count -gt 0) {
$tcc = $rC.choices[0].message.tool_calls[0]
$histC = @(
  [ordered]@{ role = "user"; content = "Find the capital city of Kazakhstan using web search." },
  [ordered]@{ role = "assistant"; content = $rC.choices[0].message.content; tool_calls = @([ordered]@{ id = $tcc.id; type = $tcc.type; function = [ordered]@{ name = $tcc.function.name; arguments = $tcc.function.arguments } }) },
  [ordered]@{ role = "tool"; tool_call_id = $tcc.id; content = '{"results":[{"title":"Kazakhstan capital","text":"The capital of Kazakhstan is Astana."}]}' },
  [ordered]@{ role = "user"; content = "What is the capital? Answer in one short sentence." }
)
Send-Req "C2-synthesize" $histC @($exa) "auto"
} else { Write-Output "SKIP C2 (C1 no tool call)" }
tasklist /FI "IMAGENAME eq ovms.exe" | Out-String
