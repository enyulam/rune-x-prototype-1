# Changelog - Rune-X Translation Platform

All notable changes to this project will be documented in this file.

## [December 2025] - Latest Updates

### ✅ Fixed

#### Backend Fixes
1. **MarianMT Neural Translation - OPERATIONAL**
   - **Issue**: MarianMT was failing with "SentencePiece library not found" error
   - **Fix**: Installed `sentencepiece>=0.2.0` library
   - **Impact**: All three translation tiers now fully operational
   - **Verification**: Health endpoint shows `"marianmt": {"available": true, "status": "ready"}`
   
2. **Backend Server Auto-Reload**
   - Triggered server reload to pick up new sentencepiece library
   - All translation engines now active and verified

#### Frontend Fixes
1. **Next.js 15 Async Params Warning - RESOLVED**
   - **Issue**: Route `/api/uploads/[id]` throwing async params deprecation warnings
   - **Fix**: Updated route handler to use `Promise<{ id: string }>` type and await params
   - **Impact**: No more console warnings, improved Next.js 15 compatibility
   - **File**: `src/app/api/uploads/[id]/route.ts`

### ✅ Verified Operational

All systems tested and confirmed working:

#### OCR Systems
- ✅ **EasyOCR**: Active (ch_sim + en languages)
- ✅ **PaddleOCR**: Active (Chinese text recognition)
- ✅ **Hybrid Fusion**: Character-level fusion working correctly

#### Translation Systems
- ✅ **Dictionary Translation**: 276+ entries loaded and active
- ✅ **MarianMT Neural Translation**: Now fully operational with sentencepiece
- ✅ **Qwen LLM Refinement**: Qwen2.5-1.5B-Instruct active and refining translations

#### Preprocessing Pipeline
- ✅ **13-Step Pipeline**: All core and optional steps functioning
- ✅ **61 Unit Tests**: 100% pass rate
- ✅ **Configuration System**: 35+ tunable parameters via .env

#### Servers
- ✅ **Backend (Port 8001)**: FastAPI server running, all endpoints responding
- ✅ **Frontend (Port 3001)**: Next.js 15.5.9 running, no errors or warnings

### 📝 Updated Documentation

1. **README.md**
   - Updated status to "FULLY OPERATIONAL"
   - Added SentencePiece to prerequisites
   - Marked all translation systems as active

2. **QUICK_START_GUIDE.md**
   - Updated health check response with verified status
   - Added "FULLY OPERATIONAL" status banner
   - Marked MarianMT as active

3. **services/inference/README.md**
   - Added operational status section at top
   - Updated installation notes to mention sentencepiece requirement
   - Added troubleshooting section for MarianMT/sentencepiece issue
   - Updated verification command to include sentencepiece

4. **services/inference/requirements.txt**
   - Added `sentencepiece>=0.2.0` to dependencies

5. **CHANGELOG.md** (this file)
   - Created to document all recent fixes and verifications

### 🧪 Testing Results

**Test Verification**: Uploaded test image (Chinese character 我 - "I/me")
- ✅ Image successfully preprocessed through 13-step pipeline
- ✅ Hybrid OCR extracted character correctly
- ✅ Dictionary translation provided: "I; me; myself; we; our"
- ✅ MarianMT neural translation working
- ✅ Qwen refinement active
- ✅ HTTP 200 OK response returned

**Backend Console Output**:
```
INFO: oneDNN v3.6.2 initialized (PaddleOCR neural network library)
UserWarning: 'pin_memory' set but no GPU found (Expected - CPU mode)
INFO: 127.0.0.1:51389 - "POST /process-image HTTP/1.1" 200 OK
```

### 🎯 Platform Health Summary

**Overall Status**: ✅ **FULLY OPERATIONAL**

**Component Status**:
```json
{
  "ocr_engines": {
    "easyocr": "ready ✅",
    "paddleocr": "ready ✅"
  },
  "translation_engines": {
    "dictionary": "ready ✅ (276+ entries)",
    "marianmt": "ready ✅ (with sentencepiece)",
    "qwen_refiner": "ready ✅ (Qwen2.5-1.5B-Instruct)"
  },
  "preprocessing": "ready ✅ (61/61 tests passing)",
  "servers": {
    "backend": "running ✅ (port 8001)",
    "frontend": "running ✅ (port 3001)"
  }
}
```

### 🚀 Known Optimizations

**Performance Notes**:
- Platform running on CPU mode (no GPU detected)
- PyTorch `pin_memory` warning expected in CPU-only environments
- Processing times are normal for CPU-based inference
- GPU support would provide 5-10x performance improvement but is not required

### 📦 Dependencies Updated

**New Dependencies**:
- `sentencepiece>=0.2.0` - Required for MarianMT tokenization

**Verified Dependencies**:
- `transformers>=4.57.3` - For MarianMT and Qwen
- `sacremoses>=0.1.1` - MarianMT tokenization helper
- `accelerate>=0.30.0` - Qwen device mapping
- `python-dotenv>=1.0.0` - Environment variable management
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support

---

## Previous Changes

### [Phase 1] - Preprocessing Module Refactor
- Created modular preprocessing system
- Implemented 13-step pipeline (8 core + 4 optional + validation)
- Added 61 comprehensive unit tests (100% pass rate)
- Implemented configuration system with .env support
- Added 35+ tunable parameters

### [Earlier] - Core Platform Development
- Implemented hybrid OCR system (EasyOCR + PaddleOCR)
- Added dictionary translation (276+ entries)
- Integrated MarianMT neural translation
- Added Qwen LLM refinement
- Built Next.js 15 frontend
- Created FastAPI backend service

---

**Last Updated**: December 18, 2025  
**Status**: ✅ All systems operational and verified

