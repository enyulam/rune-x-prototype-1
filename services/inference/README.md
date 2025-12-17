# Rune-X Inference Service

FastAPI service for Chinese handwriting OCR with dictionary-based translation.

## Features

- **OCR**: Uses PaddleOCR for Chinese handwriting text extraction
- **Translation**: Dictionary-based rule translation with per-character meanings
- **Dictionary**: JSON-based character dictionary with meanings, alternatives, and notes
- **Image Preprocessing**: Automatic image validation, resizing, and format conversion
- **Error Handling**: Comprehensive error messages and validation
- **Performance**: Optimized for various image sizes with automatic resizing

## Setup

### Prerequisites

- Python 3.7 or higher
- pip package manager

### Installation

1. **Install dependencies**:
```bash
cd services/inference
pip install -r requirements.txt
```

**Note**: PaddleOCR will automatically download model files on first use (this may take a few minutes and requires internet connection).

2. **Verify installation**:
```bash
python -c "from paddleocr import PaddleOCR; print('PaddleOCR installed successfully')"
```

3. **Dictionary**: The dictionary file is located at `data/dictionary.json`. 
   - Contains Chinese character meanings, alternative forms, and contextual notes
   - Can be extended with more characters as needed
   - Format: `{character: {meaning, alts[], notes}}`

4. **Run the service**:
```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

The service will be available at `http://localhost:8001`

### Platform-Specific Notes

#### Windows
- May require Visual C++ Redistributable
- If installation fails, try: `pip install paddleocr paddlepaddle --no-cache-dir`

#### Linux
- May require system libraries: `sudo apt-get install libgl1 libglib2.0-0`
- For headless servers, use `opencv-python-headless` (already in requirements.txt)

#### macOS
- Should work out of the box with pip install
- If issues occur, ensure Xcode command line tools are installed

## API Endpoints

### `GET /health`
Health check endpoint. Returns:
- Service status
- PaddleOCR availability and status
- Dictionary statistics (entries, alternatives, notes)
- Image processing limits and supported formats

**Example Response**:
```json
{
  "status": "ok",
  "paddle": {
    "available": true,
    "status": "ready"
  },
  "dictionary": {
    "entries": 150,
    "entries_with_alts": 25,
    "entries_with_notes": 30,
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
Process an uploaded image for OCR and translation.

**Request**: 
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: Form field `file` containing image file (JPG, PNG, or WebP)
- Max file size: 10MB
- Max dimensions: 4000x4000 pixels (auto-resized if larger)

**Response**:
```json
{
  "text": "人天",
  "translation": "person; people; human | sky; heaven; day; nature",
  "confidence": 0.935,
  "glyphs": [
    {
      "symbol": "人",
      "bbox": [10, 20, 50, 50],
      "confidence": 0.95,
      "meaning": "person; people; human"
    },
    {
      "symbol": "天",
      "bbox": [60, 20, 50, 50],
      "confidence": 0.92,
      "meaning": "sky; heaven; day; nature"
    }
  ],
  "unmapped": [],
  "coverage": 100.0,
  "dictionary_version": "1.0.0"
}
```

## Dictionary Management

### Dictionary Structure

Each entry in `data/dictionary.json` follows this format:
```json
{
  "字": {
    "meaning": "character; word; letter; name; write",
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

**Input formats supported**:
- JSON array: `["字", "符", ...]`
- JSON object: `{"unmapped": ["字", "符", ...]}`
- Array of results: `[{"unmapped": [...]}, ...]`

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
- **422 Unprocessable Entity**: No text detected in image
- **500 Internal Server Error**: OCR processing failure (memory, GPU, or other errors)
- **503 Service Unavailable**: PaddleOCR not installed or failed to initialize
- **504 Gateway Timeout**: OCR processing timed out

## Troubleshooting

### PaddleOCR Installation Issues

**Problem**: `ImportError: No module named 'paddleocr'`
**Solution**: 
```bash
pip install paddleocr paddlepaddle
```

**Problem**: PaddleOCR fails to initialize
**Solution**: 
- Check Python version (3.7+ required)
- Try reinstalling: `pip uninstall paddleocr paddlepaddle && pip install -r requirements.txt`
- Check logs for specific error messages

**Problem**: Models download slowly on first use
**Solution**: 
- This is normal - models are cached after first download
- Ensure stable internet connection
- Models are typically 100-200MB total

### OCR Processing Issues

**Problem**: "No text detected in image"
**Solution**:
- Ensure image contains readable Chinese text
- Check image quality (resolution, contrast)
- Try with a clearer, higher quality image
- Ensure text is not too small or blurry

**Problem**: "OCR processing timed out"
**Solution**:
- Try with a smaller image (reduce dimensions)
- Check if image is too large (auto-resizing helps)
- Ensure adequate system resources (CPU/memory)

**Problem**: "Insufficient memory for OCR processing"
**Solution**:
- Reduce image size before uploading
- Close other applications to free memory
- Consider using a machine with more RAM

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

## Integration with Next.js

The Next.js frontend calls this service via the `/api/process` endpoint, which proxies requests to this inference service.

Set `INFERENCE_API_URL=http://localhost:8001` in your Next.js `.env` file.

## Dictionary Features

- **Alternative Forms**: The dictionary supports alternative/variant character forms via the `alts` field
- **Contextual Notes**: Each entry can include usage notes and contextual information
- **Coverage Tracking**: Response includes coverage percentage showing how many characters were found in dictionary
- **Unmapped Tracking**: List of characters not found in dictionary for easy dictionary expansion

## Performance

- **Typical OCR time**: 2-5 seconds for standard images (1000x1000px)
- **Large images**: Automatically resized to 4000x4000px max (maintains aspect ratio)
- **Memory usage**: ~500MB-1GB for OCR processing (varies by image size)
- **First request**: May be slower due to model loading (~10-30 seconds)

## Logging

The service uses Python's logging module with INFO level by default. Logs include:
- OCR initialization status
- Image preprocessing steps
- OCR processing progress
- Error details and stack traces

To change log level, modify the `logging.basicConfig()` call in `main.py`.

