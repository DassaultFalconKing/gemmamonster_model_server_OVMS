$ev = "C:\Users\testc\AppData\Local\Temp\opencode\buildB-test"
$src = "C:\git\rc2-908d6695-handoff-docs-20260914\docs\probes\20260914-leakage-turn04"
New-Item -ItemType Directory -Path "$ev\B1" -Force | Out-Null
function Send-B1($name, $file, $extra) {
  $d = "$ev\B1\$name"
  New-Item -ItemType Directory -Path $d -Force | Out-Null
  Copy-Item $file "$d\request.json"
  $body = Get-Content "$d\request.json" -Raw
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:18091/v3/chat/completions" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 600
    $r.Content | Set-Content "$d\response.raw.json"
    $h = "HTTP $($r.StatusCode)"
  } catch { $h = "FAIL: $($_.Exception.Message)"; if ($_.ErrorDetails) { $_.ErrorDetails.Message | Set-Content "$d\response.raw.json" } }
  $resp = Get-Content "$d\response.raw.json" -Raw | ConvertFrom-Json
  $msg = $resp.choices[0].message; $c = $msg.content; if ($null -eq $c) { $c = "" }
  "{0}: {1} finish={2} calls={3} names={4} clen={5} calltag={6} ptok={7} ctok={8} content=[{9}]" -f $name, $h, $resp.choices[0].finish_reason, @($msg.tool_calls).Count, ((@($msg.tool_calls) | ForEach-Object { $_.function.name }) -join ","), "$c".Length, ($c -match "<call:"), $resp.usage.prompt_tokens, $resp.usage.completion_tokens, "$c".Substring(0, [Math]::Min(120, "$c".Length)) | Write-Output
}
Send-B1 "plain" "C:\Users\testc\AppData\Local\Temp\opencode\wsfix-acceptance-20260914\plain-no-tools-request.json" $null
Send-B1 "echo-auto" "$src\test-4-echo-auto\request.json" $null
Send-B1 "exa-required" "$src\test-7a-real-exa-required\request.json" $null
Send-B1 "exa-named" "$src\test-7b-real-exa-named\request.json" $null
Select-String -Path "$ev\server.stdout.log" -Pattern "XGrammarCache" | ForEach-Object { $_.Line.Substring(0,[Math]::Min(240,$_.Line.Length)) } | Out-String | Select-Object -First 10
tasklist /FI "IMAGENAME eq ovms.exe" | Out-String
