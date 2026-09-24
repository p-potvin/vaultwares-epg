[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$nssm = 'C:\Program Files\nssm\win64\nssm.exe'
$python = 'C:\Users\Administrator\AppData\Local\Python\bin\python.exe'
$service = 'VaultExplorerEPG'
$script = Join-Path $root 'epg_server.py'
$stdout = Join-Path $root 'runtime\epg-service.out.log'
$stderr = Join-Path $root 'runtime\epg-service.err.log'

if (-not (Test-Path -LiteralPath $nssm) -or -not (Test-Path -LiteralPath $python) -or -not (Test-Path -LiteralPath $script)) { throw 'NSSM, Python, or epg_server.py is missing.' }
& $nssm set $service Application $python
& $nssm set $service AppParameters "`"$script`""
& $nssm set $service AppDirectory $root
& $nssm set $service AppStdout $stdout
& $nssm set $service AppStderr $stderr
& $nssm set $service AppExit Default Restart
& $nssm set $service AppThrottle 5000
& $nssm set $service AppRestartDelay 5000
& $nssm set $service Start SERVICE_DELAYED_AUTO_START
& $nssm set $service ObjectName LocalSystem
& $nssm reset $service AppEnvironmentExtra

$ensure = Join-Path $root 'Ensure-EpgService.ps1'
$action = New-ScheduledTaskAction -Execute 'conhost.exe' -Argument "--headless pwsh.exe -NoProfile -WindowStyle Hidden -NonInteractive -ExecutionPolicy Bypass -File `"$ensure`""
$triggers = @((New-ScheduledTaskTrigger -AtStartup), (New-ScheduledTaskTrigger -AtLogOn))
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -MultipleInstances IgnoreNew -StartWhenAvailable:$false
Register-ScheduledTask -TaskName 'VaultWaresEPGEnsure' -Action $action -Trigger $triggers -Principal $principal -Settings $settings -Force | Out-Null
