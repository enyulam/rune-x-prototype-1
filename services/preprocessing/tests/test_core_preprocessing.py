"""
Phase 1 Verification Suite for Core Preprocessing Steps

This test suite verifies the FATAL preprocessing operations that must succeed.
It focuses on individual preprocessing steps and avoids duplicating end-to-end
pipeline tests (which are covered by the smoke test).

Test Coverage:
- Format validation
- Dimension validation (min/max)
- Large image resizing
- Small image upscaling
- Adaptive padding
- Array conversion & validation
"""

import io
import logging
import pytest
import numpy as np
from PIL import Image
from fastapi import HTTPException

# Import preprocessing functions and configuration
from ..image_preprocessing import (
    preprocess_image,
    _validate_format,
    _validate_dimensions,
    _resize_large_image,
    _upscale_small_image,
    _add_adaptive_padding
)
from ..config import (
    MIN_IMAGE_DIMENSION,
    MAX_IMAGE_DIMENSION,
    MIN_UPSCALE_DIM,
    PADDING_SIZE,
    BRIGHTNESS_THRESHOLD
)

# Configure logging for test debugging
logger = logging.getLogger(__name__)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def create_test_image():
    """
    Factory fixture to create test images with specific properties.
    
    Returns PIL Image objects with configurable dimensions, color, and format.
    """
    def _create(width=500, height=500, mode="RGB", color=(255, 255, 255), format="PNG"):
        img = Image.new(mode, (width, height), color)
        img.format = format
        return img
    return _create


@pytest.fixture
def image_to_bytes():
    """
    Convert PIL Image to bytes for preprocessing function input.
    """
    def _convert(img, format="PNG"):
        buf = io.BytesIO()
        if not hasattr(img, 'format') or img.format is None:
            img.format = format
        img.save(buf, format=format)
        return buf.getvalue()
    return _convert


# ============================================================================
# FORMAT VALIDATION TESTS
# ============================================================================

def test_format_validation_supported_jpeg(create_test_image):
    """Verify JPEG format passes validation."""
    img = create_test_image(format="JPEG")
    _validate_format(img)  # Should not raise


def test_format_validation_supported_png(create_test_image):
    """Verify PNG format passes validation."""
    img = create_test_image(format="PNG")
    _validate_format(img)  # Should not raise


def test_format_validation_supported_webp(create_test_image):
    """Verify WEBP format passes validation."""
    img = create_test_image(format="WEBP")
    _validate_format(img)  # Should not raise


def test_format_validation_unsupported_bmp(create_test_image):
    """Verify BMP format raises ValueError."""
    img = create_test_image()
    img.format = "BMP"
    
    with pytest.raises(ValueError, match="Unsupported image format"):
        _validate_format(img)


def test_format_validation_unsupported_gif(create_test_image):
    """Verify GIF format raises ValueError."""
    img = create_test_image()
    img.format = "GIF"
    
    with pytest.raises(ValueError, match="Unsupported image format"):
        _validate_format(img)


def test_preprocess_invalid_format_raises_http_400():
    """Verify unsupported format raises HTTPException 400 in preprocessing."""
    # Create a BMP image (unsupported) by saving as BMP explicitly
    img = Image.new("RGB", (100, 100))
    buf = io.BytesIO()
    img.save(buf, format="BMP")
    img_bytes = buf.getvalue()
    
    with pytest.raises(HTTPException) as exc_info:
        preprocess_image(img_bytes, apply_noise_reduction=False, 
                        apply_binarization=False, apply_deskew=False, 
                        apply_brightness_norm=False)
    
    assert exc_info.value.status_code == 400
    assert "Invalid image format" in exc_info.value.detail


# ============================================================================
# MINIMUM DIMENSION VALIDATION TESTS
# ============================================================================

def test_dimension_validation_at_minimum():
    """Verify dimensions at MIN_IMAGE_DIMENSION pass validation."""
    _validate_dimensions(MIN_IMAGE_DIMENSION, MIN_IMAGE_DIMENSION)  # Should not raise


def test_dimension_validation_above_minimum():
    """Verify dimensions above minimum pass validation."""
    _validate_dimensions(MIN_IMAGE_DIMENSION + 10, MIN_IMAGE_DIMENSION + 10)  # Should not raise


def test_dimension_validation_width_below_minimum():
    """Verify width below MIN_IMAGE_DIMENSION raises ValueError."""
    with pytest.raises(ValueError, match="too small"):
        _validate_dimensions(MIN_IMAGE_DIMENSION - 1, 100)


def test_dimension_validation_height_below_minimum():
    """Verify height below MIN_IMAGE_DIMENSION raises ValueError."""
    with pytest.raises(ValueError, match="too small"):
        _validate_dimensions(100, MIN_IMAGE_DIMENSION - 1)


def test_dimension_validation_both_below_minimum():
    """Verify both dimensions below MIN_IMAGE_DIMENSION raises ValueError."""
    with pytest.raises(ValueError, match="too small"):
        _validate_dimensions(MIN_IMAGE_DIMENSION - 1, MIN_IMAGE_DIMENSION - 1)


def test_preprocess_too_small_raises_http_400(create_test_image, image_to_bytes):
    """Verify image below MIN_IMAGE_DIMENSION raises HTTPException 400."""
    img = create_test_image(width=MIN_IMAGE_DIMENSION - 5, height=MIN_IMAGE_DIMENSION - 5)
    img_bytes = image_to_bytes(img)
    
    with pytest.raises(HTTPException) as exc_info:
        preprocess_image(img_bytes, apply_noise_reduction=False,
                        apply_binarization=False, apply_deskew=False,
                        apply_brightness_norm=False)
    
    assert exc_info.value.status_code == 400
    assert "too small" in exc_info.value.detail
    logger.debug(f"Correctly rejected image smaller than {MIN_IMAGE_DIMENSION}px")


# ============================================================================
# LARGE IMAGE RESIZING TESTS
# ============================================================================

def test_resize_large_image_no_resize_needed(create_test_image):
    """Verify images within MAX_IMAGE_DIMENSION are not resized."""
    img = create_test_image(width=MAX_IMAGE_DIMENSION, height=MAX_IMAGE_DIMENSION)
    resized = _resize_large_image(img, MAX_IMAGE_DIMENSION)
    
    assert resized.size == (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION)


def test_resize_large_image_width_exceeds_max(create_test_image):
    """Verify images with width > MAX_IMAGE_DIMENSION are resized proportionally."""
    original_width = MAX_IMAGE_DIMENSION + 1000
    original_height = 2000
    img = create_test_image(width=original_width, height=original_height)
    
    resized = _resize_large_image(img, MAX_IMAGE_DIMENSION)
    
    # Should be resized to fit within MAX_IMAGE_DIMENSION
    assert resized.size[0] <= MAX_IMAGE_DIMENSION
    assert resized.size[1] <= MAX_IMAGE_DIMENSION
    
    # Aspect ratio should be preserved (within 1% tolerance)
    original_ratio = original_width / original_height
    resized_ratio = resized.size[0] / resized.size[1]
    assert abs(original_ratio - resized_ratio) < 0.01
    
    logger.debug(f"Resized {original_width}x{original_height} -> {resized.size}")


def test_resize_large_image_height_exceeds_max(create_test_image):
    """Verify images with height > MAX_IMAGE_DIMENSION are resized proportionally."""
    original_width = 2000
    original_height = MAX_IMAGE_DIMENSION + 1000
    img = create_test_image(width=original_width, height=original_height)
    
    resized = _resize_large_image(img, MAX_IMAGE_DIMENSION)
    
    # Should be resized to fit within MAX_IMAGE_DIMENSION
    assert resized.size[0] <= MAX_IMAGE_DIMENSION
    assert resized.size[1] <= MAX_IMAGE_DIMENSION
    
    # Aspect ratio should be preserved
    original_ratio = original_width / original_height
    resized_ratio = resized.size[0] / resized.size[1]
    assert abs(original_ratio - resized_ratio) < 0.01
    
    logger.debug(f"Resized {original_width}x{original_height} -> {resized.size}")


def test_resize_large_image_both_exceed_max(create_test_image):
    """Verify images with both dimensions > MAX_IMAGE_DIMENSION are resized."""
    original_width = MAX_IMAGE_DIMENSION + 500
    original_height = MAX_IMAGE_DIMENSION + 800
    img = create_test_image(width=original_width, height=original_height)
    
    resized = _resize_large_image(img, MAX_IMAGE_DIMENSION)
    
    # Both dimensions should be within MAX_IMAGE_DIMENSION
    assert resized.size[0] <= MAX_IMAGE_DIMENSION
    assert resized.size[1] <= MAX_IMAGE_DIMENSION
    
    # At least one dimension should equal MAX_IMAGE_DIMENSION
    assert resized.size[0] == MAX_IMAGE_DIMENSION or resized.size[1] == MAX_IMAGE_DIMENSION


# ============================================================================
# SMALL IMAGE UPSCALING TESTS
# ============================================================================

def test_upscale_small_image_no_upscale_needed(create_test_image):
    """Verify images >= MIN_UPSCALE_DIM are not upscaled."""
    img = create_test_image(width=MIN_UPSCALE_DIM, height=MIN_UPSCALE_DIM)
    upscaled = _upscale_small_image(img, MIN_UPSCALE_DIM)
    
    assert upscaled.size == (MIN_UPSCALE_DIM, MIN_UPSCALE_DIM)


def test_upscale_small_image_width_below_min(create_test_image):
    """Verify images with width < MIN_UPSCALE_DIM are upscaled proportionally."""
    original_width = MIN_UPSCALE_DIM - 100
    original_height = MIN_UPSCALE_DIM + 100
    img = create_test_image(width=original_width, height=original_height)
    
    upscaled = _upscale_small_image(img, MIN_UPSCALE_DIM)
    
    # Should be upscaled to meet MIN_UPSCALE_DIM
    assert upscaled.size[0] >= MIN_UPSCALE_DIM
    assert upscaled.size[1] >= MIN_UPSCALE_DIM
    
    # Aspect ratio should be preserved
    original_ratio = original_width / original_height
    upscaled_ratio = upscaled.size[0] / upscaled.size[1]
    assert abs(original_ratio - upscaled_ratio) < 0.01
    
    logger.debug(f"Upscaled {original_width}x{original_height} -> {upscaled.size}")


def test_upscale_small_image_height_below_min(create_test_image):
    """Verify images with height < MIN_UPSCALE_DIM are upscaled proportionally."""
    original_width = MIN_UPSCALE_DIM + 100
    original_height = MIN_UPSCALE_DIM - 100
    img = create_test_image(width=original_width, height=original_height)
    
    upscaled = _upscale_small_image(img, MIN_UPSCALE_DIM)
    
    # Should be upscaled to meet MIN_UPSCALE_DIM
    assert upscaled.size[0] >= MIN_UPSCALE_DIM
    assert upscaled.size[1] >= MIN_UPSCALE_DIM
    
    # Aspect ratio should be preserved
    original_ratio = original_width / original_height
    upscaled_ratio = upscaled.size[0] / upscaled.size[1]
    assert abs(original_ratio - upscaled_ratio) < 0.01
    
    logger.debug(f"Upscaled {original_width}x{original_height} -> {upscaled.size}")


def test_upscale_small_image_both_below_min(create_test_image):
    """Verify images with both dimensions < MIN_UPSCALE_DIM are upscaled."""
    original_width = MIN_UPSCALE_DIM - 50
    original_height = MIN_UPSCALE_DIM - 80
    img = create_test_image(width=original_width, height=original_height)
    
    upscaled = _upscale_small_image(img, MIN_UPSCALE_DIM)
    
    # Both dimensions should meet MIN_UPSCALE_DIM
    assert upscaled.size[0] >= MIN_UPSCALE_DIM
    assert upscaled.size[1] >= MIN_UPSCALE_DIM


# ============================================================================
# ADAPTIVE PADDING TESTS
# ============================================================================

def test_adaptive_padding_bright_image_gets_white_padding(create_test_image):
    """
    Verify bright images (avg brightness > BRIGHTNESS_THRESHOLD) get white padding.
    """
    # Create bright image (white)
    img = create_test_image(width=100, height=100, color=(255, 255, 255))
    padded = _add_adaptive_padding(img, PADDING_SIZE)
    
    # Size should increase by 2*PADDING_SIZE on each dimension
    expected_width = 100 + 2 * PADDING_SIZE
    expected_height = 100 + 2 * PADDING_SIZE
    assert padded.size == (expected_width, expected_height)
    
    # Check corner pixel should be white (255, 255, 255)
    corner_pixel = padded.getpixel((0, 0))
    assert corner_pixel == (255, 255, 255), f"Expected white padding, got {corner_pixel}"
    
    logger.debug(f"Bright image correctly received white padding")


def test_adaptive_padding_dark_image_gets_black_padding(create_test_image):
    """
    Verify dark images (avg brightness < BRIGHTNESS_THRESHOLD) get black padding.
    """
    # Create dark image (black)
    img = create_test_image(width=100, height=100, color=(0, 0, 0))
    padded = _add_adaptive_padding(img, PADDING_SIZE)
    
    # Size should increase by 2*PADDING_SIZE on each dimension
    expected_width = 100 + 2 * PADDING_SIZE
    expected_height = 100 + 2 * PADDING_SIZE
    assert padded.size == (expected_width, expected_height)
    
    # Check corner pixel should be black (0, 0, 0)
    corner_pixel = padded.getpixel((0, 0))
    assert corner_pixel == (0, 0, 0), f"Expected black padding, got {corner_pixel}"
    
    logger.debug(f"Dark image correctly received black padding")


def test_adaptive_padding_threshold_boundary(create_test_image):
    """
    Verify padding color changes at BRIGHTNESS_THRESHOLD boundary.
    Note: The implementation uses avg_brightness > threshold, so values
    equal to threshold get black padding, values above get white.
    """
    # Test just at threshold (should get black, since it uses >)
    img_at_threshold = create_test_image(width=100, height=100, 
                                         color=(BRIGHTNESS_THRESHOLD, 
                                               BRIGHTNESS_THRESHOLD, 
                                               BRIGHTNESS_THRESHOLD))
    padded_at = _add_adaptive_padding(img_at_threshold, PADDING_SIZE)
    corner_at = padded_at.getpixel((0, 0))
    
    # Test just above threshold (should get white)
    img_above = create_test_image(width=100, height=100,
                                  color=(BRIGHTNESS_THRESHOLD + 1,
                                        BRIGHTNESS_THRESHOLD + 1,
                                        BRIGHTNESS_THRESHOLD + 1))
    padded_above = _add_adaptive_padding(img_above, PADDING_SIZE)
    corner_above = padded_above.getpixel((0, 0))
    
    # At threshold gets black (uses >), above threshold gets white
    assert corner_at == (0, 0, 0), "At threshold should get black padding (uses >)"
    assert corner_above == (255, 255, 255), "Above threshold should get white padding"
    
    logger.debug(f"Brightness threshold ({BRIGHTNESS_THRESHOLD}) boundary correctly enforced")


def test_adaptive_padding_size_correctness(create_test_image):
    """
    Verify padding adds correct amount to all sides.
    """
    original_width, original_height = 200, 150
    img = create_test_image(width=original_width, height=original_height)
    
    padded = _add_adaptive_padding(img, PADDING_SIZE)
    
    # Check dimensions increased by 2*PADDING_SIZE
    assert padded.size[0] == original_width + 2 * PADDING_SIZE
    assert padded.size[1] == original_height + 2 * PADDING_SIZE
    
    logger.debug(f"Padding correctly added {PADDING_SIZE}px on all sides")


# ============================================================================
# ARRAY CONVERSION & VALIDATION TESTS
# ============================================================================

def test_array_conversion_dtype_uint8(create_test_image, image_to_bytes):
    """
    Verify output array has dtype=uint8.
    """
    img = create_test_image(width=100, height=100)
    img_bytes = image_to_bytes(img)
    
    img_array, _ = preprocess_image(img_bytes, apply_noise_reduction=False,
                                     apply_binarization=False, apply_deskew=False,
                                     apply_brightness_norm=False)
    
    assert img_array.dtype == np.uint8, f"Expected uint8, got {img_array.dtype}"


def test_array_conversion_3d_rgb(create_test_image, image_to_bytes):
    """
    Verify output array is 3D (height, width, channels) for RGB.
    """
    img = create_test_image(width=100, height=100)
    img_bytes = image_to_bytes(img)
    
    img_array, _ = preprocess_image(img_bytes, apply_noise_reduction=False,
                                     apply_binarization=False, apply_deskew=False,
                                     apply_brightness_norm=False)
    
    assert img_array.ndim == 3, f"Expected 3D array, got {img_array.ndim}D"
    assert img_array.shape[2] == 3, f"Expected 3 channels (RGB), got {img_array.shape[2]}"


def test_array_conversion_value_range(create_test_image, image_to_bytes):
    """
    Verify output array values are clipped to [0, 255] range.
    """
    img = create_test_image(width=100, height=100)
    img_bytes = image_to_bytes(img)
    
    img_array, _ = preprocess_image(img_bytes, apply_noise_reduction=False,
                                     apply_binarization=False, apply_deskew=False,
                                     apply_brightness_norm=False)
    
    assert img_array.min() >= 0, f"Array contains values below 0: {img_array.min()}"
    assert img_array.max() <= 255, f"Array contains values above 255: {img_array.max()}"


def test_array_conversion_non_empty(create_test_image, image_to_bytes):
    """
    Verify output array is not empty.
    """
    img = create_test_image(width=100, height=100)
    img_bytes = image_to_bytes(img)
    
    img_array, _ = preprocess_image(img_bytes, apply_noise_reduction=False,
                                     apply_binarization=False, apply_deskew=False,
                                     apply_brightness_norm=False)
    
    assert img_array.size > 0, "Output array is empty"
    assert img_array.shape[0] > 0 and img_array.shape[1] > 0, "Array has zero dimensions"


def test_preprocess_returns_both_array_and_image(create_test_image, image_to_bytes):
    """
    Verify preprocess_image returns both NumPy array and PIL Image.
    """
    img = create_test_image(width=100, height=100)
    img_bytes = image_to_bytes(img)
    
    result = preprocess_image(img_bytes, apply_noise_reduction=False,
                              apply_binarization=False, apply_deskew=False,
                              apply_brightness_norm=False)
    
    assert isinstance(result, tuple), "Expected tuple return"
    assert len(result) == 2, "Expected 2 return values"
    
    img_array, img_pil = result
    assert isinstance(img_array, np.ndarray), "First return should be NumPy array"
    assert isinstance(img_pil, Image.Image), "Second return should be PIL Image"
    assert img_pil.mode == "RGB", f"PIL Image should be RGB mode, got {img_pil.mode}"
