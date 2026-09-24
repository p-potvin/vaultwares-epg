[CmdletBinding()]
param([switch]$DryRun)

$ErrorActionPreference = 'Stop'
$runtime = Join-Path $PSScriptRoot 'runtime'
$log = Join-Path $runtime 'm3u4u-sync.log'
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
$config = Join-Path $PSScriptRoot '.env'
if (Test-Path -LiteralPath $config) {
    Get-Content -LiteralPath $config | ForEach-Object {
        if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$' -and -not $_.TrimStart().StartsWith('#')) {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
        }
    }
}
$env:M3U4U_TIMEOUT_MS = '120000'
if ($DryRun) { $env:M3U4U_DRY_RUN = '1' } else { Remove-Item Env:M3U4U_DRY_RUN -ErrorAction SilentlyContinue }
& 'C:\Program Files\nodejs\node.exe' (Join-Path $PSScriptRoot 'sync-m3u4u-patchright.cjs') *>&1 | Tee-Object -FilePath $log -Append
exit $LASTEXITCODE
