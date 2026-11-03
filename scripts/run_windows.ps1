<#
.SYNOPSIS
  Starts the POLLINEX AI backend (http://localhost:8000) and frontend (http://localhost:5173) on Windows.
  Closes the backend when you press Ctrl+C in this window.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\run_windows.ps1
  powershell -ExecutionPolicy Bypass -File scripts\run_windows.ps1 -NoBrowser
#>
param([switch]$NoBrowser, [int]$ApiPort = 8000)
$ErrorActionPreference = "Continue"   # native-tool stderr must not abort (PS 5.1); exit codes are checked explicitly
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Error "Run scripts\setup_windows.ps1 first."; exit 1 }

# load .env into this process (KEY=VALUE lines; comments ignored)
if (Test-Path ".env") {
  Get-Content ".env" | Where-Object { $_ -match '^\s*[A-Za-z_][A-Za-z0-9_]*=' } | ForEach-Object {
    $k, $v = $_ -split '=', 2
    [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim(), "Process")
  }
}

Write-Host "Starting API on http://localhost:$ApiPort ..." -ForegroundColor Cyan
$api = Start-Process -FilePath $venvPy -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$ApiPort" `
  -WorkingDirectory (Join-Path $Root "backend") -PassThru -NoNewWindow

# wait for health
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
  Start-Sleep -Seconds 1
  try { $r = Invoke-RestMethod "http://127.0.0.1:$ApiPort/api/v1/health" -TimeoutSec 2; $ok = $true; break } catch { }
}
if (-not $ok) { Write-Warning "API did not answer /api/v1/health within 60 s - check the log above." }
else { Write-Host "API health: $($r.status) ($($r.checks | ConvertTo-Json -Compress))" -ForegroundColor Green }

if (-not $NoBrowser) { Start-Process "http://localhost:5173" }
try {
  Push-Location frontend
  $env:VITE_API_PROXY = "http://127.0.0.1:$ApiPort"
  npm run dev
} finally {
  Pop-Location
  if ($api -and -not $api.HasExited) { taskkill /T /F /PID $api.Id | Out-Null }
}
