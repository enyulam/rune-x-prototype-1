"""
FastAPI inference service for Chinese handwriting OCR with dictionary-based translation.
- Uses hybrid OCR system (EasyOCR + PaddleOCR) for text extraction
- Uses RuleBasedTranslator for dictionary-based meaning lookup and translation
Run with:
  uvicorn services.inference.main:app --host 0.0.0.0 --port 8001
"""

import io
import logging
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

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


# Normalized OCR result structure
@dataclass
class NormalizedOCRResult:
    """Normalized OCR result from any engine."""
    bbox: List[float]  # [x1, y1, x2, y2]
    char: str
    confidence: float
    source: str  # "easyocr" or "paddleocr"


# Fused character candidate structure
@dataclass
class CharacterCandidate:
    """Single character candidate from an OCR engine."""
    char: str
    confidence: float
    source: str


@dataclass
class FusedPosition:
    """Fused character position with multiple candidates."""
    position: int
    bbox: List[float]  # [x1, y1, x2, y2]
    candidates: List[CharacterCandidate]


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
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
        logger.info("EasyOCR initialized successfully with ch_sim and en")
        return reader
    except Exception as e:
        logger.error("EasyOCR initialization failed: %s", e)
        import traceback
        logger.debug(traceback.format_exc())
        try:
            logger.info("Fallback: Trying EasyOCR with ch_sim only...")
            reader = easyocr.Reader(['ch_sim'], gpu=False)
            logger.info("EasyOCR initialized successfully with ch_sim only")
            return reader
        except Exception as e2:
            logger.error("Fallback initialization also failed: %s", e2)
            return None


def _load_paddleocr():
    """
    Initialize PaddleOCR for Chinese text recognition.

    Returns:
        PaddleOCR instance if successful, None otherwise.
    """
    try:
        logger.info("Attempting to initialize PaddleOCR...")
        from paddleocr import PaddleOCR
        # Initialize with Chinese and English support, CPU mode
        # Note: use_gpu parameter may not be available in all versions
        try:
            ocr = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=False)
        except (TypeError, ValueError, Exception) as e:
            # Fallback: try without use_gpu parameter (some versions don't support it)
            logger.info("Trying PaddleOCR initialization without use_gpu parameter...")
            ocr = PaddleOCR(use_angle_cls=True, lang='ch')
        logger.info("PaddleOCR initialized successfully")
        return ocr
    except Exception as e:
        logger.error("PaddleOCR initialization failed: %s", e)
        import traceback
        logger.debug(traceback.format_exc())
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
            if width > height:
                new_width = MAX_IMAGE_DIMENSION
                new_height = int(height * (MAX_IMAGE_DIMENSION / width))
            else:
                new_height = MAX_IMAGE_DIMENSION
                new_width = int(width * (MAX_IMAGE_DIMENSION / height))
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info("Resized to %dx%d", new_width, new_height)
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            logger.info("Converting image from %s to RGB", image.mode)
            image = image.convert('RGB')
        
        # Enhance small images for better OCR
        if width < 300 or height < 300:
            logger.info("Small image detected (%dx%d), upscaling for better OCR...", width, height)
            scale_factor = max(300 / width, 300 / height)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info("Upscaled to %dx%d", new_width, new_height)
        
        # Enhance contrast and sharpness
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.3)
        enhancer_sharp = ImageEnhance.Sharpness(image)
        image = enhancer_sharp.enhance(1.2)
        
        # Add padding around the image
        padding = 50
        img_array_check = np.array(image)
        avg_brightness = img_array_check.mean()
        padding_color = 'black' if avg_brightness < 128 else 'white'
        padded_image = Image.new('RGB', (image.width + 2*padding, image.height + 2*padding), color=padding_color)
        padded_image.paste(image, (padding, padding))
        image = padded_image
        logger.info("Added %dpx padding with %s background", padding, padding_color)
        
        # Convert PIL Image to numpy array
        img_array = np.array(image)
        
        # Ensure array is in correct format
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


def run_easyocr(ocr_reader: easyocr.Reader, img_array: np.ndarray) -> List[NormalizedOCRResult]:
    """
    Run EasyOCR on preprocessed image and normalize results.
    
    Args:
        ocr_reader: Initialized EasyOCR Reader
        img_array: Preprocessed image as numpy array
        
    Returns:
        List of normalized OCR results
    """
    try:
        # EasyOCR format: [[bbox, text, confidence], ...]
        # bbox format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        results = ocr_reader.readtext(
            img_array,
            detail=1,
            width_ths=0.2,
            height_ths=0.2,
            paragraph=False
        )
        
        normalized = []
        for det in results:
            if not det or len(det) < 3:
                continue
                
            box, txt, conf = det
            
            # Skip empty text
            if not txt or not str(txt).strip():
                continue
            
            # Extract bounding box coordinates
            if box and len(box) >= 4:
                x_coords = [p[0] for p in box]
                y_coords = [p[1] for p in box]
                x1 = float(min(x_coords))
                y1 = float(min(y_coords))
                x2 = float(max(x_coords))
                y2 = float(max(y_coords))
                
                # Normalize confidence to [0, 1]
                confidence = float(conf)
                if confidence > 1.0:
                    confidence = confidence / 100.0
                confidence = max(0.0, min(1.0, confidence))
                
                # Process each character in the detected text
                text_str = str(txt).strip()
                # For multi-character detections, split and create separate entries
                # We'll use the same bbox for all characters (will be refined in alignment)
                for char in text_str:
                    normalized.append(
                        NormalizedOCRResult(
                            bbox=[x1, y1, x2, y2],
                            char=char,
                            confidence=confidence,
                            source="easyocr"
                        )
                    )
        
        logger.info("EasyOCR detected %d character(s)", len(normalized))
        return normalized
        
    except Exception as e:
        logger.error("EasyOCR processing failed: %s", e)
        return []


def run_paddleocr(ocr_reader, img_array: np.ndarray) -> List[NormalizedOCRResult]:
    """
    Run PaddleOCR on preprocessed image and normalize results.
    
    Args:
        ocr_reader: Initialized PaddleOCR instance
        img_array: Preprocessed image as numpy array
        
    Returns:
        List of normalized OCR results
    """
    try:
        # PaddleOCR format: [[bbox, (text, confidence)], ...]
        # bbox format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        # Note: PaddleOCR 3.x doesn't support cls parameter in ocr() method
        # The cls parameter is only used during initialization (use_angle_cls)
        results = ocr_reader.ocr(img_array)
        
        normalized = []
        if not results or not results[0]:
            return normalized
        
        for line in results[0]:
            if not line or len(line) < 2:
                continue
            
            # PaddleOCR result format varies by version:
            # Version 2.x: [[bbox, (text, confidence)], ...]
            # Version 3.x: [[bbox, text, confidence], ...] or different structure
            try:
                # Try version 2.x format: [bbox, (text, confidence)]
                if len(line) == 2 and isinstance(line[1], (tuple, list)) and len(line[1]) == 2:
                    box, (txt, conf) = line
                # Try version 3.x format: [bbox, text, confidence]
                elif len(line) == 3:
                    box, txt, conf = line
                else:
                    # Fallback: try to extract from any structure
                    box = line[0]
                    if len(line) >= 3:
                        txt, conf = line[1], line[2]
                    elif len(line) == 2:
                        if isinstance(line[1], (tuple, list)) and len(line[1]) == 2:
                            txt, conf = line[1]
                        else:
                            logger.warning(f"Unexpected PaddleOCR line format: {line}")
                            continue
                    else:
                        logger.warning(f"Unexpected PaddleOCR line format: {line}")
                        continue
            except (ValueError, TypeError, IndexError) as e:
                logger.warning(f"Error parsing PaddleOCR line {line}: {e}")
                continue
            
            # Skip empty text
            if not txt or not str(txt).strip():
                continue
            
            # Extract bounding box coordinates
            if box and len(box) >= 4:
                x_coords = [p[0] for p in box]
                y_coords = [p[1] for p in box]
                x1 = float(min(x_coords))
                y1 = float(min(y_coords))
                x2 = float(max(x_coords))
                y2 = float(max(y_coords))
                
                # Normalize confidence to [0, 1]
                confidence = float(conf)
                confidence = max(0.0, min(1.0, confidence))
                
                # Process each character in the detected text
                text_str = str(txt).strip()
                for char in text_str:
                    normalized.append(
                        NormalizedOCRResult(
                            bbox=[x1, y1, x2, y2],
                            char=char,
                            confidence=confidence,
                            source="paddleocr"
                        )
                    )
        
        logger.info("PaddleOCR detected %d character(s)", len(normalized))
        return normalized
        
    except Exception as e:
        logger.error("PaddleOCR processing failed: %s", e)
        return []


def calculate_iou(bbox1: List[float], bbox2: List[float]) -> float:
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.
    
    Args:
        bbox1: [x1, y1, x2, y2]
        bbox2: [x1, y1, x2, y2]
        
    Returns:
        IoU value between 0 and 1
    """
    x1_1, y1_1, x2_1, y2_1 = bbox1
    x1_2, y1_2, x2_2, y2_2 = bbox2
    
    # Calculate intersection
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)
    
    if x2_i <= x1_i or y2_i <= y1_i:
        return 0.0
    
    intersection = (x2_i - x1_i) * (y2_i - y1_i)
    
    # Calculate union
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection
    
    if union == 0:
        return 0.0
    
    return intersection / union


def align_ocr_outputs(
    easyocr_results: List[NormalizedOCRResult],
    paddleocr_results: List[NormalizedOCRResult],
    iou_threshold: float = 0.3
) -> List[FusedPosition]:
    """
    Align OCR results from both engines using IoU-based matching.
    Handles character-level alignment preserving all candidates from both engines.
    
    Args:
        easyocr_results: Normalized EasyOCR results
        paddleocr_results: Normalized PaddleOCR results
        iou_threshold: Minimum IoU for considering boxes as aligned
        
    Returns:
        List of fused positions with aligned candidates
    """
    fused_positions = []
    used_easyocr = set()
    used_paddleocr = set()
    
    # Sort both result sets by reading order (top-to-bottom, left-to-right)
    # Primary sort by y1 (top), secondary by x1 (left)
    easyocr_sorted = sorted(enumerate(easyocr_results), 
                            key=lambda x: (x[1].bbox[1], x[1].bbox[0]))
    paddleocr_sorted = sorted(enumerate(paddleocr_results),
                              key=lambda x: (x[1].bbox[1], x[1].bbox[0]))
    
    # Create position lists for sequential matching
    easyocr_positions = list(easyocr_sorted)
    paddleocr_positions = list(paddleocr_sorted)
    
    # Match results using greedy IoU-based alignment
    position_idx = 0
    easyocr_ptr = 0
    paddleocr_ptr = 0
    
    while easyocr_ptr < len(easyocr_positions) or paddleocr_ptr < len(paddleocr_positions):
        # Get current candidates
        easyocr_candidate = None
        paddleocr_candidate = None
        
        if easyocr_ptr < len(easyocr_positions):
            easyocr_idx, easyocr_result = easyocr_positions[easyocr_ptr]
            if easyocr_idx not in used_easyocr:
                easyocr_candidate = (easyocr_idx, easyocr_result)
        
        if paddleocr_ptr < len(paddleocr_positions):
            paddleocr_idx, paddleocr_result = paddleocr_positions[paddleocr_ptr]
            if paddleocr_idx not in used_paddleocr:
                paddleocr_candidate = (paddleocr_idx, paddleocr_result)
        
        # If both candidates exist, check if they align
        if easyocr_candidate and paddleocr_candidate:
            iou = calculate_iou(easyocr_candidate[1].bbox, paddleocr_candidate[1].bbox)
            
            if iou >= iou_threshold:
                # Aligned - create fused position with both candidates
                candidates = [
                    CharacterCandidate(
                        char=easyocr_candidate[1].char,
                        confidence=easyocr_candidate[1].confidence,
                        source="easyocr"
                    ),
                    CharacterCandidate(
                        char=paddleocr_candidate[1].char,
                        confidence=paddleocr_candidate[1].confidence,
                        source="paddleocr"
                    )
                ]
                
                # Average bbox
                bbox1 = easyocr_candidate[1].bbox
                bbox2 = paddleocr_candidate[1].bbox
                avg_bbox = [
                    (bbox1[0] + bbox2[0]) / 2,
                    (bbox1[1] + bbox2[1]) / 2,
                    (bbox1[2] + bbox2[2]) / 2,
                    (bbox1[3] + bbox2[3]) / 2
                ]
                
                fused_positions.append(
                    FusedPosition(
                        position=position_idx,
                        bbox=avg_bbox,
                        candidates=candidates
                    )
                )
                
                used_easyocr.add(easyocr_candidate[0])
                used_paddleocr.add(paddleocr_candidate[0])
                easyocr_ptr += 1
                paddleocr_ptr += 1
                position_idx += 1
                continue
        
        # Not aligned - add the one that comes first in reading order
        if easyocr_candidate and paddleocr_candidate:
            # Compare reading order
            easy_y, easy_x = easyocr_candidate[1].bbox[1], easyocr_candidate[1].bbox[0]
            paddle_y, paddle_x = paddleocr_candidate[1].bbox[1], paddleocr_candidate[1].bbox[0]
            
            if easy_y < paddle_y or (easy_y == paddle_y and easy_x < paddle_x):
                # EasyOCR comes first
                fused_positions.append(
                    FusedPosition(
                        position=position_idx,
                        bbox=easyocr_candidate[1].bbox,
                        candidates=[
                            CharacterCandidate(
                                char=easyocr_candidate[1].char,
                                confidence=easyocr_candidate[1].confidence,
                                source="easyocr"
                            )
                        ]
                    )
                )
                used_easyocr.add(easyocr_candidate[0])
                easyocr_ptr += 1
            else:
                # PaddleOCR comes first
                fused_positions.append(
                    FusedPosition(
                        position=position_idx,
                        bbox=paddleocr_candidate[1].bbox,
                        candidates=[
                            CharacterCandidate(
                                char=paddleocr_candidate[1].char,
                                confidence=paddleocr_candidate[1].confidence,
                                source="paddleocr"
                            )
                        ]
                    )
                )
                used_paddleocr.add(paddleocr_candidate[0])
                paddleocr_ptr += 1
            position_idx += 1
        elif easyocr_candidate:
            # Only EasyOCR candidate available
            fused_positions.append(
                FusedPosition(
                    position=position_idx,
                    bbox=easyocr_candidate[1].bbox,
                    candidates=[
                        CharacterCandidate(
                            char=easyocr_candidate[1].char,
                            confidence=easyocr_candidate[1].confidence,
                            source="easyocr"
                        )
                    ]
                )
            )
            used_easyocr.add(easyocr_candidate[0])
            easyocr_ptr += 1
            position_idx += 1
        elif paddleocr_candidate:
            # Only PaddleOCR candidate available
            fused_positions.append(
                FusedPosition(
                    position=position_idx,
                    bbox=paddleocr_candidate[1].bbox,
                    candidates=[
                        CharacterCandidate(
                            char=paddleocr_candidate[1].char,
                            confidence=paddleocr_candidate[1].confidence,
                            source="paddleocr"
                        )
                    ]
                )
            )
            used_paddleocr.add(paddleocr_candidate[0])
            paddleocr_ptr += 1
            position_idx += 1
        else:
            # Both are used, advance both pointers
            easyocr_ptr += 1
            paddleocr_ptr += 1
    
    logger.info("Aligned %d positions from %d EasyOCR + %d PaddleOCR results",
                len(fused_positions), len(easyocr_results), len(paddleocr_results))
    
    return fused_positions


def fuse_character_candidates(fused_positions: List[FusedPosition]) -> Tuple[List[Glyph], str]:
    """
    Convert fused positions to Glyph objects and full text string.
    For each position, use the highest-confidence candidate as the primary character.
    
    Args:
        fused_positions: List of fused character positions
        
    Returns:
        Tuple of (list of Glyph objects, full text string)
    """
    glyphs = []
    full_text_parts = []
    
    for pos in fused_positions:
        if not pos.candidates:
            continue
        
        # Select highest confidence candidate as primary
        best_candidate = max(pos.candidates, key=lambda c: c.confidence)
        
        # Convert bbox from [x1, y1, x2, y2] to [x, y, w, h] for Glyph
        x1, y1, x2, y2 = pos.bbox
        bbox_glyph = [x1, y1, x2 - x1, y2 - y1]
        
        glyphs.append(
            Glyph(
                symbol=best_candidate.char,
                bbox=bbox_glyph,
                confidence=best_candidate.confidence,
                meaning=None
            )
        )
        full_text_parts.append(best_candidate.char)
    
    full_text = "".join(full_text_parts)
    return glyphs, full_text


# Initialize OCR engines and translator
easyocr_reader = _load_easyocr()
paddleocr_reader = _load_paddleocr()
translator = get_translator()

if easyocr_reader is None:
    logger.warning("EasyOCR not available. OCR functionality will be limited.")
if paddleocr_reader is None:
    logger.warning("PaddleOCR not available. OCR functionality will be limited.")
if easyocr_reader is None and paddleocr_reader is None:
    logger.error("No OCR engines available. Install EasyOCR and/or PaddleOCR.")
else:
    logger.info("OCR service ready (EasyOCR: %s, PaddleOCR: %s)",
                "available" if easyocr_reader else "unavailable",
                "available" if paddleocr_reader else "unavailable")


@app.get("/health")
def health():
    """Health check endpoint with detailed status information."""
    stats = translator.get_statistics()
    
    ocr_status = {
        "easyocr": {
            "available": bool(easyocr_reader),
            "status": "ready" if easyocr_reader else "not_installed"
        },
        "paddleocr": {
            "available": bool(paddleocr_reader),
            "status": "ready" if paddleocr_reader else "not_installed"
        }
    }
    
    if not easyocr_reader:
        ocr_status["easyocr"]["message"] = "EasyOCR not available. Install with: pip install easyocr torch torchvision"
    if not paddleocr_reader:
        ocr_status["paddleocr"]["message"] = "PaddleOCR not available. Install with: pip install paddlepaddle paddleocr"
    
    return {
        "status": "ok",
        "ocr_engines": ocr_status,
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
    Process uploaded image for OCR and translation using hybrid OCR system.
    
    Args:
        file: Uploaded image file
        
    Returns:
        InferenceResponse with extracted text, translation, and glyphs
        
    Raises:
        HTTPException: For various error conditions
    """
    # Validate file type
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
    
    # Check if at least one OCR engine is available
    if easyocr_reader is None and paddleocr_reader is None:
        raise HTTPException(
            status_code=503,
            detail="OCR service not available. Neither EasyOCR nor PaddleOCR is installed or initialized."
        )
    
    # Preprocess image
    try:
        img_array, pil_image = _preprocess_image(content)
        logger.info("Image preprocessed: %dx%d", pil_image.size[0], pil_image.size[1])
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Image preprocessing error: %s", e)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to process image: {str(e)}"
        ) from e
    
    # Run both OCR engines in parallel on the same preprocessed image
    easyocr_results = []
    paddleocr_results = []
    
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {}
            
            if easyocr_reader:
                futures['easyocr'] = executor.submit(run_easyocr, easyocr_reader, img_array)
            if paddleocr_reader:
                futures['paddleocr'] = executor.submit(run_paddleocr, paddleocr_reader, img_array)
            
            # Wait for results
            for engine_name, future in futures.items():
                try:
                    results = future.result(timeout=OCR_TIMEOUT)
                    if engine_name == 'easyocr':
                        easyocr_results = results
                    else:
                        paddleocr_results = results
                except Exception as e:
                    logger.error("%s processing failed: %s", engine_name, e)
        
        # Check if we got any results
        if not easyocr_results and not paddleocr_results:
            raise HTTPException(
                status_code=422,
                detail="No text detected in image by any OCR engine. Please try: 1) A higher resolution image, 2) Black text on white background, 3) Clearer characters."
            )
        
        logger.info("OCR results: EasyOCR=%d chars, PaddleOCR=%d chars",
                    len(easyocr_results), len(paddleocr_results))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("OCR processing failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"OCR processing failed: {str(e)}"
        ) from e
    
    # Align and fuse OCR results
    try:
        fused_positions = align_ocr_outputs(easyocr_results, paddleocr_results)
        
        if not fused_positions:
            raise HTTPException(
                status_code=422,
                detail="No text could be extracted from the image after fusion."
            )
        
        # Convert to Glyph objects and full text
        glyphs, full_text = fuse_character_candidates(fused_positions)
        
        if not full_text or not full_text.strip():
            raise HTTPException(
                status_code=422,
                detail="No text could be extracted from the image."
            )
        
        logger.info("Fused %d positions into %d glyphs, text length: %d",
                    len(fused_positions), len(glyphs), len(full_text))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fusing OCR results: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process OCR results: {str(e)}"
        ) from e
    
    # Translate text using dictionary
    try:
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
