param([string]$TargetRoot = (Join-Path $HOME '.agents\skills'))
$ErrorActionPreference = 'Stop'
$Source = Split-Path -Parent $MyInvocation.MyCommand.Path
$Target = Join-Path $TargetRoot 'making-skills-portable'
New-Item -ItemType Directory -Force -Path $TargetRoot | Out-Null
if (Test-Path $Target) { Remove-Item -Recurse -Force $Target }
Copy-Item -Recurse -Force $Source $Target
Write-Host "installed: $Target"
