# Repeated-prefix test: long OpenCode-style history, 3 sequential turns, same prefix.
# Signal = TTFT per turn (prefix-cache reuse => turn2/turn3 TTFT << turn1).
param([string]$Endpoint = "http://127.0.0.1:18091/v3",
      [string]$ModelName = "gemma4-26-heretic")
Add-Type -AssemblyName System.Net.Http
$AccDir = "C:\git\gemma4-upstream-refit-clean-20260915\acceptance\gemma4-live-20260916-corrective"

$para = "Explain the architecture of transformer models in detail, covering attention mechanisms, feed-forward layers, layer normalization, residual connections, and positional encoding. Include mathematical formulations where appropriate. "
$historyBlock = $para * 235  # ~8K tokens, stands in for long tool-loop history

$history = @(
    @{role="user"; content="We need to refactor the request scheduler. Context: $historyBlock"},
    @{role="assistant"; content="Understood. I reviewed the scheduler context. Key areas: batching, timeouts, retry policy. Tell me which file to open first."},
    @{role="user"; content="Open the scheduler module and list its public functions. More context: $historyBlock"},
    @{role="assistant"; content="The scheduler exposes: enqueue, dequeue, reprioritize, drain. enqueue takes (task, priority); drain blocks until empty. Which one do we change?"}
)

function Turn {
    param([array]$Messages, [string]$Tag)
    $body = @{model=$ModelName; messages=$Messages; temperature=0; max_tokens=64;
        stream=$true; stream_options=@{include_usage=$true}} | ConvertTo-Json -Depth 12
    $body | Out-File -Encoding utf8 (Join-Path $AccDir "requests\prefix-$Tag.json")
    $client = New-Object System.Net.Http.HttpClient
    $client.Timeout = [TimeSpan]::FromSeconds(300)
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $sse = New-Object Collections.Generic.List[string]
    try {
        $resp = $client.PostAsync("$Endpoint/chat/completions",
            (New-Object System.Net.Http.StringContent($body,[Text.Encoding]::UTF8,"application/json"))).Result
        $reader = New-Object System.IO.StreamReader($resp.Content.ReadAsStreamAsync().Result)
        $ttft=$null; $inT=0; $outT=0; $text=""
        while (($line=$reader.ReadLine()) -ne $null) {
            $sse.Add($line); $t=$line.Trim()
            if ($t -eq "" ) { continue }; if ($t -eq "data: [DONE]") { break }
            if (-not $t.StartsWith("data:")) { continue }
            $j=($t.Substring(5).Trim() | ConvertFrom-Json)
            if ($j.choices.Count -gt 0) { $d=$j.choices[0].delta
                if ($null -eq $ttft -and $d -and $d.content -and $d.content -ne "") { $ttft=$sw.ElapsedMilliseconds }
                if ($d -and $d.content) { $text+=$d.content } }
            if ($j.usage -and $j.usage.prompt_tokens) { $inT=[int]$j.usage.prompt_tokens; $outT=[int]$j.usage.completion_tokens }
        }
        $reader.Close(); $sw.Stop()
        $sse | Set-Content -Encoding UTF8 (Join-Path $AccDir "streams\prefix-$Tag.sse.txt")
        (@{tag=$Tag; input_tokens=$inT; output_tokens=$outT; ttft_ms=$ttft; wall_ms=$sw.ElapsedMilliseconds;
           text=$text} | ConvertTo-Json -Depth 5) | Out-File -Encoding utf8 (Join-Path $AccDir "responses\prefix-$Tag.json")
        return "turn=$Tag in=$inT out=$outT ttft=${ttft}ms wall=$($sw.ElapsedMilliseconds)ms reply=$($text.Substring(0,[Math]::Min(80,$text.Length)))"
    } catch { $sw.Stop(); return "turn=$Tag FAIL: $($_.Exception.Message)" }
    finally { $client.Dispose() }
}

$m1 = $history + @(@{role="user"; content="Summarize the refactor plan in one sentence."})
Write-Host (Turn $m1 "turn1")
Start-Sleep -Seconds 2
$m2 = $m1 + @(@{role="assistant"; content="Plan: split enqueue into validate plus schedule, then add bounded retries."}) + @(@{role="user"; content="Now state the biggest risk in one sentence."})
Write-Host (Turn $m2 "turn2")
Start-Sleep -Seconds 2
$m3 = $m2 + @(@{role="assistant"; content="Biggest risk: retry storms under partial failure."}) + @(@{role="user"; content="Finally, name the first file to edit."})
Write-Host (Turn $m3 "turn3")
