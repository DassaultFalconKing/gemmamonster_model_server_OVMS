$ev = "C:\Users\testc\AppData\Local\Temp\opencode\gemmamonster-leakage-20260914"
$dd = "$ev\deep-dive"
foreach ($sub in @("turn-03-trace", "turn-04-trace")) {
  $raw = Get-Content "$dd\$sub\server-window.log" -Raw
  $re = [regex]'parseChunk\[PROCESSING_PHASE=(\w+)\] called with (\d+) tokens, text="(.*?)", finish_reason=(\d+), token IDs=\[(.*?)\]'
  $opts = [System.Text.RegularExpressions.RegexOptions]::Singleline
  $ms = [regex]::Matches($raw, $re.ToString(), $opts)
  $out = @()
  foreach ($m in $ms) {
    $txt = $m.Groups[3].Value -replace "`r", '\r' -replace "`n", '\n'
    $out += ("{0} ntok={1} fin={2} text=[{3}] ids=[{4}]" -f $m.Groups[1].Value, $m.Groups[2].Value, $m.Groups[4].Value, $txt, $m.Groups[5].Value)
  }
  $out | Set-Content "$dd\$sub\parsechunks-parsed.txt"
  Write-Output ("=== " + $sub + " chunks=" + $out.Count + " ===")
  $out | ForEach-Object { Write-Output $_ }
}
