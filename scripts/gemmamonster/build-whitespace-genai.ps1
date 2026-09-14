param([string]$RuntimeRoot = 'C:\g54r2')
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$genai = Join-Path $RuntimeRoot 'openvino_genai_src'
$xgrammar = Join-Path $RuntimeRoot 'openvino_genai_build/_deps/xgrammar-src'
$genaiSha = '7ea2546852a382cd16bd22dea0cfad2db70ed744'
$xgrammarSha = '9aa840b6d16abf094f3e8e2ac9c10465b77656c9'
function Run-Git([string]$Root, [string[]]$Arguments) {
    & git -C $Root @Arguments
    if ($LASTEXITCODE -ne 0) { throw "git failed in $Root" }
}
function Apply-Patch([string]$Root, [string]$Name) {
    $patch = Join-Path $PSScriptRoot "patches/$Name"
    & git -C $Root apply --reverse --check $patch 2>$null
    if ($LASTEXITCODE -eq 0) { return }
    Run-Git $Root @('apply', '--check', $patch)
    Run-Git $Root @('apply', $patch)
}
if (-not (Test-Path (Join-Path $xgrammar '.git'))) {
    & git clone --no-checkout https://github.com/mlc-ai/xgrammar.git $xgrammar
    if ($LASTEXITCODE -ne 0) { throw 'XGrammar clone failed' }
    Run-Git $xgrammar @('checkout', '--detach', $xgrammarSha)
}
foreach ($entry in @(@($genai,$genaiSha), @($xgrammar,$xgrammarSha))) {
    if ((& git -C $entry[0] rev-parse HEAD) -ne $entry[1]) {
        throw "Dependency SHA mismatch: $($entry[0]); check out $($entry[1]) first"
    }
    Run-Git $entry[0] @('submodule', 'update', '--init', '--recursive')
}
Apply-Patch $genai 'genai-gemma4-bounded-whitespace.patch'
Apply-Patch $xgrammar 'xgrammar-subproject-install.patch'
Push-Location $repo
try {
    & "$PSScriptRoot/Enter-GemmamonsterEnv.ps1" -RequireRuntimeRoot | Out-Null
    $build = Join-Path $RuntimeRoot 'openvino_genai_build'
    $runtime = Join-Path $RuntimeRoot 'openvino'
    $cmdFile = Join-Path $RuntimeRoot 'build-whitespace-genai.cmd'
    $commands = @"
@echo off
call "$runtime\setupvars.bat"
if errorlevel 1 exit /b 1
cmake -S "$genai" -B "$build" -G "Visual Studio 17 2022" -A x64 -DCMAKE_BUILD_TYPE=Release -DBUILD_TOKENIZERS=OFF -DENABLE_SAMPLES=OFF -DENABLE_TOOLS=OFF -DENABLE_TESTS=OFF -DENABLE_XGRAMMAR=ON "-DFETCHCONTENT_SOURCE_DIR_XGRAMMAR=$xgrammar"
if errorlevel 1 exit /b 1
cmake --build "$build" --config Release --parallel 4
if errorlevel 1 exit /b 1
cmake --install "$build" --config Release --prefix "$runtime"
"@
    [IO.File]::WriteAllText($cmdFile, $commands, [Text.UTF8Encoding]::new($false))
    & cmd.exe /d /c $cmdFile
    if ($LASTEXITCODE -ne 0) { throw "GenAI build/install failed: $LASTEXITCODE" }
    $provenance = [ordered]@{
        genai_base = $genaiSha
        xgrammar_head = $xgrammarSha
        xgrammar_submodules = @(& git -C $xgrammar submodule status --recursive)
        patches = @(Get-ChildItem "$PSScriptRoot/patches/*.patch" | Get-FileHash -Algorithm SHA256 | Select-Object Path,Hash)
        installed_genai = Get-FileHash "$runtime/runtime/bin/intel64/Release/openvino_genai.dll" -Algorithm SHA256 | Select-Object Path,Hash
    }
    $provenance | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $RuntimeRoot 'whitespace-dependencies.json')
} finally { Pop-Location }
