$ev = "C:\Users\testc\AppData\Local\Temp\opencode\gemmamonster-leakage-20260914"
$td = "$ev\test-6-minimal-exa-auto"
New-Item -ItemType Directory -Path $td -Force | Out-Null
$minParams = [ordered]@{
  type = "object"
  properties = [ordered]@{
    query = [ordered]@{ type = "string" }
  }
  required = @("query")
}
$req = [ordered]@{
  model = "gemma4"
  messages = @(
    [ordered]@{ role = "user"; content = "Please search the internet for the winner of the 2026 Eurovision Song Contest and report the winning country and song title." }
  )
  tools = @(
    [ordered]@{
      type = "function"
      function = [ordered]@{
        name = "exa_web_search_exa"
        description = "Search the web."
        parameters = $minParams
      }
    }
  )
  tool_choice = "auto"
  max_tokens = 512
  temperature = 0
}
$req | ConvertTo-Json -Depth 12 | Set-Content "$td\request.json"
($req.tools | ConvertTo-Json -Depth 12) | Set-Content "$td\tools.json"
$start = (Get-Content "$ev\server-fresh\server.stdout.log" | Measure-Object -Line).Lines
$start | Set-Content "$td\log-start-line.txt"
$body = Get-Content "$td\request.json" -Raw
$t0 = Get-Date
try {
  $r = Invoke-WebRequest -Uri "http://127.0.0.1:18091/v3/chat/completions" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 600
  $r.Content | Set-Content "$td\response.raw.json"
  "HTTP $($r.StatusCode)" | Set-Content "$td\http.txt"
} catch {
  "FAIL: $($_.Exception.Message)" | Set-Content "$td\http.txt"
  if ($_.ErrorDetails) { $_.ErrorDetails.Message | Set-Content "$td\response.raw.json" }
}
[int](Get-Date -Date ((Get-Date) - $t0) -UFormat "%s") 2>$null | Out-Null
$total = (Get-Content "$ev\server-fresh\server.stdout.log" | Measure-Object -Line).Lines
$total | Set-Content "$td\log-end-line.txt"
Get-Content "$ev\server-fresh\server.stdout.log" | Select-Object -Skip $start | Set-Content "$td\server-window.log"
$m = Select-String -Path "$td\server-window.log" -Pattern "guided|Guided|xgrammar|XGrammar|structured|Structured|validat|Validat|schema|Schema|grammar|Grammar|will not be applied"
if ($m) { $m | ForEach-Object { $_.Line } | Set-Content "$td\server-guided-lines.txt" } else { "NO_MATCHES" | Set-Content "$td\server-guided-lines.txt" }
$resp = Get-Content "$td\response.raw.json" -Raw | ConvertFrom-Json
$msg = $resp.choices[0].message
$s = [ordered]@{
  http = (Get-Content "$td\http.txt")
  finish_reason = $resp.choices[0].finish_reason
  content = $msg.content
  tool_calls_count = @($msg.tool_calls).Count
  tool_names = ((@($msg.tool_calls) | ForEach-Object { $_.function.name }) -join ",")
  tool_arguments = ((@($msg.tool_calls) | ForEach-Object { $_.function.arguments }) -join " | ")
  has_literal_call_open = ($msg.content -match "<call:")
  completion_tokens = $resp.usage.completion_tokens
}
$s | ConvertTo-Json | Set-Content "$td\summary.json"
Get-Content "$td\http.txt"
Get-Content "$td\summary.json"
