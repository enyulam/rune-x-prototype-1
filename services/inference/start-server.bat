@echo off
REM Backend Server Startup Script - Run from this directory
REM This ensures uvicorn runs from the correct location

echo Starting Rune-X Backend Server...

REM Activate virtual environment (assuming project root is 2 levels up)
set PROJECT_ROOT=%~dp0..\..
if exist "%PROJECT_ROOT%venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "%PROJECT_ROOT%venv\Scripts\activate.bat"
) else (
    echo WARNING: Virtual environment not found. Continuing with system Python...
)

echo Working directory: %CD%
echo.

echo Starting uvicorn server on http://0.0.0.0:8001...
echo Note: OCR engines (EasyOCR + PaddleOCR) may take 30-60 seconds to initialize.
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload

