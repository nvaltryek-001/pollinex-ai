<#
.SYNOPSIS
  Runs every automated POLLINEX AI test suite on Windows and prints a summary.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\test_windows.ps1
  powershell -ExecutionPolicy Bypass -File scripts\test_windows.ps1 -E2E     # starts the stack and runs Playwright
#>
param([switch]$E2E)
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Error "Run scripts\setup_windows.ps1 first."; exit 1 }
$results = [ordered]@{}

function Step($name, [scriptblock]$block) {
  Write-Host "`n== $name" -ForegroundColor Cyan
  & $block
  $results[$name] = if ($LASTEXITCODE -eq 0) { "PASS" } else { "FAIL ($LASTEXITCODE)" }
}

Step "AI engine + simulation (pytest)" { & $venvPy -m pytest -q ai-engine/tests simulation/tests }
Step "Backend API/DB/auth (pytest)"    { & $venvPy -m pytest -q backend/tests }
Step "Alembic migration (fresh SQLite)" {
  Push-Location backend
  $env:DATABASE_URL = "sqlite:///./_migration_check.db"
  & $venvPy -m alembic upgrade head
  $c = $LASTEXITCODE; Remove-Item _migration_check.db -ErrorAction SilentlyContinue; Remove-Item Env:DATABASE_URL
  Pop-Location; $global:LASTEXITCODE = $c
}
Push-Location frontend
Step "Frontend typecheck" { npm run typecheck }
Step "Frontend unit tests (vitest)" { npm test }
Step "Frontend production build" { npm run build }
Pop-Location

if ($E2E) {
  Push-Location frontend; npx playwright install chromium; Pop-Location
  $env:RATE_LIMIT_ENABLED = "false"   # E2E logs in many times from one IP
  $api = Start-Process -FilePath $venvPy -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8000" -WorkingDirectory (Join-Path $Root "backend") -PassThru -NoNewWindow
  Push-Location frontend
  $web = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "preview", "--", "--port", "5173" -PassThru -NoNewWindow
  Start-Sleep -Seconds 12
  Step "End-to-end (Playwright)" { npx playwright test }
  Pop-Location
  # kill whole process trees (npm.cmd -> node/vite, python -> uvicorn)
  foreach ($p in @($web, $api)) { if ($p -and -not $p.HasExited) { taskkill /T /F /PID $p.Id | Out-Null } }
  Remove-Item Env:RATE_LIMIT_ENABLED -ErrorAction SilentlyContinue
}

Write-Host "`n== Summary" -ForegroundColor Cyan
$results.GetEnumerator() | ForEach-Object {
  $color = if ($_.Value -eq "PASS") { "Green" } else { "Red" }
  Write-Host ("{0,-40} {1}" -f $_.Key, $_.Value) -ForegroundColor $color
}
if ($results.Values | Where-Object { $_ -ne "PASS" }) { exit 1 }
