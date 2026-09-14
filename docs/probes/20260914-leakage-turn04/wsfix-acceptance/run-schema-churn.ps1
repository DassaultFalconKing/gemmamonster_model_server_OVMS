param([string]$RestBase = "http://127.0.0.1:18091", [string]$OutDir = "")
# Schema-churn stress: 120 requests, each (almost) every one a DISTINCT moderate
# structural grammar. Continues on soft anomaly; stops only on hard failure.
$ev = "C:\Users\testc\AppData\Local\Temp\opencode\wsfix-acceptance-20260914"
if ($OutDir -eq "") { $OutDir = "$ev\schema-churn" }
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$serverLog = "$ev\server.stdout.log"
$logStart = (Get-Content $serverLog | Measure-Object -Line).Lines
$logStart | Set-Content "$OutDir\server-log-start-line.txt"
$script:n = 0
$script:fps = @{}
$script:soft = @()
$script:rssPeak = 0
$script:privPeak = 0
$script:freeLow = [long]::MaxValue
$script:hardAt = $null
function Sha16($s) {
  $b = [System.Text.Encoding]::UTF8.GetBytes($s)
  $h = [System.Security.Cryptography.SHA256]::Create().ComputeHash($b)
  return (($h | ForEach-Object { $_.ToString("x2") }) -join "").Substring(0, 16)
}
function Res-Snap($every) {
  $p = Get-Process ovms -ErrorAction SilentlyContinue
  $ws = -1; $priv = -1
  if ($p) {
    $ws = [math]::Round(($p | Measure-Object WorkingSet64 -Sum).Sum / 1MB)
    $priv = [math]::Round(($p | Measure-Object PrivateMemorySize64 -Sum).Sum / 1MB)
  }
  $free = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory
  if ($ws -gt $script:rssPeak) { $script:rssPeak = $ws }
  if ($priv -gt $script:privPeak) { $script:privPeak = $priv }
  if ($free -lt $script:freeLow) { $script:freeLow = $free }
  $gpu = ""
  if (($script:n % 10) -eq 0 -or $every -eq "always") {
    try {
      $s = Get-Counter "\GPU Adapter Memory(*)\*" -ErrorAction Stop |
        Select-Object -ExpandProperty CounterSamples |
        Where-Object { $_.Path -match "0x0001214c" } |
        ForEach-Object { "{0}={1}" -f ($_.Path -replace '^.*\\', ''), [math]::Round($_.CookedValue / 1MB, 1) }
      $gpu = ($s -join " ")
    } catch { $gpu = "GPU_COUNTER_FAIL" }
  }
  return [ordered]@{ alive = ($null -ne $p); ws = $ws; priv = $priv; free = $free; gpu = $gpu }
}
function Send-Churn($tag, $messages, $tools, $choice, $temp, $maxTok, $ptc) {
  $script:n++
  $d = "$OutDir\{0:D3}-{1}" -f $script:n, $tag
  New-Item -ItemType Directory -Path $d -Force | Out-Null
  $req = [ordered]@{
    model = "gemma4"; messages = $messages; tool_choice = $choice
    max_tokens = $maxTok; temperature = $temp
  }
  if ($null -ne $ptc) { $req.parallel_tool_calls = $ptc }
  if ($tools) { $req.tools = $tools }
  $req | ConvertTo-Json -Depth 14 | Set-Content "$d\request.json"
  $toolsJson = "no-tools"
  if ($tools) { $toolsJson = ($tools | ConvertTo-Json -Depth 14 -Compress) }
  $toolsJson | Set-Content "$d\tools.json"
  $fp = Sha16 ($toolsJson + "|" + ("" + $choice | Out-String).Trim())
  $fp | Set-Content "$d\fingerprint.txt"
  if (-not $script:fps.ContainsKey($fp)) { $script:fps[$fp] = $script:n }
  $isNew = ($script:fps[$fp] -eq $script:n)
  $t0 = Get-Date
  $outcome = ""
  try {
    $body = Get-Content "$d\request.json" -Raw
    $r = Invoke-WebRequest -Uri "$RestBase/v3/chat/completions" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 600
    $r.Content | Set-Content "$d\response.raw.json"
    $j = $r.Content | ConvertFrom-Json
    $m = $j.choices[0].message; $c = $m.content; if ($null -eq $c) { $c = "" }
    $fin = $j.choices[0].finish_reason; $nc = @($m.tool_calls).Count
    $outcome = "HTTP200 finish={0} calls={1} clen={2} calltag={3} ptok={4} ctok={5}" -f $fin, $nc, "$c".Length, ($c -match "<call:"), $j.usage.prompt_tokens, $j.usage.completion_tokens
    if (($fin -eq "length" -and "$c" -eq "" -and $nc -eq 0) -or ($c -match "<call:")) {
      $script:soft += ("{0:D3}-{1}: {2}" -f $script:n, $tag, $outcome)
      $outcome += " SOFT_ANOMALY"
    }
  } catch {
    $outcome = "HARD_FAIL: $($_.Exception.Message)"
    if ($_.ErrorDetails) { $_.ErrorDetails.Message | Set-Content "$d\response.raw.json" }
  }
  $ms = [int]((Get-Date) - $t0).TotalMilliseconds
  $rs = Res-Snap "every5"
  $line = "{0:D3} {1} fp={2}{3} choice={4} t={5} max={6} ptc={7} ms={8} :: {9} :: alive={10} ws={11} priv={12} freeKB={13} {14}" -f $script:n, $tag, $fp, $(if ($isNew) { "*" } else { "" }), ("" + $choice | Out-String).Trim().Substring(0, [Math]::Min(28, ("" + $choice | Out-String).Trim().Length)), $temp, $maxTok, $ptc, $ms, $outcome, $rs.alive, $rs.ws, $rs.priv, $rs.free, $rs.gpu
  $line | Set-Content "$d\result.txt"
  Add-Content "$OutDir\churn.log" $line
  if (($script:n % 10) -eq 0 -or $outcome -match "FAIL|ANOMALY") { Write-Output $line }
  if ($outcome -match "HARD_FAIL" -or (-not $rs.alive)) {
    $script:hardAt = $script:n
    Write-Output "HARD STOP at request $script:n"
    return $false
  }
  return $true
}
function MkTool($name, $props, $required) {
  $o = [ordered]@{ type = "object"; properties = $props }
  if ($required -and $required.Count -gt 0) { $o.required = $required }
  $o.additionalProperties = $false
  return [ordered]@{
    type = "function"
    function = [ordered]@{
      name = $name; description = "Diagnostic tool $name."
      parameters = $o
    }
  }
}
function S($t) { return [ordered]@{ type = "string"; description = "field $t" } }
function I($t) { return [ordered]@{ type = "integer"; description = "field $t" } }
function B($t) { return [ordered]@{ type = "boolean"; description = "field $t" } }
function U($t) { return [ordered]@{ role = "user"; content = $t } }
function Named($n) { return [ordered]@{ type = "function"; function = [ordered]@{ name = $n } } }
$go = $true
$idx = 0
function NextIdx() { $script:idxHack = $null; return ($script:n + 1) }
# ---- 20 simple unique schemas (tool_001..020, 1-3 props, mixed types) ----
for ($k = 1; $k -le 20 -and $go; $k++) {
  $nm = "tool_{0:D3}" -f $k
  $props = [ordered]@{}
  $props["alpha"] = (S "alpha")
  if (($k % 3) -ge 1) { $props["count"] = (I "count") }
  if (($k % 3) -eq 2) { $props["flag"] = (B "flag") }
  $req = @("alpha")
  if (($k % 2) -eq 0) { $req = @("alpha", "count") }
  $ch = "auto"; if (($k % 5) -eq 0) { $ch = "required" }
  $t = 0; if (($k % 4) -eq 0) { $t = 1.0 }
  $ptc = $null; if (($k % 2) -eq 0) { $ptc = $false }
  $go = Send-Churn "simple-$nm" @(U "Use $nm with alpha set to probe value $k.") @((MkTool $nm $props $req)) $ch $t 256 $ptc
}
# ---- 20 schemas with 4-8 properties ----
for ($k = 21; $k -le 40 -and $go; $k++) {
  $nm = "tool_{0:D3}" -f $k
  $props = [ordered]@{}
  $np = 4 + ($k % 5)
  for ($p = 1; $p -le $np; $p++) {
    $mod = ($p + $k) % 3
    if ($mod -eq 0) { $props["s_prop_$p"] = (S "s$p") }
    elseif ($mod -eq 1) { $props["i_prop_$p"] = (I "i$p") }
    else { $props["b_prop_$p"] = (B "b$p") }
  }
  $req = @("s_prop_1"); if (($k % 2) -eq 0) { $req = @("s_prop_1", "i_prop_2") }
  $ch = "auto"; if (($k % 4) -eq 0) { $ch = "required" }
  $t = 0; if (($k % 3) -eq 0) { $t = 1.0 }
  $go = Send-Churn "mid-$nm" @(U "Use $nm to record batch $k with all applicable fields.") @((MkTool $nm $props $req)) $ch $t 256 $null
}
# ---- 20 nested-object schemas ----
for ($k = 41; $k -le 60 -and $go; $k++) {
  $nm = "tool_{0:D3}" -f $k
  $inner = [ordered]@{ type = "object"; properties = [ordered]@{ city = (S "city"); zip = (S "zip") }; required = @("city") }
  $props = [ordered]@{ name = (S "name"); address = $inner }
  if (($k % 2) -eq 0) { $props["priority"] = (I "priority") }
  $ch = "auto"; if (($k % 5) -eq 0) { $ch = "required" }
  $t = 0; if (($k % 4) -eq 0) { $t = 1.0 }
  $go = Send-Churn "nested-$nm" @(U "Use $nm to store contact $k living in Paris.") @((MkTool $nm $props @("name", "address"))) $ch $t 256 $null
}
# ---- 20 array/enum schemas ----
for ($k = 61; $k -le 80 -and $go; $k++) {
  $nm = "tool_{0:D3}" -f $k
  $props = [ordered]@{}
  if (($k % 2) -eq 0) {
    $props["tags"] = [ordered]@{ type = "array"; description = "tags"; items = [ordered]@{ type = "string" } }
    $props["level"] = [ordered]@{ type = "string"; description = "level"; enum = @("low", "mid", "high") }
    $req = @("tags")
  } else {
    $props["scores"] = [ordered]@{ type = "array"; description = "scores"; items = [ordered]@{ type = "integer" } }
    $props["mode"] = [ordered]@{ type = "string"; description = "mode"; enum = @("fast", "slow") }
    $req = @("mode")
  }
  $ch = "auto"; if (($k % 4) -eq 0) { $ch = "required" }
  $t = 0; if (($k % 3) -eq 0) { $t = 1.0 }
  $go = Send-Churn "arr-$nm" @(U "Use $nm to log run $k with appropriate values.") @((MkTool $nm $props $req)) $ch $t 256 $null
}
# ---- 20 two-tool schemas ----
for ($k = 81; $k -le 100 -and $go; $k++) {
  $a = "tool_{0:D3}_a" -f $k; $b = "tool_{0:D3}_b" -f $k
  $ta = (MkTool $a ([ordered]@{ q = (S "q") }) @("q"))
  $tb = (MkTool $b ([ordered]@{ x = (I "x"); y = (S "y") }) @("x"))
  $ch = "auto"; if (($k % 3) -eq 0) { $ch = "required" }
  $t = 0; if (($k % 4) -eq 0) { $t = 1.0 }
  $go = Send-Churn "two-$k" @(U "Pick the right tool for query $k about Paris and call it.") @($ta, $tb) $ch $t 256 $null
}
# ---- 20 mixed named/required/auto variants (named ALWAYS present in toolset) ----
for ($k = 101; $k -le 120 -and $go; $k++) {
  $nm = "tool_{0:D3}" -f $k
  $props = [ordered]@{ input = (S "input") }
  if (($k % 2) -eq 0) { $props["n"] = (I "n") }
  $tool = (MkTool $nm $props @("input"))
  $mod = $k % 4
  $ch = "auto"; $tools = @($tool)
  if ($mod -eq 1) { $ch = (Named $nm) }
  elseif ($mod -eq 2) { $ch = "required" }
  elseif ($mod -eq 3) { $tools = @($tool, (MkTool ($nm + "_aux") ([ordered]@{ z = (S "z") }) @("z"))); $ch = (Named $nm) }
  $t = 0; if (($k % 3) -eq 0) { $t = 1.0 }
  $mx = 256; if (($k % 5) -eq 0) { $mx = 512 }
  $ptc = $null; if (($k % 2) -eq 0) { $ptc = $true }
  $go = Send-MixedAlias $nm $tools $ch $t $mx $ptc $k
}
function Send-MixedAlias($nm, $tools, $ch, $t, $mx, $ptc, $k) {
  return Send-Churn "mix-$nm" @(U "Use the designated tool for case $k with input set to value-$k.") $tools $ch $t $mx $ptc
}
"TOTAL=$($script:n) UNIQUE_FPS=$($script:fps.Count) HARD_AT=$($script:hardAt)" | Set-Content "$OutDir\churn-totals.txt"
"soft anomalies: $($script:soft.Count)" | Add-Content "$OutDir\churn-totals.txt"
$script:soft | Set-Content "$OutDir\soft-anomalies.txt"
"RSS_PEAK_MB=$($script:rssPeak) PRIV_PEAK_MB=$($script:privPeak) FREE_LOW_KB=$($script:freeLow)" | Add-Content "$OutDir\churn-totals.txt"
Get-Content "$OutDir\churn-totals.txt"
tasklist /FI "IMAGENAME eq ovms.exe" | Out-String
