@echo off
REM Quick Virtual Environment Activation Script
REM Run this script to activate the venv in your current terminal session

echo Activating Rune-X Virtual Environment...
echo.

REM Get the script directory (project root)
set SCRIPT_DIR=%~dp0

REM Activate virtual environment
if exist "%SCRIPT_DIR%venv\Scripts\activate.bat" (
    call "%SCRIPT_DIR%venv\Scripts\activate.bat"
    echo.
    echo Virtual environment activated!
    echo Python: 
    python --version
    echo Python Path:
    python -c "import sys; print(sys.executable)"
    echo.
) else (
    echo ERROR: Virtual environment not found at %SCRIPT_DIR%venv\Scripts\activate.bat
    echo Please ensure the venv directory exists.
    exit /b 1
)

