$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

Write-Host "Building KeyPulseNexus.exe ..." -ForegroundColor Cyan
python -m PyInstaller --clean --noconfirm main.spec

Write-Host ""
Write-Host "Build complete." -ForegroundColor Green
Write-Host "Output:" -ForegroundColor Yellow
Write-Host "  $projectRoot\dist\KeyPulseNexus.exe"
