param(
  [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Join-Path $PSScriptRoot '..')

if (-not $SkipInstall) {
  Write-Host '[1/3] pip install -r requirements.txt...' -ForegroundColor Cyan
  python -m pip install -r requirements.txt
} else {
  Write-Host '[1/3] pip install skipped' -ForegroundColor Yellow
}

Write-Host '[2/3] Python syntax compile...' -ForegroundColor Cyan
python -m py_compile main.py config.py tools\yougile_api.py tools\dispatcher_api.py

Write-Host '[3/3] Check required env keys for runtime...' -ForegroundColor Cyan
$required = @('API_TOKEN','YOUGILE_API_KEY','COLUMN_ID')
$envFile = @{}
if (Test-Path '.env') {
  foreach ($line in (Get-Content '.env')) {
    if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
    $parts = $line -split '=', 2
    $key = $parts[0].Trim()
    $val = $parts[1].Trim()
    if ($key) { $envFile[$key] = $val }
  }
}
foreach ($k in $required) {
  $runtimeVal = [Environment]::GetEnvironmentVariable($k)
  $fileVal = if ($envFile.ContainsKey($k)) { $envFile[$k] } else { $null }
  if ([string]::IsNullOrWhiteSpace($runtimeVal) -and [string]::IsNullOrWhiteSpace($fileVal)) {
    Write-Warning "Missing required key: $k"
  }
}
Write-Host 'Bot predeploy check completed.' -ForegroundColor Green
