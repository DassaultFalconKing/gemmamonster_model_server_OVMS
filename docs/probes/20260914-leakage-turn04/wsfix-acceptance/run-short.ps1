$ev = "C:\Users\testc\AppData\Local\Temp\opencode\wsfix-acceptance-20260914"
$src = "C:\git\rc2-908d6695-handoff-docs-20260914\docs\probes\20260914-leakage-turn04"
$cases = @(
  @("p1-echo-auto", "$src\test-4-echo-auto\request.json"),
  @("p2-realexa-auto", "$src\test-5-real-exa-auto\request.json"),
  @("p3-minimal-auto", "$src\test-6-minimal-exa-auto\request.json"),
  @("p4-required", "$src\test-7a-real-exa-required\request.json"),
  @("p5-named", "$src\test-7b-real-exa-named\request.json"),
  @("p6-contam-auto", "$src\test-8-contaminated-exa-auto\request.json")
)
foreach ($c in $cases) {
  $td = "$ev\short\$($c[0])"
  New-Item -ItemType Directory -Path $td -Force | Out-Null
  Copy-Item $c[1] "$td\request.json"
  $body = Get-Content "$td\request.json" -Raw
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:18091/v3/chat/completions" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 600
    $r.Content | Set-Content "$td\response.raw.json"
    $h = "HTTP $($r.StatusCode)"
  } catch {
    $h = "FAIL: $($_.Exception.Message)"
    if ($_.ErrorDetails) { $_.ErrorDetails.Message | Set-Content "$td\response.raw.json" }
  }
  $resp = Get-Content "$td\response.raw.json" -Raw | ConvertFrom-Json
  $msg = $resp.choices[0].message; $ct = $msg.content; if ($null -eq $ct) { $ct = "" }
  "{0}: {1} finish={2} calls={3} names={4} content_len={5} <call:={6} ptok={7} ctok={8}" -f $c[0], $h, $resp.choices[0].finish_reason, @($msg.tool_calls).Count, ((@($msg.tool_calls) | ForEach-Object { $_.function.name }) -join ","), "$ct".Length, ($ct -match "<call:"), $resp.usage.prompt_tokens, $resp.usage.completion_tokens | Write-Output
}
tasklist /FI "IMAGENAME eq ovms.exe" | Out-String
