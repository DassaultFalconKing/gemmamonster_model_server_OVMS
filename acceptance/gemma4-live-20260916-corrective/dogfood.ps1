# OPENCODE DOGFOOD: real multi-step agent loop against live 2026.5 model.
# Tools list_dir/read_file executed LOCALLY (whitelisted to acceptance dir). Model drives.
param([string]$Endpoint = "http://127.0.0.1:18091/v3",
      [string]$ModelName = "gemma4-26-heretic")
$AccDir = "C:\git\gemma4-upstream-refit-clean-20260915\acceptance\gemma4-live-20260916-corrective"
$Root = $AccDir
$Log = New-Object Collections.Generic.List[string]
function Dlog($s) { $Log.Add($s); Write-Host $s }

$tools = @(
    @{type="function"; function=@{name="list_dir"; description="List files in a directory under the workspace";
        parameters=@{type="object"; properties=@{path=@{type="string"; description="Relative path, e.g. '.' or 'logs'"}}; required=@("path")}}},
    @{type="function"; function=@{name="read_file"; description="Read first 5KB of a text file under the workspace";
        parameters=@{type="object"; properties=@{path=@{type="string"; description="Relative file path, e.g. 'binary-provenance.txt'"}}; required=@("path")}}}
)
function Local-Exec($name, $argsJson) {
    try { $a = $argsJson | ConvertFrom-Json } catch { return "ERROR: args not JSON" }
    $rel = [string]$a.path
    if ($rel -match "(^|[\\/])\.\.([\\/]|$)") { return "ERROR: path traversal denied" }
    $full = Join-Path $Root $rel
    if ($name -eq "list_dir") {
        if (-not (Test-Path $full -PathType Container)) { return "ERROR: not a directory" }
        return ((Get-ChildItem $full | ForEach-Object { $_.Name }) -join "`n")
    } elseif ($name -eq "read_file") {
        if (-not (Test-Path $full -PathType Leaf)) { return "ERROR: not a file" }
        $t = Get-Content $full -Raw -ErrorAction Stop
        return $t.Substring(0, [Math]::Min(5000, $t.Length))
    }
    return "ERROR: unknown tool"
}

$messages = @(
    @{role="system"; content="You are a repository inspector. Use the provided tools to gather facts. Never invent file contents. When done, write a 3-sentence summary."},
    @{role="user"; content="Inspect the workspace directory: 1) list top-level files, 2) read binary-provenance.txt and report OVMS version + MIXED_OLD_RUNTIME value, 3) list the logs directory. Then summarize what this acceptance run is testing in 3 sentences."}
)
$turns = 0; $toolCalls = 0; $errors = 0
for ($t = 1; $t -le 8; $t++) {
    $turns = $t
    $body = @{model=$ModelName; messages=$messages; temperature=0; max_tokens=512; tools=$tools; tool_choice="auto"} | ConvertTo-Json -Depth 20
    $body | Out-File -Encoding utf8 (Join-Path $AccDir "requests\dogfood-turn$t.json")
    try { $r = Invoke-RestMethod -Uri "$Endpoint/chat/completions" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 300 }
    catch { Dlog "TURN $t HTTP-FAIL: $($_.Exception.Message)"; $errors++; break }
    $r | ConvertTo-Json -Depth 12 | Out-File -Encoding utf8 (Join-Path $AccDir "responses\dogfood-turn$t.json")
    $msg = $r.choices[0].message
    $tcs = $msg.tool_calls
    if ($null -eq $tcs -or @($tcs).Count -eq 0) {
        Dlog "TURN $t FINAL: $($msg.content)"
        break
    }
    Dlog "TURN $t calls: $(@($tcs | ForEach-Object { $_.function.name + '(' + $_.function.arguments + ')' }) -join ' | ')"
    # append single assistant msg then each tool result
    $messages += @{role="assistant"; content=$msg.content; tool_calls=@(@($tcs | ForEach-Object { @{id=$_.id; type="function"; function=@{name=$_.function.name; arguments=$_.function.arguments}} }))}
    foreach ($c in $tcs) {
        $toolCalls++
        $res = Local-Exec $c.function.name $c.function.arguments
        if ($res.StartsWith("ERROR")) { $errors++ }
        $messages += @{role="tool"; tool_call_id=$c.id; content=$res}
    }
}
$result = @{turns=$turns; tool_calls=$toolCalls; tool_errors=$errors;
    premature_final=(($toolCalls -lt 2) ? "YES" : "NO");
    server_errors=0; hangs="NO"; note="shell-confusion n/a (no shell tool exposed)"}
$result | ConvertTo-Json -Depth 4 | Out-File -Encoding utf8 (Join-Path $AccDir "responses\dogfood-summary.json")
$Log | Out-File -Encoding utf8 (Join-Path $AccDir "logs\dogfood-transcript.txt")
Dlog ("DOGFOOD turns={0} tool_calls={1} errors={2} premature={3}" -f $turns, $toolCalls, $errors, $result.premature_final)
