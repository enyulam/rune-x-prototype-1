# Step-by-Step Image Analysis and Translation Flow

This document explains the complete logic flow of how the Rune-X platform processes images and generates translations.

## Overview

The platform uses a **hybrid OCR system** that combines EasyOCR and PaddleOCR engines, then fuses their results at the character level. Translation is performed using a **three-tier system**: dictionary-based character translation, MarianMT neural sentence translation, and Qwen LLM refinement for improved coherence and OCR noise correction.

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
**Location**: `services/inference/main.py` → `_preprocess_image()`

The preprocessing pipeline optimizes images for OCR:

1. **Load Image**: Opens image with PIL (Python Imaging Library)
2. **Format Validation**: Ensures JPEG, PNG, or WebP format
3. **Dimension Check**: 
   - Minimum: 50×50 pixels
   - Maximum: 4000×4000 pixels (auto-resized if larger)
4. **Color Mode**: Converts to RGB if needed
5. **Small Image Enhancement**:
   - If image < 300px on any dimension:
     - Calculates scale factor to reach 300px minimum
     - Upscales using LANCZOS resampling
6. **Contrast Enhancement**:
   - Increases contrast by 1.3×
   - Sharpens image by 1.2×
7. **Padding Addition**:
   - Adds 50px padding around image
   - Background color: black (if image is dark) or white (if image is bright)
   - Helps OCR detect edge characters
8. **Array Conversion**: Converts PIL Image to NumPy array (uint8, 0-255 range)

**Output**: Preprocessed NumPy array ready for OCR engines

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

## Phase 5: Result Alignment & Fusion

### Step 5.1: Sort by Reading Order
**Location**: `services/inference/main.py` → `align_ocr_outputs()`

- Sorts EasyOCR results: primary by Y-coordinate (top), secondary by X-coordinate (left)
- Sorts PaddleOCR results: same reading order
- Ensures characters are processed in natural reading sequence

### Step 5.2: IoU-Based Alignment
**Location**: `services/inference/main.py` → `align_ocr_outputs()`

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

### Step 5.3: Character Selection
**Location**: `services/inference/main.py` → `fuse_character_candidates()`

For each fused position:

1. **Select Best Candidate**:
   - Chooses highest confidence candidate as primary
   - Example: If EasyOCR=0.92, PaddleOCR=0.88 → selects EasyOCR's "我"

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

**Output**: 
- List of `Glyph` objects
- Full text string: `"我"`

---

## Phase 6: Dictionary-Based Translation

### Step 6.1: Prepare Translation Input
**Location**: `services/inference/main.py` → `process_image()`

- Converts `Glyph` objects to dictionary format:
  ```python
  [
    {"symbol": "我", "bbox": [...], "confidence": 0.92},
    ...
  ]
  ```

### Step 6.2: Dictionary Lookup
**Location**: `services/inference/translator.py` → `translate_text()`

For each character in the text:

1. **Exact Match Lookup**:
   - Searches `dictionary.json` for character
   - Example: Looks up `"我"` → finds entry

2. **Alternative Form Check**:
   - If not found, searches `alts` fields in all entries
   - Handles variant character forms

3. **Extract Meaning**:
   - Retrieves `meaning` field from dictionary entry
   - Example: `"我"` → `"I; me; myself; we; our"`

4. **Enrich Glyph**:
   - Adds meaning to glyph object
   - Tracks unmapped characters (not in dictionary)

5. **Build Translation String**:
   - Concatenates meanings with separator: `" | "`
   - Example: `"I; me; myself; we; our | love; affection; like; care for; cherish | you; your; yourself"`

### Step 6.3: Calculate Statistics
**Location**: `services/inference/translator.py` → `translate_text()`

- **Coverage**: Percentage of characters with dictionary entries
  - Formula: `(mapped_chars / total_chars) × 100`
- **Unmapped List**: Characters not found in dictionary
- **Dictionary Version**: Version from dictionary metadata

**Output**: Translation result dictionary:
```python
{
  "glyphs": [enriched_glyph_objects],
  "translation": "I; me; myself; we; our | love; affection; like; care for; cherish | you; your; yourself",
  "unmapped": [],
  "coverage": 100.0,
  "dictionary_version": "1.0.0"
}
```

---

## Phase 7: Neural Sentence Translation (MarianMT)

### Step 7.1: Initialize MarianMT Translation
**Location**: `services/inference/main.py` → `process_image()`

- Checks if `sentence_translator` is available
- MarianMT model loads lazily on first use (~300MB download)

### Step 7.2: Translate Full Sentence
**Location**: `services/inference/sentence_translator.py` → `translate()`

1. **Input Validation**:
   - Checks if text is empty
   - Truncates to 512 characters if too long

2. **Tokenization**:
   - Converts Chinese text to token IDs using MarianMT tokenizer
   - Adds padding and truncation
   - Returns PyTorch tensors

3. **Neural Translation**:
   - MarianMT encoder-decoder generates English tokens
   - Processes entire sentence as context
   - Considers full sentence structure

4. **Decoding**:
   - Converts token IDs back to English text
   - Removes special tokens (padding, etc.)

**Output**: Natural English sentence translation
- Example: `"我爱你"` → `"I love you"`

### Step 7.3: Error Handling
- If translation fails → returns `None` (graceful fallback)
- Logs errors for debugging
- Pipeline continues even if MarianMT fails

---

## Phase 8: Qwen LLM Refinement

### Step 8.1: Initialize Qwen Refiner
**Location**: `services/inference/main.py` → `process_image()`

- Checks if `qwen_refiner` is available
- Qwen model loads lazily on first use (~3GB download)
- Uses Qwen2.5-1.5B-Instruct model (CPU-friendly)

### Step 8.2: Detect Sentence Boundaries
**Location**: `services/inference/qwen_refiner.py` → `_detect_sentence_boundaries()`

- Splits OCR text on periods, line breaks, and Chinese punctuation (。！？)
- Preserves sentence structure for better refinement
- Handles single sentences or multiple sentences

**Example**:
- Input: `"我爱你。你好吗？"`
- Output: `["我爱你。", "你好吗？"]`

### Step 8.3: Create Refinement Prompt
**Location**: `services/inference/qwen_refiner.py` → `_create_refinement_prompt()`

Creates prompt with:
- Original OCR text (may contain noise)
- MarianMT translation
- Instructions to:
  - Correct OCR noise-induced mistranslations
  - Improve contextual coherence
  - Improve fluency without adding information
  - Preserve sentence order and structure
  - Prefer literal accuracy over creative paraphrasing
  - Avoid hallucination

### Step 8.4: Qwen Inference
**Location**: `services/inference/qwen_refiner.py` → `refine_translation_with_qwen()`

1. **Format Input**:
   - Applies Qwen chat template to prompt
   - Tokenizes input for model

2. **Generate Refined Translation**:
   - Uses Qwen model to generate refined output
   - Parameters:
     - `temperature=0.3` (deterministic)
     - `max_new_tokens` (limited to prevent excessive generation)
     - `top_p=0.9` (nucleus sampling)

3. **Decode Response**:
   - Converts token IDs to text
   - Cleans up tokenization artifacts

4. **Validation**:
   - Checks output length (not too short/long)
   - Ensures reasonable quality

**Output**: Refined English translation
- Example: MarianMT `"I love you"` → Qwen `"I love you"` (improved coherence, corrected OCR noise)

### Step 8.5: Error Handling
- If refinement fails → returns `None` (falls back to MarianMT)
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

Creates `InferenceResponse` with all three translation types:
```python
{
  "text": "我爱你",
  "translation": "I; me; myself; we; our | love; affection; like; care for; cherish | you; your; yourself",
  "sentence_translation": "I love you",
  "refined_translation": "I love you",
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
  "dictionary_version": "1.0.0"
}
```

**Translation Fields Explained**:
- `translation`: Dictionary-based character-level meanings (concatenated)
- `sentence_translation`: MarianMT neural sentence translation (context-aware)
- `refined_translation`: Qwen-refined translation (improved coherence, OCR noise corrected)

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
  - **Extracted Text**: "我爱你"
  - **Character Meanings**: "I; me; myself; we; our | love; affection; like; care for; cherish | you; your; yourself"
  - **Full Sentence Translation**: "I love you" (MarianMT)
  - **Refined Translation**: "I love you" (Qwen - if available)
  - **Glyphs**: Individual character breakdown with meanings
  - **Confidence**: Overall confidence score
  - **Coverage**: Dictionary coverage percentage

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

### Why Dictionary-Based Translation?

1. **Deterministic**: Consistent results, no API costs
2. **Fast**: Instant lookup, no network calls
3. **Extensible**: Easy to add new characters
4. **Transparent**: Users can see exact source of meanings

### Why MarianMT Neural Translation?

1. **Context-Aware**: Processes entire sentence as context, not just characters
2. **Natural Output**: Produces grammatically correct, fluent English
3. **Handles Grammar**: Understands sentence structure and word order
4. **Complementary**: Works alongside dictionary for comprehensive understanding

### Why Qwen LLM Refinement?

1. **OCR Noise Correction**: Corrects mistranslations caused by OCR errors
2. **Coherence Improvement**: Enhances contextual coherence across sentences
3. **Fluency Enhancement**: Improves readability without altering meaning
4. **Local Processing**: Fully local, no cloud APIs, deterministic
5. **Structure Preservation**: Maintains sentence order and paragraph boundaries
6. **Literal Accuracy**: Prefers accuracy over creative paraphrasing

---

## Performance Characteristics

- **Total Processing Time**: 5-20 seconds (typical image)
  - First request: 30-90 seconds (model downloads + initialization)
  - Subsequent requests: 5-20 seconds
- **OCR Phase**: 2-5 seconds (both engines in parallel)
- **Alignment/Fusion**: < 100ms
- **Dictionary Translation**: < 50ms (dictionary lookup)
- **MarianMT Translation**: 1-3 seconds (neural inference)
- **Qwen Refinement**: 5-15 seconds (LLM inference, CPU-dependent)
- **Memory Usage**: ~3-5GB (OCR engines + MarianMT + Qwen models loaded)
  - EasyOCR: ~500MB
  - PaddleOCR: ~500MB
  - MarianMT: ~300MB
  - Qwen2.5-1.5B: ~3GB

---

## Error Handling

The system includes comprehensive error handling at each phase:

1. **File Validation**: Rejects invalid formats/sizes early
2. **OCR Failures**: One engine can fail, other continues (graceful degradation)
3. **No Text Detected**: Returns 422 with helpful message
4. **Dictionary Misses**: Tracks unmapped characters for expansion
5. **MarianMT Failures**: Falls back gracefully, returns `None` if unavailable
6. **Qwen Refinement Failures**: Falls back to MarianMT translation, doesn't break pipeline
7. **Timeouts**: 30-second timeout per OCR engine
8. **Model Loading**: Lazy loading with error handling, graceful fallback if models unavailable

---

## Example Flow: Processing "我爱你" (I love you)

1. **Upload**: User uploads image of "我爱你"
2. **Preprocessing**: Image upscaled, contrast enhanced, padded
3. **EasyOCR**: Detects "我", "爱", "你" with confidences [0.92, 0.88, 0.90]
4. **PaddleOCR**: Detects "我", "爱", "你" with confidences [0.88, 0.85, 0.92]
5. **Alignment**: All characters aligned (IoU > 0.3 for each)
6. **Fusion**: Creates fused positions with both candidates for each character
7. **Selection**: Chooses highest confidence candidate for each position
8. **Dictionary Translation**: Lookup → "I; me; myself; we; our | love; affection; like; care for; cherish | you; your; yourself"
9. **MarianMT Translation**: Neural translation → "I love you"
10. **Qwen Refinement**: Refines MarianMT output → "I love you" (improved coherence, corrected any OCR noise)
11. **Response**: Returns complete result with:
    - Dictionary translation (character meanings)
    - MarianMT translation (sentence-level)
    - Qwen refined translation (enhanced)
    - Glyphs with meanings and confidence scores

---

This hybrid approach provides robust, accurate OCR with comprehensive three-tier translation capabilities:
- **Dictionary-based**: Character-level meanings for detailed understanding
- **MarianMT**: Context-aware sentence translation for natural English
- **Qwen Refinement**: Enhanced coherence and OCR noise correction

The system preserves uncertainty information for downstream analysis while providing multiple translation perspectives for comprehensive understanding.

