# Server Startup Guide

This guide explains how to start the frontend and backend servers for the Rune-X platform.

## Quick Start

### Backend Server (FastAPI + Hybrid OCR)

**Option 1: Using PowerShell Script (Recommended)**
```powershell
.\start-backend.ps1
```

**Option 2: Using Batch File**
```cmd
start-backend.bat
```

**Option 3: Manual Start**
```bash
cd services\inference
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend Server (Next.js)

```bash
npm run dev
```

## Server Details

### Backend Server
- **Port**: 8001
- **URL**: http://localhost:8001
- **Health Check**: http://localhost:8001/health
- **Features**: 
  - Hybrid OCR system (EasyOCR + PaddleOCR)
  - Dictionary-based translation
  - Image preprocessing and enhancement

**Note**: Backend initialization takes 30-60 seconds as OCR engines load their models.

### Frontend Server
- **Port**: 3001
- **URL**: http://localhost:3001
- **Features**: 
  - Image upload interface
  - OCR results display
  - Translation and context display

## Verification

After starting both servers, verify they're running:

1. **Check Backend Health**:
   ```bash
   curl http://localhost:8001/health
   ```
   Or open in browser: http://localhost:8001/health

2. **Check Frontend**:
   Open browser: http://localhost:3001

## Troubleshooting

### Backend won't start
- Ensure you're in the correct directory (`services\inference`)
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify Python is in your PATH
- Check for port conflicts: `netstat -ano | findstr ":8001"`

### Frontend won't start
- Ensure Node.js dependencies are installed: `npm install`
- Check for port conflicts: `netstat -ano | findstr ":3001"`
- Verify database is set up: `npm run db:generate && npm run db:push`

### OCR engines not initializing
- EasyOCR and PaddleOCR models download automatically on first run
- This can take several minutes depending on internet speed
- Models are cached locally after first download

## Stopping Servers

- **Backend**: Press `Ctrl+C` in the terminal running the backend
- **Frontend**: Press `Ctrl+C` in the terminal running the frontend

Or kill processes:
```powershell
# Kill backend (port 8001)
Get-NetTCPConnection -LocalPort 8001 | Select-Object -ExpandProperty OwningProcess | Stop-Process -Force

# Kill frontend (port 3001)
Get-NetTCPConnection -LocalPort 3001 | Select-Object -ExpandProperty OwningProcess | Stop-Process -Force
```

