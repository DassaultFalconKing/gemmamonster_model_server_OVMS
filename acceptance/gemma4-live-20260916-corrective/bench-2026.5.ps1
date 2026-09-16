# CORRECTIVE LIVE ACCEPTANCE bench harness (2026.5, streaming-based).
# Measures per run: ttft_ms (first content chunk), wall_ms, input/output tokens
# (final usage chunk), tok_s (output/wall_total, comparable to scouting),
# tpot_ms ((wall-ttft)/(out-1)), http_status, finish_reason.
param(
    [string]$Endpoint = "http://127.0.0.1:18091/v3",
    [string]$ModelName = "gemma4-26-heretic",
    [Parameter(Mandatory)][string]$ProfileName,
    [int]$WarmupRuns = 1,
    [int]$MeasuredRuns = 3
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Net.Http
$AccDir = "C:\git\gemma4-upstream-refit-clean-20260915\acceptance\gemma4-live-20260916-corrective"
$CsvPath = Join-Path $AccDir "results.csv"

$BasePara = "Explain the architecture of transformer models in detail, covering attention mechanisms, feed-forward layers, layer normalization, residual connections, and positional encoding. Include mathematical formulations where appropriate. "

function Invoke-StreamRun {
    param([string]$Prompt, [int]$MaxTokens, [string]$SaveSse)
    $bodyObj = @{
        model = $ModelName
        messages = @(@{ role = "user"; content = $Prompt })
        temperature = 0
        max_tokens = $MaxTokens
        stream = $true
        stream_options = @{ include_usage = $true }
    }
    $body = $bodyObj | ConvertTo-Json -Depth 10
    $client = New-Object System.Net.Http.HttpClient
    $client.Timeout = [TimeSpan]::FromSeconds(600)
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $ttft = $null; $inTok = 0; $outTok = 0; $finish = ""; $status = 0
    $sseLines = New-Object Collections.Generic.List[string]
    try {
        $resp = $client.PostAsync("$Endpoint/chat/completions",
            (New-Object System.Net.Http.StringContent($body, [Text.Encoding]::UTF8, "application/json"))).Result
        if ($null -eq $resp) { throw "PostAsync returned null response (connection failed before headers)" }
        $status = [int]$resp.StatusCode
        if (-not $resp.IsSuccessStatusCode) {
            $errBody = $resp.Content.ReadAsStringAsync().Result
            $sw.Stop()
            return @{ http_status = $status; success = $false; error = $errBody;
                wall_ms = $sw.ElapsedMilliseconds; ttft_ms = $null;
                input_tokens = 0; output_tokens = 0; tok_s = 0; tpot_ms = $null; finish_reason = "http_error" }
        }
        $stream = $resp.Content.ReadAsStreamAsync().Result
        $reader = New-Object System.IO.StreamReader($stream)
        while (($line = $reader.ReadLine()) -ne $null) {
            if ($SaveSse) { $sseLines.Add($line) }
            $t = $line.Trim()
            if ($t -eq "" -or $t -eq "data: [DONE]") { if ($t -eq "data: [DONE]") { break }; continue }
            if (-not $t.StartsWith("data:")) { continue }
            $payload = $t.Substring(5).Trim()
            try { $j = $payload | ConvertFrom-Json } catch { continue }
            if ($null -eq $ttft -and $j.choices -and $j.choices.Count -gt 0) {
                $d = $j.choices[0].delta
                if ($d -and (($d.content -and $d.content -ne "") -or $d.tool_calls -or $d.reasoning_content)) {
                    $ttft = $sw.ElapsedMilliseconds
                }
            }
            if ($j.usage -and $j.usage.prompt_tokens) {
                $inTok = [int]$j.usage.prompt_tokens; $outTok = [int]$j.usage.completion_tokens
            }
            if ($j.choices -and $j.choices.Count -gt 0 -and $j.choices[0].finish_reason) {
                $finish = [string]$j.choices[0].finish_reason
            }
        }
        $reader.Close()
        $sw.Stop()
        if ($SaveSse) { $sseLines | Set-Content -Encoding UTF8 $SaveSse }
        $wall = $sw.ElapsedMilliseconds
        $tokS = if ($wall -gt 0 -and $outTok -gt 0) { [math]::Round($outTok / ($wall / 1000.0), 2) } else { 0 }
        $tpot = if ($ttft -ne $null -and $outTok -gt 1) { [math]::Round(($wall - $ttft) / ($outTok - 1), 2) } else { $null }
        return @{ http_status = $status; success = ($status -eq 200 -and $outTok -gt 0); error = $null;
            wall_ms = $wall; ttft_ms = $ttft; input_tokens = $inTok; output_tokens = $outTok;
            tok_s = $tokS; tpot_ms = $tpot; finish_reason = $finish }
    } catch {
        $sw.Stop()
        $lineNo = $_.InvocationInfo.ScriptLineNumber
        $errText = "L$lineNo $($_.FullyQualifiedErrorId): $($_.Exception.Message)"
        return @{ http_status = $status; success = $false; error = $errText;
            wall_ms = $sw.ElapsedMilliseconds; ttft_ms = $ttft;
            input_tokens = $inTok; output_tokens = $outTok; tok_s = 0; tpot_ms = $null; finish_reason = "exception" }
    } finally {
        $client.Dispose()
    }
}

function Get-GpuSnapshot {
    $snap = @{ ws_mb = $null; gpu_util = $null }
    try {
        $p = Get-Process ovms -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($p) { $snap.ws_mb = [math]::Round($p.WS / 1MB, 1) }
    } catch {}
    try {
        $c = Get-Counter "\GPU Engine(*engtype_3D*)\Utilization Percentage" -ErrorAction SilentlyContinue
        if ($c) {
            $vals = $c.CounterSamples | ForEach-Object { $_.CookedValue }
            $snap.gpu_util = [math]::Round(($vals | Measure-Object -Maximum).Maximum, 1)
        }
    } catch {}
    return $snap
}

# Calibrate prompt multipliers against real tokenizer via a probe request.
function Build-Prompt-For-Target {
    param([int]$TargetTokens)
    $mult = [math]::Max(1, [math]::Round($TargetTokens / 60))
    $probe = $BasePara * $mult
    $r = Invoke-StreamRun -Prompt $probe -MaxTokens 8 -SaveSse $null
    if ($r.success -and $r.input_tokens -gt 0) {
        $perRep = $r.input_tokens / $mult
        $mult2 = [math]::Max(1, [math]::Round($TargetTokens / $perRep))
        Write-Host "  calibration: mult=$mult gave $($r.input_tokens) input tokens (perRep=$([math]::Round($perRep,2))); rescaled mult=$mult2"
        return ($BasePara * $mult2)
    }
    Write-Host "  calibration probe failed, using mult=$mult"
    return $probe
}

$shortPrompt = "Write a concise explanation of speculative decoding."
Write-Host "Calibrating MEDIUM (~8K) prompt..."
$mediumPrompt = Build-Prompt-For-Target -TargetTokens 8000
Write-Host "Calibrating LONG (~32K) prompt..."
$longPrompt = Build-Prompt-For-Target -TargetTokens 32000

$workloads = @(
    @{ Name = "short";  Prompt = $shortPrompt },
    @{ Name = "medium8k"; Prompt = $mediumPrompt },
    @{ Name = "long32k";  Prompt = $longPrompt }
)

if (-not (Test-Path $CsvPath)) {
    "profile,workload,run,input_tokens,output_tokens,ttft_ms,wall_ms,tpot_ms,tok_s,http_status,finish_reason,timestamp" | Set-Content -Encoding UTF8 $CsvPath
}

$allRows = @()
foreach ($w in $workloads) {
    Write-Host "=== $($w.Name) (profile $ProfileName) ==="
    $tag = "$ProfileName-$($w.Name)"
    for ($i = 1; $i -le ($WarmupRuns + $MeasuredRuns); $i++) {
        $isWarm = $i -le $WarmupRuns
        $label = if ($isWarm) { "warmup" } else { "run$($i - $WarmupRuns)" }
        $sseFile = if (-not $isWarm -and ($i - $WarmupRuns) -eq 1) { Join-Path $AccDir "streams\$tag-run1.sse.txt" } else { $null }
        Write-Host "  $label ..."
        $r = Invoke-StreamRun -Prompt $w.Prompt -MaxTokens 256 -SaveSse $sseFile
        $ts = [DateTime]::UtcNow.ToString("o")
        if ($r.success) {
            Write-Host ("    OK: in={0} out={1} ttft={2}ms wall={3}ms tpot={4}ms tok/s={5} finish={6}" -f `
                $r.input_tokens, $r.output_tokens, $r.ttft_ms, $r.wall_ms, $r.tpot_ms, $r.tok_s, $r.finish_reason)
        } else {
            Write-Host "    FAILED: $($r.error) status=$($r.http_status)"
        }
        if (-not $isWarm) {
            $row = [pscustomobject]@{
                profile = $ProfileName; workload = $w.Name; run = ($i - $WarmupRuns)
                input_tokens = $r.input_tokens; output_tokens = $r.output_tokens
                ttft_ms = $r.ttft_ms; wall_ms = $r.wall_ms; tpot_ms = $r.tpot_ms; tok_s = $r.tok_s
                http_status = $r.http_status; finish_reason = $r.finish_reason; timestamp = $ts
            }
            $allRows += $row
            ("{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11}" -f $row.profile, $row.workload, $row.run,
                $row.input_tokens, $row.output_tokens, $row.ttft_ms, $row.wall_ms, $row.tpot_ms,
                $row.tok_s, $row.http_status, $row.finish_reason, $row.timestamp) | Add-Content -Encoding UTF8 $CsvPath
        }
        Start-Sleep -Seconds 2
    }
    $g = Get-GpuSnapshot
    Write-Host ("  [snapshot] ovms WS={0}MB gpu3D_util={1}%" -f $g.ws_mb, $g.gpu_util)
    $allRows += [pscustomobject]@{ profile = $ProfileName; workload = $w.Name; run = "snapshot_ws_mb";
        input_tokens = $g.ws_mb; output_tokens = ""; ttft_ms = ""; wall_ms = "";
        tpot_ms = ""; tok_s = ("gpu_util=" + $g.gpu_util); http_status = ""; finish_reason = ""; timestamp = [DateTime]::UtcNow.ToString("o") }
}

$jsonPath = Join-Path $AccDir ("runs-" + $ProfileName + ".json")
$allRows | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $jsonPath
Write-Host "Saved: $CsvPath, $jsonPath"
foreach ($w in @("short","medium8k","long32k")) {
    $s = $allRows | Where-Object { $_.workload -eq $w -and $_.run -is [int] }
    if ($s) {
        $t = $s | Measure-Object -Property tok_s -Average -Minimum -Maximum
        $vals = @($s | ForEach-Object { [double]$_.tok_s })
        $mean = $t.Average; $sd = 0
        if ($vals.Count -gt 1) {
            $sd = [math]::Sqrt((($vals | ForEach-Object { ($_ - $mean) * ($_ - $mean) } | Measure-Object -Sum).Sum) / ($vals.Count - 1))
        }
        Write-Host ("  {0}: mean={1} min={2} max={3} stddev={4} | runs: {5}" -f $w,
            [math]::Round($mean,2), $t.Minimum, $t.Maximum, [math]::Round($sd,2), (($vals | ForEach-Object { $_.ToString() }) -join "/"))
    }
}
