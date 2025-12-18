# Rune-X Image Preprocessing Module

Production-grade image preprocessing for OCR with two-tier enhancement strategy.

## Architecture

The preprocessing module implements a **fault-tolerant, configurable pipeline**:

1. **Core Preprocessing (Steps 1-8)**: FATAL operations that must succeed
2. **Optional Enhancements (Steps 9-12)**: Gracefully degrade if they fail  
3. **Array Conversion (Step 13)**: FATAL validation before returning

## Features

### Core Preprocessing (FATAL - Will raise exceptions)

1. **Image Loading & Format Validation** - Supports JPEG, PNG, WEBP
2. **Dimension Validation** - Ensures 50px ≤ size ≤ 4000px
3. **Large Image Resizing** - Downscales images > 4000px (preserves aspect ratio)
4. **RGB Conversion** - Handles RGBA, grayscale, palette modes
5. **Small Image Upscaling** - Upscales images < 300px minimum
6. **Contrast Enhancement** - 1.3x default multiplier
7. **Sharpness Enhancement** - 1.2x default multiplier
8. **Adaptive Padding** - 50px border, color based on brightness

### Optional Enhancements (OPTIONAL - Will log warnings on failure)

9. **Noise Reduction** - Bilateral filter (preserves edges)
10. **Binarization** - Adaptive thresholding (handles varying lighting)
11. **Deskewing** - Hough line transform (tilt correction)
12. **Brightness Normalization** - CLAHE (better than basic histogram equalization)

### Final Validation (FATAL)

13. **Array Conversion & Validation** - Ensures valid NumPy output

## Usage

### Basic Usage

```python
from preprocessing.image_preprocessing import preprocess_image

# Read image bytes
with open("document.jpg", "rb") as f:
    img_bytes = f.read()

# Preprocess with all enhancements
img_array, img_pil = preprocess_image(img_bytes)

# Use img_array for OCR
# Use img_pil for logging/debugging
```

### Selective Enhancement

```python
# Disable optional enhancements for speed
img_array, img_pil = preprocess_image(
    img_bytes,
    apply_noise_reduction=False,
    apply_binarization=False,
    apply_deskew=False,
    apply_brightness_norm=False
)
```

### With FastAPI

```python
from fastapi import UploadFile
from preprocessing.image_preprocessing import preprocess_image

async def process_upload(file: UploadFile):
    img_bytes = await file.read()
    img_array, img_pil = preprocess_image(img_bytes)
    # Process with OCR...
```

## Configuration

Configuration hierarchy (highest to lowest priority):

1. **Function parameters** (runtime overrides)
2. **Environment variables** (.env file)
3. **Config defaults** (config.py)

### Environment Variables

All preprocessing parameters can be overridden via environment variables:

#### Dimension Constraints

```bash
PREPROCESSING_MIN_IMAGE_DIMENSION=50        # Minimum width/height
PREPROCESSING_MAX_IMAGE_DIMENSION=4000      # Maximum before resizing
PREPROCESSING_MIN_UPSCALE_DIM=300          # Upscale threshold
```

#### Enhancement Factors

```bash
PREPROCESSING_CONTRAST_FACTOR=1.3          # Contrast multiplier
PREPROCESSING_SHARPNESS_FACTOR=1.2         # Sharpness multiplier
PREPROCESSING_PADDING_SIZE=50              # Border padding (px)
PREPROCESSING_BRIGHTNESS_THRESHOLD=128     # Padding color threshold
```

#### Optional Enhancements (true/false)

```bash
PREPROCESSING_ENABLE_NOISE_REDUCTION=true
PREPROCESSING_ENABLE_BINARIZATION=true
PREPROCESSING_ENABLE_DESKEW=true
PREPROCESSING_ENABLE_BRIGHTNESS_NORM=true
```

#### OpenCV Algorithm Parameters

```bash
# Bilateral Filter (Noise Reduction)
PREPROCESSING_BILATERAL_D=9
PREPROCESSING_BILATERAL_SIGMA_COLOR=75
PREPROCESSING_BILATERAL_SIGMA_SPACE=75

# Adaptive Threshold (Binarization)
PREPROCESSING_ADAPTIVE_BLOCK_SIZE=11
PREPROCESSING_ADAPTIVE_C=2

# Deskewing
PREPROCESSING_DESKEW_MAX_ANGLE=45.0
PREPROCESSING_DESKEW_CANNY_LOW=50
PREPROCESSING_DESKEW_CANNY_HIGH=150
PREPROCESSING_DESKEW_HOUGH_THRESHOLD=200

# CLAHE (Brightness Normalization)
PREPROCESSING_CLAHE_CLIP_LIMIT=2.0
PREPROCESSING_CLAHE_TILE_SIZE=8
```

### Get Current Configuration

```python
from preprocessing.config import get_config_summary

config = get_config_summary()
print(config)
```

## Error Handling

### Fatal Errors (Raise HTTPException)

- Invalid image format
- Dimensions too small/large
- Image loading failures
- Color conversion failures
- Enhancement failures (contrast, sharpness, padding)
- Array validation failures

```python
from fastapi import HTTPException

try:
    img_array, img_pil = preprocess_image(img_bytes)
except HTTPException as e:
    print(f"Preprocessing failed: {e.detail}")
    # Return error to client
```

### Optional Enhancement Failures (Log warnings)

- Noise reduction failure
- Binarization failure
- Deskewing failure
- Brightness normalization failure

These failures are logged but don't stop the pipeline. The image proceeds with only the successful enhancements applied.

## Dependencies

### Required

- `PIL` (Pillow) - Image loading, format conversion, enhancements
- `numpy` - Array operations
- `fastapi` - HTTPException for error handling

### Optional (for enhanced features)

- `opencv-python` or `opencv-python-headless` - Advanced enhancements
  - If not installed, optional enhancements are automatically disabled
  - A warning is logged on module import

## Performance

### Typical Processing Times (on CPU)

- **Core preprocessing only**: ~50-150ms
- **With all enhancements**: ~200-500ms
- **First run (model loading)**: +1-2 seconds

### Optimization Tips

1. **Disable unused enhancements** for speed
2. **Use opencv-python-headless** in production (smaller, no GUI dependencies)
3. **Set appropriate dimension limits** to avoid processing unnecessarily large images
4. **Adjust algorithm parameters** via environment variables for your use case

## Testing

Run unit tests:

```bash
cd services/inference
python -m pytest services/preprocessing/tests/ -v
```

Run with coverage:

```bash
python -m pytest services/preprocessing/tests/ --cov=services/preprocessing --cov-report=html
```

## Integration Example

```python
# main.py
from preprocessing.image_preprocessing import preprocess_image
from fastapi import UploadFile

async def process_image(file: UploadFile):
    # Read uploaded file
    img_bytes = await file.read()
    
    # Preprocess
    img_array, img_pil = preprocess_image(
        img_bytes,
        apply_noise_reduction=True,
        apply_binarization=True,
        apply_deskew=True,
        apply_brightness_norm=True
    )
    
    # Run OCR
    ocr_results = ocr_engine.process(img_array)
    
    # Return results
    return {
        "text": ocr_results.text,
        "preprocessing": {
            "final_size": img_pil.size,
            "format": img_pil.format,
            "mode": img_pil.mode
        }
    }
```

## License

Part of the Rune-X translation platform.

