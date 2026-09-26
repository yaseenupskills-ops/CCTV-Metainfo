# run_frontend.ps1 — start the React frontend (Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.Command.Path
$Root = Split-Path -Parent $Root

Push-Location (Join-Path $Root "frontend")
npm run dev
Pop-Location
