# Rune-X Inference Service

FastAPI service for Chinese handwriting OCR with hybrid OCR system and dictionary-based translation.

## Features

- **Hybrid OCR System**: Runs EasyOCR and PaddleOCR in parallel, then fuses results at character level
- **Character-Level Fusion**: Preserves all character hypotheses from both engines using IoU-based alignment
- **Dual Translation System**: 
  - **Dictionary-Based Translation**: Character-level meanings from custom dictionary (276+ entries)
  - **Neural Sentence Translation**: Context-aware sentence-level translation using MarianMT (Helsinki-NLP/opus-mt-zh-en)
- **Dictionary**: JSON-based character dictionary with 276+ entries (meanings, alternatives, notes)
- **Image Preprocessing**: Automatic validation, resizing, contrast enhancement, and format conversion
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
- Both OCR engines will initialize on first request (takes 20-60 seconds)
- Sentence translator loads model lazily (on first translation request)

2. **Install PyTorch** (required for EasyOCR):
```bash
# CPU version (recommended for most users)
pip install torch torchvision

# GPU version (if you have CUDA)
# See: https://pytorch.org/get-started/locally/
```

3. **Verify installation**:
```bash
python -c "import easyocr; import paddleocr; from transformers import MarianMTModel, MarianTokenizer; print('All dependencies installed successfully')"
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

**Processing Flow**:
1. Image preprocessing (upscaling, contrast, padding)
2. Parallel OCR execution (EasyOCR + PaddleOCR)
3. Result normalization and alignment
4. Character-level fusion
5. Dictionary lookup and character-level translation
6. Neural sentence-level translation (MarianMT)
7. Response generation

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

### Dual Translation Approach

The service provides two complementary translation methods:

1. **Dictionary-Based Translation** (`translation` field):
   - Character-by-character lookup from `dictionary.json`
   - Concatenates meanings with ` | ` separator
   - Fast, deterministic, preserves all character meanings
   - Example: "我 | 爱 | 你" → "I; me; myself; we; our | love; affection; like; care for; cherish | you; your; yourself"

2. **Neural Sentence Translation** (`sentence_translation` field):
   - Uses MarianMT model (Helsinki-NLP/opus-mt-zh-en)
   - Processes entire sentence as context
   - Produces natural, grammatically correct English
   - Example: "我爱你" → "I love you"
   - Lazy-loaded (model downloads on first use, ~300MB)
   - Falls back gracefully if unavailable

### Translation Flow

1. After OCR extraction and character fusion
2. Dictionary lookup for each character → `translation` field
3. Neural translation of full text → `sentence_translation` field
4. Both included in response (if available)

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

## Testing

Run basic tests:
```bash
python tests/test_translator.py
```

Or use pytest:
```bash
pytest tests/test_translator.py
```

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
- **Large images**: Automatically resized to 4000x4000px max (maintains aspect ratio)
- **Memory usage**: ~1-2GB for OCR processing (both engines loaded)
- **First request**: May be slower due to model loading (~20-60 seconds for both engines)
- **Parallel processing**: Both engines run simultaneously, so total time ≈ max(Time(EasyOCR), Time(PaddleOCR))

## Logging

The service uses Python's logging module with INFO level by default. Logs include:
- OCR engine initialization status
- Image preprocessing steps
- OCR processing progress (both engines)
- Alignment and fusion statistics
- Error details and stack traces

To change log level, modify the `logging.basicConfig()` call in `main.py`.

## Architecture Notes

### Why Hybrid OCR?

- **Complementary Strengths**: EasyOCR excels at stylized handwriting, PaddleOCR at standard text
- **Improved Accuracy**: Multiple hypotheses per character improve recognition confidence
- **Robustness**: If one engine fails, the other continues processing
- **Uncertainty Preservation**: All candidates preserved for downstream analysis

### Future Enhancements

- Weighted fusion based on confidence scores
- Engine-specific preprocessing strategies
- Confidence threshold filtering
- Additional OCR engines (Tesseract, etc.)
