# Backend Server Startup Script for Rune-X Platform
# This script starts the FastAPI backend server with hybrid OCR (EasyOCR + PaddleOCR)

Write-Host "Starting Rune-X Backend Server..." -ForegroundColor Cyan
Write-Host ""

# Get the script directory (project root)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $scriptDir "services\inference"

# Check if backend directory exists
if (-not (Test-Path $backendDir)) {
    Write-Host "ERROR: Backend directory not found: $backendDir" -ForegroundColor Red
    exit 1
}

# Check if main.py exists
$mainPy = Join-Path $backendDir "main.py"
if (-not (Test-Path $mainPy)) {
    Write-Host "ERROR: main.py not found in $backendDir" -ForegroundColor Red
    exit 1
}

# Check if port 8001 is already in use
$portInUse = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "WARNING: Port 8001 is already in use. Please stop the existing process first." -ForegroundColor Yellow
    Write-Host "Press any key to continue anyway, or Ctrl+C to cancel..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

Write-Host "Starting uvicorn server on http://0.0.0.0:8001..." -ForegroundColor Cyan
Write-Host "Note: OCR engines (EasyOCR + PaddleOCR) may take 30-60 seconds to initialize." -ForegroundColor Yellow
Write-Host "Note: Translation engines (MarianMT, Qwen) will initialize on first use." -ForegroundColor Yellow
Write-Host ""

# Change to backend directory
Set-Location $backendDir
Write-Host "Working directory: $(Get-Location)" -ForegroundColor Green
Write-Host ""

# Set PYTHONPATH to ensure imports work correctly
$env:PYTHONPATH = $backendDir

# Start the server from the backend directory
# Note: uvicorn's reloader may show the parent directory, but it will work correctly
Write-Host "Starting server..." -ForegroundColor Cyan
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload

