"""
Rune-X Image Preprocessing Module

This module provides production-grade image preprocessing for OCR engines.

Architecture:
- Core Preprocessing (Steps 1-8): FATAL operations that must succeed
- Optional Enhancements (Steps 9-12): Gracefully degrade if they fail
- Array Conversion (Step 13): FATAL operation to ensure valid output

Error Handling Strategy:
- Core steps RAISE exceptions immediately (no silent failures)
- Optional steps LOG warnings and continue (preserves OCR pipeline)
- No scattered try-catch blocks (clear separation of concerns)

Configuration Hierarchy:
1. Function parameters (primary, runtime control)
2. Module constants (defaults, version-controlled)
3. .env overrides (secondary, deployment-specific)
"""

import io
import logging
from typing import Tuple

import numpy as np
from PIL import Image, ImageEnhance, ImageOps
from fastapi import HTTPException

# Import configuration
from . import config

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logging.warning("opencv-python not installed. Optional enhancements (noise reduction, binarization, deskewing, brightness normalization) will be unavailable.")

# ============================================================================
# PREPROCESSING CONSTANTS (Imported from config module)
# ============================================================================

# Dimension Limits
MIN_IMAGE_DIMENSION = config.MIN_IMAGE_DIMENSION
MAX_IMAGE_DIMENSION = config.MAX_IMAGE_DIMENSION
MIN_UPSCALE_DIM = config.MIN_UPSCALE_DIM

# Enhancement Factors
CONTRAST_FACTOR = config.CONTRAST_FACTOR
SHARPNESS_FACTOR = config.SHARPNESS_FACTOR

# Padding
PADDING_SIZE = config.PADDING_SIZE
BRIGHTNESS_THRESHOLD = config.BRIGHTNESS_THRESHOLD

# Supported Formats
SUPPORTED_FORMATS = config.SUPPORTED_FORMATS

# Optional Enhancement Defaults
DEFAULT_NOISE_REDUCTION = config.DEFAULT_NOISE_REDUCTION
DEFAULT_BINARIZATION = config.DEFAULT_BINARIZATION
DEFAULT_DESKEW = config.DEFAULT_DESKEW
DEFAULT_BRIGHTNESS_NORM = config.DEFAULT_BRIGHTNESS_NORM


# ============================================================================
# MAIN PREPROCESSING FUNCTION
# ============================================================================

def preprocess_image(
    img_bytes: bytes,
    apply_noise_reduction: bool = DEFAULT_NOISE_REDUCTION,
    apply_binarization: bool = DEFAULT_BINARIZATION,
    apply_deskew: bool = DEFAULT_DESKEW,
    apply_brightness_norm: bool = DEFAULT_BRIGHTNESS_NORM
) -> Tuple[np.ndarray, Image.Image]:
    """
    Preprocess an input image for OCR with two-tier enhancement strategy.

    This function implements a production-grade preprocessing pipeline:
    1. Core enhancements (FATAL): Must succeed or pipeline fails
    2. Optional enhancements (OPTIONAL): Fail gracefully with logging

    Core Enhancement Steps (FATAL - will raise exceptions):
    - Step 1: Image loading & format validation
    - Step 2: Dimension validation
    - Step 3: Large image resizing (>4000px)
    - Step 4: RGB color mode conversion
    - Step 5: Small image upscaling (<300px)
    - Step 6: Contrast enhancement (1.3x)
    - Step 7: Sharpness enhancement (1.2x)
    - Step 8: Adaptive padding (50px, brightness-based)

    Optional Enhancement Steps (OPTIONAL - will log warnings on failure):
    - Step 9: Noise reduction (median blur)
    - Step 10: Binarization (Otsu thresholding)
    - Step 11: Deskewing (tilt correction)
    - Step 12: Brightness normalization (histogram equalization)

    Final Step (FATAL):
    - Step 13: Array conversion & validation

    Args:
        img_bytes (bytes): Raw image bytes from uploaded file.
        apply_noise_reduction (bool): Apply median blur noise reduction.
            Recommended for scanned/photographed documents.
        apply_binarization (bool): Apply Otsu binarization (thresholding).
            Recommended for high-contrast handwriting.
        apply_deskew (bool): Apply deskewing/tilt correction.
            Recommended for rotated documents.
        apply_brightness_norm (bool): Apply histogram equalization.
            Recommended for unevenly lit images.

    Returns:
        Tuple[np.ndarray, Image.Image]:
            - img_array: Preprocessed image as NumPy array (uint8, 0-255) for OCR
            - img_pil: Final PIL Image for logging/metadata/debugging

    Raises:
        HTTPException: If any core preprocessing step fails (400/500 status)
        
    Examples:
        >>> with open("image.jpg", "rb") as f:
        ...     img_bytes = f.read()
        >>> img_array, img_pil = preprocess_image(img_bytes)
        >>> # Use img_array for OCR processing
        >>> # Use img_pil for logging or metadata extraction

        >>> # Disable optional enhancements for speed
        >>> img_array, img_pil = preprocess_image(
        ...     img_bytes,
        ...     apply_noise_reduction=False,
        ...     apply_binarization=False
        ... )

    Notes:
        - Core steps will RAISE exceptions if they fail
        - Optional steps will LOG warnings and continue
        - Requires opencv-python for optional enhancements
        - All enhancements preserve image aspect ratio
        - Deterministic output for same input and parameters
    """
    logger = logging.getLogger(__name__)
    
    # ========================================================================
    # CORE PREPROCESSING (FATAL - These steps MUST succeed)
    # ========================================================================
    
    # Step 1: Load image and validate format
    try:
        img_pil = Image.open(io.BytesIO(img_bytes))
        _validate_format(img_pil)
        logger.debug(f"Loaded image: format={img_pil.format}, size={img_pil.size}, mode={img_pil.mode}")
    except Exception as e:
        logger.error(f"Failed to load or validate image: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid image format: {str(e)}")
    
    # Step 2: Validate dimensions
    width, height = img_pil.size
    try:
        _validate_dimensions(width, height)
        logger.debug(f"Validated dimensions: {width}x{height}")
    except ValueError as e:
        logger.error(f"Invalid image dimensions: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    # Step 3: Resize large images
    try:
        img_pil = _resize_large_image(img_pil, MAX_IMAGE_DIMENSION)
        if (width, height) != img_pil.size:
            logger.info(f"Resized image from {width}x{height} to {img_pil.size}")
    except Exception as e:
        logger.error(f"Failed to resize large image: {e}")
        raise HTTPException(status_code=500, detail=f"Image resizing failed: {str(e)}")
    
    # Step 4: Ensure RGB color mode
    try:
        original_mode = img_pil.mode
        img_pil = _ensure_rgb(img_pil)
        if original_mode != img_pil.mode:
            logger.debug(f"Converted image from {original_mode} to {img_pil.mode}")
    except Exception as e:
        logger.error(f"Failed to convert to RGB: {e}")
        raise HTTPException(status_code=500, detail=f"Color conversion failed: {str(e)}")
    
    # Step 5: Upscale small images
    try:
        original_size = img_pil.size
        img_pil = _upscale_small_image(img_pil, MIN_UPSCALE_DIM)
        if original_size != img_pil.size:
            logger.info(f"Upscaled image from {original_size} to {img_pil.size}")
    except Exception as e:
        logger.error(f"Failed to upscale small image: {e}")
        raise HTTPException(status_code=500, detail=f"Image upscaling failed: {str(e)}")
    
    # Step 6: Enhance contrast
    try:
        img_pil = _enhance_contrast(img_pil, CONTRAST_FACTOR)
        logger.debug(f"Enhanced contrast by {CONTRAST_FACTOR}x")
    except Exception as e:
        logger.error(f"Failed to enhance contrast: {e}")
        raise HTTPException(status_code=500, detail=f"Contrast enhancement failed: {str(e)}")
    
    # Step 7: Enhance sharpness
    try:
        img_pil = _enhance_sharpness(img_pil, SHARPNESS_FACTOR)
        logger.debug(f"Enhanced sharpness by {SHARPNESS_FACTOR}x")
    except Exception as e:
        logger.error(f"Failed to enhance sharpness: {e}")
        raise HTTPException(status_code=500, detail=f"Sharpness enhancement failed: {str(e)}")
    
    # Step 8: Add adaptive padding
    try:
        img_pil = _add_adaptive_padding(img_pil, PADDING_SIZE)
        logger.debug(f"Added {PADDING_SIZE}px adaptive padding")
    except Exception as e:
        logger.error(f"Failed to add padding: {e}")
        raise HTTPException(status_code=500, detail=f"Padding failed: {str(e)}")
    
    # ========================================================================
    # OPTIONAL ENHANCEMENTS (Fail gracefully, log warnings)
    # ========================================================================
    
    # Convert to numpy array for OpenCV operations
    img_np = np.array(img_pil)
    
    # Step 9: Noise reduction (optional)
    if apply_noise_reduction and CV2_AVAILABLE:
        try:
            img_np = _apply_noise_reduction(img_np)
            logger.debug("Applied noise reduction (median blur)")
        except Exception as e:
            logger.warning(f"Noise reduction failed, continuing without it: {e}")
    elif apply_noise_reduction and not CV2_AVAILABLE:
        logger.warning("Noise reduction requested but opencv-python not available")
    
    # Step 10: Binarization (optional)
    if apply_binarization and CV2_AVAILABLE:
        try:
            img_np = _apply_binarization(img_np)
            logger.debug("Applied Otsu binarization")
        except Exception as e:
            logger.warning(f"Binarization failed, continuing without it: {e}")
    elif apply_binarization and not CV2_AVAILABLE:
        logger.warning("Binarization requested but opencv-python not available")
    
    # Step 11: Deskewing (optional)
    if apply_deskew and CV2_AVAILABLE:
        try:
            img_np = _apply_deskew(img_np)
            logger.debug("Applied deskewing (tilt correction)")
        except Exception as e:
            logger.warning(f"Deskewing failed, continuing without it: {e}")
    elif apply_deskew and not CV2_AVAILABLE:
        logger.warning("Deskewing requested but opencv-python not available")
    
    # Step 12: Brightness normalization (optional)
    if apply_brightness_norm and CV2_AVAILABLE:
        try:
            img_np = _apply_brightness_normalization(img_np)
            logger.debug("Applied brightness normalization (histogram equalization)")
        except Exception as e:
            logger.warning(f"Brightness normalization failed, continuing without it: {e}")
    elif apply_brightness_norm and not CV2_AVAILABLE:
        logger.warning("Brightness normalization requested but opencv-python not available")
    
    # ========================================================================
    # FINAL ARRAY CONVERSION & VALIDATION (FATAL)
    # ========================================================================
    
    # Step 13: Validate output array
    try:
        if not isinstance(img_np, np.ndarray):
            raise ValueError("Image is not a valid numpy array")
        
        if img_np.dtype != np.uint8:
            logger.warning(f"Converting array from {img_np.dtype} to uint8")
            img_np = img_np.astype(np.uint8)
        
        if img_np.size == 0:
            raise ValueError("Processed image array is empty")
        
        # Convert back to PIL for return
        img_pil_final = Image.fromarray(img_np)
        
        logger.info(f"Preprocessing complete: final size={img_pil_final.size}, dtype={img_np.dtype}, shape={img_np.shape}")
        
        return img_np, img_pil_final
        
    except Exception as e:
        logger.error(f"Failed to validate output array: {e}")
        raise HTTPException(status_code=500, detail=f"Array validation failed: {str(e)}")


# ============================================================================
# HELPER FUNCTIONS (To be implemented)
# ============================================================================

def _validate_format(img_pil: Image.Image) -> None:
    """
    Validate image format is supported (FATAL).
    
    Args:
        img_pil: PIL Image object
        
    Raises:
        ValueError: If format is not supported
    """
    if img_pil.format not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported image format: {img_pil.format}. "
            f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )


def _validate_dimensions(width: int, height: int) -> None:
    """
    Validate image dimensions are within acceptable range (FATAL).
    
    Args:
        width: Image width in pixels
        height: Image height in pixels
        
    Raises:
        ValueError: If dimensions are too small
    """
    if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
        raise ValueError(
            f"Image dimensions too small: {width}x{height}. "
            f"Minimum required: {MIN_IMAGE_DIMENSION}x{MIN_IMAGE_DIMENSION}"
        )


def _resize_large_image(img_pil: Image.Image, max_dim: int) -> Image.Image:
    """
    Resize image if larger than max dimension (FATAL).
    
    Maintains aspect ratio while ensuring both dimensions are <= max_dim.
    
    Args:
        img_pil: PIL Image object
        max_dim: Maximum allowed dimension (width or height)
        
    Returns:
        Resized PIL Image (or original if already within limits)
        
    Raises:
        Exception: If resizing operation fails
    """
    width, height = img_pil.size
    
    if width <= max_dim and height <= max_dim:
        return img_pil
    
    # Calculate scaling factor to fit within max_dim
    scale = min(max_dim / width, max_dim / height)
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    return img_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)


def _ensure_rgb(img_pil: Image.Image) -> Image.Image:
    """
    Convert image to RGB mode if needed (FATAL).
    
    Handles common color modes: RGBA, L (grayscale), P (palette), etc.
    
    Args:
        img_pil: PIL Image object
        
    Returns:
        PIL Image in RGB mode
        
    Raises:
        Exception: If conversion fails
    """
    if img_pil.mode == "RGB":
        return img_pil
    
    # RGBA -> RGB (composite on white background)
    if img_pil.mode == "RGBA":
        background = Image.new("RGB", img_pil.size, (255, 255, 255))
        background.paste(img_pil, mask=img_pil.split()[3])  # Use alpha channel as mask
        return background
    
    # All other modes -> RGB
    return img_pil.convert("RGB")


def _upscale_small_image(img_pil: Image.Image, min_dim: int) -> Image.Image:
    """
    Upscale image if smaller than minimum dimension (FATAL).
    
    Maintains aspect ratio while ensuring both dimensions are >= min_dim.
    
    Args:
        img_pil: PIL Image object
        min_dim: Minimum required dimension (width or height)
        
    Returns:
        Upscaled PIL Image (or original if already large enough)
        
    Raises:
        Exception: If upscaling operation fails
    """
    width, height = img_pil.size
    
    if width >= min_dim and height >= min_dim:
        return img_pil
    
    # Calculate scaling factor to meet min_dim
    scale = max(min_dim / width, min_dim / height)
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    return img_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)


def _enhance_contrast(img_pil: Image.Image, factor: float) -> Image.Image:
    """
    Enhance image contrast (FATAL).
    
    Args:
        img_pil: PIL Image object
        factor: Contrast enhancement factor (1.0 = no change, >1.0 = more contrast)
        
    Returns:
        Contrast-enhanced PIL Image
        
    Raises:
        Exception: If enhancement fails
    """
    enhancer = ImageEnhance.Contrast(img_pil)
    return enhancer.enhance(factor)


def _enhance_sharpness(img_pil: Image.Image, factor: float) -> Image.Image:
    """
    Enhance image sharpness (FATAL).
    
    Args:
        img_pil: PIL Image object
        factor: Sharpness enhancement factor (1.0 = no change, >1.0 = sharper)
        
    Returns:
        Sharpness-enhanced PIL Image
        
    Raises:
        Exception: If enhancement fails
    """
    enhancer = ImageEnhance.Sharpness(img_pil)
    return enhancer.enhance(factor)


def _add_adaptive_padding(img_pil: Image.Image, padding: int) -> Image.Image:
    """
    Add adaptive padding based on image brightness (FATAL).
    
    Analyzes average brightness and adds white padding for bright images,
    black padding for dark images.
    
    Args:
        img_pil: PIL Image object
        padding: Padding size in pixels (applied to all sides)
        
    Returns:
        PIL Image with padding
        
    Raises:
        Exception: If padding operation fails
    """
    # Calculate average brightness
    grayscale = img_pil.convert("L")
    avg_brightness = np.array(grayscale).mean()
    
    # Choose padding color based on brightness
    if avg_brightness > BRIGHTNESS_THRESHOLD:
        border_color = (255, 255, 255)  # White padding for bright images
    else:
        border_color = (0, 0, 0)  # Black padding for dark images
    
    return ImageOps.expand(img_pil, border=padding, fill=border_color)


def _apply_noise_reduction(img_np: np.ndarray) -> np.ndarray:
    """
    Apply bilateral filter for noise reduction (OPTIONAL).
    
    Uses bilateral filter which preserves edges while reducing noise.
    
    Args:
        img_np: NumPy array (uint8, RGB or grayscale)
        
    Returns:
        Noise-reduced NumPy array
        
    Raises:
        Exception: If opencv-python not available or filtering fails
    """
    if not CV2_AVAILABLE:
        raise ImportError("opencv-python is required for noise reduction")
    
    # Bilateral filter: reduces noise while keeping edges sharp
    return cv2.bilateralFilter(
        img_np,
        d=config.BILATERAL_FILTER_D,
        sigmaColor=config.BILATERAL_SIGMA_COLOR,
        sigmaSpace=config.BILATERAL_SIGMA_SPACE
    )


def _apply_binarization(img_np: np.ndarray) -> np.ndarray:
    """
    Apply adaptive thresholding for binarization (OPTIONAL).
    
    Uses adaptive thresholding which works better than Otsu for
    images with varying lighting conditions.
    
    Args:
        img_np: NumPy array (uint8, RGB or grayscale)
        
    Returns:
        Binarized NumPy array (black and white only)
        
    Raises:
        Exception: If opencv-python not available or binarization fails
    """
    if not CV2_AVAILABLE:
        raise ImportError("opencv-python is required for binarization")
    
    # Convert to grayscale if needed
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_np
    
    # Adaptive threshold: better for varying illumination
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=config.ADAPTIVE_THRESHOLD_BLOCK_SIZE,
        C=config.ADAPTIVE_THRESHOLD_C
    )
    
    # Convert back to RGB for consistency
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)


def _apply_deskew(img_np: np.ndarray) -> np.ndarray:
    """
    Apply deskewing/tilt correction (OPTIONAL).
    
    Detects and corrects text rotation using Hough line transform.
    Only applies correction if angle is between -45° and +45°.
    
    Args:
        img_np: NumPy array (uint8, RGB or grayscale)
        
    Returns:
        Deskewed NumPy array
        
    Raises:
        Exception: If opencv-python not available or deskewing fails
    """
    if not CV2_AVAILABLE:
        raise ImportError("opencv-python is required for deskewing")
    
    # Convert to grayscale if needed
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_np
    
    # Edge detection
    edges = cv2.Canny(gray, config.DESKEW_CANNY_LOW, config.DESKEW_CANNY_HIGH, apertureSize=3)
    
    # Detect lines using Hough transform
    lines = cv2.HoughLines(edges, 1, np.pi / 180, config.DESKEW_HOUGH_THRESHOLD)
    
    if lines is None or len(lines) == 0:
        # No lines detected, return original
        return img_np
    
    # Calculate median angle
    angles = []
    for line in lines:
        _, theta = line[0]  # rho not needed, only theta for angle calculation
        angle = (theta * 180 / np.pi) - 90
        angles.append(angle)
    
    median_angle = np.median(angles)
    
    # Only deskew if angle is reasonable
    if abs(median_angle) > config.DESKEW_MAX_ANGLE:
        return img_np
    
    # Rotate image to correct skew
    height, width = img_np.shape[:2]
    center = (width // 2, height // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    
    deskewed = cv2.warpAffine(
        img_np,
        rotation_matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE
    )
    
    return deskewed


def _apply_brightness_normalization(img_np: np.ndarray) -> np.ndarray:
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) (OPTIONAL).
    
    CLAHE is better than standard histogram equalization as it avoids
    over-amplification of noise in relatively homogeneous regions.
    
    Args:
        img_np: NumPy array (uint8, RGB or grayscale)
        
    Returns:
        Brightness-normalized NumPy array
        
    Raises:
        Exception: If opencv-python not available or normalization fails
    """
    if not CV2_AVAILABLE:
        raise ImportError("opencv-python is required for brightness normalization")
    
    # Convert to LAB color space for better results
    if len(img_np.shape) == 3:
        lab = cv2.cvtColor(img_np, cv2.COLOR_RGB2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
    else:
        l_channel = img_np
    
    # Apply CLAHE to L channel (or grayscale image)
    clahe = cv2.createCLAHE(
        clipLimit=config.CLAHE_CLIP_LIMIT,
        tileGridSize=(config.CLAHE_TILE_GRID_SIZE, config.CLAHE_TILE_GRID_SIZE)
    )
    l_channel_equalized = clahe.apply(l_channel)
    
    # Merge back to RGB if needed
    if len(img_np.shape) == 3:
        lab_equalized = cv2.merge([l_channel_equalized, a_channel, b_channel])
        return cv2.cvtColor(lab_equalized, cv2.COLOR_LAB2RGB)
    else:
        return l_channel_equalized

