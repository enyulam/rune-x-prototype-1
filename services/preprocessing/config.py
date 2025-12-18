"""
Rune-X Image Preprocessing Configuration

This module provides centralized configuration for image preprocessing.
Configuration can be overridden via environment variables for deployment flexibility.

Configuration Hierarchy:
1. Environment variables (.env) - highest priority
2. This config file - default values
3. Function parameters - runtime overrides

Environment Variable Format:
- PREPROCESSING_MIN_IMAGE_DIMENSION=50
- PREPROCESSING_MAX_IMAGE_DIMENSION=4000
- PREPROCESSING_CONTRAST_FACTOR=1.3
- PREPROCESSING_ENABLE_NOISE_REDUCTION=true
"""

import os
from typing import Set


def _get_bool_env(key: str, default: bool) -> bool:
    """Get boolean value from environment variable."""
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


def _get_int_env(key: str, default: int) -> int:
    """Get integer value from environment variable."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float_env(key: str, default: float) -> float:
    """Get float value from environment variable."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


# ============================================================================
# DIMENSION CONSTRAINTS
# ============================================================================

MIN_IMAGE_DIMENSION = _get_int_env(
    "PREPROCESSING_MIN_IMAGE_DIMENSION",
    50
)
"""Minimum allowed width/height in pixels"""

MAX_IMAGE_DIMENSION = _get_int_env(
    "PREPROCESSING_MAX_IMAGE_DIMENSION",
    4000
)
"""Maximum allowed width/height before resizing"""

MIN_UPSCALE_DIM = _get_int_env(
    "PREPROCESSING_MIN_UPSCALE_DIM",
    300
)
"""Minimum dimension for upscaling (images smaller than this will be upscaled)"""


# ============================================================================
# ENHANCEMENT FACTORS
# ============================================================================

CONTRAST_FACTOR = _get_float_env(
    "PREPROCESSING_CONTRAST_FACTOR",
    1.3
)
"""Contrast enhancement multiplier (1.0 = no change, >1.0 = more contrast)"""

SHARPNESS_FACTOR = _get_float_env(
    "PREPROCESSING_SHARPNESS_FACTOR",
    1.2
)
"""Sharpness enhancement multiplier (1.0 = no change, >1.0 = sharper)"""


# ============================================================================
# PADDING CONFIGURATION
# ============================================================================

PADDING_SIZE = _get_int_env(
    "PREPROCESSING_PADDING_SIZE",
    50
)
"""Border padding in pixels (applied to all sides)"""

BRIGHTNESS_THRESHOLD = _get_int_env(
    "PREPROCESSING_BRIGHTNESS_THRESHOLD",
    128
)
"""Threshold for adaptive padding color (0-255, >threshold = white, <=threshold = black)"""


# ============================================================================
# SUPPORTED FORMATS
# ============================================================================

SUPPORTED_FORMATS: Set[str] = {"JPEG", "PNG", "WEBP"}
"""Set of supported image formats"""


# ============================================================================
# OPTIONAL ENHANCEMENT DEFAULTS
# ============================================================================

DEFAULT_NOISE_REDUCTION = _get_bool_env(
    "PREPROCESSING_ENABLE_NOISE_REDUCTION",
    True
)
"""Enable noise reduction by default"""

DEFAULT_BINARIZATION = _get_bool_env(
    "PREPROCESSING_ENABLE_BINARIZATION",
    True
)
"""Enable binarization by default"""

DEFAULT_DESKEW = _get_bool_env(
    "PREPROCESSING_ENABLE_DESKEW",
    True
)
"""Enable deskewing by default"""

DEFAULT_BRIGHTNESS_NORM = _get_bool_env(
    "PREPROCESSING_ENABLE_BRIGHTNESS_NORM",
    True
)
"""Enable brightness normalization by default"""


# ============================================================================
# OPENCV ALGORITHM PARAMETERS
# ============================================================================

# Noise Reduction (Bilateral Filter)
BILATERAL_FILTER_D = _get_int_env("PREPROCESSING_BILATERAL_D", 9)
"""Diameter of pixel neighborhood for bilateral filter"""

BILATERAL_SIGMA_COLOR = _get_int_env("PREPROCESSING_BILATERAL_SIGMA_COLOR", 75)
"""Filter sigma in color space for bilateral filter"""

BILATERAL_SIGMA_SPACE = _get_int_env("PREPROCESSING_BILATERAL_SIGMA_SPACE", 75)
"""Filter sigma in coordinate space for bilateral filter"""

# Binarization (Adaptive Threshold)
ADAPTIVE_THRESHOLD_BLOCK_SIZE = _get_int_env("PREPROCESSING_ADAPTIVE_BLOCK_SIZE", 11)
"""Block size for adaptive thresholding (must be odd)"""

ADAPTIVE_THRESHOLD_C = _get_int_env("PREPROCESSING_ADAPTIVE_C", 2)
"""Constant subtracted from mean in adaptive thresholding"""

# Deskewing
DESKEW_MAX_ANGLE = _get_float_env("PREPROCESSING_DESKEW_MAX_ANGLE", 45.0)
"""Maximum rotation angle for deskewing (degrees)"""

DESKEW_CANNY_LOW = _get_int_env("PREPROCESSING_DESKEW_CANNY_LOW", 50)
"""Lower threshold for Canny edge detection"""

DESKEW_CANNY_HIGH = _get_int_env("PREPROCESSING_DESKEW_CANNY_HIGH", 150)
"""Upper threshold for Canny edge detection"""

DESKEW_HOUGH_THRESHOLD = _get_int_env("PREPROCESSING_DESKEW_HOUGH_THRESHOLD", 200)
"""Accumulator threshold for Hough line detection"""

# CLAHE (Brightness Normalization)
CLAHE_CLIP_LIMIT = _get_float_env("PREPROCESSING_CLAHE_CLIP_LIMIT", 2.0)
"""Threshold for contrast limiting in CLAHE"""

CLAHE_TILE_GRID_SIZE = _get_int_env("PREPROCESSING_CLAHE_TILE_SIZE", 8)
"""Size of grid for histogram equalization in CLAHE"""


# ============================================================================
# CONFIGURATION SUMMARY
# ============================================================================

def get_config_summary() -> dict:
    """
    Get a summary of current preprocessing configuration.
    
    Returns:
        dict: Configuration values grouped by category
    """
    return {
        "dimensions": {
            "min_dimension": MIN_IMAGE_DIMENSION,
            "max_dimension": MAX_IMAGE_DIMENSION,
            "min_upscale_dim": MIN_UPSCALE_DIM
        },
        "enhancement": {
            "contrast_factor": CONTRAST_FACTOR,
            "sharpness_factor": SHARPNESS_FACTOR,
            "padding_size": PADDING_SIZE,
            "brightness_threshold": BRIGHTNESS_THRESHOLD
        },
        "optional_enhancements": {
            "noise_reduction": DEFAULT_NOISE_REDUCTION,
            "binarization": DEFAULT_BINARIZATION,
            "deskew": DEFAULT_DESKEW,
            "brightness_norm": DEFAULT_BRIGHTNESS_NORM
        },
        "formats": {
            "supported": list(SUPPORTED_FORMATS)
        },
        "opencv_params": {
            "bilateral_filter": {
                "d": BILATERAL_FILTER_D,
                "sigma_color": BILATERAL_SIGMA_COLOR,
                "sigma_space": BILATERAL_SIGMA_SPACE
            },
            "adaptive_threshold": {
                "block_size": ADAPTIVE_THRESHOLD_BLOCK_SIZE,
                "c": ADAPTIVE_THRESHOLD_C
            },
            "deskew": {
                "max_angle": DESKEW_MAX_ANGLE,
                "canny_low": DESKEW_CANNY_LOW,
                "canny_high": DESKEW_CANNY_HIGH,
                "hough_threshold": DESKEW_HOUGH_THRESHOLD
            },
            "clahe": {
                "clip_limit": CLAHE_CLIP_LIMIT,
                "tile_grid_size": CLAHE_TILE_GRID_SIZE
            }
        }
    }

