# Short-only control: 1 warmup + 5 measured SHORT runs, streaming.
param([string]$Endpoint = "http://127.0.0.1:18091/v3",
      [string]$ModelName = "gemma4-26-heretic",
      [string]$Tag = "control")
Add-Type -AssemblyName System.Net.Http
$Prompt = "Write a concise explanation of speculative decoding."
function Run-One {
    $body = @{model=$ModelName; messages=@(@{role="user"; content=$Prompt});
        temperature=0; max_tokens=256; stream=$true;
        stream_options=@{include_usage=$true}} | ConvertTo-Json -Depth 10
    $client = New-Object System.Net.Http.HttpClient
    $client.Timeout = [TimeSpan]::FromSeconds(300)
    $sw = [Diagnostics.Stopwatch]::StartNew()
    try {
        $resp = $client.PostAsync("$Endpoint/chat/completions",
            (New-Object System.Net.Http.StringContent($body,[Text.Encoding]::UTF8,"application/json"))).Result
        if ($null -eq $resp) { throw "null response" }
        if (-not $resp.IsSuccessStatusCode) { throw "HTTP $([int]$resp.StatusCode)" }
        $reader = New-Object System.IO.StreamReader($resp.Content.ReadAsStreamAsync().Result)
        $ttft=$null; $inT=0; $outT=0; $fin=""
        while (($line=$reader.ReadLine()) -ne $null) {
            $t=$line.Trim(); if ($t -eq "" ) { continue }; if ($t -eq "data: [DONE]") { break }
            if (-not $t.StartsWith("data:")) { continue }
            $j=($t.Substring(5).Trim() | ConvertFrom-Json)
            if ($null -eq $ttft -and $j.choices.Count -gt 0) { $d=$j.choices[0].delta
                if ($d -and (($d.content -and $d.content -ne "") -or $d.tool_calls)) { $ttft=$sw.ElapsedMilliseconds } }
            if ($j.usage -and $j.usage.prompt_tokens) { $inT=[int]$j.usage.prompt_tokens; $outT=[int]$j.usage.completion_tokens }
            if ($j.choices.Count -gt 0 -and $j.choices[0].finish_reason) { $fin=[string]$j.choices[0].finish_reason }
        }
        $reader.Close(); $sw.Stop(); $wall=$sw.ElapsedMilliseconds
        return "OK in=$inT out=$outT ttft=${ttft}ms wall=${wall}ms toks=$([math]::Round($outT/($wall/1000.0),2)) finish=$fin"
    } catch { $sw.Stop(); return "FAIL L$($_.InvocationInfo.ScriptLineNumber): $($_.Exception.Message)" }
    finally { $client.Dispose() }
}
Write-Host "warmup: $(Run-One) [$Tag]"
for ($i=1; $i -le 5; $i++) { Write-Host "run${i}: $(Run-One) [$Tag]"; Start-Sleep -Seconds 2 }
