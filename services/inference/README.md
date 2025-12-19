# Rune-X Inference Service

FastAPI service for Chinese handwriting OCR with hybrid OCR system, three-tier translation (dictionary + MarianMT + Qwen), and comprehensive 13-step image preprocessing pipeline.

## ✅ Status: FULLY OPERATIONAL

**Verified December 2025**: All systems active and tested.

- ✅ **EasyOCR**: Ready
- ✅ **PaddleOCR**: Ready
- ✅ **MarianMT**: Ready (with sentencepiece)
- ✅ **Qwen Refiner**: Ready
- ✅ **CC-CEDICT Dictionary**: 120,474 entries loaded
- ✅ **Preprocessing**: All 61 tests passing

## Features

- **Hybrid OCR System**: Runs EasyOCR and PaddleOCR in parallel, then fuses results at character level using dedicated `ocr_fusion.py` module
- **OCR Fusion Module**: Production-grade fusion with CC-CEDICT intelligent tie-breaking (120,474 entries), quality metrics, and comprehensive logging (30 tests, 100% pass rate)
- **Character-Level Fusion**: Preserves all character hypotheses from both engines using greedy IoU-based alignment with reading order preservation
- **Optimized Preprocessing**: Minimal preprocessing for handwritten text (aggressive steps disabled to preserve character integrity)
- **Three-Tier Translation System**: 
  - **Dictionary-Based Translation**: Character-level meanings from CC-CEDICT (120,474 entries with traditional/simplified forms, pinyin, and multiple definitions)
  - **Neural Sentence Translation**: Grammar and fluency optimization using MarianMT (Helsinki-NLP/opus-mt-zh-en) via MarianAdapter with semantic constraints (Phase 5)
  - **LLM Refinement**: Qwen2.5-1.5B-Instruct model for refining translations, correcting OCR noise, and improving coherence
- **CC-CEDICT Dictionary**: Comprehensive JSON-based Chinese-English dictionary with 120,474 entries including traditional/simplified forms, pinyin, and multiple English definitions per character
- **Modular Image Preprocessing**: Production-grade preprocessing system with 13 configurable steps (8 core + 4 optional + validation), fully tested with 61 unit tests (100% pass rate), configurable via environment variables with 35+ tunable parameters
- **Error Handling**: Comprehensive error messages and validation with graceful fallback
- **Performance**: Optimized for various image sizes with automatic resizing

## Architecture

### Hybrid OCR System

The service implements a dual-engine OCR approach:

1. **Parallel Execution**: Both EasyOCR and PaddleOCR run simultaneously on the same preprocessed image
2. **Output Normalization**: Results from both engines are normalized to a common format
3. **Alignment**: Character positions are aligned using Intersection over Union (IoU) matching
4. **Fusion**: All character candidates are preserved at each aligned position
5. **Reading Order**: Final sequence sorted top-to-bottom, left-to-right

### OCR Fusion Module (`ocr_fusion.py`)

**Status**: ✅ Production-Ready (December 2025)

A dedicated, modular system for fusing OCR results from multiple engines with advanced features:

#### **Core Components**:
- **`calculate_iou()`**: Computes bounding box overlap (Intersection over Union)
- **`align_ocr_outputs()`**: Aligns characters using greedy IoU matching with reading order preservation
- **`fuse_character_candidates()`**: Selects best character from aligned candidates with intelligent tie-breaking

#### **Key Features**:
- ✅ **Intelligent Tie-Breaking**: CC-CEDICT dictionary (120,474 entries) resolves equal confidence scenarios by preferring valid dictionary entries
- ✅ **Confidence-Based Selection**: Selects highest confidence character when confidence differs clearly
- ✅ **Quality Metrics**: Computes average OCR confidence and translation coverage percentage
- ✅ **Production Logging**: 15 strategic log points tracking all fusion decisions
- ✅ **Comprehensive Testing**: 30 unit tests with 100% pass rate
- ✅ **Type Safety**: Full Pydantic model validation (NormalizedOCRResult, CharacterCandidate, FusedPosition, Glyph)

#### **Metrics**:
- **Average Confidence**: Mean OCR confidence across all recognized characters (0.0-1.0)
- **Translation Coverage**: Percentage of characters with dictionary entries (0.0-100.0%)

#### **Example Log Output**:
```
INFO - Starting OCR alignment: 5 EasyOCR results, 5 PaddleOCR results (IoU threshold: 0.30)
INFO - Alignment summary: 5 total positions (4 aligned, 1 EasyOCR-only, 0 PaddleOCR-only)
INFO - Starting character fusion: 5 positions, translator: enabled
INFO - Position 2: Selected '学' from EasyOCR (conf: 0.95 > 0.85)
INFO - Position 4: Dictionary-guided selection '好' (tie-broken from equal confidence candidates)
INFO - Fusion complete: 5 glyphs, 5 characters | Tie-breaks: 1 (dictionary-guided: 1) | Avg confidence: 92.40%, Coverage: 80.0%
```

### OCR Engines

- **EasyOCR**: 
  - Languages: Chinese Simplified (`ch_sim`) + English (`en`)
  - Format: `[[bbox, text, confidence], ...]`
  - Strengths: Good for stylized handwriting, mixed content
  
- **PaddleOCR**:
  - Languages: Chinese (`ch`)
  - Format: `[[bbox, text, confidence], ...]` (version 3.x)
  - Strengths: High accuracy for standard Chinese text, advanced models

## Setup

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. **Install dependencies**:
```bash
cd services/inference
pip install -r requirements.txt
```

**Note**: 
- EasyOCR requires PyTorch and torchvision (install separately based on your system)
- PaddleOCR will automatically download model files on first use (requires internet connection, ~200-300MB)
- MarianMT (transformers) will download translation model on first use (~300MB from HuggingFace)
- **SentencePiece** is required for MarianMT tokenization (installed via requirements.txt)
- Qwen2.5-1.5B-Instruct will download on first use (~3GB from HuggingFace)
- Both OCR engines will initialize on first request (takes 20-60 seconds)
- Translation engines (MarianMT, Qwen) load models lazily (on first translation request)

2. **Install PyTorch** (required for EasyOCR):
```bash
# CPU version (recommended for most users)
pip install torch torchvision

# GPU version (if you have CUDA)
# See: https://pytorch.org/get-started/locally/
```

3. **Verify installation**:
```bash
python -c "import easyocr; import paddleocr; from transformers import MarianMTModel, MarianTokenizer, AutoModelForCausalLM; import accelerate; import sentencepiece; print('All dependencies installed successfully')"
```

4. **Dictionary**: The dictionary file is located at `data/dictionary.json`. 
   - Contains 276+ Chinese character entries
   - Format: `{character: {meaning, pinyin, alts[], notes}}`
   - Can be extended with more characters as needed

5. **Run the service**:
```bash
# From the services/inference directory
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Or use the startup script from project root
.\start-backend.ps1  # Windows PowerShell
# or
start-backend.bat    # Windows CMD
```

The service will be available at `http://localhost:8001`

### Platform-Specific Notes

#### Windows
- May require Visual C++ Redistributable
- If installation fails, try: `pip install paddleocr paddlepaddle --no-cache-dir`
- Use PowerShell or CMD (not Git Bash) for startup scripts

#### Linux
- May require system libraries: `sudo apt-get install libgl1 libglib2.0-0`
- For headless servers, use `opencv-python-headless` (already in requirements.txt)

#### macOS
- Should work out of the box with pip install
- If issues occur, ensure Xcode command line tools are installed

## API Endpoints

### `GET /health`

Health check endpoint. Returns status of both OCR engines and dictionary.

**Example Response**:
```json
{
  "status": "ok",
  "ocr_engines": {
    "easyocr": {
      "available": true,
      "status": "ready"
    },
    "paddleocr": {
      "available": true,
      "status": "ready"
    }
  },
  "translation_engines": {
    "marianmt": {
      "available": true,
      "status": "ready"
    },
    "qwen_refiner": {
      "available": true,
      "status": "ready",
      "model": "Qwen2.5-1.5B-Instruct"
    }
  },
  "dictionary": {
    "entries": 276,
    "entries_with_alts": 188,
    "entries_with_notes": 276,
    "version": "1.0.0"
  },
  "limits": {
    "max_image_size_mb": 10.0,
    "max_dimension": 4000,
    "min_dimension": 50,
    "supported_formats": ["image/jpeg", "image/jpg", "image/png", "image/webp"]
  }
}
```

### `POST /process-image`

Process an uploaded image for OCR and translation using hybrid OCR system.

**Request**: 
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: Form field `file` containing image file (JPG, PNG, or WebP)
- Max file size: 10MB
- Max dimensions: 4000x4000 pixels (auto-resized if larger)

**Response**:
```json
{
  "text": "我爱你",
  "translation": "I; me; myself; we; our | love; affection; like; care for; cherish | you; your; yourself",
  "sentence_translation": "I love you",
  "refined_translation": "I love you",
  "qwen_status": "available",
  "confidence": 0.92,
  "glyphs": [
    {
      "symbol": "我",
      "bbox": [10, 20, 50, 50],
      "confidence": 0.92,
      "meaning": "I; me; myself; we; our"
    },
    {
      "symbol": "爱",
      "bbox": [60, 20, 100, 50],
      "confidence": 0.88,
      "meaning": "love; affection; like; care for; cherish"
    },
    {
      "symbol": "你",
      "bbox": [110, 20, 150, 50],
      "confidence": 0.90,
      "meaning": "you; your; yourself"
    }
  ],
  "unmapped": [],
  "coverage": 100.0,
  "dictionary_version": "1.0.0"
}
```

**Translation Fields**:
- `translation`: Dictionary-based character-level translation (concatenated meanings)
- `sentence_translation`: Neural sentence-level translation using MarianMT (context-aware, natural English)
- `refined_translation`: Qwen LLM-refined translation (improved coherence, OCR noise corrected)
- `qwen_status`: Status of Qwen refinement ("available", "unavailable", "failed", "skipped")

**Processing Flow**:
1. Image preprocessing (13-step modular pipeline):
   - **Core Steps (FATAL)**: Format validation, dimension validation, large image resizing, RGB conversion, small image upscaling, contrast enhancement, sharpness enhancement, adaptive padding
   - **Optional Enhancements**: Noise reduction (bilateral filter), binarization (adaptive thresholding), deskewing (Hough transform), brightness normalization (CLAHE)
   - **Final Validation**: Array conversion and validation
2. Parallel OCR execution (EasyOCR + PaddleOCR)
3. Result normalization and alignment
4. Character-level fusion
5. Dictionary lookup and character-level translation
6. Neural sentence-level translation (MarianMT)
7. Qwen LLM refinement of MarianMT translation (if available)
8. Response generation

## Hybrid OCR Details

### Output Normalization

Both OCR engines return results in a normalized format:
```python
{
  "bbox": [x1, y1, x2, y2],
  "char": "我",
  "confidence": 0.92,
  "source": "easyocr" | "paddleocr"
}
```

### Alignment Algorithm

- Uses Intersection over Union (IoU) to match bounding boxes
- Default IoU threshold: 0.3 (configurable)
- Handles multi-character detections by splitting into individual characters
- Preserves reading order (top-to-bottom, left-to-right)

### Fusion Strategy

- All character candidates from both engines are preserved
- No majority voting or candidate discarding
- Highest confidence candidate selected as primary for each position
- Multiple candidates available for uncertainty analysis

## Translation System

### Three-Tier Translation Approach

The service provides three complementary translation methods:

1. **Dictionary-Based Translation** (`translation` field):
   - Character-by-character lookup from `dictionary.json`
   - Concatenates meanings with ` | ` separator
   - Fast, deterministic, preserves all character meanings
   - Example: "我 | 爱 | 你" → "I; me; myself; we; our | love; affection; like; care for; cherish | you; your; yourself"

2. **Neural Sentence Translation** (`sentence_translation` field):
   - Uses MarianMT model (Helsinki-NLP/opus-mt-zh-en) via **MarianAdapter** (Phase 5)
   - **Role**: Grammar and fluency optimizer under semantic constraints
   - **Behavior**: 
     - Respects OCR fusion output and CC-CEDICT dictionary anchors
     - Improves fluency, grammar, and phrase-level meaning
     - Never contradicts high-confidence glyph anchors (≥0.85 OCR confidence + dictionary match)
   - **Token Locking**: High-confidence glyphs with dictionary matches are locked and preserved
   - **Phrase-Level Refinement**: Operates at phrase-level granularity for better context handling
   - **Semantic Metrics**: Provides confidence scores and change tracking via `semantic` field in API response
   - Example: "我爱你" → "I love you" (with locked tokens preserved)
   - Lazy-loaded (model downloads on first use, ~300MB)
   - Falls back gracefully if unavailable

3. **LLM Refinement** (`refined_translation` field):
   - Uses Qwen2.5-1.5B-Instruct model
   - Refines MarianMT translation output
   - Corrects OCR noise-induced mistranslations
   - Improves contextual coherence and fluency
   - Preserves meaning while enhancing readability
   - Example: MarianMT "I love you" → Qwen "I love you" (improved coherence)
   - Lazy-loaded (model downloads on first use, ~3GB)
   - Falls back to MarianMT translation if unavailable

### Translation Flow

1. After OCR extraction and character fusion
2. Dictionary lookup for each character → `translation` field
3. Neural translation of full text → `sentence_translation` field
4. Qwen LLM refinement of MarianMT translation → `refined_translation` field
5. All three included in response (if available)

## Image Preprocessing Pipeline

**Module Location**: `services/preprocessing/image_preprocessing.py`  
**Wrapper**: `services/inference/main.py` → `_preprocess_image()`

The preprocessing system uses a **modular, production-grade architecture** with comprehensive testing and configuration support.

### Core Preprocessing Steps (FATAL - Must succeed)

These steps are critical for OCR and will raise `HTTPException` if they fail:

1. **Image Loading & Format Validation**
   - Opens image with PIL from raw bytes
   - Validates format: JPEG, PNG, or WebP
   - Raises HTTPException (400) if unsupported

2. **Dimension Validation**
   - Minimum: 50×50 pixels
   - Maximum: 4000×4000 pixels (before resizing)
   - Raises HTTPException (400) if too small

3. **Large Image Resizing**
   - If width or height > 4000px, proportionally resizes to fit
   - Maintains aspect ratio using LANCZOS resampling

4. **RGB Color Conversion**
   - Converts non-RGB modes (RGBA, L, P) to RGB
   - Handles transparency by compositing on white background

5. **Small Image Upscaling**
   - If any dimension < 300px, upscales to 300px minimum
   - Uses LANCZOS resampling for quality
   - Improves OCR accuracy for small text

6. **Contrast Enhancement**
   - Increases contrast by 1.3× (configurable)
   - Uses `ImageEnhance.Contrast`

7. **Sharpness Enhancement**
   - Increases sharpness by 1.2× (configurable)
   - Uses `ImageEnhance.Sharpness`

8. **Adaptive Padding**
   - Adds 50px padding (configurable) around image
   - White padding for bright images (>128), black for dark
   - Helps OCR detect edge characters

### Optional Enhancement Steps (OPTIONAL - Fail gracefully)

These steps enhance OCR quality but will only log warnings if they fail:

9. **Noise Reduction** (Bilateral Filter)
   - **Enabled by default** in production
   - Preserves edges while reducing noise
   - Recommended for: scanned/photographed documents
   - Requires: opencv-python

10. **Binarization** (Adaptive Thresholding)
    - **Disabled by default** (can cause issues with some images)
    - Converts to black/white
    - Recommended for: high-contrast handwriting
    - Requires: opencv-python

11. **Deskewing** (Tilt Correction)
    - **Enabled by default** in production
    - Corrects text rotation using Hough line transform
    - Recommended for: rotated documents
    - Requires: opencv-python

12. **Brightness Normalization** (CLAHE)
    - **Enabled by default** in production
    - Applies Contrast Limited Adaptive Histogram Equalization
    - Recommended for: unevenly lit images
    - Requires: opencv-python

13. **Array Conversion & Validation**
    - Converts PIL Image to NumPy array (uint8 format)
    - Validates dtype and shape
    - Returns both NumPy array (for OCR) and PIL Image (for metadata)

### Configuration

The preprocessing system is fully configurable via:

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

2. **Environment Variables** (`.env`):
   ```bash
   PREPROCESSING_CONTRAST_FACTOR=1.3
   PREPROCESSING_SHARPNESS_FACTOR=1.2
   PREPROCESSING_PADDING_SIZE=50
   PREPROCESSING_ENABLE_NOISE_REDUCTION=true
   PREPROCESSING_ENABLE_DESKEW=true
   PREPROCESSING_ENABLE_BRIGHTNESS_NORM=true
   ```

   See `services/preprocessing/README.md` for complete list of 35+ configurable parameters.

3. **Configuration File** (`services/preprocessing/config.py`):
   - Centralized defaults for all parameters
   - Automatic environment variable loading

### Error Handling

- **Core Steps (1-8, 13)**: Raise `HTTPException` on failure (fatal errors)
- **Optional Steps (9-12)**: Log warnings and continue (graceful degradation)
- **OpenCV Unavailable**: Optional enhancements automatically disabled

### Testing

The preprocessing module includes comprehensive testing:

- **61 unit tests** (100% pass rate)
  - 25 tests for core preprocessing
  - 20 tests for optional enhancements
  - 16 tests for toggle combinations
- **All 16 toggle permutations** tested and verified
- **Graceful degradation** tested for missing dependencies

Run tests:
```bash
cd services/inference
python -m pytest ../preprocessing/tests/ -v
```

### Module Structure

```
services/preprocessing/
├── __init__.py
├── config.py               # Configuration & env variables
├── image_preprocessing.py  # Main preprocessing logic
├── README.md              # Full documentation
└── tests/
    ├── __init__.py
    ├── test_core_preprocessing.py      # 25 tests
    ├── test_optional_enhancements.py   # 20 tests
    └── test_toggle_combinations.py     # 16 permutation tests
```

For detailed documentation, see `services/preprocessing/README.md`

## Dictionary Management

### Dictionary Structure

Each entry in `data/dictionary.json` follows this format:
```json
{
  "我": {
    "pinyin": "wǒ",
    "meaning": "I; me; myself; we; our",
    "alts": ["alternative forms", "variants"],
    "notes": "Contextual information and usage notes"
  }
}
```

### Adding New Characters

Edit `data/dictionary.json` and add entries:
```json
{
  "新字符": {
    "pinyin": "xīn zì fú",
    "meaning": "new character meaning",
    "alts": ["variant1", "variant2"],
    "notes": "Usage notes and context"
  }
}
```

### Reporting Unmapped Characters

Use the reporting script to identify missing dictionary entries:

```bash
# Collect unmapped characters from OCR results
python scripts/report_unmapped.py unmapped_chars.json suggestions.json
```

This generates a template file with unmapped characters that you can fill in and merge into the dictionary.


## Error Handling

The service provides specific error messages for different failure scenarios:

- **400 Bad Request**: Invalid image format, file too large, or image too small
- **422 Unprocessable Entity**: No text detected in image by any OCR engine
- **500 Internal Server Error**: OCR processing failure (memory, GPU, or other errors)
- **503 Service Unavailable**: Neither OCR engine available or failed to initialize
- **504 Gateway Timeout**: OCR processing timed out

**Graceful Degradation**: If one OCR engine fails, the system continues with the other engine.

## Troubleshooting

### OCR Engine Installation Issues

**Problem**: `ImportError: No module named 'easyocr'` or `'paddleocr'`
**Solution**: 
```bash
pip install -r requirements.txt
```

**Problem**: EasyOCR requires PyTorch
**Solution**: 
```bash
pip install torch torchvision
```

**Problem**: PaddleOCR fails to initialize
**Solution**: 
- Check Python version (3.8+ required)
- Try reinstalling: `pip uninstall paddleocr paddlepaddle && pip install -r requirements.txt`
- Check logs for specific error messages
- PaddleOCR 3.x doesn't support `use_gpu` parameter - this is handled automatically

**Problem**: Models download slowly on first use
**Solution**: 
- This is normal - models are cached after first download
- Ensure stable internet connection
- EasyOCR models: ~100-200MB
- PaddleOCR models: ~200-300MB

**Problem**: "MarianTokenizer requires the SentencePiece library"
**Solution**: ✅ **FIXED**
```bash
pip install sentencepiece
```
- This is now included in requirements.txt
- Restart the backend server after installing
- Verify with health check: MarianMT should show `"available": true`

### OCR Processing Issues

**Problem**: "No text detected in image"
**Solution**:
- Ensure image contains readable Chinese text
- Check image quality (resolution, contrast)
- Try with a clearer, higher quality image
- Ensure text is not too small or blurry
- The hybrid system should improve detection - check if both engines are running

**Problem**: "PaddleOCR processing failed: too many values to unpack"
**Solution**:
- This is fixed in the latest code - ensure you're running the latest version
- PaddleOCR 3.x uses different result format than 2.x

**Problem**: "OCR processing timed out"
**Solution**:
- Try with a smaller image (reduce dimensions)
- Check if image is too large (auto-resizing helps)
- Ensure adequate system resources (CPU/memory)
- Both engines run in parallel, which may increase memory usage

**Problem**: "Insufficient memory for OCR processing"
**Solution**:
- Reduce image size before uploading
- Close other applications to free memory
- Consider using a machine with more RAM
- Both OCR engines load models into memory

### Image Format Issues

**Problem**: "Unsupported file type"
**Solution**:
- Convert image to JPG, PNG, or WebP format
- Ensure file extension matches actual format

**Problem**: "Image too small" or "Image too large"
**Solution**:
- Minimum size: 50x50 pixels
- Maximum size: 4000x4000 pixels (auto-resized)
- Maximum file size: 10MB

## Configuration

### Environment Variables

- `INFERENCE_API_URL`: URL of this service (used by Next.js frontend)
- Default port: `8001`

### Service Configuration

Configuration constants in `main.py`:
- `MAX_IMAGE_SIZE`: Maximum file size (default: 10MB)
- `MAX_IMAGE_DIMENSION`: Maximum width/height (default: 4000px)
- `MIN_IMAGE_DIMENSION`: Minimum width/height (default: 50px)
- `OCR_TIMEOUT`: OCR processing timeout (default: 30 seconds)
- IoU threshold for alignment: 0.3 (in `align_ocr_outputs()` function)

## Integration with Next.js

The Next.js frontend calls this service via the `/api/process` endpoint, which proxies requests to this inference service.

Set `INFERENCE_API_URL=http://localhost:8001` in your Next.js `.env` file.

## Dictionary Features

- **Alternative Forms**: The dictionary supports alternative/variant character forms via the `alts` field
- **Pinyin**: Phonetic transcription for pronunciation
- **Contextual Notes**: Each entry can include usage notes and contextual information
- **Coverage Tracking**: Response includes coverage percentage showing how many characters were found in dictionary
- **Unmapped Tracking**: List of characters not found in dictionary for easy dictionary expansion

## Performance

- **Typical OCR time**: 3-8 seconds for standard images (1000x1000px) with both engines
- **Translation time**: 
  - MarianMT: 1-3 seconds (neural inference)
  - Qwen refinement: 5-15 seconds (LLM inference, CPU-dependent)
- **Large images**: Automatically resized to 4000x4000px max (maintains aspect ratio)
- **Memory usage**: ~3-5GB total (OCR engines + MarianMT + Qwen models loaded)
  - EasyOCR: ~500MB
  - PaddleOCR: ~500MB
  - MarianMT: ~300MB
  - Qwen2.5-1.5B: ~3GB
- **First request**: May be slower due to model loading (~20-60 seconds for OCR engines, ~30 seconds for MarianMT, ~3-5 minutes for Qwen)
- **Parallel processing**: OCR engines run simultaneously, so total time ≈ max(Time(EasyOCR), Time(PaddleOCR))

## Image Preprocessing Details

**Note**: The preprocessing system has been modularized into `services/preprocessing/` with comprehensive testing and configuration support. See the "Image Preprocessing Pipeline" section above for complete documentation.

### Quick Summary

The preprocessing pipeline performs 13 steps in two tiers:

**Core Steps (FATAL - must succeed)**:
1. Format Validation (JPEG, PNG, WEBP)
2. Dimension Validation (50-4000px)
3. Large Image Resizing (>4000px)
4. RGB Color Conversion
5. **Small Image Upscaling**: Upscales images smaller than 300px to improve OCR accuracy
6. **Contrast Enhancement**: Increases contrast by 1.3× to improve text-background separation
7. **Sharpness Enhancement**: Increases sharpness by 1.2× to enhance edge definition
8. **Adaptive Padding**: Adds 50px padding with color chosen based on image brightness (black for dark images, white for bright images)
9. **Array Conversion**: Converts PIL Image to NumPy array with proper dtype validation

## Testing

The Rune-X inference service includes comprehensive testing for all critical components.

### Preprocessing Module Tests (61 Tests)

Run all preprocessing tests:

```bash
cd services/inference
python -m pytest ../preprocessing/tests/ -v
```

Run specific test suites:

```bash
# Core preprocessing tests (25 tests)
python -m pytest ../preprocessing/tests/test_core_preprocessing.py -v

# Optional enhancements tests (20 tests)
python -m pytest ../preprocessing/tests/test_optional_enhancements.py -v

# Toggle combinations tests (16 permutation tests)
python -m pytest ../preprocessing/tests/test_toggle_combinations.py -v
```

**Test Coverage**:
- ✅ Format validation (5 tests)
- ✅ Dimension validation (7 tests)
- ✅ Large image resizing (4 tests)
- ✅ Small image upscaling (4 tests)
- ✅ Adaptive padding (4 tests)
- ✅ Array conversion & validation (6 tests)
- ✅ Noise reduction (5 tests)
- ✅ Binarization (5 tests)
- ✅ Deskewing (5 tests)
- ✅ Brightness normalization (5 tests)
- ✅ All 16 toggle combinations (16 tests)

### Pipeline Smoke Test

Verify end-to-end execution:

```bash
cd services/inference
python -m pytest tests/test_pipeline_smoke.py -v
```

This test verifies that the full OCR → translation → refinement pipeline executes without crashing.

### Translator Tests

Run translator unit tests:

```bash
cd services/inference
python -m pytest tests/test_translator.py -v
```

### Run All Tests

```bash
cd services/inference
python -m pytest -v
```

## Logging

The service uses Python's logging module with INFO level by default. Logs include:
- OCR engine initialization status
- Image preprocessing steps (format validation, resizing, enhancement)
- OCR processing progress (both engines)
- Alignment and fusion statistics
- Translation engine status (MarianMT, Qwen)
- Error details and stack traces

To change log level, modify the `logging.basicConfig()` call in `main.py`.

## Architecture Notes

### Why Hybrid OCR?

- **Complementary Strengths**: EasyOCR excels at stylized handwriting, PaddleOCR at standard text
- **Improved Accuracy**: Multiple hypotheses per character improve recognition confidence
- **Robustness**: If one engine fails, the other continues processing
- **Uncertainty Preservation**: All candidates preserved for downstream analysis

### Why Three-Tier Translation?

- **Comprehensive Coverage**: Dictionary provides character meanings, MarianMT provides sentence context, Qwen refines for quality
- **OCR Noise Correction**: Qwen LLM can correct mistranslations caused by OCR errors
- **Coherence Improvement**: Qwen enhances contextual coherence across sentences
- **Graceful Degradation**: System works even if one translation tier is unavailable
- **User Choice**: Users can see all three translation types and choose which to use

### Phase 5: MarianMT Refactoring (December 2025)

**MarianMT Role Redefinition**: MarianMT is no longer "the translator" but a **grammar and fluency optimizer** that works with the OCR + dictionary stack instead of overriding it.

#### MarianAdapter Architecture

The `MarianAdapter` (`marian_adapter.py`) wraps the existing `SentenceTranslator` to provide:
- **Structured Input/Output**: Accepts glyphs + metadata, returns annotated translation
- **Token Locking**: High-confidence glyphs (≥0.85 OCR confidence + dictionary match) are locked and preserved
- **Phrase-Level Refinement**: Groups glyphs into phrases for better context handling
- **Semantic Metrics**: Tracks changes, calculates confidence scores
- **Semantic Constraints**: Enforces rules via `SemanticContract` (`semantic_constraints.py`)

#### Locking Strategy

**Confidence Thresholds**:
- **High Confidence**: ≥0.85 OCR confidence → Locked (even without dictionary)
- **High Confidence + Dictionary**: ≥0.85 OCR confidence + dictionary match → Locked
- **Low Confidence**: <0.70 OCR confidence → Unlocked (allow MarianMT to improve)
- **Medium Confidence**: 0.70-0.85 → Unlocked if no dictionary match

**Placeholder System**:
- Locked glyphs replaced with `__LOCK_[character]__` before MarianMT
- Placeholders survive translation unchanged
- Original characters restored after translation

#### Rollback Instructions

**To disable MarianAdapter and revert to direct MarianMT**:

1. In `main.py` (line ~368), comment out MarianAdapter initialization:
   ```python
   # marian_adapter = get_marian_adapter(...)
   marian_adapter = None
   ```

2. In `main.py` (line ~755), replace adapter call with direct translator:
   ```python
   # Replace:
   # adapter_output = marian_adapter.translate(...)
   # sentence_translation = adapter_output.translation if adapter_output else None
   
   # With:
   if sentence_translator and sentence_translator.is_available():
       sentence_translation = sentence_translator.translate(full_text)
   ```

3. Remove semantic metadata extraction (line ~848):
   ```python
   # semantic_metadata = None  # Comment out or remove
   ```

4. Remove semantic field from InferenceResponse (line ~860):
   ```python
   # semantic=semantic_metadata,  # Comment out or remove
   ```

**Note**: This reverts to pre-Phase 5 behavior. All Phase 5 enhancements (token locking, phrase refinement, metrics) will be disabled.

### Future Enhancements

- Weighted fusion based on confidence scores
- Engine-specific preprocessing strategies
- Confidence threshold filtering
- Additional OCR engines (Tesseract, etc.)
- Binarization and deskewing preprocessing
- Vertical text layout reconstruction
- Language model error correction for OCR mistakes
