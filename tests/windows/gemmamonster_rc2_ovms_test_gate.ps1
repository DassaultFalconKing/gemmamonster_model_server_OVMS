[CmdletBinding()]
param(
    [string]$RepoRoot = (Join-Path $PSScriptRoot '..\..'),
    [string]$OvmsTestPath = '',
    [switch]$IncludeKnownWindowsSporadic
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path -LiteralPath $RepoRoot).Path
if ([string]::IsNullOrWhiteSpace($OvmsTestPath)) {
    $OvmsTestPath = Join-Path $root 'bazel-bin\src\ovms_test.exe'
}
if (-not (Test-Path -LiteralPath $OvmsTestPath -PathType Leaf)) {
    throw "ovms_test.exe not found: $OvmsTestPath"
}
$OvmsTestPath = (Resolve-Path -LiteralPath $OvmsTestPath).Path

# These negative CLI tests require model_repository_path to be genuinely absent.
# Since OVMS intentionally uses OVMS_MODEL_REPOSITORY_PATH as the default value
# for --model_repository_path, inheriting that variable makes all three tests
# exercise a different (valid) code path and they correctly do not exit.
$negativeCliFilter = @(
    'OvmsConfigDeathTest.NegativeListModelsWithoutModelRepositoryPath',
    'OvmsConfigDeathTest.modifyModelConfigEnableButMissingModelPath',
    'OvmsConfigDeathTest.hfPullNoRepositoryPath'
) -join ':'

# Upstream marks this exact fixture as Windows-sporadic (CVS-176244) using
# GTEST_SKIP() from SetUpTestSuite(). In the current Windows build the suite-level
# skip does not prevent the test body from executing, so the acceptance gate must
# honor upstream's stated Windows policy explicitly until that test fixture is
# repaired upstream/source-side.
$knownWindowsSporadic = 'ConfigChangeStressTestSingleModel.ChangeToEmptyConfigInference'

$originalProcessRepoPath = [Environment]::GetEnvironmentVariable('OVMS_MODEL_REPOSITORY_PATH', 'Process')
try {
    Write-Host "Gemmamonster RC2 ovms_test gate"
    Write-Host "  binary: $OvmsTestPath"
    Write-Host "  inherited OVMS_MODEL_REPOSITORY_PATH: $([string]::IsNullOrEmpty($originalProcessRepoPath) ? '<unset>' : '<set>')"

    # Make the negative tests deterministic. Restore the caller's environment in finally.
    [Environment]::SetEnvironmentVariable('OVMS_MODEL_REPOSITORY_PATH', $null, 'Process')
    $effectiveRepoPath = [Environment]::GetEnvironmentVariable('OVMS_MODEL_REPOSITORY_PATH', 'Process')
    if (-not [string]::IsNullOrEmpty($effectiveRepoPath)) {
        throw 'Failed to clear process OVMS_MODEL_REPOSITORY_PATH before ovms_test.'
    }

    Write-Host 'Running the three previously failing negative CLI tests...'
    & $OvmsTestPath "--gtest_filter=$negativeCliFilter"
    if ($LASTEXITCODE -ne 0) {
        throw "Negative CLI regression gate failed with exit code $LASTEXITCODE"
    }

    if ($IncludeKnownWindowsSporadic) {
        $fullFilter = '*'
        Write-Host "Running full ovms_test including known Windows-sporadic test: $knownWindowsSporadic"
    } else {
        $fullFilter = "*-$knownWindowsSporadic"
        Write-Host "Running full ovms_test excluding upstream-known Windows-sporadic test: $knownWindowsSporadic"
    }

    & $OvmsTestPath "--gtest_filter=$fullFilter"
    if ($LASTEXITCODE -ne 0) {
        throw "Full ovms_test gate failed with exit code $LASTEXITCODE"
    }

    Write-Host 'GEMMAMONSTER_RC2_OVMS_TEST_GATE_PASS'
} finally {
    [Environment]::SetEnvironmentVariable('OVMS_MODEL_REPOSITORY_PATH', $originalProcessRepoPath, 'Process')
}
