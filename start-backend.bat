@echo off
REM Backend Server Startup Script for Rune-X Platform
REM This script starts the FastAPI backend server with hybrid OCR (EasyOCR + PaddleOCR)

echo Starting Rune-X Backend Server...
echo.

REM Get the script directory (project root)
set SCRIPT_DIR=%~dp0
set BACKEND_DIR=%SCRIPT_DIR%services\inference

REM Check if backend directory exists
if not exist "%BACKEND_DIR%" (
    echo ERROR: Backend directory not found: %BACKEND_DIR%
    exit /b 1
)

REM Check if main.py exists
if not exist "%BACKEND_DIR%\main.py" (
    echo ERROR: main.py not found in %BACKEND_DIR%
    exit /b 1
)

echo Starting uvicorn server on http://0.0.0.0:8001...
echo Note: OCR engines (EasyOCR + PaddleOCR) may take 30-60 seconds to initialize.
echo Note: Translation engines (MarianMT, Qwen) will initialize on first use.
echo.

REM Change to backend directory and start the server
REM This ensures uvicorn's reloader watches the correct directory
cd /d "%BACKEND_DIR%"
echo Working directory: %CD%
echo.

REM Start the server from the backend directory
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload

