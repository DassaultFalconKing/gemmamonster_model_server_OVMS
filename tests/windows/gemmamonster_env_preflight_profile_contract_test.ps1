$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$preflightPath = Join-Path $repoRoot 'scripts\gemmamonster\Enter-GemmamonsterEnv.ps1'
if (-not (Test-Path -LiteralPath $preflightPath -PathType Leaf)) {
    throw "Missing preflight script: $preflightPath"
}

$text = Get-Content -LiteralPath $preflightPath -Raw -Encoding UTF8

function Assert-Contains([string]$Pattern, [string]$Description) {
    if ($text -notmatch $Pattern) {
        throw "Missing preflight profile contract: $Description"
    }
}

# Default behavior remains the existing isolated maintainer-RC2 profile.
Assert-Contains "ValidateSet\([^\)]*maintainer-rc2[^\)]*rc1-parity[^\)]*\)" 'ToolchainProfile accepts maintainer-rc2 and rc1-parity'
Assert-Contains "ToolchainProfile\s*=\s*'maintainer-rc2'" 'maintainer-rc2 remains the default profile'

# Repository declaration and active Bazel are deliberately separate concepts.
# Current acceptance uses 6.4.0 to support the installed VC layout with vcpkg.
Assert-Contains "DECLARED_BAZEL_VERSION\s*=\s*'6\.4\.0'" 'profile data records repository Bazel declaration 6.4.0'
Assert-Contains "'maintainer-rc2'\s*=\s*\[ordered\]@\{\s*ACTIVE_BAZEL_VERSION\s*=\s*'6\.4\.0'" 'maintainer-rc2 resolves active Bazel 6.4.0'
Assert-Contains "ACTIVE_BAZEL_VERSION\s*=\s*'6\.4\.0'" 'rc1-parity resolves active Bazel 6.4.0'

# RC1 parity must select the shared historical dependency/build root.
Assert-Contains "GEMMAMONSTER_ROOT\s*=\s*'C:\\\\opt'" 'rc1-parity uses C:\opt root'
Assert-Contains "OpenVINO_DIR\s*=\s*'C:\\\\opt\\\\openvino\\\\runtime\\\\cmake'" 'rc1-parity uses C:\opt OpenVINO runtime'

# Existing isolated maintainer profile must remain represented as a distinct root.
Assert-Contains "GEMMAMONSTER_ROOT\s*=\s*'C:\\\\g54r2'" 'maintainer-rc2 retains C:\g54r2 root'

# Both profiles must remain on the same proven 2026.4 RC2 dependency pins.
foreach ($sha in @(
    '227c33757d1ef95d4da506d00686f923fdd2a535',
    'a04accf6282d9b304214b492694b18c3979f667a',
    '7ea2546852a382cd16bd22dea0cfad2db70ed744'
)) {
    Assert-Contains ([regex]::Escape($sha)) "dependency pin $sha"
}

Assert-Contains "OV_USE_BINARY\s*=\s*'1'" 'binary OpenVINO/GenAI dependency mode remains explicit'
Assert-Contains "RUNTIME_PROFILE\s*=\s*\`$ToolchainProfile" 'preflight summary reports the selected profile rather than a hard-coded value'

Write-Host 'GEMMAMONSTER_ENV_PREFLIGHT_PROFILE_CONTRACT_PASS'
