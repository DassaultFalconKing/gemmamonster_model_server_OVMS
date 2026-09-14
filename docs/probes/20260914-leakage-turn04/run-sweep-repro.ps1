$ev = "C:\Users\testc\AppData\Local\Temp\opencode\gemmamonster-leakage-20260914"
$td = "$ev\sweep-long-context"
function Send-Variant($subdir, $maxTokens) {
  $vd = "$td\$subdir"
  New-Item -ItemType Directory -Path $vd -Force | Out-Null
  $base = Get-Content "$td\turn-04\request.json" -Raw | ConvertFrom-Json
  $req = [ordered]@{
    model = "gemma4"
    messages = $base.messages
    tools = $base.tools
    tool_choice = "auto"
    max_tokens = $maxTokens
    temperature = 0
  }
  $req | ConvertTo-Json -Depth 14 | Set-Content "$vd\request.json"
  $start = (Get-Content "$ev\server-fresh\server.stdout.log" | Measure-Object -Line).Lines
  $body = Get-Content "$vd\request.json" -Raw
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:18091/v3/chat/completions" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 600
    $r.Content | Set-Content "$vd\response.raw.json"
    "HTTP $($r.StatusCode)" | Set-Content "$vd\http.txt"
  } catch {
    "FAIL: $($_.Exception.Message)" | Set-Content "$vd\http.txt"
    if ($_.ErrorDetails) { $_.ErrorDetails.Message | Set-Content "$vd\response.raw.json" }
  }
  $total = (Get-Content "$ev\server-fresh\server.stdout.log" | Measure-Object -Line).Lines
  Get-Content "$ev\server-fresh\server.stdout.log" | Select-Object -Skip $start | Set-Content "$vd\server-window.log"
  $resp = Get-Content "$vd\response.raw.json" -Raw | ConvertFrom-Json
  $msg = $resp.choices[0].message
  $c = $msg.content; if ($null -eq $c) { $c = "" }
  $s = [ordered]@{
    http = (Get-Content "$vd\http.txt")
    max_tokens_sent = $maxTokens
    finish_reason = $resp.choices[0].finish_reason
    content_len = "$c".Length
    content_excerpt = "$c".Substring(0, [Math]::Min(300, "$c".Length))
    tool_calls_count = @($msg.tool_calls).Count
    tool_names = ((@($msg.tool_calls) | ForEach-Object { $_.function.name }) -join ",")
    tool_arguments = ((@($msg.tool_calls) | ForEach-Object { $_.function.arguments }) -join " | ")
    has_literal_call_open = ($c -match "<call:")
    prompt_tokens = $resp.usage.prompt_tokens
    completion_tokens = $resp.usage.completion_tokens
  }
  $s | ConvertTo-Json -Depth 5 | Set-Content "$vd\summary.json"
  Write-Output "=== $subdir (max_tokens=$maxTokens) ==="
  Get-Content "$vd\summary.json"
}
Send-Variant "turn-04-retry-256" 256
Send-Variant "turn-04-budget-1024" 1024
