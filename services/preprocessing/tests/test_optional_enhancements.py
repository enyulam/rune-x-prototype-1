"""
Unit tests for optional preprocessing enhancements.

These tests verify that optional enhancements work correctly when opencv is available
and fail gracefully (with logging) when it's not.
"""

import io
import pytest
import numpy as np
from PIL import Image

from ..image_preprocessing import (
    preprocess_image,
    _apply_noise_reduction,
    _apply_binarization,
    _apply_deskew,
    _apply_brightness_normalization,
    CV2_AVAILABLE
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def create_test_image():
    """Factory fixture to create test images."""
    def _create(width=500, height=500, mode="RGB", color=(255, 255, 255)):
        img = Image.new(mode, (width, height), color)
        img.format = "PNG"
        return img
    return _create


@pytest.fixture
def image_to_bytes():
    """Convert PIL Image to bytes."""
    def _convert(img):
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    return _convert


@pytest.fixture
def create_test_array():
    """Create numpy array for testing."""
    def _create(width=500, height=500, channels=3, value=128):
        if channels == 3:
            return np.full((height, width, channels), value, dtype=np.uint8)
        else:
            return np.full((height, width), value, dtype=np.uint8)
    return _create


# ============================================================================
# TEST STEP 9: NOISE REDUCTION
# ============================================================================

@pytest.mark.skipif(not CV2_AVAILABLE, reason="opencv-python not installed")
def test_apply_noise_reduction_rgb(create_test_array):
    """Test noise reduction on RGB image."""
    img_array = create_test_array(channels=3)
    result = _apply_noise_reduction(img_array)
    
    assert isinstance(result, np.ndarray)
    assert result.dtype == np.uint8
    assert result.shape == img_array.shape


@pytest.mark.skipif(not CV2_AVAILABLE, reason="opencv-python not installed")
def test_apply_noise_reduction_grayscale(create_test_array):
    """Test noise reduction on grayscale image."""
    img_array = create_test_array(channels=1)
    result = _apply_noise_reduction(img_array)
    
    assert isinstance(result, np.ndarray)
    assert result.dtype == np.uint8


@pytest.mark.skipif(CV2_AVAILABLE, reason="Test requires opencv to be unavailable")
def test_apply_noise_reduction_without_opencv(create_test_array):
    """Test that noise reduction raises ImportError without opencv."""
    img_array = create_test_array()
    
    with pytest.raises(ImportError, match="opencv-python is required"):
        _apply_noise_reduction(img_array)


def test_preprocess_with_noise_reduction(create_test_image, image_to_bytes):
    """Test end-to-end preprocessing with noise reduction enabled."""
    img = create_test_image()
    img_bytes = image_to_bytes(img)
    
    # Should not raise even if opencv is unavailable
    img_array, img_pil = preprocess_image(
        img_bytes,
        apply_noise_reduction=True,
        apply_binarization=False,
        apply_deskew=False,
        apply_brightness_norm=False
    )
    
    assert isinstance(img_array, np.ndarray)
    assert isinstance(img_pil, Image.Image)


# ============================================================================
# TEST STEP 10: BINARIZATION
# ============================================================================

@pytest.mark.skipif(not CV2_AVAILABLE, reason="opencv-python not installed")
def test_apply_binarization_rgb(create_test_array):
    """Test binarization on RGB image."""
    img_array = create_test_array(channels=3, value=128)
    result = _apply_binarization(img_array)
    
    assert isinstance(result, np.ndarray)
    assert result.dtype == np.uint8
    # Result should be RGB (converted back after thresholding)
    assert result.ndim == 3
    assert result.shape[2] == 3


@pytest.mark.skipif(not CV2_AVAILABLE, reason="opencv-python not installed")
def test_apply_binarization_grayscale(create_test_array):
    """Test binarization on grayscale image."""
    img_array = create_test_array(channels=1, value=128)
    result = _apply_binarization(img_array)
    
    assert isinstance(result, np.ndarray)
    # Should be converted to RGB
    assert result.ndim == 3


@pytest.mark.skipif(CV2_AVAILABLE, reason="Test requires opencv to be unavailable")
def test_apply_binarization_without_opencv(create_test_array):
    """Test that binarization raises ImportError without opencv."""
    img_array = create_test_array()
    
    with pytest.raises(ImportError, match="opencv-python is required"):
        _apply_binarization(img_array)


def test_preprocess_with_binarization(create_test_image, image_to_bytes):
    """Test end-to-end preprocessing with binarization enabled."""
    img = create_test_image()
    img_bytes = image_to_bytes(img)
    
    # Should not raise even if opencv is unavailable
    img_array, img_pil = preprocess_image(
        img_bytes,
        apply_noise_reduction=False,
        apply_binarization=True,
        apply_deskew=False,
        apply_brightness_norm=False
    )
    
    assert isinstance(img_array, np.ndarray)
    assert isinstance(img_pil, Image.Image)


# ============================================================================
# TEST STEP 11: DESKEWING
# ============================================================================

@pytest.mark.skipif(not CV2_AVAILABLE, reason="opencv-python not installed")
def test_apply_deskew_no_lines(create_test_array):
    """Test deskewing when no lines are detected (returns original)."""
    img_array = create_test_array(channels=3, value=128)  # Uniform gray, no lines
    result = _apply_deskew(img_array)
    
    # Should return original when no lines detected
    assert isinstance(result, np.ndarray)
    assert result.shape == img_array.shape


@pytest.mark.skipif(not CV2_AVAILABLE, reason="opencv-python not installed")
def test_apply_deskew_with_lines(create_test_array):
    """Test deskewing with detectable lines."""
    # Create image with horizontal lines
    img_array = create_test_array(channels=3, value=255)
    # Add some black horizontal lines
    img_array[100:110, :] = 0
    img_array[200:210, :] = 0
    img_array[300:310, :] = 0
    
    result = _apply_deskew(img_array)
    
    assert isinstance(result, np.ndarray)
    assert result.shape == img_array.shape


@pytest.mark.skipif(CV2_AVAILABLE, reason="Test requires opencv to be unavailable")
def test_apply_deskew_without_opencv(create_test_array):
    """Test that deskewing raises ImportError without opencv."""
    img_array = create_test_array()
    
    with pytest.raises(ImportError, match="opencv-python is required"):
        _apply_deskew(img_array)


def test_preprocess_with_deskew(create_test_image, image_to_bytes):
    """Test end-to-end preprocessing with deskewing enabled."""
    img = create_test_image()
    img_bytes = image_to_bytes(img)
    
    # Should not raise even if opencv is unavailable
    img_array, img_pil = preprocess_image(
        img_bytes,
        apply_noise_reduction=False,
        apply_binarization=False,
        apply_deskew=True,
        apply_brightness_norm=False
    )
    
    assert isinstance(img_array, np.ndarray)
    assert isinstance(img_pil, Image.Image)


# ============================================================================
# TEST STEP 12: BRIGHTNESS NORMALIZATION
# ============================================================================

@pytest.mark.skipif(not CV2_AVAILABLE, reason="opencv-python not installed")
def test_apply_brightness_normalization_rgb(create_test_array):
    """Test brightness normalization on RGB image."""
    img_array = create_test_array(channels=3, value=100)
    result = _apply_brightness_normalization(img_array)
    
    assert isinstance(result, np.ndarray)
    assert result.dtype == np.uint8
    assert result.shape == img_array.shape
    # Result should have improved brightness distribution
    assert result.mean() != img_array.mean()  # Should be different


@pytest.mark.skipif(not CV2_AVAILABLE, reason="opencv-python not installed")
def test_apply_brightness_normalization_grayscale(create_test_array):
    """Test brightness normalization on grayscale image."""
    img_array = create_test_array(channels=1, value=100)
    result = _apply_brightness_normalization(img_array)
    
    assert isinstance(result, np.ndarray)
    assert result.dtype == np.uint8


@pytest.mark.skipif(CV2_AVAILABLE, reason="Test requires opencv to be unavailable")
def test_apply_brightness_normalization_without_opencv(create_test_array):
    """Test that brightness normalization raises ImportError without opencv."""
    img_array = create_test_array()
    
    with pytest.raises(ImportError, match="opencv-python is required"):
        _apply_brightness_normalization(img_array)


def test_preprocess_with_brightness_norm(create_test_image, image_to_bytes):
    """Test end-to-end preprocessing with brightness normalization enabled."""
    img = create_test_image()
    img_bytes = image_to_bytes(img)
    
    # Should not raise even if opencv is unavailable
    img_array, img_pil = preprocess_image(
        img_bytes,
        apply_noise_reduction=False,
        apply_binarization=False,
        apply_deskew=False,
        apply_brightness_norm=True
    )
    
    assert isinstance(img_array, np.ndarray)
    assert isinstance(img_pil, Image.Image)


# ============================================================================
# TEST ALL OPTIONAL ENHANCEMENTS COMBINED
# ============================================================================

def test_preprocess_all_enhancements_enabled(create_test_image, image_to_bytes):
    """Test preprocessing with all optional enhancements enabled."""
    img = create_test_image(width=500, height=500)
    img_bytes = image_to_bytes(img)
    
    # Should complete successfully regardless of opencv availability
    img_array, img_pil = preprocess_image(
        img_bytes,
        apply_noise_reduction=True,
        apply_binarization=True,
        apply_deskew=True,
        apply_brightness_norm=True
    )
    
    assert isinstance(img_array, np.ndarray)
    assert isinstance(img_pil, Image.Image)
    assert img_pil.mode == "RGB"


def test_preprocess_all_enhancements_disabled(create_test_image, image_to_bytes):
    """Test preprocessing with all optional enhancements disabled."""
    img = create_test_image(width=500, height=500)
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


def test_preprocess_selective_enhancements(create_test_image, image_to_bytes):
    """Test preprocessing with selective enhancements."""
    img = create_test_image()
    img_bytes = image_to_bytes(img)
    
    # Test various combinations
    combinations = [
        (True, False, False, False),
        (False, True, False, False),
        (False, False, True, False),
        (False, False, False, True),
        (True, True, False, False),
        (True, False, True, False),
        (False, True, True, False),
    ]
    
    for noise, binarize, deskew, brightness in combinations:
        img_array, img_pil = preprocess_image(
            img_bytes,
            apply_noise_reduction=noise,
            apply_binarization=binarize,
            apply_deskew=deskew,
            apply_brightness_norm=brightness
        )
        
        assert isinstance(img_array, np.ndarray)
        assert isinstance(img_pil, Image.Image)


# ============================================================================
# TEST GRACEFUL DEGRADATION
# ============================================================================

def test_optional_enhancement_graceful_failure(create_test_image, image_to_bytes, monkeypatch):
    """Test that optional enhancements fail gracefully with logging."""
    img = create_test_image()
    img_bytes = image_to_bytes(img)
    
    # Mock opencv functions to raise exceptions
    if CV2_AVAILABLE:
        import cv2
        
        def mock_bilateral_filter(*args, **kwargs):
            raise RuntimeError("Simulated failure")
        
        monkeypatch.setattr("cv2.bilateralFilter", mock_bilateral_filter)
        
        # Should complete successfully even with simulated failure
        img_array, img_pil = preprocess_image(
            img_bytes,
            apply_noise_reduction=True,
            apply_binarization=False,
            apply_deskew=False,
            apply_brightness_norm=False
        )
        
        # Should still return valid output
        assert isinstance(img_array, np.ndarray)
        assert isinstance(img_pil, Image.Image)

