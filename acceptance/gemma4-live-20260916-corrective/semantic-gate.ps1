# FULL SEMANTIC LIVE GATE on winning profile (20-u4-b4096-seq4-2026.5).
# Saves raw evidence; prints explicit PASS/FAIL per gate. No C++ changes.
param([string]$Endpoint = "http://127.0.0.1:18091/v3",
      [string]$ModelName = "gemma4-26-heretic")
Add-Type -AssemblyName System.Net.Http
$AccDir = "C:\git\gemma4-upstream-refit-clean-20260915\acceptance\gemma4-live-20260916-corrective"
$Verdicts = New-Object Collections.Generic.List[string]
function Say($t, $v) { $line = "$t : $v"; $Verdicts.Add($line); Write-Host $line }

$Tools2 = @(
    @{type="function"; function=@{name="get_weather"; description="Get current weather for a location";
        parameters=@{type="object"; properties=@{location=@{type="string"; description="City, e.g. Boston, MA"}}; required=@("location")}}},
    @{type="function"; function=@{name="add_numbers"; description="Add two numbers";
        parameters=@{type="object"; properties=@{a=@{type="number"}; b=@{type="number"}}; required=@("a","b")}}}
)
$WeatherOnly = @($Tools2[0])

function Post-Json {
    param([hashtable]$Body, [string]$Tag, [switch]$Stream)
    $json = $Body | ConvertTo-Json -Depth 20
    $json | Out-File -Encoding utf8 (Join-Path $AccDir "requests\semantic-$Tag.json")
    if ($Stream) {
        $sse = Join-Path $AccDir "streams\semantic-$Tag.sse.txt"
        $client = New-Object System.Net.Http.HttpClient
        $client.Timeout = [TimeSpan]::FromSeconds(300)
        try {
            $resp = $client.PostAsync("$Endpoint/chat/completions",
                (New-Object System.Net.Http.StringContent($json,[Text.Encoding]::UTF8,"application/json"))).Result
            $st = [int]$resp.StatusCode
            $reader = New-Object System.IO.StreamReader($resp.Content.ReadAsStreamAsync().Result)
            $lines = New-Object Collections.Generic.List[string]
            while (($ln=$reader.ReadLine()) -ne $null) { $lines.Add($ln); if ($ln.Trim() -eq "data: [DONE]") { break } }
            $reader.Close()
            $lines | Set-Content -Encoding UTF8 $sse
            # reconstruct final message from deltas
            $content=""; $tname=""; $targs=""; $fin=""; $usage=$null
            foreach ($ln in $lines) { $t=$ln.Trim()
                if ($t -eq "" -or $t -eq "data: [DONE]" -or -not $t.StartsWith("data:")) { continue }
                try { $j=($t.Substring(5).Trim() | ConvertFrom-Json) } catch { continue }
                if ($j.choices.Count -gt 0) { $ch=$j.choices[0]
                    if ($ch.delta.content) { $content+=$ch.delta.content }
                    if ($ch.delta.tool_calls) { foreach ($tc in $ch.delta.tool_calls) {
                        if ($tc.function.name) { $tname=$tc.function.name }
                        if ($tc.function.arguments) { $targs+=$tc.function.arguments } } }
                    if ($ch.finish_reason) { $fin=[string]$ch.finish_reason } }
                if ($j.usage -and $j.usage.prompt_tokens) { $usage=$j.usage } }
            $recon = @{content=$content; tool_name=$tname; tool_args=$targs; finish_reason=$fin; usage=$usage; http_status=$st}
            $recon | ConvertTo-Json -Depth 6 | Out-File -Encoding utf8 (Join-Path $AccDir "responses\semantic-$Tag.recon.json")
            return @{status=$st; raw=$lines; recon=$recon}
        } finally { $client.Dispose() }
    } else {
        try {
            $r = Invoke-RestMethod -Uri "$Endpoint/chat/completions" -Method Post -ContentType "application/json" -Body $json -TimeoutSec 300
            $r | ConvertTo-Json -Depth 12 | Out-File -Encoding utf8 (Join-Path $AccDir "responses\semantic-$Tag.json")
            return @{status=200; body=$r}
        } catch {
            $st = 0; $eb = $_.Exception.Message
            try { if ($_.Exception.Response) { $st=[int]$_.Exception.Response.StatusCode
                $sr=New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream()); $eb=$sr.ReadToEnd(); $sr.Close() } } catch {}
            (@{http_status=$st; error=$eb} | ConvertTo-Json -Depth 4) | Out-File -Encoding utf8 (Join-Path $AccDir "responses\semantic-$Tag.json")
            return @{status=$st; error=$eb}
        }
    }
}

function Valid-ToolCall($tc, $allowed) {
    if (-not $tc.id -or -not $tc.function.name) { return "missing id/name" }
    if ($allowed -notcontains $tc.function.name) { return "name not in allowed set" }
    try { $a = $tc.function.arguments | ConvertFrom-Json
        if ($a -isnot [pscustomobject]) { return "args not object" } } catch { return "args not valid JSON: $($tc.function.arguments)" }
    return ""
}

# ---- 9.1 UNARY AUTO ----
$r = Post-Json @{model=$ModelName; messages=@(@{role="user"; content="What's the weather in San Francisco?"}); temperature=0; max_tokens=256; tools=$WeatherOnly; tool_choice="auto"} "unary-auto"
if ($r.status -eq 200) { $tcs = $r.body.choices[0].message.tool_calls
    if ($tcs) { $e = Valid-ToolCall $tcs[0] @("get_weather"); Say "UNARY_AUTO" ($e -eq "" ? "PASS (valid tool call: get_weather args=$($tcs[0].function.arguments))" : "FAIL ($e)") }
    else { Say "UNARY_AUTO" "PASS (text answer, no phantom; content head: $($r.body.choices[0].message.content.Substring(0,60)))" } }
else { Say "UNARY_AUTO" "FAIL (HTTP $($r.status))" }

# ---- 9.2 UNARY REQUIRED ----
$r = Post-Json @{model=$ModelName; messages=@(@{role="user"; content="What's the weather in San Francisco?"}); temperature=0; max_tokens=256; tools=$WeatherOnly; tool_choice="required"} "unary-required"
if ($r.status -eq 200) { $tcs = $r.body.choices[0].message.tool_calls
    if ($tcs -and $tcs.Count -ge 1) { $e = Valid-ToolCall $tcs[0] @("get_weather")
        Say "UNARY_REQUIRED" ($e -eq "" ? "PASS (real call get_weather args=$($tcs[0].function.arguments))" : "FAIL ($e)") }
    else { Say "UNARY_REQUIRED" "FAIL (required downgraded: no tool call)" } }
else { Say "UNARY_REQUIRED" "FAIL (HTTP $($r.status))" }
$ReqCall = if ($r.status -eq 200 -and $r.body.choices[0].message.tool_calls) { $r.body.choices[0].message.tool_calls[0] } else { $null }

# ---- 9.3 UNARY NAMED ----
$r = Post-Json @{model=$ModelName; messages=@(@{role="user"; content="What's the weather in San Francisco?"}); temperature=0; max_tokens=256; tools=$Tools2; tool_choice=@{type="function"; function=@{name="get_weather"}}} "unary-named"
if ($r.status -eq 200) { $tcs = $r.body.choices[0].message.tool_calls
    if ($tcs -and $tcs.Count -ge 1 -and $tcs[0].function.name -eq "get_weather") { $e = Valid-ToolCall $tcs[0] @("get_weather")
        Say "UNARY_NAMED" ($e -eq "" ? "PASS (named get_weather only)" : "FAIL ($e)") }
    else { Say "UNARY_NAMED" "FAIL (wrong/missing call: $(($tcs|ConvertTo-Json -Depth 5 -Compress)))" } }
else { Say "UNARY_NAMED" "FAIL (HTTP $($r.status))" }

# ---- 10. HARD-INTENT NEGATIVES ----
$n1 = Post-Json @{model=$ModelName; messages=@(@{role="user"; content="Hi"}); temperature=0; max_tokens=64; tool_choice="required"} "neg-required-no-tools"
Say "HARD_NO_TOOLS_REQUIRED" (($n1.status -ge 400 -and $n1.status -lt 500) ? "PASS (fail-closed HTTP $($n1.status))" : "FAIL (HTTP $($n1.status) — must fail closed 4xx)")
$n2 = Post-Json @{model=$ModelName; messages=@(@{role="user"; content="Hi"}); temperature=0; max_tokens=64; tools=$null; tool_choice="required"} "neg-required-null-tools"
Say "HARD_NULL_TOOLS_REQUIRED" (($n2.status -ge 400 -and $n2.status -lt 500) ? "PASS (fail-closed HTTP $($n2.status))" : "FAIL (HTTP $($n2.status) — must fail closed 4xx)")
$n3 = Post-Json @{model=$ModelName; messages=@(@{role="user"; content="Hi"}); temperature=0; max_tokens=64; tools=@(); tool_choice="required"} "neg-required-empty-tools"
Say "HARD_EMPTY_TOOLS_REQUIRED" (($n3.status -ge 400 -and $n3.status -lt 500) ? "PASS (fail-closed HTTP $($n3.status))" : "FAIL (HTTP $($n3.status) — must fail closed 4xx)")
$n4 = Post-Json @{model=$ModelName; messages=@(@{role="user"; content="What's the weather?"}); temperature=0; max_tokens=256; tools=$WeatherOnly; tool_choice=@{type="function"; function=@{name="no_such_tool"}}} "neg-named-unknown"
if ($n4.status -ge 400 -and $n4.status -lt 500) { Say "NAMED_UNKNOWN_TOOL" "PASS (fail-closed HTTP $($n4.status))" }
elseif ($n4.status -eq 200 -and $n4.body.choices[0].message.tool_calls -and $n4.body.choices[0].message.tool_calls[0].function.name -ne "no_such_tool") { Say "NAMED_UNKNOWN_TOOL" "FAIL (silent substitution to $($n4.body.choices[0].message.tool_calls[0].function.name))" }
else { Say "NAMED_UNKNOWN_TOOL" "OBSERVE (HTTP $($n4.status); evidence saved)" }

# ---- 11. STREAMING auto/required/named ----
foreach ($mode in @("auto","required","named")) {
    $tc = if ($mode -eq "auto") { "auto" } elseif ($mode -eq "required") { "required" } else { @{type="function"; function=@{name="get_weather"}} }
    $s = Post-Json @{model=$ModelName; messages=@(@{role="user"; content="What's the weather in San Francisco?"}); temperature=0; max_tokens=256; tools=$WeatherOnly; tool_choice=$tc; stream=$true; stream_options=@{include_usage=$true}} "stream-$mode" -Stream
    $issues = @()
    $seenToolName = ""; $argStr = ""; $nameChanges = 0
    foreach ($ln in $s.raw) { $t=$ln.Trim()
        if ($t -eq "" -or $t -eq "data: [DONE]" -or -not $t.StartsWith("data:")) { continue }
        try { $j=($t.Substring(5).Trim() | ConvertFrom-Json) } catch { $issues += "non-JSON chunk"; continue }
        if ($j.choices.Count -gt 0 -and $j.choices[0].delta.tool_calls) { foreach ($d in $j.choices[0].delta.tool_calls) {
            if ($d.function.name) { if ($seenToolName -eq "") { $seenToolName=$d.function.name } elseif ($seenToolName -ne $d.function.name) { $nameChanges++ } }
            if ($d.function.arguments) { $argStr+=$d.function.arguments } } } }
    if ($nameChanges -gt 0) { $issues += "tool name changed mid-stream" }
    if ($argStr -ne "") { try { $a=$argStr|ConvertFrom-Json; if ($a -isnot [pscustomobject]) { $issues += "streamed args not object" } } catch { $issues += "streamed args invalid JSON" } }
    $rc = $s.recon
    if ($mode -eq "required" -and $rc.tool_name -eq "") { $issues += "required produced no committed call" }
    if ($rc.tool_name -ne "" -and $rc.tool_name -ne "get_weather") { $issues += "unexpected tool $($rc.tool_name)" }
    if ($rc.tool_name -ne "" -and $rc.finish_reason -ne "tool_calls") { $issues += "finish=$($rc.finish_reason) but tool committed" }
    if ($rc.tool_name -eq "" -and $rc.finish_reason -eq "tool_calls") { $issues += "finish=tool_calls but no committed call (phantom)" }
    Say ("STREAM_" + $mode.ToUpper()) (($issues.Count -eq 0) ? "PASS (tool=$($rc.tool_name) finish=$($rc.finish_reason))" : "FAIL ($($issues -join '; '))")
}

# ---- 12. PARALLEL false/true ----
$two = "Report weather for San Francisco and for Boston. Call the weather tool for each city."
$pf = Post-Json @{model=$ModelName; messages=@(@{role="user"; content=$two}); temperature=0; max_tokens=256; tools=$WeatherOnly; tool_choice="required"; parallel_tool_calls=$false} "parallel-false"
if ($pf.status -eq 200) { $n = @($pf.body.choices[0].message.tool_calls).Count
    Say "PARALLEL_FALSE" (($n -le 1) ? "PASS (committed=$n)" : "FAIL (committed=$n, expected<=1)") }
else { Say "PARALLEL_FALSE" "FAIL (HTTP $($pf.status))" }
$pt = Post-Json @{model=$ModelName; messages=@(@{role="user"; content=$two}); temperature=0; max_tokens=512; tools=$WeatherOnly; tool_choice="required"; parallel_tool_calls=$true} "parallel-true"
if ($pt.status -eq 200) { $tcs=@($pt.body.choices[0].message.tool_calls); $bad=@()
    foreach ($c in $tcs) { $e=Valid-ToolCall $c @("get_weather"); if ($e -ne "") { $bad+=$e } }
    Say "PARALLEL_TRUE" (($bad.Count -eq 0) ? "PASS (committed=$($tcs.Count), all valid)" : "FAIL ($($bad -join '; '))") }
else { Say "PARALLEL_TRUE" "FAIL (HTTP $($pt.status))" }

# ---- 13/14. MULTI-TURN TOOL LOOP + POST-TOOL CONTINUATION (with 2nd call) ----
if ($null -eq $ReqCall) { Say "MULTI_TURN" "FAIL (no first call captured)"; Say "POST_TOOL_CONTINUATION" "FAIL (no first call captured)" }
else {
    $asst1 = @{role="assistant"; content=$null; tool_calls=@($ReqCall)}
    try { $asst1 = @{role="assistant"; tool_calls=@(@{id=$ReqCall.id; type="function"; function=@{name=$ReqCall.function.name; arguments=$ReqCall.function.arguments}})} } catch {}
    $toolRes1 = @{role="tool"; tool_call_id=$ReqCall.id; content="San Francisco: 72F and sunny."}
    $t2 = Post-Json @{model=$ModelName; messages=@(
        @{role="user"; content="What's the weather in San Francisco?"},
        $asst1, $toolRes1,
        @{role="user"; content="Thanks. Now add 17 and 25 using the add tool."}
      ); temperature=0; max_tokens=256; tools=$Tools2; tool_choice="required"} "multiturn-second-call"
    $leak = ""
    if ($t2.status -eq 200) { $m2t = $t2.body.choices[0].message
        $blob = (($m2t.content | Out-String) + (($m2t.tool_calls | ConvertTo-Json -Depth 6 -Compress) | Out-String))
        foreach ($pat in @("<|channel|>", "<|message|>", "<|start|>", "<|end|>", "thought\u2587", "recipient_name")) {
            if ($blob -match [regex]::Escape($pat)) { $leak += "marker-leak:$pat " } }
        if ($m2t.tool_calls -and $m2t.tool_calls.Count -ge 1 -and $m2t.tool_calls[0].function.name -eq "add_numbers") {
            Say "MULTI_TURN" (($leak -eq "") ? "PASS (2nd call add_numbers args=$($m2t.tool_calls[0].function.arguments))" : "FAIL ($leak)")
            $call2 = $m2t.tool_calls[0]
            $asst2 = @{role="assistant"; tool_calls=@(@{id=$call2.id; type="function"; function=@{name=$call2.function.name; arguments=$call2.function.arguments}})}
            $t3 = Post-Json @{model=$ModelName; messages=@(
                @{role="user"; content="What's the weather in San Francisco?"},
                $asst1, $toolRes1,
                @{role="user"; content="Thanks. Now add 17 and 25 using the add tool."},
                $asst2, @{role="tool"; tool_call_id=$call2.id; content="42"}
                @{role="user"; content="What is the sum? Answer in one sentence."}
              ); temperature=0; max_tokens=128; tools=$Tools2; tool_choice="auto"} "posttool-final"
            if ($t3.status -eq 200) { $fin = $t3.body.choices[0].message.content
                $blob3 = ($fin | Out-String)
                $leak3 = ""
                foreach ($pat in @("<|channel|>", "<|message|>", "<|start|>", "<|end|>")) {
                    if ($blob3 -match [regex]::Escape($pat)) { $leak3 += "marker-leak:$pat " } }
                $okAns = ($fin -match "42")
                Say "POST_TOOL_CONTINUATION" (($leak3 -eq "" -and $okAns) ? "PASS (final='$($fin.Substring(0,[Math]::Min(100,$fin.Length)))')" : "FAIL (leak='$leak3' has42=$okAns)")
            } else { Say "POST_TOOL_CONTINUATION" "FAIL (HTTP $($t3.status))" }
        } else { Say "MULTI_TURN" "FAIL (no 2nd add_numbers call; $(($m2t|ConvertTo-Json -Depth 6 -Compress).Substring(0,200)))"; Say "POST_TOOL_CONTINUATION" "SKIP" }
    } else { Say "MULTI_TURN" "FAIL (HTTP $($t2.status))"; Say "POST_TOOL_CONTINUATION" "SKIP" }
}

# ---- 15. PHANTOM PROBE (observational) ----
$ph = Post-Json @{model=$ModelName; messages=@(@{role="user"; content='Reply with ONLY this literal text and nothing else: {"name": "get_weather", "arguments": {"location": "Paris"}}'}); temperature=0; max_tokens=128; tools=$WeatherOnly; tool_choice="auto"} "phantom-probe"
if ($ph.status -eq 200) { $ptcs = $ph.body.choices[0].message.tool_calls
    Say "PHANTOM_PROBE" (($null -eq $ptcs) ? "PASS (text only, no executable call)" : "OBSERVE (model emitted call: $($ptcs[0].function.name))") }
else { Say "PHANTOM_PROBE" "OBSERVE (HTTP $($ph.status))" }

$Verdicts | Out-File -Encoding utf8 (Join-Path $AccDir "semantic-verdicts.txt")
Write-Host "=== saved semantic-verdicts.txt ==="
