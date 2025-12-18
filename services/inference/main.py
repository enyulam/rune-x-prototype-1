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
from sentence_translator import get_sentence_translator
from qwen_refiner import get_qwen_refiner

# Import new modular preprocessing system
import sys
from pathlib import Path
# Add parent directory to path for preprocessing module
sys.path.insert(0, str(Path(__file__).parent.parent))
from preprocessing.image_preprocessing import preprocess_image

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
    translation: str  # Dictionary-based character-level translation
    sentence_translation: Optional[str] = None  # Neural sentence-level translation (MarianMT)
    refined_translation: Optional[str] = None  # Qwen-refined translation
    qwen_status: Optional[str] = None  # Status: "available", "unavailable", "failed", "skipped"
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


# ============================================================================
# OLD PREPROCESSING FUNCTION (DEPRECATED - Replaced with modular preprocessing)
# ============================================================================
# The old monolithic preprocessing function has been replaced with the new
# modular preprocessing system located in services/preprocessing/
# 
# Old location: main.py lines 151-243 (pre-refactor)
# New location: services/preprocessing/image_preprocessing.py
# 
# The old function performed these steps inline:
# 1. Image loading & format validation (JPEG/PNG/WEBP)
# 2. Dimension validation (MIN_IMAGE_DIMENSION to MAX_IMAGE_DIMENSION)
# 3. Large image resizing (>MAX_IMAGE_DIMENSION)
# 4. RGB conversion
# 5. Small image upscaling (<300px)
# 6. Contrast enhancement (1.3x)
# 7. Sharpness enhancement (1.2x)
# 8. Adaptive padding (50px, brightness-based color)
#
# The new modular system adds:
# - Configurable parameters via config.py and environment variables
# - Optional enhancements (noise reduction, binarization, deskewing, brightness normalization)
# - Comprehensive unit tests (45 tests)
# - Better error handling (fatal vs optional steps)
# - Production-grade logging
# ============================================================================


def _preprocess_image(image_bytes: bytes) -> Tuple[np.ndarray, Image.Image]:
    """
    Preprocess image for better OCR results using modular preprocessing system.
    
    This function now delegates to the new modular preprocessing system
    located in services/preprocessing/image_preprocessing.py
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        Tuple of (numpy array for OCR, PIL Image for metadata)
        
    Raises:
        HTTPException: If image is invalid or cannot be processed
    """
    # Use new modular preprocessing system with all enhancements enabled
    # The preprocessing module handles:
    # - Format validation, dimension checks, resizing
    # - RGB conversion, upscaling, contrast/sharpness enhancement
    # - Adaptive padding
    # - Optional: noise reduction, binarization, deskewing, brightness normalization
    return preprocess_image(
        image_bytes,
        apply_noise_reduction=True,
        apply_binarization=False,  # Disable for now - can cause issues with some images
        apply_deskew=True,
        apply_brightness_norm=True
    )


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


# Initialize OCR engines and translators
easyocr_reader = _load_easyocr()
paddleocr_reader = _load_paddleocr()
translator = get_translator()  # Dictionary-based translator
sentence_translator = get_sentence_translator()  # Neural sentence translator (MarianMT)
qwen_refiner = get_qwen_refiner()  # Qwen LLM refiner

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

if sentence_translator is None:
    logger.warning("Sentence translator not available. Install transformers and torch for neural translation.")
else:
    logger.info("Sentence translator ready (MarianMT)")

if qwen_refiner is None:
    logger.warning("Qwen refiner not available. Install transformers and torch for translation refinement.")
else:
    logger.info("Qwen refiner ready (Qwen2.5-1.5B-Instruct)")


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
    
    translation_status = {
        "marianmt": {
            "available": bool(sentence_translator and sentence_translator.is_available()),
            "status": "ready" if (sentence_translator and sentence_translator.is_available()) else "not_installed"
        },
        "qwen_refiner": {
            "available": bool(qwen_refiner and qwen_refiner.is_available()),
            "status": "ready" if (qwen_refiner and qwen_refiner.is_available()) else "not_installed",
            "model": "Qwen2.5-1.5B-Instruct" if qwen_refiner else None
        }
    }
    
    if not easyocr_reader:
        ocr_status["easyocr"]["message"] = "EasyOCR not available. Install with: pip install easyocr torch torchvision"
    if not paddleocr_reader:
        ocr_status["paddleocr"]["message"] = "PaddleOCR not available. Install with: pip install paddlepaddle paddleocr"
    
    if not sentence_translator or not sentence_translator.is_available():
        translation_status["marianmt"]["message"] = "MarianMT not available. Install with: pip install transformers torch"
    if not qwen_refiner or not qwen_refiner.is_available():
        translation_status["qwen_refiner"]["message"] = "Qwen refiner not available. Install with: pip install transformers torch"
    
    return {
        "status": "ok",
        "ocr_engines": ocr_status,
        "translation_engines": translation_status,
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
    logger.info("=== Received image processing request ===")
    logger.info("File: %s, Content-Type: %s", file.filename, file.content_type)
    
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
    
    # Log the extracted OCR text for debugging
    logger.info("Extracted OCR text (first 200 chars): %s", full_text[:200] if full_text else "Empty")
    logger.info("Extracted OCR text length: %d characters", len(full_text))
    
    # Perform sentence-level neural translation (MarianMT)
    sentence_translation = None
    if sentence_translator and sentence_translator.is_available():
        try:
            logger.info("Calling MarianMT translator with text: %s", full_text[:100] if full_text else "Empty")
            sentence_translation = sentence_translator.translate(full_text)
            logger.info("Sentence translation completed: %s", sentence_translation[:200] if sentence_translation else "None")
        except Exception as e:
            logger.error("Sentence translation failed: %s", e)
            sentence_translation = None
    else:
        logger.debug("Sentence translator not available, skipping neural translation")
    
    # Perform Qwen refinement on MarianMT translation
    refined_translation = None
    qwen_status = None
    
    if sentence_translation and qwen_refiner and qwen_refiner.is_available():
        try:
            logger.info("Starting Qwen refinement of MarianMT translation...")
            refined_translation = qwen_refiner.refine_translation_with_qwen(
                nmt_translation=sentence_translation,
                ocr_text=full_text
            )
            if refined_translation:
                logger.info("Qwen refinement completed: %s", refined_translation[:50])
                qwen_status = "available"
            else:
                logger.warning("Qwen refinement returned None, using MarianMT translation")
                qwen_status = "failed"
        except Exception as e:
            logger.error("Qwen refinement failed: %s", e)
            refined_translation = None
            qwen_status = "failed"
    else:
        if not sentence_translation:
            logger.debug("No MarianMT translation available, skipping Qwen refinement")
            qwen_status = "skipped"
        elif not qwen_refiner or not qwen_refiner.is_available():
            logger.debug("Qwen refiner not available, skipping refinement")
            qwen_status = "unavailable"
    
    return InferenceResponse(
        text=full_text,
        translation=translation_result.get("translation", ""),  # Dictionary-based
        sentence_translation=sentence_translation,  # Neural sentence translation (MarianMT)
        refined_translation=refined_translation,  # Qwen-refined translation
        qwen_status=qwen_status,  # Status: "available", "unavailable", "failed", "skipped"
        confidence=avg_confidence,
        glyphs=enriched_glyphs,
        unmapped=translation_result.get("unmapped", []),
        coverage=translation_result.get("coverage", 0.0),
        dictionary_version=translation_result.get("dictionary_version")
    )
