$w = "C:\Users\testc\AppData\Local\Temp\opencode\wsfix-acceptance-20260914"
$body = Get-Content "$w\agentic\B2-route-web\request.json" -Raw
$log = @()
for ($i = 1; $i -le 60; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:18091/v3/chat/completions" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 600
    $j = $r.Content | ConvertFrom-Json
    $st = "{0} ok finish={1} calls={2}" -f $i, $j.choices[0].finish_reason, @($j.choices[0].message.tool_calls).Count
  } catch { $st = "{0} FAIL: {1}" -f $i, $_.Exception.Message }
  $p = Get-Process ovms -ErrorAction SilentlyContinue
  $mem = if ($p) { [math]::Round(($p | Measure-Object WorkingSet64 -Sum).Sum / 1MB) } else { -1 }
  $line = "{0} memMB={1} alive={2}" -f $st, $mem, ($null -ne $p)
  $log += $line
  if (($i % 10) -eq 0 -or $st -match "FAIL" -or $null -eq $p) { Write-Output $line }
  if ($st -match "FAIL" -or $null -eq $p) { break }
  Start-Sleep -Seconds 2
}
$log | Set-Content "$w\grammar-soak.log"
Write-Output "SOAK DONE lines=$($log.Count)"
tasklist /FI "IMAGENAME eq ovms.exe" | Out-String
