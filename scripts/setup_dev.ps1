# setup_dev.ps1 — one-time development environment setup (Windows)
# Run from the repository root.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $Root

Write-Host "CCTV Forensic Analyzer - Development Setup" -ForegroundColor Cyan
Write-Host "Root: $Root" -ForegroundColor Gray

# 1. Copy env templates if missing
if (-not (Test-Path (Join-Path $Root ".env"))) {
    Copy-Item (Join-Path $Root ".env.example") (Join-Path $Root ".env")
    Write-Host "[1/4] Created root .env (edit values!)" -ForegroundColor Yellow
} else {
    Write-Host "[1/4] Root .env already exists" -ForegroundColor Green
}

if (-not (Test-Path (Join-Path $Root "backend\.env"))) {
    Copy-Item (Join-Path $Root ".env.example") (Join-Path $Root "backend\.env")
    Write-Host "[1/4] Created backend\.env (edit values!)" -ForegroundColor Yellow
} else {
    Write-Host "[1/4] backend\.env already exists" -ForegroundColor Green
}

# 2. Backend virtual environment
$Venv = Join-Path $Root "backend\.venv"
if (-not (Test-Path $Venv)) {
    Write-Host "[2/4] Creating backend virtual environment..."
    python -m venv $Venv
    Write-Host "[2/4] Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "[2/4] Virtual environment already exists" -ForegroundColor Green
}

# 3. Install backend dependencies
Write-Host "[3/4] Installing backend dependencies..."
& (Join-Path $Venv "Scripts\python.exe") -m pip install --upgrade pip
& (Join-Path $Venv "Scripts\pip.exe") install -r (Join-Path $Root "backend\requirements-dev.txt")

# 4. Frontend dependencies
Write-Host "[4/4] Installing frontend dependencies..."
Push-Location (Join-Path $Root "frontend")
npm install
Pop-Location

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. Edit .env with your PostgreSQL credentials and JWT secret"
Write-Host "  2. cd backend; .\.venv\Scripts\Activate.ps1"
Write-Host "  3. alembic upgrade head"
Write-Host "  4. python -m app.db.seed"
Write-Host "  5. uvicorn app.main:app --reload --port 8000"
Write-Host "  6. cd ..\frontend; npm run dev"
