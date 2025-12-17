# Quick Start Guide - Testing OCR and Translation

## ✅ Current Status

**Good News**: Yes, you can run the program and upload an image to extract text and get translations! All the code is in place and working.

## 🔧 Setup Required

### 1. Environment Variables

You need to create a `.env` file in the project root with:

```env
# Database
DATABASE_URL="file:./prisma/db/dev.db"
NEXTAUTH_URL="http://localhost:3001"
NEXTAUTH_SECRET="your-secret-key-here"

# Inference Service (REQUIRED for OCR to work)
INFERENCE_API_URL="http://localhost:8001"
```

**Important**: The `INFERENCE_API_URL` must be set to `http://localhost:8001` for the OCR to work!

### 2. Verify Services Are Running

**Backend (FastAPI)**: Should be running on port 8001
```bash
# Check if running
curl http://localhost:8001/health

# If not running, start it:
cd services/inference
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

**Frontend (Next.js)**: Should be running on port 3001
```bash
# Check if running
# Open http://localhost:3001 in browser

# If not running, start it:
npm run dev
```

## 🚀 How to Test

### Step 1: Start Backend Service
```bash
cd services/inference
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Wait for: `INFO:     Uvicorn running on http://0.0.0.0:8001`

### Step 2: Start Frontend Service
```bash
npm run dev
```

Wait for: `Ready on http://localhost:3001`

### Step 3: Verify Backend is Working
```bash
curl http://localhost:8001/health
```

Should return:
```json
{
  "status": "ok",
  "paddle": {
    "available": true,
    "status": "ready"
  },
  "dictionary": {
    "entries": 67,
    ...
  }
}
```

### Step 4: Upload an Image

1. Open browser: `http://localhost:3001`
2. Login (or register if first time)
3. Go to Upload page
4. Select a Chinese handwriting image (JPG, PNG, or WebP)
5. Click "Process Images"
6. Wait for processing (2-5 seconds typically)
7. View results:
   - Extracted text
   - Character-by-character meanings
   - Full translation
   - Confidence scores

## 📋 What You'll See

### Successful Processing:
- ✅ Extracted Chinese text from image
- ✅ Character meanings (from dictionary)
- ✅ Full translation (concatenated meanings)
- ✅ Confidence scores for each character
- ✅ Coverage percentage (how many characters found in dictionary)
- ✅ Unmapped characters list (if any)

### Example Result:
```
Extracted Text: 人天
Translation: person; people; human | sky; heaven; day; nature
Confidence: 0.935
Coverage: 100%
```

## ⚠️ Common Issues

### Issue 1: "Processing unavailable - INFERENCE_API_URL not configured"
**Solution**: Create `.env` file with `INFERENCE_API_URL="http://localhost:8001"`

### Issue 2: "503 Service Unavailable"
**Solution**: Make sure backend is running on port 8001

### Issue 3: "No text detected in image"
**Solution**: 
- Ensure image contains readable Chinese text
- Check image quality (should be clear, not blurry)
- Try a different image

### Issue 4: Frontend can't connect to backend
**Solution**: 
- Verify backend is running: `curl http://localhost:8001/health`
- Check CORS settings (should be configured)
- Verify `INFERENCE_API_URL` in `.env`

## 🎯 Accuracy Expectations

### What Works Well:
- ✅ Clear, high-quality Chinese handwriting
- ✅ Standard Chinese characters
- ✅ Characters in the dictionary (67+ entries currently)

### Limitations:
- ⚠️ Very blurry or low-quality images
- ⚠️ Characters not in dictionary (will show as "unmapped")
- ⚠️ Extremely stylized or artistic fonts
- ⚠️ Very small text

### Dictionary Coverage:
- Current: 67 entries
- Can be expanded by editing `services/inference/data/dictionary.json`

## 📊 Current Capabilities

✅ **Working**:
- Real OCR text extraction (PaddleOCR)
- Dictionary-based translation
- Character-level meanings
- Confidence scoring
- Coverage tracking
- Error handling

❌ **Not Yet Implemented** (Phase 7+):
- Batch processing
- Progress indicators
- Visual bounding box overlays
- Export functionality
- Enhanced search/filter

## 🧪 Quick Test

Test the full pipeline:

1. **Backend Health Check**:
   ```bash
   curl http://localhost:8001/health
   ```

2. **Test OCR Directly** (optional):
   ```bash
   curl -X POST http://localhost:8001/process-image \
     -F "file=@path/to/your/image.jpg"
   ```

3. **Test via Frontend**:
   - Upload image through web UI
   - See results displayed

## ✅ Verification Checklist

Before testing, verify:
- [ ] `.env` file exists with `INFERENCE_API_URL="http://localhost:8001"`
- [ ] Backend service running on port 8001
- [ ] Frontend service running on port 3001
- [ ] PaddleOCR initialized (check health endpoint)
- [ ] Dictionary loaded (67+ entries)
- [ ] Database initialized (`npm run db:push`)

---

**You're all set!** The system is ready to extract text and translate Chinese handwriting images.

