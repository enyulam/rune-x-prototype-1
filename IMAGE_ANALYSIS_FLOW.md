# Step-by-Step Image Analysis and Translation Flow

This document explains the complete logic flow of how the Rune-X platform processes images and generates translations.

## Overview

The platform uses a **hybrid OCR system** that combines EasyOCR and PaddleOCR engines, then fuses their results at the character level using the **OCR Fusion Module** with CC-CEDICT dictionary-guided tie-breaking. Translation is performed using a **three-tier system**: CC-CEDICT dictionary-based character translation (120,474 entries), MarianMT neural sentence translation via **MarianAdapter** (Phase 5) with token locking and semantic constraints, and Qwen LLM refinement via **QwenAdapter** (Phase 6) with token locking preservation and semantic confidence metrics.

---

## Phase 1: Frontend Upload & Initial Processing

### Step 1.1: User Uploads Image
**Location**: `src/app/upload/page.tsx`

- User selects an image file (JPG, PNG, WebP)
- Frontend validates file type and size
- Image is displayed in the upload interface

### Step 1.2: File Upload to Server
**Location**: `src/app/api/upload/route.ts`

1. **Authentication Check**: Verifies user is logged in
2. **File Storage**: 
   - Reads file bytes from request
   - Creates `uploads/` directory if needed
   - Generates unique filename: `{timestamp}-{originalName}`
   - Saves file to disk
3. **Database Record**:
   - Creates `Upload` record in database
   - Status: `PENDING`
   - Stores file path, original name, user ID
   - Optionally stores metadata (provenance, imaging method, script type)
4. **Response**: Returns `uploadId` to frontend

### Step 1.3: Trigger Processing
**Location**: `src/app/upload/page.tsx`

- Frontend receives `uploadId`
- Calls `/api/process` endpoint with `uploadId`
- Updates UI to show "Processing..." status

---

## Phase 2: Backend OCR Processing

### Step 2.1: Process Request Received
**Location**: `src/app/api/process/route.ts`

1. **Fetch Upload Record**: Retrieves upload from database using `uploadId`
2. **Update Status**: Changes status to `PROCESSING`
3. **Read File**: Loads image file from disk into buffer
4. **Prepare Form Data**: Creates multipart form with image file
5. **Forward to Inference Service**: POSTs to `http://localhost:8001/process-image`

---

## Phase 3: Image Preprocessing

### Step 3.1: File Validation
**Location**: `services/inference/main.py` → `process_image()`

- **Content Type Check**: Validates JPG, PNG, WebP, or `application/octet-stream`
- **File Size Check**: Ensures file ≤ 10MB
- **Empty File Check**: Rejects empty files

### Step 3.2: Image Preprocessing
**Location**: `services/preprocessing/image_preprocessing.py` → `preprocess_image()`  
**Wrapper**: `services/inference/main.py` → `_preprocess_image()`

The preprocessing system uses a **modular architecture** with two tiers of enhancements:

#### **Core Preprocessing Steps (FATAL - Must succeed)**

These steps are critical for OCR and will raise `HTTPException` if they fail:

1. **Image Loading & Format Validation**
   - Opens image with PIL from raw bytes
   - Validates format: JPEG, PNG, or WebP
   - Raises HTTPException (400) if unsupported
   - **Module**: `_validate_format()`

2. **Dimension Validation**
   - Minimum: 50×50 pixels
   - Maximum: 4000×4000 pixels (before resizing)
   - Raises HTTPException (400) if too small
   - **Module**: `_validate_dimensions()`

3. **Large Image Resizing**
   - Triggers if width or height > 4000px
   - Proportionally resizes to fit within 4000×4000px
   - Maintains aspect ratio using LANCZOS resampling
   - **Module**: `_resize_large_image()`

4. **RGB Color Conversion**
   - Converts non-RGB modes (RGBA, L, P) to RGB
   - Handles transparency by compositing on white background
   - Ensures consistent color space for OCR
   - **Module**: `_ensure_rgb()`

5. **Small Image Upscaling**
   - Triggers if any dimension < 300px
   - Calculates scale factor to reach 300px minimum
   - Upscales using LANCZOS resampling
   - Improves OCR accuracy for small text
   - **Module**: `_upscale_small_image()`

6. **Contrast Enhancement**
   - Increases contrast by 1.3× (configurable)
   - Uses `ImageEnhance.Contrast`
   - Improves text-background separation
   - **Module**: `_enhance_contrast()`

7. **Sharpness Enhancement**
   - Increases sharpness by 1.2× (configurable)
   - Uses `ImageEnhance.Sharpness`
   - Enhances edge definition
   - **Module**: `_enhance_sharpness()`

8. **Adaptive Padding**
   - Adds 50px padding (configurable) around image
   - Analyzes average brightness to determine color
   - White padding for bright images (>128), black for dark
   - Helps OCR detect edge characters
   - **Module**: `_add_adaptive_padding()`

#### **Optional Enhancement Steps (OPTIONAL - Fail gracefully)**

These steps enhance OCR quality but will only log warnings if they fail:

9. **Noise Reduction** (Bilateral Filter)
   - **Enabled by default** in production
   - Applies bilateral filter (preserves edges while reducing noise)
   - Parameters: d=9, sigmaColor=75, sigmaSpace=75
   - Recommended for: scanned/photographed documents
   - **Module**: `_apply_noise_reduction()`
   - **Requires**: opencv-python

10. **Binarization** (Adaptive Thresholding)
    - **Disabled by default** (can cause issues with some images)
    - Converts to black/white using adaptive thresholding
    - Block size: 11, constant: 2
    - Recommended for: high-contrast handwriting
    - **Module**: `_apply_binarization()`
    - **Requires**: opencv-python

11. **Deskewing** (Tilt Correction)
    - **Enabled by default** in production
    - Detects text rotation using Hough line transform
    - Corrects angles between -45° and +45°
    - Recommended for: rotated documents
    - **Module**: `_apply_deskew()`
    - **Requires**: opencv-python

12. **Brightness Normalization** (CLAHE)
    - **Enabled by default** in production
    - Applies Contrast Limited Adaptive Histogram Equalization
    - Clip limit: 2.0, tile grid: 8×8
    - Recommended for: unevenly lit images
    - **Module**: `_apply_brightness_normalization()`
    - **Requires**: opencv-python

13. **Array Conversion & Validation**
    - Converts PIL Image to NumPy array (uint8 format)
    - Validates dtype and shape
    - Clips values to [0, 255] range
    - Returns both NumPy array (for OCR) and PIL Image (for metadata)

#### **Configuration**

The preprocessing system is **fully configurable** via:

1. **Function Parameters** (runtime):
   ```python
   preprocess_image(
       img_bytes,
       apply_noise_reduction=True,
       apply_binarization=False,
       apply_deskew=True,
       apply_brightness_norm=True
   )
   ```

2. **Configuration File** (`services/preprocessing/config.py`):
   - 35+ parameters
   - Default values for all constants

3. **Environment Variables** (`.env`):
   - `PREPROCESSING_CONTRAST_FACTOR=1.3`
   - `PREPROCESSING_SHARPNESS_FACTOR=1.2`
   - `PREPROCESSING_PADDING_SIZE=50`
   - See `services/preprocessing/README.md` for complete list

#### **Error Handling Strategy**

- **Core Steps (1-8, 13)**: Raise `HTTPException` on failure (fatal errors)
- **Optional Steps (9-12)**: Log warnings and continue (graceful degradation)
- **OpenCV Unavailable**: Optional enhancements automatically disabled

**Output**: 
- NumPy array (uint8, RGB, [H, W, 3]) ready for OCR engines
- PIL Image object for metadata/logging

**Module Structure**:
```
services/preprocessing/
├── __init__.py
├── config.py               # Configuration & env variables
├── image_preprocessing.py  # Main preprocessing logic
├── README.md              # Full documentation
└── tests/
    ├── test_core_preprocessing.py      # 25 tests
    ├── test_optional_enhancements.py   # 20 tests
    └── test_toggle_combinations.py     # 16 permutation tests
```

**Test Coverage**: 61 unit tests, 100% pass rate

---

## Phase 4: Parallel OCR Execution

### Step 4.1: Initialize Parallel Execution
**Location**: `services/inference/main.py` → `process_image()`

- Creates `ThreadPoolExecutor` with 2 workers
- Submits both OCR tasks simultaneously
- Sets timeout: 30 seconds per engine

### Step 4.2: EasyOCR Processing
**Location**: `services/inference/main.py` → `run_easyocr()`

1. **OCR Execution**:
   - Calls `ocr_reader.readtext(img_array, detail=1, ...)`
   - Parameters: `width_ths=0.2`, `height_ths=0.2`, `paragraph=False`
   - Returns: `[[bbox, text, confidence], ...]`

2. **Result Normalization**:
   - For each detection:
     - Extracts bounding box: `[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]`
     - Converts to `[x1, y1, x2, y2]` format (min/max coordinates)
     - Normalizes confidence to [0, 1] range
     - **Character Splitting**: If text contains multiple characters, creates separate entries for each
   - Creates `NormalizedOCRResult` objects:
     ```python
     {
       bbox: [x1, y1, x2, y2],
       char: "我",
       confidence: 0.92,
       source: "easyocr"
     }
     ```

**Output**: List of normalized EasyOCR results

### Step 4.3: PaddleOCR Processing
**Location**: `services/inference/main.py` → `run_paddleocr()`

1. **OCR Execution**:
   - Calls `ocr_reader.ocr(img_array)`
   - Returns: `[[bbox, text, confidence], ...]` (version 3.x format)

2. **Result Normalization**:
   - Handles version differences (2.x vs 3.x format)
   - Extracts bounding box coordinates
   - Normalizes confidence to [0, 1]
   - **Character Splitting**: Creates separate entries for each character
   - Creates `NormalizedOCRResult` objects:
     ```python
     {
       bbox: [x1, y1, x2, y2],
       char: "我",
       confidence: 0.88,
       source: "paddleocr"
     }
     ```

**Output**: List of normalized PaddleOCR results

### Step 4.4: Wait for Results
- Both engines run concurrently
- System waits for both to complete (or timeout)
- If one fails, the other continues (graceful degradation)

---

## Phase 5: OCR Fusion (Character-Level Alignment & Selection)

**Module**: `services/inference/ocr_fusion.py`  
**Status**: ✅ Production-Ready (Phase 3: CC-CEDICT Integration)

### Step 5.1: Sort by Reading Order
**Location**: `services/inference/ocr_fusion.py` → `align_ocr_outputs()`

- Sorts EasyOCR results: primary by Y-coordinate (top), secondary by X-coordinate (left)
- Sorts PaddleOCR results: same reading order
- Ensures characters are processed in natural reading sequence

### Step 5.2: IoU-Based Alignment
**Location**: `services/inference/ocr_fusion.py` → `align_ocr_outputs()`

For each character position:

1. **Calculate IoU** (Intersection over Union):
   - Compares bounding boxes from both engines
   - Formula: `IoU = Intersection Area / Union Area`
   - Threshold: 0.3 (configurable)

2. **Matching Logic**:
   - If IoU ≥ 0.3: Characters are **aligned** (same position)
     - Creates `FusedPosition` with both candidates
     - Averages bounding boxes: `[(bbox1 + bbox2) / 2]`
     - Preserves both character hypotheses
   - If IoU < 0.3: Characters are **separate** (different positions)
     - Adds each as separate position
     - Maintains reading order

3. **Candidate Preservation**:
   - All character hypotheses are kept
   - No majority voting or discarding
   - Structure:
     ```python
     FusedPosition(
       position: 0,
       bbox: [avg_x1, avg_y1, avg_x2, avg_y2],
       candidates: [
         CharacterCandidate(char="我", confidence=0.92, source="easyocr"),
         CharacterCandidate(char="我", confidence=0.88, source="paddleocr")
       ]
     )
     ```

**Output**: List of `FusedPosition` objects with aligned candidates

### Step 5.3: Character Selection with CC-CEDICT Tie-Breaking
**Location**: `services/inference/ocr_fusion.py` → `fuse_character_candidates()`

For each fused position:

1. **Select Best Candidate**:
   - **If confidence differs clearly**: Chooses highest confidence candidate
   - **If confidence is equal** (tie): Uses **CC-CEDICT dictionary-guided tie-breaking**
     - Checks if candidates exist in CC-CEDICT dictionary (120,474 entries)
     - Prefers valid dictionary entries over non-dictionary characters
     - Example: If both "你" and "你" have 0.85 confidence, prefers valid dictionary entry

2. **Convert to Glyph Format**:
   - Converts bbox from `[x1, y1, x2, y2]` to `[x, y, w, h]`
   - Creates `Glyph` object:
     ```python
     Glyph(
       symbol: "我",
       bbox: [x, y, width, height],
       confidence: 0.92,
       meaning: None  # Will be filled in translation phase
     )
     ```

3. **Build Full Text**:
   - Concatenates all primary characters: `"我"`

4. **Calculate Quality Metrics**:
   - **Average Confidence**: Mean OCR confidence across all glyphs (0.0-1.0)
   - **Translation Coverage**: Percentage of characters with dictionary entries (0.0-100.0%)

**Output**: 
- List of `Glyph` objects
- Full text string: `"我"`
- Average confidence: `0.92`
- Translation coverage: `100.0%`

---

## Phase 6: CC-CEDICT Dictionary Translation

**Module**: `services/inference/cc_translation.py`  
**Status**: ✅ Production-Ready (Phase 4: CC-CEDICT Translation Module)  
**Dictionary**: CC-CEDICT with 120,474 entries (replaces 276-entry RuleBasedTranslator)

### Step 6.1: Initialize CC-CEDICT Translator
**Location**: `services/inference/main.py` → `process_image()`

- Initializes `CCDictionary` from `data/cc_cedict.json` (120,474 entries)
- Creates `CCDictionaryTranslator` instance
- Falls back to `RuleBasedTranslator` if CC-CEDICT unavailable

### Step 6.2: Character-Level Translation
**Location**: `services/inference/cc_translation.py` → `translate_text()`

For each character in the text:

1. **CC-CEDICT Lookup**:
   - Searches CC-CEDICT dictionary for character
   - Handles traditional/simplified forms automatically
   - Example: Looks up `"我"` → finds entry with multiple definitions

2. **Definition Selection**:
   - Uses `DefinitionStrategy` (default: `FIRST`)
   - Available strategies:
     - `FIRST`: Use first definition (default)
     - `SHORTEST`: Use shortest definition (most concise)
     - `MOST_COMMON`: Use most common English words (future)
     - `CONTEXT_AWARE`: Based on surrounding characters (future)

3. **Extract Meaning**:
   - Retrieves primary definition from CC-CEDICT entry
   - Example: `"我"` → `"I; me; myself; we; our"`
   - Stores all definitions for reference

4. **Enrich Glyph**:
   - Adds meaning to glyph object
   - Includes pinyin, traditional/simplified forms
   - Tracks unmapped characters (not in CC-CEDICT)

5. **Build Translation String**:
   - Concatenates meanings with separator: `" | "`
   - Example: `"I; me; myself; we; our | love; affection; like; care for; cherish | you; your; yourself"`

### Step 6.3: Calculate Statistics
**Location**: `services/inference/cc_translation.py` → `translate_text()`

- **Coverage**: Percentage of characters with CC-CEDICT entries
  - Formula: `(mapped_chars / total_chars) × 100`
  - Typical coverage: 80%+ (vs ~30% with RuleBasedTranslator)
- **Unmapped List**: Characters not found in CC-CEDICT
- **Dictionary Source**: "CC-CEDICT" or "RuleBasedTranslator" (fallback)
- **Dictionary Version**: CC-CEDICT version from metadata

**Output**: Translation result dictionary:
```python
{
  "glyphs": [enriched_glyph_objects],
  "translation": "I; me; myself; we; our | love; affection; like; care for; cherish | you; your; yourself",
  "unmapped": [],
  "coverage": 100.0,
  "translation_source": "CC-CEDICT",
  "dictionary_version": "1.0.0"
}
```

---

## Phase 7: Neural Sentence Translation (MarianAdapter - Phase 5)

**Module**: `services/inference/marian_adapter.py`  
**Status**: ✅ Production-Ready (Phase 5: MarianMT Refactoring)  
**Role**: Grammar and fluency optimizer under semantic constraints

### Step 7.1: Initialize MarianAdapter
**Location**: `services/inference/main.py` → `process_image()`

- Initializes `MarianAdapter` wrapping `SentenceTranslator`
- Loads `SemanticContract` for constraint enforcement
- MarianMT model loads lazily on first use (~300MB download)
- Falls back to direct `SentenceTranslator` if adapter unavailable

### Step 7.2: Identify Locked Tokens
**Location**: `services/inference/marian_adapter.py` → `_identify_locked_tokens()`

For each glyph:
1. **Check Locking Criteria**:
   - **Lock if**: OCR confidence ≥ 0.85 AND dictionary match exists
   - **Lock if**: OCR confidence ≥ 0.85 (even without dictionary)
   - **Unlock if**: OCR confidence < 0.70 (low confidence, allow improvement)
   - **Unlock if**: Multi-glyph ambiguity exists (let MarianMT resolve)

2. **Create Locked Token List**:
   - Stores glyph indices that must be preserved
   - Example: Glyphs 0, 1, 3, 4 locked (high confidence + dictionary)

### Step 7.3: Replace Locked Tokens with Placeholders
**Location**: `services/inference/marian_adapter.py` → `_replace_locked_with_placeholders()`

- Replaces locked Chinese characters with placeholders before MarianMT
- Format: `__LOCK_人__`, `__LOCK_好__`, etc.
- Example: `"你好世界"` → `"__LOCK_你____LOCK_好__世界"` (if "你" and "好" are locked)

### Step 7.4: MarianMT Translation
**Location**: `services/inference/marian_adapter.py` → `translate()`

1. **Input Validation**:
   - Checks if text is empty
   - Truncates to 512 characters if too long

2. **Tokenization**:
   - Converts Chinese text (with placeholders) to token IDs
   - Placeholders survive tokenization unchanged

3. **Neural Translation**:
   - MarianMT encoder-decoder generates English tokens
   - Processes entire sentence as context
   - Placeholders translate to themselves (preserved)

4. **Decoding**:
   - Converts token IDs back to English text
   - Placeholders remain intact

**Output**: English translation with placeholders
- Example: `"__LOCK_你____LOCK_好__世界"` → `"__LOCK_你____LOCK_好__ world"`

### Step 7.5: Restore Locked Tokens
**Location**: `services/inference/marian_adapter.py` → `_restore_locked_tokens()`

- Replaces placeholders with original Chinese characters
- Example: `"__LOCK_你____LOCK_好__ world"` → `"你好 world"`

### Step 7.6: Phrase-Level Refinement
**Location**: `services/inference/marian_adapter.py` → `_identify_phrase_spans()`

- Groups glyphs into `PhraseSpan` objects
- Identifies locked vs unlocked phrase spans
- Enables phrase-level semantic refinement (framework ready)

### Step 7.7: Track Token Changes & Calculate Metrics
**Location**: `services/inference/marian_adapter.py` → `_track_token_changes()`, `_calculate_semantic_metrics()`

- Tracks which tokens were changed vs preserved
- Calculates semantic confidence score (0.0-1.0)
- Computes token modification percentages
- Tracks dictionary override count

**Output**: `MarianAdapterOutput` with:
- `translation`: Natural English sentence translation
- `locked_tokens`: List of locked glyph indices
- `preserved_tokens`: List of preserved glyph indices
- `changed_tokens`: List of changed glyph indices
- `semantic_confidence`: Confidence score (0.0-1.0)
- `metadata`: Detailed metrics and statistics

**Example**: `"我爱你"` → `"I love you"` (with tokens 0, 1, 2 locked if high confidence)

### Step 7.8: Error Handling
- If adapter fails → falls back to direct `SentenceTranslator`
- If translation fails → returns `None` (graceful fallback)
- Logs errors for debugging
- Pipeline continues even if MarianMT fails

---

## Phase 8: Qwen LLM Refinement (QwenAdapter - Phase 6)

**Module**: `services/inference/qwen_adapter.py`  
**Status**: ✅ Production-Ready (Phase 6: Qwen 2.5B Refinement)  
**Role**: Fluency and coherence optimizer under constraints

### Step 8.1: Initialize QwenAdapter
**Location**: `services/inference/main.py` → `process_image()`

- Initializes `QwenAdapter` wrapping `QwenRefiner`
- Loads `QwenSemanticContract` for constraint enforcement
- Qwen model loads lazily on first use (~3GB download)
- Uses Qwen2.5-1.5B-Instruct model (CPU-friendly)
- Falls back to direct `QwenRefiner` if adapter unavailable

### Step 8.2: Map Glyphs to English Tokens
**Location**: `services/inference/qwen_adapter.py` → `_map_glyphs_to_english_tokens()`

- Maps Chinese glyph indices to English token indices (heuristic)
- Proportional mapping: `glyph_index ≈ round(token_index * (len(glyphs) / len(tokens)))`
- Derives locked English tokens from locked Chinese glyph indices
- Example: Locked glyphs [0, 1] → locked English tokens [0, 1]

### Step 8.3: Identify Phrase Spans
**Location**: `services/inference/qwen_adapter.py` → `_identify_phrase_spans()`

- Identifies contiguous spans of English tokens forming candidate phrases
- Groups tokens into `PhraseSpan` objects
- Marks spans as locked/unlocked based on token lock status
- Collects glyph indices for each phrase span

### Step 8.4: Replace Locked English Tokens with Placeholders
**Location**: `services/inference/qwen_adapter.py` → `_replace_locked_with_placeholders()`

- Replaces locked English tokens with placeholders before Qwen refinement
- Format: `__LOCK_T0__`, `__LOCK_T1__`, etc.
- Example: `"Hello world test"` → `"__LOCK_T0__ __LOCK_T1__ test"` (if tokens 0, 1 are locked)

### Step 8.5: Qwen Refinement
**Location**: `services/inference/qwen_adapter.py` → `translate()`

1. **Call QwenRefiner**:
   - Passes text with placeholders to `QwenRefiner.refine_translation_with_qwen()`
   - Qwen processes text (should preserve placeholders)
   - Original OCR text provided for context

2. **Qwen Inference** (internal to QwenRefiner):
   - Applies Qwen chat template to prompt
   - Uses Qwen2.5-1.5B-Instruct model
   - Parameters: `temperature=0.3`, `top_p=0.9`
   - Generates refined output

**Output**: Refined English translation with placeholders
- Example: `"__LOCK_T0__ __LOCK_T1__ test"` → `"__LOCK_T0__ __LOCK_T1__ test!"` (Qwen adds punctuation)

### Step 8.6: Restore Locked Tokens
**Location**: `services/inference/qwen_adapter.py` → `_restore_locked_tokens()`

- Replaces placeholders with original English tokens
- Example: `"__LOCK_T0__ __LOCK_T1__ test!"` → `"Hello world test!"`

### Step 8.7: Phrase-Level Refinement (Framework Ready)
**Location**: `services/inference/qwen_adapter.py` → `_refine_phrases()`

- Currently a placeholder (no-op, logs only)
- Future enhancement: Call Qwen on each unlocked phrase separately
- Merge refined phrases back into final text

### Step 8.8: Track Changes & Calculate Confidence
**Location**: `services/inference/qwen_adapter.py` → `_track_qwen_changes()`, `_calculate_qwen_confidence()`

- Tracks which English tokens were changed vs preserved
- Calculates `qwen_confidence` score (0.0-1.0) using weighted factors:
  - 40% weight: Locked token preservation rate
  - 30% weight: Unlocked token stability
  - 30% weight: Phrase-level fluency score (heuristic)

**Output**: `QwenAdapterOutput` with:
- `refined_text`: Refined English translation
- `changed_tokens`: List of modified English token indices
- `preserved_tokens`: List of preserved English token indices
- `locked_tokens`: List of locked English token indices
- `qwen_confidence`: Confidence score (0.0-1.0)
- `metadata`: Detailed metrics and statistics

**Example**: MarianMT `"I love you"` → Qwen `"I love you!"` (improved coherence, locked tokens preserved)

### Step 8.9: Error Handling
- If adapter fails → falls back to direct `QwenRefiner`
- If refinement fails → returns `None` (falls back to MarianMT translation)
- Logs errors for debugging
- Pipeline continues with MarianMT translation if Qwen fails

---

## Phase 9: Response Generation

### Step 9.1: Enrich Final Glyphs
**Location**: `services/inference/main.py` → `process_image()`

- Merges translation meanings into glyph objects
- Calculates average confidence across all glyphs
- Ensures all glyphs have meanings (if available)

### Step 9.2: Build Response
**Location**: `services/inference/main.py` → `process_image()`

Creates `InferenceResponse` with all three translation types and metadata:
```python
{
  "text": "我爱你",
  "translation": "I; me; myself; we; our | love; affection; like; care for; cherish | you; your; yourself",
  "sentence_translation": "I love you",
  "refined_translation": "I love you!",
  "qwen_status": "available",
  "confidence": 0.92,
  "glyphs": [
    {
      "symbol": "我",
      "bbox": [x, y, w, h],
      "confidence": 0.92,
      "meaning": "I; me; myself; we; our"
    },
    {
      "symbol": "爱",
      "bbox": [x, y, w, h],
      "confidence": 0.88,
      "meaning": "love; affection; like; care for; cherish"
    },
    {
      "symbol": "你",
      "bbox": [x, y, w, h],
      "confidence": 0.90,
      "meaning": "you; your; yourself"
    }
  ],
  "unmapped": [],
  "coverage": 100.0,
  "dictionary_source": "CC-CEDICT",
  "dictionary_version": "1.0.0",
  "translation_source": "CC-CEDICT",
  "semantic": {
    "engine": "MarianMT",
    "semantic_confidence": 0.85,
    "tokens_modified": 0,
    "tokens_locked": 3,
    "tokens_preserved": 3,
    "tokens_modified_percent": 0.0,
    "tokens_locked_percent": 100.0,
    "tokens_preserved_percent": 100.0,
    "dictionary_override_count": 0
  },
  "qwen": {
    "engine": "Qwen2.5-1.5B-Instruct",
    "qwen_confidence": 0.90,
    "tokens_modified": 1,
    "tokens_locked": 3,
    "tokens_preserved": 2,
    "tokens_modified_percent": 20.0,
    "tokens_locked_percent": 60.0,
    "tokens_preserved_percent": 40.0,
    "phrase_spans_refined": 1,
    "phrase_spans_locked": 1
  }
}
```

**Translation Fields Explained**:
- `translation`: CC-CEDICT dictionary-based character-level meanings (concatenated)
- `sentence_translation`: MarianMT neural sentence translation via MarianAdapter (context-aware, with token locking)
- `refined_translation`: Qwen-refined translation via QwenAdapter (improved coherence, OCR noise corrected, locked tokens preserved)
- `qwen_status`: Status of Qwen refinement ("available", "unavailable", "failed", "skipped")

**Metadata Fields**:
- `semantic`: MarianAdapter metadata (token locking, semantic confidence, change tracking)
- `qwen`: QwenAdapter metadata (token locking preservation, qwen_confidence, phrase spans)
- `dictionary_source`: OCR fusion dictionary source ("CC-CEDICT" or "Translator")
- `translation_source`: Translation dictionary source ("CC-CEDICT", "RuleBasedTranslator", or "Error")

### Step 9.3: Return to Frontend
**Location**: `services/inference/main.py` → `process_image()`

- Returns JSON response to Next.js API route
- Status code: 200 OK
- All three translation types included (if available)

---

## Phase 10: Frontend Display

### Step 10.1: Receive Response
**Location**: `src/app/api/process/route.ts`

- Receives JSON response from inference service
- Extracts all translation fields:
  - `translation` (dictionary-based)
  - `sentence_translation` (MarianMT)
  - `refined_translation` (Qwen)
- Updates database record:
  - Status: `COMPLETED`
  - Stores extracted text, all translations, glyphs
  - Stores `sentenceTranslation` and `refinedTranslation` in metadata

### Step 10.2: Display Results
**Location**: `src/app/upload/ResultsDisplay.tsx`

- Updates UI with results in "Translation & Context" section:
  - **Original Image**: Displayed via secure API endpoint (`/api/uploads/[id]`)
    - Images served directly from file system with authentication
    - Proper caching headers for performance
    - Images persist and don't disappear (no blob URL revocation)
  - **Extracted Text**: "我爱你"
  - **Character Meanings**: "I; me; myself; we; our | love; affection; like; care for; cherish | you; your; yourself"
  - **Full Sentence Translation**: "I love you" (MarianMT)
  - **Refined Translation**: "I love you" (Qwen - if available)
  - **Glyphs**: Individual character breakdown with meanings
  - **Confidence**: Overall confidence score
  - **Coverage**: Dictionary coverage percentage

### Step 10.3: Image Serving
**Location**: `src/app/api/uploads/[id]/route.ts`

- Secure image serving endpoint:
  - **Authentication**: Verifies user owns the upload
  - **File Access**: Reads image from file system (`uploads/` directory)
  - **Content-Type**: Automatically detects image format (JPEG, PNG, WebP)
  - **Caching**: Sets cache headers for 1 year (immutable)
  - **Error Handling**: Returns 404 if file not found or unauthorized

---

## Key Design Decisions

### Why Hybrid OCR?

1. **Complementary Strengths**:
   - EasyOCR: Better at stylized handwriting, mixed content
   - PaddleOCR: Better at standard Chinese text, higher accuracy

2. **Robustness**:
   - If one engine fails, the other continues
   - Parallel execution doesn't significantly increase total time

3. **Uncertainty Preservation**:
   - Multiple hypotheses per character position
   - Enables downstream confidence analysis

### Why Character-Level Fusion?

1. **Precision**: Aligns at the smallest unit (character) rather than word/phrase
2. **Flexibility**: Handles cases where engines detect different numbers of characters
3. **Uncertainty**: Preserves all candidate characters for analysis

### Why IoU-Based Alignment?

1. **Spatial Matching**: Uses bounding box overlap, not just text matching
2. **Handles Variations**: Works even if engines detect slightly different bounding boxes
3. **Configurable**: IoU threshold (0.3) balances strictness vs. flexibility

### Why CC-CEDICT Dictionary Translation?

1. **Comprehensive Coverage**: 120,474 entries (vs 276 in RuleBasedTranslator), 80%+ coverage
2. **Deterministic**: Consistent results, no API costs
3. **Fast**: Instant lookup, no network calls
4. **Multiple Definitions**: Handles multiple meanings per character with selection strategies
5. **Traditional/Simplified**: Automatic handling of character variants
6. **Transparent**: Users can see exact source of meanings

### Why MarianAdapter (MarianMT with Constraints)?

1. **Context-Aware**: Processes entire sentence as context, not just characters
2. **Natural Output**: Produces grammatically correct, fluent English
3. **Handles Grammar**: Understands sentence structure and word order
4. **Semantic Constraints**: Respects OCR fusion output and CC-CEDICT anchors
5. **Token Locking**: Preserves high-confidence glyph meanings (≥0.85 OCR + dictionary match)
6. **Phrase-Level Refinement**: Operates at phrase-level granularity for better context
7. **Explainable**: Provides semantic confidence metrics and change tracking
8. **Complementary**: Works alongside dictionary for comprehensive understanding

### Why QwenAdapter (Qwen with Constraints)?

1. **OCR Noise Correction**: Corrects mistranslations caused by OCR errors
2. **Coherence Improvement**: Enhances contextual coherence across sentences
3. **Fluency Enhancement**: Improves readability without altering meaning
4. **Token Locking Preservation**: Never alters locked tokens (from MarianAdapter)
5. **Semantic Constraints**: Respects MarianMT output and semantic constraints
6. **Phrase-Level Refinement**: Framework ready for phrase-level processing
7. **Semantic Confidence**: Provides qwen_confidence metrics for quality assessment
8. **Local Processing**: Fully local, no cloud APIs, deterministic
9. **Structure Preservation**: Maintains sentence order and paragraph boundaries
10. **Literal Accuracy**: Prefers accuracy over creative paraphrasing
11. **Explainable**: Provides transparency into what changed vs preserved

---

## Performance Characteristics

- **Total Processing Time**: 5-25 seconds (typical image)
  - First request: 30-90 seconds (model downloads + initialization)
  - Subsequent requests: 5-25 seconds
- **OCR Phase**: 2-5 seconds (both engines in parallel)
- **OCR Fusion**: < 100ms (alignment + character selection + CC-CEDICT tie-breaking)
- **CC-CEDICT Translation**: < 100ms (dictionary lookup, 120,474 entries)
- **MarianAdapter Translation**: 1-4 seconds (neural inference + token locking + phrase refinement)
- **QwenAdapter Refinement**: 5-15 seconds (LLM inference + token locking + confidence calculation, CPU-dependent)
- **Memory Usage**: ~3-5GB (OCR engines + MarianMT + Qwen models loaded)
  - EasyOCR: ~500MB
  - PaddleOCR: ~500MB
  - CC-CEDICT Dictionary: ~50MB (JSON in memory)
  - MarianMT: ~300MB
  - Qwen2.5-1.5B: ~3GB

---

## Error Handling

The system includes comprehensive error handling at each phase:

1. **File Validation**: Rejects invalid formats/sizes early
2. **OCR Failures**: One engine can fail, other continues (graceful degradation)
3. **No Text Detected**: Returns 422 with helpful message
4. **OCR Fusion Failures**: Falls back to single-engine results if fusion fails
5. **CC-CEDICT Failures**: Falls back to RuleBasedTranslator (276 entries) if CC-CEDICT unavailable
6. **Dictionary Misses**: Tracks unmapped characters for expansion
7. **MarianAdapter Failures**: Falls back to direct SentenceTranslator, then returns `None` if unavailable
8. **QwenAdapter Failures**: Falls back to direct QwenRefiner, then to MarianMT translation, doesn't break pipeline
9. **Timeouts**: 30-second timeout per OCR engine
10. **Model Loading**: Lazy loading with error handling, graceful fallback if models unavailable
11. **Token Locking Failures**: Logs warnings but continues processing (non-fatal)
12. **Semantic Metrics Failures**: Returns default values if calculation fails (non-fatal)

---

## Example Flow: Processing "我爱你" (I love you)

1. **Upload**: User uploads image of "我爱你"
2. **Preprocessing**: Image upscaled, contrast enhanced, padded
3. **EasyOCR**: Detects "我", "爱", "你" with confidences [0.92, 0.88, 0.90]
4. **PaddleOCR**: Detects "我", "爱", "你" with confidences [0.88, 0.85, 0.92]
5. **OCR Fusion**: 
   - Alignment: All characters aligned (IoU > 0.3 for each)
   - Fusion: Creates fused positions with both candidates for each character
   - Selection: Chooses highest confidence candidate (with CC-CEDICT tie-breaking if needed)
   - Metrics: Average confidence 0.92, coverage 100.0%
6. **CC-CEDICT Translation**: 
   - Lookup → "I; me; myself; we; our | love; affection; like; care for; cherish | you; your; yourself"
   - Translation source: "CC-CEDICT"
7. **MarianAdapter Translation**: 
   - Token locking: All 3 glyphs locked (high confidence + dictionary match)
   - Placeholders: `"__LOCK_我____LOCK_爱____LOCK_你__"`
   - Neural translation → `"__LOCK_我____LOCK_爱____LOCK_你__"` → "I love you" (after restoration)
   - Semantic metrics: confidence 0.85, tokens_locked 3, tokens_modified 0
8. **QwenAdapter Refinement**: 
   - Glyph-to-token mapping: Glyphs [0,1,2] → English tokens [0,1,2]
   - Token locking: English tokens [0,1,2] locked
   - Placeholders: `"__LOCK_T0__ __LOCK_T1__ __LOCK_T2__"`
   - Qwen refinement → `"__LOCK_T0__ __LOCK_T1__ __LOCK_T2__!"` → "I love you!" (after restoration)
   - Qwen metrics: qwen_confidence 0.90, tokens_locked 3, tokens_modified 1 (punctuation)
9. **Response**: Returns complete result with:
    - CC-CEDICT dictionary translation (character meanings)
    - MarianAdapter translation (sentence-level with token locking)
    - QwenAdapter refined translation (enhanced with locked tokens preserved)
    - Glyphs with meanings and confidence scores
    - Semantic metadata (MarianAdapter metrics)
    - Qwen metadata (QwenAdapter metrics)

---

This hybrid approach provides robust, accurate OCR with comprehensive three-tier translation capabilities:
- **CC-CEDICT Dictionary**: Character-level meanings (120,474 entries, 80%+ coverage) for detailed understanding
- **MarianAdapter**: Context-aware sentence translation with semantic constraints (token locking, phrase-level refinement) for natural English
- **QwenAdapter**: Enhanced coherence and OCR noise correction with token locking preservation and semantic confidence metrics

The system preserves uncertainty information for downstream analysis while providing multiple translation perspectives for comprehensive understanding. All translation stages respect high-confidence OCR-decoded glyphs through token locking mechanisms, ensuring reliable preservation of dictionary-anchored meanings.

