[CmdletBinding()]
param(
    [string]$TaskName = 'VaultWaresOnnTiviMateSync'
)

$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'Sync-OnnTiviMate.ps1'
$action = New-ScheduledTaskAction -Execute 'conhost.exe' -Argument "--headless pwsh.exe -NoProfile -WindowStyle Hidden -NonInteractive -ExecutionPolicy Bypass -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Daily -At '12:00AM'
$principal = New-ScheduledTaskPrincipal -UserId ("{0}\{1}" -f $env:USERDOMAIN,$env:USERNAME) -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -MultipleInstances IgnoreNew -StartWhenAvailable:$false
Register-ScheduledTask -TaskName $TaskName -TaskPath '\VaultWares\' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Get-ScheduledTask -TaskName $TaskName -TaskPath '\VaultWares\' | Select-Object TaskName, State
