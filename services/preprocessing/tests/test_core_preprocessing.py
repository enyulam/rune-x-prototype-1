"""
Unit tests for core preprocessing steps (FATAL operations).

These tests verify that all mandatory preprocessing steps work correctly
and raise appropriate exceptions on failure.
"""

import io
import pytest
import numpy as np
from PIL import Image
from fastapi import HTTPException

from ..image_preprocessing import (
    preprocess_image,
    _validate_format,
    _validate_dimensions,
    _resize_large_image,
    _ensure_rgb,
    _upscale_small_image,
    _enhance_contrast,
    _enhance_sharpness,
    _add_adaptive_padding
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def create_test_image():
    """Factory fixture to create test images with specific properties."""
    def _create(width=500, height=500, mode="RGB", color=(255, 255, 255), format="PNG"):
        """Create a test image with specified parameters."""
        img = Image.new(mode, (width, height), color)
        img.format = format
        return img
    return _create


@pytest.fixture
def image_to_bytes():
    """Convert PIL Image to bytes."""
    def _convert(img, format="PNG"):
        buf = io.BytesIO()
        # Ensure format is set
        if not hasattr(img, 'format') or img.format is None:
            img.format = format
        img.save(buf, format=format)
        return buf.getvalue()
    return _convert


# ============================================================================
# TEST STEP 1: IMAGE LOADING & FORMAT VALIDATION
# ============================================================================

def test_validate_format_supported(create_test_image):
    """Test that supported formats pass validation."""
    for fmt in ["JPEG", "PNG", "WEBP"]:
        img = create_test_image(format=fmt)
        _validate_format(img)  # Should not raise


def test_validate_format_unsupported(create_test_image):
    """Test that unsupported formats raise ValueError."""
    img = create_test_image()
    img.format = "BMP"  # Unsupported format
    
    with pytest.raises(ValueError, match="Unsupported image format"):
        _validate_format(img)


def test_preprocess_invalid_image_bytes():
    """Test that invalid image bytes raise HTTPException."""
    invalid_bytes = b"not an image"
    
    with pytest.raises(HTTPException) as exc_info:
        preprocess_image(invalid_bytes)
    
    assert exc_info.value.status_code == 400
    assert "Invalid image format" in exc_info.value.detail


# ============================================================================
# TEST STEP 2: DIMENSION VALIDATION
# ============================================================================

def test_validate_dimensions_valid():
    """Test that valid dimensions pass validation."""
    _validate_dimensions(100, 100)  # Should not raise
    _validate_dimensions(50, 50)    # Minimum
    _validate_dimensions(4000, 4000)  # Maximum (before resizing)


def test_validate_dimensions_too_small():
    """Test that dimensions below minimum raise ValueError."""
    with pytest.raises(ValueError, match="too small"):
        _validate_dimensions(49, 100)
    
    with pytest.raises(ValueError, match="too small"):
        _validate_dimensions(100, 49)
    
    with pytest.raises(ValueError, match="too small"):
        _validate_dimensions(49, 49)


def test_preprocess_image_too_small(create_test_image, image_to_bytes):
    """Test that images below minimum dimensions are rejected."""
    img = create_test_image(width=40, height=40)
    img_bytes = image_to_bytes(img)
    
    with pytest.raises(HTTPException) as exc_info:
        preprocess_image(img_bytes)
    
    assert exc_info.value.status_code == 400
    assert "too small" in exc_info.value.detail


# ============================================================================
# TEST STEP 3: LARGE IMAGE RESIZING
# ============================================================================

def test_resize_large_image_no_resize_needed(create_test_image):
    """Test that images within limits are not resized."""
    img = create_test_image(width=500, height=500)
    resized = _resize_large_image(img, 4000)
    
    assert resized.size == (500, 500)


def test_resize_large_image_width_exceeds(create_test_image):
    """Test resizing when width exceeds limit."""
    img = create_test_image(width=5000, height=2000)
    resized = _resize_large_image(img, 4000)
    
    assert resized.size[0] <= 4000
    assert resized.size[1] <= 4000
    # Aspect ratio preserved
    assert abs((5000/2000) - (resized.size[0]/resized.size[1])) < 0.01


def test_resize_large_image_height_exceeds(create_test_image):
    """Test resizing when height exceeds limit."""
    img = create_test_image(width=2000, height=5000)
    resized = _resize_large_image(img, 4000)
    
    assert resized.size[0] <= 4000
    assert resized.size[1] <= 4000
    # Aspect ratio preserved
    assert abs((2000/5000) - (resized.size[0]/resized.size[1])) < 0.01


# ============================================================================
# TEST STEP 4: RGB CONVERSION
# ============================================================================

def test_ensure_rgb_already_rgb(create_test_image):
    """Test that RGB images pass through unchanged."""
    img = create_test_image(mode="RGB")
    result = _ensure_rgb(img)
    
    assert result.mode == "RGB"
    assert result.size == img.size


def test_ensure_rgb_from_rgba(create_test_image):
    """Test RGBA to RGB conversion."""
    img = create_test_image(mode="RGBA", color=(255, 0, 0, 128))
    result = _ensure_rgb(img)
    
    assert result.mode == "RGB"
    assert result.size == img.size


def test_ensure_rgb_from_grayscale(create_test_image):
    """Test grayscale to RGB conversion."""
    img = create_test_image(mode="L", color=128)
    result = _ensure_rgb(img)
    
    assert result.mode == "RGB"
    assert result.size == img.size


def test_ensure_rgb_from_palette(create_test_image):
    """Test palette mode to RGB conversion."""
    img = create_test_image(mode="P")
    result = _ensure_rgb(img)
    
    assert result.mode == "RGB"


# ============================================================================
# TEST STEP 5: SMALL IMAGE UPSCALING
# ============================================================================

def test_upscale_small_image_no_upscale_needed(create_test_image):
    """Test that images above minimum are not upscaled."""
    img = create_test_image(width=500, height=500)
    upscaled = _upscale_small_image(img, 300)
    
    assert upscaled.size == (500, 500)


def test_upscale_small_image_width_below_min(create_test_image):
    """Test upscaling when width is below minimum."""
    img = create_test_image(width=200, height=400)
    upscaled = _upscale_small_image(img, 300)
    
    assert upscaled.size[0] >= 300
    assert upscaled.size[1] >= 300
    # Aspect ratio preserved
    assert abs((200/400) - (upscaled.size[0]/upscaled.size[1])) < 0.01


def test_upscale_small_image_height_below_min(create_test_image):
    """Test upscaling when height is below minimum."""
    img = create_test_image(width=400, height=200)
    upscaled = _upscale_small_image(img, 300)
    
    assert upscaled.size[0] >= 300
    assert upscaled.size[1] >= 300
    # Aspect ratio preserved
    assert abs((400/200) - (upscaled.size[0]/upscaled.size[1])) < 0.01


# ============================================================================
# TEST STEP 6: CONTRAST ENHANCEMENT
# ============================================================================

def test_enhance_contrast(create_test_image):
    """Test contrast enhancement."""
    # Create image with gradient (has contrast to enhance)
    img = Image.new("RGB", (100, 100))
    pixels = img.load()
    for i in range(100):
        for j in range(100):
            # Create gradient from 0 to 255
            gray_value = int((i / 100) * 255)
            pixels[i, j] = (gray_value, gray_value, gray_value)
    img.format = "PNG"
    
    enhanced = _enhance_contrast(img, 1.5)
    
    assert enhanced.size == img.size
    assert enhanced.mode == img.mode
    # Enhanced image should have different pixel values
    # (uniform gray has no contrast to enhance, so we use gradient)
    assert not np.array_equal(np.array(img), np.array(enhanced))


def test_enhance_contrast_no_change(create_test_image):
    """Test contrast enhancement with factor=1.0 (no change)."""
    img = create_test_image()
    enhanced = _enhance_contrast(img, 1.0)
    
    # Should be nearly identical
    assert enhanced.size == img.size


# ============================================================================
# TEST STEP 7: SHARPNESS ENHANCEMENT
# ============================================================================

def test_enhance_sharpness(create_test_image):
    """Test sharpness enhancement."""
    img = create_test_image()
    enhanced = _enhance_sharpness(img, 1.5)
    
    assert enhanced.size == img.size
    assert enhanced.mode == img.mode


def test_enhance_sharpness_no_change(create_test_image):
    """Test sharpness enhancement with factor=1.0 (no change)."""
    img = create_test_image()
    enhanced = _enhance_sharpness(img, 1.0)
    
    assert enhanced.size == img.size


# ============================================================================
# TEST STEP 8: ADAPTIVE PADDING
# ============================================================================

def test_add_adaptive_padding_bright_image(create_test_image):
    """Test that bright images get white padding."""
    img = create_test_image(width=100, height=100, color=(255, 255, 255))
    padded = _add_adaptive_padding(img, 50)
    
    # Size should increase by 2*padding on each side
    assert padded.size == (200, 200)
    
    # Check corner pixel (should be white for bright image)
    corner_pixel = padded.getpixel((0, 0))
    assert corner_pixel == (255, 255, 255)


def test_add_adaptive_padding_dark_image(create_test_image):
    """Test that dark images get black padding."""
    img = create_test_image(width=100, height=100, color=(0, 0, 0))
    padded = _add_adaptive_padding(img, 50)
    
    # Size should increase by 2*padding on each side
    assert padded.size == (200, 200)
    
    # Check corner pixel (should be black for dark image)
    corner_pixel = padded.getpixel((0, 0))
    assert corner_pixel == (0, 0, 0)


# ============================================================================
# TEST END-TO-END CORE PREPROCESSING
# ============================================================================

def test_preprocess_image_end_to_end(create_test_image, image_to_bytes):
    """Test full preprocessing pipeline with valid image."""
    img = create_test_image(width=500, height=500)
    img_bytes = image_to_bytes(img)
    
    # Disable optional enhancements for this test
    img_array, img_pil = preprocess_image(
        img_bytes,
        apply_noise_reduction=False,
        apply_binarization=False,
        apply_deskew=False,
        apply_brightness_norm=False
    )
    
    # Check numpy array output
    assert isinstance(img_array, np.ndarray)
    assert img_array.dtype == np.uint8
    assert img_array.ndim == 3  # RGB image
    
    # Check PIL image output
    assert isinstance(img_pil, Image.Image)
    assert img_pil.mode == "RGB"
    
    # Image should be padded (50px on each side)
    assert img_pil.size[0] > 500
    assert img_pil.size[1] > 500


def test_preprocess_image_various_sizes(create_test_image, image_to_bytes):
    """Test preprocessing with various image sizes."""
    test_sizes = [
        (50, 50),      # Minimum
        (100, 200),    # Small, needs upscaling
        (500, 500),    # Normal
        (1000, 500),   # Wide
        (500, 1000),   # Tall
    ]
    
    for width, height in test_sizes:
        img = create_test_image(width=width, height=height)
        img_bytes = image_to_bytes(img)
        
        img_array, img_pil = preprocess_image(
            img_bytes,
            apply_noise_reduction=False,
            apply_binarization=False,
            apply_deskew=False,
            apply_brightness_norm=False
        )
        
        assert isinstance(img_array, np.ndarray)
        assert isinstance(img_pil, Image.Image)
        assert img_pil.mode == "RGB"


def test_preprocess_image_various_formats(create_test_image, image_to_bytes):
    """Test preprocessing with various image formats."""
    for fmt in ["PNG", "JPEG"]:  # WEBP might not be available in test environment
        img = create_test_image(format=fmt)
        img_bytes = image_to_bytes(img, format=fmt)
        
        img_array, img_pil = preprocess_image(
            img_bytes,
            apply_noise_reduction=False,
            apply_binarization=False,
            apply_deskew=False,
            apply_brightness_norm=False
        )
        
        assert isinstance(img_array, np.ndarray)
        assert isinstance(img_pil, Image.Image)

