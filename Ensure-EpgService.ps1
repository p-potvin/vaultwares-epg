$ErrorActionPreference = 'Stop'
$service = Get-Service -Name 'VaultExplorerEPG' -ErrorAction Stop
if ($service.Status -eq 'Paused') { Resume-Service -Name $service.Name -ErrorAction SilentlyContinue }
if ((Get-Service -Name $service.Name).Status -ne 'Running') { Start-Service -Name $service.Name }
