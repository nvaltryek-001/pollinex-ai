<#
.SYNOPSIS
  One-time POLLINEX AI setup on Windows 10/11 (PowerShell 5.1 or 7+).

.DESCRIPTION
  - checks Python (3.11-3.13) and Node (20+)
  - creates .venv and installs backend requirements
  - installs frontend npm packages
  - creates .env from .env.example with a random JWT secret
  - optional: -Postgres switch configures DATABASE_URL for a local PostgreSQL instead of SQLite

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
  powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1 -Postgres -PgPassword "yourpass"
#>
param(
  [switch]$Postgres,
  [string]$PgUser = "pollinex",
  [string]$PgPassword = "",
  [string]$PgHost = "localhost",
  [int]$PgPort = 5432,
  [string]$PgDb = "pollinex",
  [switch]$WithPlaywright,
  [switch]$NoLock,
  [string]$PythonExe = ""
)
$ErrorActionPreference = "Continue"   # native-tool stderr must not abort (PS 5.1); exit codes are checked explicitly
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Need($cmd, $hint) {
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { Write-Error "$cmd not found. $hint"; exit 1 }
}

Write-Host "== Checking prerequisites" -ForegroundColor Cyan
$py = if ($PythonExe) { $PythonExe } elseif (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
Need $py "Install Python 3.12 from https://www.python.org/downloads/ (tick 'Add python.exe to PATH')."
Need node "Install Node.js 20 LTS or newer from https://nodejs.org/"
Need npm  "npm ships with Node.js."
$pyver = & $py -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
Write-Host "Python $pyver, Node $(node --version)"
if ([version]$pyver -lt [version]"3.11") { Write-Error "Python 3.11+ required (found $pyver)"; exit 1 }

Write-Host "== Python virtual environment (.venv)" -ForegroundColor Cyan
if (-not (Test-Path ".venv")) { & $py -m venv .venv }
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
& $venvPy -m pip install --upgrade pip
if ((Test-Path "backend\requirements.lock.txt") -and -not $NoLock) {
  Write-Host "Installing the exact versions verified in CI (backend\requirements.lock.txt)"
  & $venvPy -m pip install -r backend\requirements.txt -c backend\requirements.lock.txt
  if ($LASTEXITCODE -ne 0) { Write-Warning "Locked install failed on this platform - retrying with version ranges"; & $venvPy -m pip install -r backend\requirements.txt }
} else {
  & $venvPy -m pip install -r backend\requirements.txt
}
if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed"; exit 1 }

Write-Host "== Frontend packages" -ForegroundColor Cyan
Push-Location frontend
if ((Test-Path "package-lock.json") -and -not $NoLock) { npm ci --no-audit --no-fund } else { npm install --no-audit --no-fund }
if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Error "npm install failed"; exit 1 }
if ($WithPlaywright) { npx playwright install chromium }
Pop-Location

Write-Host "== Environment file (.env)" -ForegroundColor Cyan
if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  $secret = & $venvPy -c "import secrets; print(secrets.token_urlsafe(48))"
  (Get-Content ".env") -replace '^JWT_SECRET=.*', "JWT_SECRET=$secret" | Set-Content ".env" -Encoding UTF8
  Write-Host "Created .env with a random JWT_SECRET"
} else { Write-Host ".env already exists - left unchanged" }

if ($Postgres) {
  if (-not $PgPassword) { $PgPassword = Read-Host "PostgreSQL password for user $PgUser" }
  $url = "postgresql+psycopg://${PgUser}:${PgPassword}@${PgHost}:${PgPort}/${PgDb}"
  $content = Get-Content ".env" | Where-Object { $_ -notmatch '^DATABASE_URL=' -and $_ -notmatch '^AUTO_CREATE_TABLES=' }
  $content + "DATABASE_URL=$url" + "AUTO_CREATE_TABLES=false" | Set-Content ".env" -Encoding UTF8
  Write-Host "Running database migrations against $PgHost/$PgDb"
  Push-Location backend
  $env:DATABASE_URL = $url
  & $venvPy -m alembic upgrade head
  $code = $LASTEXITCODE
  Pop-Location
  if ($code -ne 0) { Write-Error "alembic upgrade failed - is PostgreSQL running and does database '$PgDb' exist? (createdb -U $PgUser $PgDb)"; exit 1 }
} else {
  Write-Host "Using SQLite (backend\pollinex.db) - tables are created automatically on first start."
}

Write-Host "== Dependency check" -ForegroundColor Cyan
& $venvPy scripts\check_dependencies.py
if ($LASTEXITCODE -ne 0) { Write-Warning "Some checks failed - see above." }

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Start the app:   powershell -ExecutionPolicy Bypass -File scripts\run_windows.ps1"
Write-Host "Run all tests:   powershell -ExecutionPolicy Bypass -File scripts\test_windows.ps1"
