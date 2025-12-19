# 🔍 OCR System Guide - How It Works

## 📋 Current OCR Logic Overview

The Rune-X platform uses a **Hybrid Dual-Engine OCR System** that combines results from two OCR engines for maximum accuracy.

---

## 🎯 OCR Engines Used

### **Engine 1: EasyOCR** 
- **Language Support**: Chinese Simplified (`ch_sim`) + English
- **Strengths**: 
  - Good for handwriting
  - Handles various fonts well
  - Robust with difficult images
- **Source Tag**: `"easyocr"` in results
- **Location in Code**: `main.py` lines 225-264

### **Engine 2: PaddleOCR**
- **Language Support**: Chinese (`ch`)
- **Strengths**:
  - Fast processing
  - Excellent for Chinese text
  - Advanced models (PP-OCRv5)
- **Source Tag**: `"paddleocr"` in results
- **Location in Code**: `main.py` lines 267-353

---

## 🔄 Complete OCR Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. IMAGE UPLOAD                                             │
│    User uploads image with Chinese text                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. PREPROCESSING (13 Steps)                                │
│    - Grayscale conversion                                   │
│    - Noise reduction                                        │
│    - Contrast enhancement                                   │
│    - Binarization                                           │
│    - Morphology operations                                  │
│    - Edge enhancement                                       │
│    - Sharpening                                             │
│    + Optional: Bilateral filter, CLAHE, etc.               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. PARALLEL OCR EXECUTION                                   │
│                                                             │
│    ┌──────────────────┐      ┌──────────────────┐         │
│    │   EasyOCR        │      │   PaddleOCR      │         │
│    │   (ch_sim+en)    │      │   (ch)           │         │
│    └──────────────────┘      └──────────────────┘         │
│             ↓                         ↓                    │
│    Result: 5 characters      Result: 6 characters         │
│    With bounding boxes       With bounding boxes          │
│    + confidence scores       + confidence scores          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. OCR FUSION (ocr_fusion.py)                              │
│                                                             │
│    Step 1: Normalize Results                               │
│    - Convert to common format                              │
│    - Tag with source ("easyocr" or "paddleocr")           │
│                                                             │
│    Step 2: Align Characters                                │
│    - Calculate IoU (Intersection over Union)              │
│    - Match overlapping bounding boxes                      │
│    - Use greedy matching algorithm                         │
│                                                             │
│    Step 3: Fuse Candidates                                 │
│    - Combine results at each position                      │
│    - Keep all candidates from both engines                 │
│    - Dictionary-guided tie-breaking (CC-CEDICT)           │
│    - Select best character when confidence equal           │
│                                                             │
│    Step 4: Sort Reading Order                              │
│    - Top-to-bottom, left-to-right                         │
│    - Maintain proper character sequence                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. FUSED RESULT                                            │
│    - Best characters selected                              │
│    - All candidates preserved                              │
│    - Confidence scores calculated                          │
│    - Coverage percentage computed                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. TRANSLATION                                             │
│    CCDictionaryTranslator (120,474 entries)               │
│    ↓ (fallback if needed)                                  │
│    RuleBasedTranslator (276 entries)                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. FINAL RESPONSE                                          │
│    JSON with text, translation, glyphs, metadata          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 How to See Which Engine is Being Used

### **Method 1: Backend Console Logs** (Recommended)

#### Start the Backend:
```bash
cd services/inference
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

#### Startup Logs:
```
INFO: Attempting to initialize EasyOCR (langs=['ch_sim', 'en'])...
WARNING: Using CPU. Note: This module is much faster with a GPU.
INFO: EasyOCR initialized successfully with ch_sim and en

INFO: Attempting to initialize PaddleOCR...
INFO: PaddleOCR initialized successfully

✅ CC-CEDICT dictionary loaded successfully with 120,474 entries.
✅ CC-CEDICT translator initialized (120,474 entries, strategy: first).

INFO: OCR service ready (EasyOCR: True, PaddleOCR: True)
```

#### During Image Processing:
```
INFO: Preprocessing complete. Image shape: (800, 600, 3)

INFO: Starting parallel OCR execution (timeout: 60s)
INFO: EasyOCR detected 5 character(s)
INFO: PaddleOCR detected 6 character(s)

INFO: OCR results: EasyOCR=5 chars, PaddleOCR=6 chars

INFO: Fused 6 positions into 6 glyphs, text length: 6 
      (confidence: 89.50%, coverage: 80.0%) [Dict: CC-CEDICT]

INFO: CC-CEDICT translation completed: 100.0% coverage (6/6 characters)

DEBUG: CCDictionaryTranslator Stats: translations=1, characters=6, 
       mapped=6, unmapped=0, coverage=100.0%, strategy=first
```

**Key Log Messages to Watch:**

| Log Message | Meaning |
|-------------|---------|
| `EasyOCR detected N character(s)` | EasyOCR found N characters |
| `PaddleOCR detected N character(s)` | PaddleOCR found N characters |
| `OCR results: EasyOCR=X chars, PaddleOCR=Y chars` | Results from both engines |
| `Fused N positions into M glyphs` | Fusion completed successfully |
| `[Dict: CC-CEDICT]` | Using CC-CEDICT for fusion |
| `CC-CEDICT translation completed` | Using CC-CEDICT for translation |

---

### **Method 2: API Response** (JSON)

When you upload an image, check the response:

```json
{
  "text": "你好世界",
  "translation": "you good world boundary",
  "confidence": 0.89,               // OCR fusion average confidence
  "coverage": 100.0,                // Translation coverage
  "dictionary_source": "CC-CEDICT", // OCR fusion dictionary
  "dictionary_version": "1.0",      // Dictionary version
  "translation_source": "CC-CEDICT",// Translation dictionary
  "glyphs": [
    {
      "symbol": "你",
      "bbox": [10, 20, 50, 60],
      "confidence": 0.92,
      "meaning": "you",
      "candidates": [                // Shows both engine results
        {
          "text": "你",
          "confidence": 0.92,
          "source": "easyocr"        // ← EasyOCR result
        },
        {
          "text": "你", 
          "confidence": 0.88,
          "source": "paddleocr"      // ← PaddleOCR result
        }
      ]
    },
    {
      "symbol": "好",
      "bbox": [55, 20, 95, 60],
      "confidence": 0.85,
      "meaning": "good",
      "candidates": [
        {
          "text": "好",
          "confidence": 0.85,
          "source": "easyocr"
        },
        {
          "text": "妤",              // Different result!
          "confidence": 0.85,
          "source": "paddleocr"
        }
      ]
      // Note: "好" was selected because CC-CEDICT tie-breaking chose it
    }
  ]
}
```

**Key Fields:**

| Field | Shows |
|-------|-------|
| `glyphs[].candidates` | All OCR candidates from both engines |
| `glyphs[].candidates[].source` | Which engine: "easyocr" or "paddleocr" |
| `confidence` | Average OCR fusion confidence |
| `dictionary_source` | OCR fusion dictionary used |
| `translation_source` | Translation dictionary used |

---

### **Method 3: Browser DevTools** (Frontend Testing)

1. Open Rune-X in browser: `http://localhost:3001`
2. Press `F12` to open DevTools
3. Go to **Network** tab
4. Upload an image
5. Find the `/inference` request
6. Click it and view **Response** tab

You'll see the full JSON with all OCR engine results!

---

## 📊 OCR Fusion Example

### Example: Processing "你好"

**Input**: Image with Chinese text "你好"

**Step 1: Both Engines Run**
```
EasyOCR Results:
  - Character: "你", Confidence: 0.92, BBox: [10,20,50,60]
  - Character: "好", Confidence: 0.85, BBox: [55,20,95,60]

PaddleOCR Results:
  - Character: "你", Confidence: 0.88, BBox: [12,18,52,62]
  - Character: "妤", Confidence: 0.85, BBox: [56,19,96,61]
```

**Step 2: Alignment (IoU Matching)**
```
Position 1: BBox overlap detected
  - EasyOCR: "你" (0.92)
  - PaddleOCR: "你" (0.88)
  → Match! Same character, fuse them

Position 2: BBox overlap detected
  - EasyOCR: "好" (0.85)
  - PaddleOCR: "妤" (0.85)
  → Conflict! Different characters, same confidence
  → Use CC-CEDICT tie-breaking
  → "好" is more common → Select "好"
```

**Step 3: Fused Result**
```
Final Text: "你好"
Confidence: 88.5% (average of 0.92, 0.90, 0.85, 0.85)
Coverage: 100% (both characters in CC-CEDICT)
```

---

## 🎯 When Each Engine is Better

### **EasyOCR Excels At:**
- Handwritten text
- Stylized fonts
- Low-contrast images
- Mixed Chinese/English

### **PaddleOCR Excels At:**
- Printed Chinese text
- High-resolution images
- Standard fonts
- Fast processing needed

### **Fusion Advantage:**
- **Best of both worlds!**
- If one engine fails, other compensates
- Multiple candidates increase accuracy
- Dictionary-guided selection for ambiguous cases

---

## 💡 Code Locations

### Main OCR Logic:
- **File**: `services/inference/main.py`
- **Lines 225-264**: EasyOCR processing
- **Lines 267-353**: PaddleOCR processing
- **Lines 540-598**: Parallel execution & fusion

### OCR Fusion Module:
- **File**: `services/inference/ocr_fusion.py`
- **calculate_iou()**: Bounding box overlap calculation
- **align_ocr_outputs()**: Character alignment algorithm
- **fuse_character_candidates()**: Candidate fusion & selection

---

## 🔧 Configuration

### OCR Timeout:
```python
OCR_TIMEOUT = 60  # seconds per engine
```

### Parallel Execution:
```python
# Both engines run simultaneously using ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=2) as executor:
    futures['easyocr'] = executor.submit(run_easyocr, ...)
    futures['paddleocr'] = executor.submit(run_paddleocr, ...)
```

---

## 🚨 Fallback Behavior

### If EasyOCR Fails:
- PaddleOCR results still used
- System continues normally
- Warning logged

### If PaddleOCR Fails:
- EasyOCR results still used
- System continues normally
- Warning logged

### If Both Fail:
- HTTP 422 error returned
- "No text detected" message
- Suggestions provided

---

## 📝 Quick Test

Want to see it in action right now?

1. **Start Backend:**
   ```bash
   cd services/inference
   uvicorn main:app --host 0.0.0.0 --port 8001 --reload
   ```

2. **Watch Console Logs** for:
   - ✅ EasyOCR initialized
   - ✅ PaddleOCR initialized
   - ✅ CC-CEDICT loaded

3. **Upload Test Image** via frontend or API

4. **Observe Logs** showing:
   - EasyOCR detected N characters
   - PaddleOCR detected N characters
   - Fused N positions
   - Translation completed

5. **Check API Response** for:
   - `glyphs[].candidates[]` - Shows both engine results
   - `dictionary_source` - Shows CC-CEDICT
   - `translation_source` - Shows CC-CEDICT

---

## 🎉 Summary

**Current OCR System:**
- ✅ **Dual-Engine**: EasyOCR + PaddleOCR
- ✅ **Parallel Execution**: Both run simultaneously
- ✅ **Intelligent Fusion**: Best results selected
- ✅ **Dictionary-Guided**: CC-CEDICT for tie-breaking
- ✅ **Fully Observable**: Logs + API response show everything
- ✅ **Fault-Tolerant**: Works even if one engine fails

**Where to See It:**
1. **Backend console logs** - Real-time processing details
2. **API response JSON** - Complete results with candidates
3. **Browser DevTools** - Network tab, /inference request

**The system automatically uses BOTH engines and combines their results for maximum accuracy!** 🚀

