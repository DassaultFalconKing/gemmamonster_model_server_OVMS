$ev = "C:\Users\testc\AppData\Local\Temp\opencode\gemmamonster-leakage-20260914"
function Get-Decode($windowPath, $outPath) {
  $lines = Get-Content $windowPath
  $start = -1
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match "256 tokens generated; full decode") { $start = $i; break }
  }
  if ($start -lt 0) { "NO_DECODE_LINE in $windowPath" | Write-Output; return }
  $buf = @()
  for ($i = $start; $i -lt $lines.Count; $i++) {
    if ($i -gt $start -and $lines[$i] -match "^\[\d{4}-\d{2}-\d{2} ") { break }
    $buf += $lines[$i]
  }
  $first = $buf[0] -replace '^.*full decode \(skip_special=false\): "', ''
  $text = $first + "`n" + (($buf | Select-Object -Skip 1) -join "`n")
  if ($text.EndsWith('"')) { $text = $text.Substring(0, $text.Length - 1) }
  $text | Set-Content $outPath -NoNewline
  "chars: $($text.Length)" | Write-Output
}
Get-Decode "$ev\deep-dive\sweep-kg\turn-29\server-window.log" "$ev\deep-dive\k-fail-full-decode.txt"
Get-Decode "$ev\deep-dive\sweep-kg-prefix-true\turn-23\server-window.log" "$ev\deep-dive\f1-fail-full-decode.txt"
