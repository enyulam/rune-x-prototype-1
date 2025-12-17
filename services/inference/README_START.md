# Starting the Backend Server

## Important: Directory Requirement

The backend server **MUST** be started from the `services/inference` directory.

## Quick Start

1. **Navigate to the backend directory:**
   ```bash
   cd services\inference
   ```

2. **Start the server:**
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
   ```

## Why This Directory?

Uvicorn's module loader needs to find `main.py` in the current directory. If you run from the project root, you'll get:
```
ERROR: Error loading ASGI app. Could not import module "main".
```

## Alternative: Use the Startup Scripts

From the project root, use:
- **PowerShell**: `.\start-backend.ps1`
- **Batch**: `start-backend.bat`

These scripts automatically navigate to the correct directory.

## Verification

After starting, wait 30-60 seconds for OCR engines to initialize, then check:
- Health endpoint: http://localhost:8001/health
- Should show both EasyOCR and PaddleOCR as available

