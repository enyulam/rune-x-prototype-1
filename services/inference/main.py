"""
FastAPI inference service for Chinese handwriting OCR with dictionary-based translation.
- Uses EasyOCR for text extraction
- Uses RuleBasedTranslator for dictionary-based meaning lookup and translation
Run with:
  uvicorn services.inference.main:app --host 0.0.0.0 --port 8001
"""

import io
import logging
from typing import List, Optional, Tuple

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image, ImageEnhance
import numpy as np
import easyocr

from translator import get_translator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Rune-X Handwriting OCR")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration constants
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_IMAGE_DIMENSION = 4000  # Max width or height
MIN_IMAGE_DIMENSION = 50  # Min width or height
OCR_TIMEOUT = 30  # seconds
SUPPORTED_FORMATS = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp'}


class Glyph(BaseModel):
    symbol: str
    bbox: Optional[List[float]] = None  # [x, y, w, h]
    confidence: float
    meaning: Optional[str] = None


class InferenceResponse(BaseModel):
    text: str
    translation: str
    confidence: float
    glyphs: List[Glyph]
    unmapped: Optional[List[str]] = None
    coverage: Optional[float] = None
    dictionary_version: Optional[str] = None


def _load_easyocr() -> Optional[easyocr.Reader]:
    """
    Initialize the EasyOCR Reader for Chinese handwriting.

    Returns:
        easyocr.Reader instance if successful, None otherwise.
    """
    try:
        logger.info("Attempting to initialize EasyOCR (langs=['ch_sim', 'en'])...")
        # Use simplified Chinese with English for better coverage
        # Adding English helps with mixed content and sometimes improves detection
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
        logger.info("EasyOCR initialized successfully with ch_sim and en")
        return reader
    except Exception as e:
        logger.error("EasyOCR initialization failed: %s", e)
        logger.error("Error type: %s", type(e).__name__)
        import traceback
        logger.debug(traceback.format_exc())
        # Fallback: try with just ch_sim
        try:
            logger.info("Fallback: Trying EasyOCR with ch_sim only...")
            reader = easyocr.Reader(['ch_sim'], gpu=False)
            logger.info("EasyOCR initialized successfully with ch_sim only")
            return reader
        except Exception as e2:
            logger.error("Fallback initialization also failed: %s", e2)
            return None


def _preprocess_image(image_bytes: bytes) -> Tuple[np.ndarray, Image.Image]:
    """
    Preprocess image for better OCR results.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        Tuple of (numpy array for OCR, PIL Image for metadata)
        
    Raises:
        HTTPException: If image is invalid or cannot be processed
    """
    try:
        # Load image with PIL for validation and preprocessing
        image = Image.open(io.BytesIO(image_bytes))
        
        # Validate image format
        if image.format not in ['JPEG', 'PNG', 'WEBP']:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image format: {image.format}. Please use JPG, PNG, or WebP."
            )
        
        # Check image dimensions
        width, height = image.size
        if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
            raise HTTPException(
                status_code=400,
                detail=f"Image too small: {width}x{height}. Minimum size: {MIN_IMAGE_DIMENSION}x{MIN_IMAGE_DIMENSION}"
            )
        
        if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
            logger.info("Large image detected (%dx%d), resizing...", width, height)
            # Maintain aspect ratio
            if width > height:
                new_width = MAX_IMAGE_DIMENSION
                new_height = int(height * (MAX_IMAGE_DIMENSION / width))
            else:
                new_height = MAX_IMAGE_DIMENSION
                new_width = int(width * (MAX_IMAGE_DIMENSION / height))
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info("Resized to %dx%d", new_width, new_height)
        
        # Convert to RGB if needed (OCR engines expect RGB)
        if image.mode != 'RGB':
            logger.info("Converting image from %s to RGB", image.mode)
            image = image.convert('RGB')
        
        # Enhance small images for better OCR (especially single characters)
        # If image is relatively small, upscale it to improve OCR accuracy
        if width < 300 or height < 300:  # Increased minimum from 200 to 300
            logger.info("Small image detected (%dx%d), upscaling for better OCR...", width, height)
            # Upscale to at least 300px on the smaller dimension while maintaining aspect ratio
            scale_factor = max(300 / width, 300 / height)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info("Upscaled to %dx%d", new_width, new_height)
        
        # Enhance contrast for better OCR (especially helpful for single characters)
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.3)  # Increased contrast enhancement from 1.2 to 1.3
        enhancer_sharp = ImageEnhance.Sharpness(image)
        image = enhancer_sharp.enhance(1.2)  # Increased sharpening from 1.1 to 1.2
        
        # Add padding around the image to help OCR detect edge characters
        # This is especially helpful for single characters
        padding = 50  # Increased padding from 30 to 50 for better detection
        # Use black padding for white-on-black images, white for black-on-white
        # Check if image is mostly dark (white text on black background)
        img_array_check = np.array(image)
        avg_brightness = img_array_check.mean()
        padding_color = 'black' if avg_brightness < 128 else 'white'
        padded_image = Image.new('RGB', (image.width + 2*padding, image.height + 2*padding), color=padding_color)
        padded_image.paste(image, (padding, padding))
        image = padded_image
        logger.info("Added %dpx padding with %s background", padding, padding_color)
        
        # Convert PIL Image to numpy array for EasyOCR
        img_array = np.array(image)
        
        # Ensure array is in correct format for EasyOCR (uint8, 0-255 range)
        if img_array.dtype != np.uint8:
            img_array = img_array.astype(np.uint8)
        if img_array.max() > 255 or img_array.min() < 0:
            img_array = np.clip(img_array, 0, 255).astype(np.uint8)
        
        return img_array, image
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Image preprocessing failed: %s", e)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image file: {str(e)}. Please ensure the file is a valid image."
        ) from e


def _extract_ocr_results(ocr_result: List) -> Tuple[List[Glyph], str]:
    """
    Extract glyphs and text from EasyOCR results.

    Args:
        ocr_result: Raw EasyOCR result (list of [bbox, text, confidence])
        
    Returns:
        Tuple of (list of Glyph objects, full text string)
    """
    glyphs: List[Glyph] = []
    full_text_parts: List[str] = []
    
    if not ocr_result:
        return glyphs, ""

    try:
        for det in ocr_result:
            # EasyOCR format: [bbox, text, confidence]
            if not det or len(det) < 3:
                continue

            try:
                box, txt, conf = det

                # Skip empty text
                if not txt or not str(txt).strip():
                    continue

                # Extract bounding box coordinates [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                if box and len(box) >= 4:
                    x_coords = [p[0] for p in box]
                    y_coords = [p[1] for p in box]
                    x = float(min(x_coords))
                    y = float(min(y_coords))
                    w = float(max(x_coords) - min(x_coords))
                    h = float(max(y_coords) - min(y_coords))

                    confidence = float(conf)
                    if confidence > 1.0:
                        confidence = confidence / 100.0
                    confidence = max(0.0, min(1.0, confidence))

                    glyphs.append(
                        Glyph(
                            symbol=str(txt).strip(),
                            bbox=[x, y, w, h],
                            confidence=confidence,
                            meaning=None,
                        )
                    )
                else:
                    # No bounding box, but still add text
                    glyphs.append(
                        Glyph(
                            symbol=str(txt).strip(),
                            bbox=None,
                            confidence=float(conf) if isinstance(conf, (int, float)) else 0.5,
                            meaning=None,
                        )
                    )

                full_text_parts.append(str(txt).strip())

            except Exception as e:
                logger.warning("Error processing OCR detection: %s", e)
                continue

        full_text = "".join(full_text_parts)
        return glyphs, full_text

    except Exception as e:
        logger.error("Error extracting OCR results: %s", e)
        return glyphs, "".join(full_text_parts)


# Initialize OCR and translator
ocr = _load_easyocr()
translator = get_translator()

if ocr is None:
    logger.warning("EasyOCR not available. OCR functionality will be limited.")
    logger.warning("Install with: pip install easyocr torch torchvision")
else:
    logger.info("OCR service ready")


@app.get("/health")
def health():
    """Health check endpoint with detailed status information."""
    stats = translator.get_statistics()
    
    ocr_status = {
        "available": bool(ocr),
        "status": "ready" if ocr else "not_installed"
    }
    
    if not ocr:
        ocr_status["message"] = "EasyOCR not available. Install with: pip install easyocr torch torchvision"
    
    return {
        "status": "ok",
        "paddle": ocr_status,  # kept key name for backward compatibility
        "dictionary": {
            "entries": stats["total_entries"],
            "entries_with_alts": stats["entries_with_alts"],
            "entries_with_notes": stats["entries_with_notes"],
            "version": stats["version"]
        },
        "limits": {
            "max_image_size_mb": MAX_IMAGE_SIZE / (1024 * 1024),
            "max_dimension": MAX_IMAGE_DIMENSION,
            "min_dimension": MIN_IMAGE_DIMENSION,
            "supported_formats": list(SUPPORTED_FORMATS)
        }
    }


@app.post("/process-image", response_model=InferenceResponse)
async def process_image(file: UploadFile = File(...)):
    """
    Process uploaded image for OCR and translation.
    
    Args:
        file: Uploaded image file
        
    Returns:
        InferenceResponse with extracted text, translation, and glyphs
        
    Raises:
        HTTPException: For various error conditions (invalid image, OCR failure, etc.)
    """
    # Validate file type
    # Note: Some clients (including our Next.js proxy) may send images as application/octet-stream.
    # We allow that through and rely on PIL-based validation in _preprocess_image.
    if file.content_type not in SUPPORTED_FORMATS and file.content_type != "application/octet-stream":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Supported formats: image/jpg, image/png, image/jpeg, image/webp"
        )
    
    # Read and validate file size
    content = await file.read()
    file_size = len(content)
    
    if file_size > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {file_size / (1024 * 1024):.2f}MB. Maximum size: {MAX_IMAGE_SIZE / (1024 * 1024)}MB"
        )
    
    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file uploaded"
        )
    
    logger.info("Processing image: %s, size: %.2fKB", file.filename, file_size / 1024)
    
    # Check if OCR is available
    if ocr is None:
        logger.warning("EasyOCR not available, returning error")
        raise HTTPException(
            status_code=503,
            detail="OCR service not available. EasyOCR is not installed or failed to initialize. "
                   "Please install with: pip install easyocr torch torchvision"
        )
    
    # Preprocess image and keep original for fallback
    original_image = None
    original_array = None
    try:
        # Load original image first (before preprocessing)
        original_image = Image.open(io.BytesIO(content))
        if original_image.mode != 'RGB':
            original_image = original_image.convert('RGB')
        original_array = np.array(original_image)
        # Ensure original array is in correct format for EasyOCR
        if original_array.dtype != np.uint8:
            original_array = original_array.astype(np.uint8)
        if original_array.max() > 255 or original_array.min() < 0:
            original_array = np.clip(original_array, 0, 255).astype(np.uint8)
        logger.info("Original image: %dx%d, mode: %s", original_image.size[0], original_image.size[1], original_image.mode)
        
        # Now preprocess
        img_array, pil_image = _preprocess_image(content)
        logger.info("Image preprocessed: %dx%d, mode: %s", pil_image.size[0], pil_image.size[1], pil_image.mode)
        logger.info("Preprocessed image array shape: %s, min: %.2f, max: %.2f", img_array.shape, img_array.min(), img_array.max())
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Image preprocessing error: %s", e)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to process image: {str(e)}"
        ) from e
    
    # Perform OCR with EasyOCR - try multiple strategies
    result = None
    try:
        logger.info("Starting OCR with EasyOCR...")
        logger.info("Image shape: %s, dtype: %s", img_array.shape, img_array.dtype)
        
        # Strategy 1: Try with preprocessed image and relaxed parameters
        logger.info("Attempt 1: Preprocessed image with relaxed parameters")
        result = ocr.readtext(
            img_array, 
            detail=1,
            width_ths=0.2,
            height_ths=0.2,
            paragraph=False,
            allowlist=None
        )
        logger.info("Attempt 1 completed with %d detections", len(result) if result else 0)
        
        # Strategy 1b: If preprocessed image failed and it's vertical, try rotating preprocessed image
        if (not result or result == [None] or len(result) == 0) and pil_image is not None:
            img_height, img_width = pil_image.size[1], pil_image.size[0]
            if img_height > img_width * 1.2:
                logger.warning("Attempt 1 failed, trying rotated preprocessed image...")
                try:
                    rotated_preprocessed = pil_image.rotate(-90, expand=True)
                    rotated_prep_array = np.array(rotated_preprocessed)
                    if rotated_prep_array.dtype != np.uint8:
                        rotated_prep_array = rotated_prep_array.astype(np.uint8)
                    result = ocr.readtext(rotated_prep_array, detail=1, width_ths=0.2, height_ths=0.2, paragraph=False)
                    logger.info("Attempt 1b (rotated preprocessed) completed with %d detections", len(result) if result else 0)
                except Exception as e:
                    logger.warning("Rotated preprocessed attempt failed: %s", e)
        
        # Strategy 2: If no results, try with even more relaxed parameters
        if not result or result == [None] or len(result) == 0:
            logger.warning("Attempt 1 failed, trying with minimal thresholds...")
            result = ocr.readtext(
                img_array,
                detail=1,
                width_ths=0.1,
                height_ths=0.1,
                paragraph=False
            )
            logger.info("Attempt 2 completed with %d detections", len(result) if result else 0)
        
        # Strategy 3: Try resizing very large images to more manageable size (EasyOCR may struggle with very large images)
        if (not result or result == [None] or len(result) == 0) and original_image is not None:
            img_height, img_width = original_image.size[1], original_image.size[0]
            # If image is very large (>1500px on any side), resize it
            if img_width > 1500 or img_height > 1500:
                logger.warning("Attempt 2 failed, image is very large (%dx%d), trying resized version...", img_width, img_height)
                try:
                    # Resize to max 1200px on the larger dimension while maintaining aspect ratio
                    max_dim = 1200
                    if img_width > img_height:
                        new_width = max_dim
                        new_height = int(img_height * (max_dim / img_width))
                    else:
                        new_height = max_dim
                        new_width = int(img_width * (max_dim / img_height))
                    resized_image = original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    resized_array = np.array(resized_image)
                    if resized_array.dtype != np.uint8:
                        resized_array = resized_array.astype(np.uint8)
                    result = ocr.readtext(resized_array, detail=1, width_ths=0.2, height_ths=0.2, paragraph=False)
                    logger.info("Attempt 3a (resized) completed with %d detections", len(result) if result else 0)
                except Exception as e:
                    logger.warning("Resize attempt failed: %s", e)
        
        # Strategy 3b: Try rotating vertical image to horizontal (EasyOCR works much better with horizontal text)
        if (not result or result == [None] or len(result) == 0) and original_image is not None:
            img_height, img_width = original_image.size[1], original_image.size[0]
            if img_height > img_width * 1.2:  # Image is significantly taller than wide (vertical)
                logger.warning("Attempt 3a failed, image is vertical (%dx%d), trying rotated to horizontal...", img_width, img_height)
                try:
                    # Rotate 90 degrees clockwise to make it horizontal
                    rotated_image = original_image.rotate(-90, expand=True)
                    rotated_array = np.array(rotated_image)
                    if rotated_array.dtype != np.uint8:
                        rotated_array = rotated_array.astype(np.uint8)
                    result = ocr.readtext(rotated_array, detail=1, width_ths=0.2, height_ths=0.2, paragraph=False)
                    logger.info("Attempt 3b (rotated horizontal) completed with %d detections", len(result) if result else 0)
                except Exception as e:
                    logger.warning("Rotation attempt failed: %s", e)
        
        # Strategy 4: Try with original image (no preprocessing) - sometimes preprocessing hurts
        if (not result or result == [None] or len(result) == 0) and original_image is not None:
            logger.warning("Attempt 3 failed, trying with original image (no preprocessing)...")
            result = ocr.readtext(
                original_array,
                detail=1,
                width_ths=0.2,
                height_ths=0.2,
                paragraph=False
            )
            logger.info("Attempt 4 (original image) completed with %d detections", len(result) if result else 0)
        
        # Strategy 5: Try inverted image (white text on black -> black text on white)
        if (not result or result == [None] or len(result) == 0) and original_image is not None:
            logger.warning("Attempt 4 failed, trying inverted image (white->black, black->white)...")
            try:
                # Invert colors: white text on black becomes black text on white
                inverted_image = Image.eval(original_image, lambda x: 255 - x)
                inverted_array = np.array(inverted_image)
                result = ocr.readtext(
                    inverted_array,
                    detail=1,
                    width_ths=0.2,
                    height_ths=0.2,
                    paragraph=False
                )
                logger.info("Attempt 5 (inverted) completed with %d detections", len(result) if result else 0)
            except Exception as e:
                logger.warning("Image inversion failed: %s", e)
        
        # Strategy 6: Try inverted + rotated (for vertical white-on-black text)
        if (not result or result == [None] or len(result) == 0) and original_image is not None:
            img_height, img_width = original_image.size[1], original_image.size[0]
            if img_height > img_width * 1.2:
                logger.warning("Attempt 5 failed, trying inverted + rotated image...")
                try:
                    inverted_image = Image.eval(original_image, lambda x: 255 - x)
                    rotated_inverted = inverted_image.rotate(-90, expand=True)
                    rotated_inv_array = np.array(rotated_inverted)
                    if rotated_inv_array.dtype != np.uint8:
                        rotated_inv_array = rotated_inv_array.astype(np.uint8)
                    result = ocr.readtext(rotated_inv_array, detail=1, width_ths=0.2, height_ths=0.2)
                    logger.info("Attempt 6 (inverted rotated) completed with %d detections", len(result) if result else 0)
                except Exception as e:
                    logger.warning("Inverted rotation attempt failed: %s", e)
        
        # Strategy 7: Last resort - original image with minimal parameters
        if (not result or result == [None] or len(result) == 0) and original_image is not None:
            logger.warning("Attempt 6 failed, trying original image with minimal parameters...")
            result = ocr.readtext(original_array, detail=1)
            logger.info("Attempt 7 (minimal) completed with %d detections", len(result) if result else 0)
        
        # Strategy 8: Try grayscale + thresholding for better contrast
        if (not result or result == [None] or len(result) == 0) and original_image is not None:
            logger.warning("Attempt 7 failed, trying grayscale with thresholding...")
            try:
                import cv2
                gray = cv2.cvtColor(original_array, cv2.COLOR_RGB2GRAY)
                # Apply adaptive thresholding
                _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                # Convert back to RGB for EasyOCR
                thresh_rgb = cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)
                result = ocr.readtext(thresh_rgb, detail=1, width_ths=0.2, height_ths=0.2)
                logger.info("Attempt 7 (thresholded) completed with %d detections", len(result) if result else 0)
            except Exception as e:
                logger.warning("Thresholding attempt failed: %s", e)
        
        # Strategy 8: Try inverted + rotated image
        if (not result or result == [None] or len(result) == 0) and original_image is not None:
            img_height, img_width = original_image.size[1], original_image.size[0]
            if img_height > img_width * 1.2:
                logger.warning("Attempt 7 failed, trying inverted + rotated image...")
                try:
                    inverted_image = Image.eval(original_image, lambda x: 255 - x)
                    rotated_inverted = inverted_image.rotate(-90, expand=True)
                    rotated_inv_array = np.array(rotated_inverted)
                    if rotated_inv_array.dtype != np.uint8:
                        rotated_inv_array = rotated_inv_array.astype(np.uint8)
                    result = ocr.readtext(rotated_inv_array, detail=1, width_ths=0.2, height_ths=0.2)
                    logger.info("Attempt 8 (inverted rotated) completed with %d detections", len(result) if result else 0)
                except Exception as e:
                    logger.warning("Inverted rotation attempt failed: %s", e)
        
        # Strategy 9: Try inverted image with minimal parameters
        if (not result or result == [None] or len(result) == 0) and original_image is not None:
            logger.warning("Attempt 8 failed, trying inverted image with minimal parameters...")
            try:
                inverted_image = Image.eval(original_image, lambda x: 255 - x)
                inverted_array = np.array(inverted_image)
                result = ocr.readtext(inverted_array, detail=1)
                logger.info("Attempt 9 (inverted minimal) completed with %d detections", len(result) if result else 0)
            except Exception as e:
                logger.warning("Final inversion attempt failed: %s", e)
        
        # Strategy 10: Try with aggressive contrast enhancement and edge detection
        if (not result or result == [None] or len(result) == 0) and original_image is not None:
            logger.warning("Attempt 9 failed, trying aggressive contrast enhancement...")
            try:
                import cv2
                # Convert to grayscale
                gray = cv2.cvtColor(original_array, cv2.COLOR_RGB2GRAY)
                # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
                enhanced = clahe.apply(gray)
                # Convert back to RGB
                enhanced_rgb = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
                result = ocr.readtext(enhanced_rgb, detail=1, width_ths=0.1, height_ths=0.1, 
                                     text_threshold=0.3, link_threshold=0.3)
                logger.info("Attempt 10 (CLAHE enhanced) completed with %d detections", len(result) if result else 0)
            except Exception as e:
                logger.warning("CLAHE enhancement attempt failed: %s", e)
        
        # Strategy 11: Try with morphological operations to enhance character shapes
        if (not result or result == [None] or len(result) == 0) and original_image is not None:
            logger.warning("Attempt 10 failed, trying morphological operations...")
            try:
                import cv2
                gray = cv2.cvtColor(original_array, cv2.COLOR_RGB2GRAY)
                # Invert if it's white-on-black
                avg_brightness = gray.mean()
                if avg_brightness < 128:
                    gray = 255 - gray
                # Apply morphological closing to connect character parts
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                morphed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
                morphed_rgb = cv2.cvtColor(morphed, cv2.COLOR_GRAY2RGB)
                result = ocr.readtext(morphed_rgb, detail=1, width_ths=0.1, height_ths=0.1,
                                     text_threshold=0.2, link_threshold=0.2)
                logger.info("Attempt 11 (morphological) completed with %d detections", len(result) if result else 0)
            except Exception as e:
                logger.warning("Morphological operations attempt failed: %s", e)
        
        # Strategy 12: Try upscaling small characters (if image is large but characters might be small)
        if (not result or result == [None] or len(result) == 0) and original_image is not None:
            logger.warning("Attempt 11 failed, trying upscaled version...")
            try:
                # Upscale by 2x to make characters larger
                upscaled = original_image.resize(
                    (original_image.width * 2, original_image.height * 2),
                    Image.Resampling.LANCZOS
                )
                upscaled_array = np.array(upscaled)
                if upscaled_array.dtype != np.uint8:
                    upscaled_array = upscaled_array.astype(np.uint8)
                result = ocr.readtext(upscaled_array, detail=1, width_ths=0.1, height_ths=0.1,
                                     text_threshold=0.3, link_threshold=0.3, mag_ratio=1.0)
                logger.info("Attempt 12 (upscaled 2x) completed with %d detections", len(result) if result else 0)
            except Exception as e:
                logger.warning("Upscaling attempt failed: %s", e)
        
        # Strategy 13: Try inverted + upscaled
        if (not result or result == [None] or len(result) == 0) and original_image is not None:
            logger.warning("Attempt 12 failed, trying inverted + upscaled...")
            try:
                inverted = Image.eval(original_image, lambda x: 255 - x)
                upscaled_inv = inverted.resize(
                    (inverted.width * 2, inverted.height * 2),
                    Image.Resampling.LANCZOS
                )
                upscaled_inv_array = np.array(upscaled_inv)
                if upscaled_inv_array.dtype != np.uint8:
                    upscaled_inv_array = upscaled_inv_array.astype(np.uint8)
                result = ocr.readtext(upscaled_inv_array, detail=1, width_ths=0.1, height_ths=0.1,
                                     text_threshold=0.3, link_threshold=0.3)
                logger.info("Attempt 13 (inverted upscaled) completed with %d detections", len(result) if result else 0)
            except Exception as e:
                logger.warning("Inverted upscaling attempt failed: %s", e)
        
        # Strategy 14: Try with very low thresholds and different mag_ratio
        if (not result or result == [None] or len(result) == 0) and original_image is not None:
            logger.warning("Attempt 13 failed, trying with very low thresholds and mag_ratio...")
            try:
                result = ocr.readtext(original_array, detail=1, width_ths=0.05, height_ths=0.05,
                                     text_threshold=0.1, link_threshold=0.1, mag_ratio=1.5)
                logger.info("Attempt 14 (ultra-low thresholds) completed with %d detections", len(result) if result else 0)
            except Exception as e:
                logger.warning("Ultra-low threshold attempt failed: %s", e)
        
        if not result or result == [None] or len(result) == 0:
            logger.error("All OCR attempts failed - no text detected")
            logger.error("Preprocessed image: %dx%d, Original image: %dx%d", 
                        pil_image.size[0] if pil_image else 0, pil_image.size[1] if pil_image else 0,
                        original_image.size[0] if original_image else 0, original_image.size[1] if original_image else 0)
            logger.error("This may indicate: 1) Image too small (<100px), 2) Text too stylized, 3) Poor image quality, 4) EasyOCR model limitation")
            raise HTTPException(
                status_code=422,
                detail="No text detected in image after 14 different OCR attempts (including preprocessing, inversion, rotation, upscaling, contrast enhancement, and morphological operations). The image may contain characters that are too stylized or difficult for EasyOCR to recognize. Please try: 1) A higher resolution image (at least 300x300px recommended), 2) Black text on white background, 3) Clearer, more standard characters, 4) Horizontal text layout, 5) Less stylized handwriting."
            )
            
    except HTTPException:
        raise
    except TimeoutError as exc:
        logger.error("OCR operation timed out")
        raise HTTPException(
            status_code=504,
            detail=f"OCR processing timed out after {OCR_TIMEOUT} seconds. Try with a smaller or higher quality image."
        ) from exc
    except Exception as e:
        logger.error("OCR processing failed: %s", e)
        error_msg = str(e)
        
        # Provide more specific error messages
        if "memory" in error_msg.lower() or "out of memory" in error_msg.lower():
            raise HTTPException(
                status_code=500,
                detail="Insufficient memory for OCR processing. Try with a smaller image."
            ) from e
        elif "cuda" in error_msg.lower() or "gpu" in error_msg.lower():
            raise HTTPException(
                status_code=500,
                detail="GPU processing error. Please check GPU configuration or use CPU mode."
            ) from e
        else:
            raise HTTPException(
                status_code=500,
                detail=f"OCR processing failed: {error_msg}"
            ) from e
    
    # Extract OCR results
    try:
        glyphs, full_text = _extract_ocr_results(result)
        
        if not full_text or not full_text.strip():
            logger.warning("No text extracted from OCR results")
            raise HTTPException(
                status_code=422,
                detail="No text could be extracted from the image. Please check image quality and ensure it contains readable text."
            )
        
        logger.info("Extracted %d glyphs, text length: %d", len(glyphs), len(full_text))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error extracting OCR results: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process OCR results: {str(e)}"
        ) from e
    
    # Translate text using dictionary
    try:
        # Convert glyphs to dict format for translator
        glyph_dicts = [
            {
                "symbol": g.symbol,
                "bbox": g.bbox,
                "confidence": g.confidence
            }
            for g in glyphs
        ]
        
        translation_result = translator.translate_text(full_text, glyph_dicts)
        logger.info("Translation completed: %.1f%% coverage", translation_result.get('coverage', 0))
        
    except Exception as e:
        logger.error("Translation failed: %s", e)
        # Continue with empty translation rather than failing completely
        translation_result = {
            "glyphs": glyph_dicts,
            "translation": "",
            "unmapped": [],
            "coverage": 0.0,
            "dictionary_version": "1.0.0"
        }
    
    # Enrich glyphs with meanings from translation
    enriched_glyphs = []
    translation_glyphs = translation_result.get("glyphs", [])
    
    for i, original_glyph in enumerate(glyphs):
        # Try to match with translation result
        if i < len(translation_glyphs):
            enriched_data = translation_glyphs[i]
            enriched_glyphs.append(
                Glyph(
                    symbol=enriched_data.get("symbol", original_glyph.symbol),
                    bbox=enriched_data.get("bbox") or original_glyph.bbox,
                    confidence=enriched_data.get("confidence", original_glyph.confidence),
                    meaning=enriched_data.get("meaning")
                )
            )
        else:
            # No translation data, use original glyph
            enriched_glyphs.append(original_glyph)
    
    # Calculate average confidence
    if enriched_glyphs:
        avg_confidence = sum(g.confidence for g in enriched_glyphs) / len(enriched_glyphs)
    else:
        avg_confidence = 0.0
    
    logger.info("Processing complete: %d glyphs, confidence: %.2f", len(enriched_glyphs), avg_confidence)
    
    return InferenceResponse(
        text=full_text,
        translation=translation_result.get("translation", ""),
        confidence=avg_confidence,
        glyphs=enriched_glyphs,
        unmapped=translation_result.get("unmapped", []),
        coverage=translation_result.get("coverage", 0.0),
        dictionary_version=translation_result.get("dictionary_version")
    )

