[CmdletBinding()]
param([switch]$DryRun, [switch]$SkipM3u4uSync, [switch]$SkipTiviMateReload)

$ErrorActionPreference = 'Stop'
$device = '100.93.218.48:5555'
$adb = (Get-Command adb -ErrorAction Stop).Source
$playlist = Join-Path $env:TEMP 'vaultwares-nos-canals.m3u'
$log = Join-Path $PSScriptRoot 'runtime\onn-tivimate-sync.log'
New-Item -ItemType Directory -Path (Split-Path $log) -Force | Out-Null
function Log([string]$message) { "$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssK') $message" | Tee-Object -FilePath $log -Append }
function Adb([string[]]$Arguments) { & $adb @Arguments; if ($LASTEXITCODE -ne 0) { throw "ADB failed: $($Arguments -join ' ')" } }
try {
  Log 'starting bounded ONN sync'
  if (-not $SkipM3u4uSync) { & (Join-Path $PSScriptRoot 'Run-M3u4uSync.ps1'); if ($LASTEXITCODE -ne 0) { throw 'm3u4u sync failed' } }
  Adb @('connect', $device)
  $devices = (& $adb devices) -join "`n"
  if ($devices -notmatch ('(?m)^' + [regex]::Escape($device) + '\s+device\b')) { throw 'ONN streamer is unavailable' }
  Adb @('-s', $device, 'shell', 'input', 'keyevent', '164')
  Invoke-WebRequest -Uri 'http://127.0.0.1:8787/playlist.m3u?refresh=1' -OutFile $playlist -TimeoutSec 30
  $header = Get-Content -LiteralPath $playlist -TotalCount 1
  $channels = (Select-String -LiteralPath $playlist -Pattern '^#EXTINF:' | Measure-Object).Count
  if (-not $header.StartsWith('#EXTM3U')) { throw "playlist validation failed: $channels channels" }
  if ($channels -ne 41) { throw "playlist validation failed: expected 41 channels, received $channels" }
  if ($DryRun) { Log 'dry run completed'; exit 0 }
  Adb @('-s', $device, 'push', $playlist, '/sdcard/Download/vaultwares-nos-canals.m3u')
  if (-not $SkipTiviMateReload) {
    Adb @('-s', $device, 'shell', 'am', 'force-stop', 'ar.tvplayer.tv')
    Adb @('-s', $device, 'shell', 'am', 'start', '-n', 'ar.tvplayer.tv/.ui.MainActivity')
    Start-Sleep -Seconds 2
    1..3 | ForEach-Object { Adb @('-s', $device, 'shell', 'input', 'keyevent', '4'); Start-Sleep -Milliseconds 1000 }
    Adb @('-s', $device, 'shell', 'input', 'tap', '55', '1007')
    Adb @('-s', $device, 'shell', 'input', 'keyevent', '66')
    Adb @('-s', $device, 'shell', 'input', 'tap', '1500', '315')
    Adb @('-s', $device, 'shell', 'input', 'tap', '1510', '500')
  }
  Log 'completed successfully'
} catch { Log "failed: $($_.Exception.Message)"; exit 1 }
