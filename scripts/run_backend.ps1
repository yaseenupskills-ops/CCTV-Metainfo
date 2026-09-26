# run_backend.ps1 — start the FastAPI backend (Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.Command.Path
$Root = Split-Path -Parent $Root
$Venv = Join-Path $Root "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $Venv)) {
    Write-Host "Virtual environment not found. Run .\scripts\setup_dev.ps1 first." -ForegroundColor Red
    exit 1
}

Push-Location (Join-Path $Root "backend")
& $Venv -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Pop-Location
