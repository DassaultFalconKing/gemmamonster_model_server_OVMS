param([string]$RestBase = "http://127.0.0.1:18091", [string]$OutDir = "")
# DISCRIMINATOR: 120 DISTINCT prompts x SAME single grammar (echo tool).
# If this dies like schema-churn -> history/prefix accumulation suffices (grammar theory WEAKENED).
# If this survives -> distinct-grammar count is the killer variable (grammar theory CONFIRMED).
$ev = "C:\Users\testc\AppData\Local\Temp\opencode\gemmamonster-leakage-20260914"
if ($OutDir -eq "") { $OutDir = "$ev\deep-dive\prompt-churn" }
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$serverLog = "$ev\server-fresh\server.stdout.log"
$tool = [ordered]@{
  type = "function"
  function = [ordered]@{
    name = "echo"; description = "Echo back the given text."
    parameters = [ordered]@{
      type = "object"
      properties = [ordered]@{ text = [ordered]@{ type = "string"; description = "Text to echo." } }
      required = @("text"); additionalProperties = $false
    }
  }
}
$topics = @("the capital of France", "the speed of light", "the deepest ocean trench",
  "the inventor of the telephone", "the largest desert", "photosynthesis",
  "the boiling point of water", "the currency of Japan", "quantum entanglement",
  "the tallest mountain", "Mozart birth year", "the human genome", "black holes",
  "the Eiffel tower height", " medewerkers")
$soft = @(); $n = 0; $hardAt = $null
for ($k = 1; $k -le 120; $k++) {
  $n++
  $d = "$OutDir\{0:D3}" -f $n
  New-Item -ItemType Directory -Path $d -Force | Out-Null
  $topic = $topics[($k - 1) % $topics.Count]
  $pad = ("Unrelated background context number $k. " * (3 + ($k % 7)))
  $t = 0; if (($k % 3) -eq 0) { $t = 1.0 }
  $req = [ordered]@{
    model = "gemma4"
    messages = @([ordered]@{ role = "user"; content = "$pad Now echo exactly this string: prompt-churn-item-$k about $topic." })
    tools = @($tool); tool_choice = "auto"; max_tokens = 256; temperature = $t
  }
  $req | ConvertTo-Json -Depth 12 | Set-Content "$d\request.json"
  $body = Get-Content "$d\request.json" -Raw
  $t0 = Get-Date
  $outcome = ""
  try {
    $r = Invoke-WebRequest -Uri "$RestBase/v3/chat/completions" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 600
    $r.Content | Set-Content "$d\response.raw.json"
    $j = $r.Content | ConvertFrom-Json
    $m = $j.choices[0].message; $c = $m.content; if ($null -eq $c) { $c = "" }
    $fin = $j.choices[0].finish_reason; $nc = @($m.tool_calls).Count
    $outcome = "HTTP200 finish={0} calls={1} clen={2} calltag={3} ptok={4} ctok={5}" -f $fin, $nc, "$c".Length, ($c -match "<call:"), $j.usage.prompt_tokens, $j.usage.completion_tokens
    if (($fin -eq "length" -and "$c" -eq "" -and $nc -eq 0) -or ($c -match "<call:")) {
      $soft += ("{0:D3}: {1}" -f $n, $outcome); $outcome += " SOFT_ANOMALY"
    }
  } catch { $outcome = "HARD_FAIL: $($_.Exception.Message)"; if ($_.ErrorDetails) { $_.ErrorDetails.Message | Set-Content "$d\response.raw.json" } }
  $ms = [int]((Get-Date) - $t0).TotalMilliseconds
  $p = Get-Process ovms -ErrorAction SilentlyContinue
  $line = "{0:D3} ms={1} :: {2} :: alive={3}" -f $n, $ms, $outcome, ($null -ne $p)
  Add-Content "$OutDir\prompt-churn.log" $line
  if (($n % 10) -eq 0 -or $outcome -match "FAIL|ANOMALY") { Write-Output $line }
  if ($outcome -match "HARD_FAIL" -or $null -eq $p) { $hardAt = $n; Write-Output "HARD STOP at $n"; break }
}
"TOTAL=$n HARD_AT=$hardAt SOFT=$($soft.Count)" | Set-Content "$OutDir\totals.txt"
$soft | Set-Content "$OutDir\soft-anomalies.txt"
Get-Content "$OutDir\totals.txt"
tasklist /FI "IMAGENAME eq ovms.exe" | Out-String
