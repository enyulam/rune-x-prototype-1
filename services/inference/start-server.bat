@echo off
REM Backend Server Startup Script - Run from this directory
REM This ensures uvicorn runs from the correct location

echo Starting Rune-X Backend Server...
echo Working directory: %CD%
echo.

echo Starting uvicorn server on http://0.0.0.0:8001...
echo Note: OCR engines (EasyOCR + PaddleOCR) may take 30-60 seconds to initialize.
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload

