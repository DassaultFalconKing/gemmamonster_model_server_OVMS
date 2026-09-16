$ErrorActionPreference = 'Stop'
$dir = 'C:\git\artifacts\gemma4-promotion-20260916\live'
$path = 'C:\git\gemma4-upstream-refit-clean-20260915\dist\windows\ovms\ovms.exe'
$instances = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'ovms.exe' -and $_.ExecutablePath -eq $path -and $_.CommandLine -match '--rest_port 18091' })
if ($instances.Count -ne 1) { throw "Expected one matching OVMS instance, got $($instances.Count)" }
$instance = $instances[0]
$modules = @((Get-Process -Id $instance.ProcessId).Modules | Select-Object ModuleName,FileName)
$info = @{timestamp=[DateTime]::UtcNow.ToString('o'); pid=$instance.ProcessId; executable=$instance.ExecutablePath; command_line=$instance.CommandLine; modules=$modules}
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$info | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 "$dir\process-$stamp.json"
Write-Output "OVMS PID=$($instance.ProcessId) modules=$($modules.Count)"
$modules | Where-Object { $_.ModuleName -match 'openvino|python312' } | Format-Table -AutoSize
