$ErrorActionPreference = 'Stop'
$evidence = 'C:\git\artifacts\gemma4-promotion-20260916'
if ((Get-Content "$evidence\exit-code.txt" -Raw).Trim() -ne '0') { throw 'Semantic test gate has not passed' }
$live = "$evidence\live"
New-Item -ItemType Directory -Force -Path $live | Out-Null
$package = 'C:\git\gemma4-upstream-refit-clean-20260915\dist\windows\ovms'
$oldLauncher = 'C:\git\gemma4-rc-main-promotion-20260916\acceptance\gemma4-live-20260916-corrective\launch-20-u4-b4096-seq4-2026.5.bat'
$oldLog = 'C:\git\gemma4-upstream-refit-clean-20260915\acceptance\gemma4-live-20260916-corrective\logs\ovms-20-u4-b4096-seq4-2026.5.log'
$text = [IO.File]::ReadAllText($oldLauncher).Replace($oldLog, "$live\ovms.log")
$text = $text.Replace('@echo off', "@echo off`r`ncall `"$package\setupvars.bat`"`r`nif errorlevel 1 exit /b 1")
[IO.File]::WriteAllText("$live\launch.bat", $text)
$tcp = New-Object Net.Sockets.TcpClient
try { $tcp.Connect('127.0.0.1',18091); $occupied = $true } catch { $occupied = $false } finally { $tcp.Dispose() }
if ($occupied) { throw 'Port 18091 is occupied; inspect owner before launch' }
$proc = Start-Process -FilePath cmd.exe -ArgumentList @('/d','/c',"`"$live\launch.bat`"") -WindowStyle Hidden -PassThru
$proc.Id | Set-Content "$live\launcher-pid.txt"
Write-Output "Started launcher PID $($proc.Id), logs: $live\ovms.log"
