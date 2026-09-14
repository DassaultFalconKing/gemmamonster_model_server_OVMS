$w = "C:\Users\testc\AppData\Local\Temp\opencode\gemmamonster-leakage-20260914\deep-dive\turn-04-trace\server-window.log"
$out = "C:\Users\testc\AppData\Local\Temp\opencode\gemmamonster-leakage-20260914\deep-dive\server-render"
$lines = Get-Content $w
$start = -1
for ($i = 0; $i -lt $lines.Count; $i++) {
  if ($lines[$i] -match "\[18896\].*Pipeline input text: ") { $start = $i; break }
}
$buf = @()
for ($i = $start; $i -lt $lines.Count; $i++) {
  if ($i -gt $start -and $lines[$i] -match "^\[\d{4}-\d{2}-\d{2} ") { break }
  $buf += $lines[$i]
}
$first = $buf[0] -replace "^.*Pipeline input text: ", ""
$text = $first + "`n" + (($buf | Select-Object -Skip 1) -join "`n")
$text | Set-Content "$out\server-pipeline-input-text.txt" -NoNewline
"server text chars: $($text.Length)" | Write-Output
"tail: " + ($text.Substring($text.Length - 120)) | Write-Output
