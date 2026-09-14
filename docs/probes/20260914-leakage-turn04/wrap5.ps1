$ev = "C:\Users\testc\AppData\Local\Temp\opencode\gemmamonster-leakage-20260914"
$td = "$ev\test-5-real-exa-auto"
$start = [int](Get-Content "$td\log-start-line.txt")
$total = (Get-Content "$ev\server-fresh\server.stdout.log" | Measure-Object -Line).Lines
Get-Content "$ev\server-fresh\server.stdout.log" | Select-Object -Skip $start | Set-Content "$td\server-window.log"
$total | Set-Content "$td\log-end-line.txt"
Select-String -Path "$td\server-window.log" -Pattern "guided|Guided|xgrammar|XGrammar|structured|Structured|validat|Validat|schema|Schema|grammar|Grammar|will not be applied" | ForEach-Object { $_.Line } | Set-Content "$td\server-guided-lines.txt"
$resp = Get-Content "$td\response.raw.json" -Raw | ConvertFrom-Json
$msg = $resp.choices[0].message
$s = [ordered]@{
  http = 200
  finish_reason = $resp.choices[0].finish_reason
  content = $msg.content
  tool_calls_count = @($msg.tool_calls).Count
  tool_names = ((@($msg.tool_calls) | ForEach-Object { $_.function.name }) -join ",")
  tool_arguments = ((@($msg.tool_calls) | ForEach-Object { $_.function.arguments }) -join " | ")
  has_literal_call_open = ($msg.content -match "<call:")
  completion_tokens = $resp.usage.completion_tokens
}
$s | ConvertTo-Json | Set-Content "$td\summary.json"
Write-Output ("window lines: " + ($total - $start))
Get-Content "$td\summary.json"
Write-Output "--- guided lines ---"
Get-Content "$td\server-guided-lines.txt"
