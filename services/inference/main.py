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
from cc_dictionary import CCDictionary
from cc_translation import CCDictionaryTranslator, DefinitionStrategy
from marian_adapter import get_marian_adapter  # Phase 5: MarianMT adapter layer
from qwen_adapter import (  # Phase 6: Qwen adapter layer
    get_qwen_adapter,
    QwenAdapterInput,
)

# Import OCR fusion module
from ocr_fusion import (
    NormalizedOCRResult,
    CharacterCandidate,
    FusedPosition,
    Glyph,
    calculate_iou,
    align_ocr_outputs,
    fuse_character_candidates
)

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
    dictionary_source: Optional[str] = None  # OCR fusion dictionary source: "CC-CEDICT" or "Translator"
    dictionary_version: Optional[str] = None  # OCR fusion dictionary version
    translation_source: Optional[str] = None  # Translation dictionary source: "CC-CEDICT", "RuleBasedTranslator", or "Error"
    semantic: Optional[Dict[str, Any]] = None  # Phase 5 Step 7: Semantic refinement metadata (MarianMT adapter)
    qwen: Optional[Dict[str, Any]] = None  # Phase 6 Step 7: Qwen refinement metadata (QwenAdapter)


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
    # OPTIMIZED: Minimal preprocessing for handwritten text
    # Testing confirmed: Aggressive preprocessing (noise reduction, deskewing, brightness norm)
    # was corrupting handwritten Chinese characters, causing severe OCR accuracy degradation
    # Current configuration provides best results for handwritten text
    return preprocess_image(
        image_bytes,
        apply_noise_reduction=False,  # Disabled: Corrupts handwriting
        apply_binarization=False,      # Disabled: Can cause issues
        apply_deskew=False,            # Disabled: Corrupts handwriting
        apply_brightness_norm=False    # Disabled: Corrupts handwriting
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


# Initialize OCR engines and translators
easyocr_reader = _load_easyocr()
paddleocr_reader = _load_paddleocr()
translator = get_translator()  # Dictionary-based translator
sentence_translator = get_sentence_translator()  # Neural sentence translator (MarianMT) - kept for fallback
qwen_refiner = get_qwen_refiner()  # Qwen LLM refiner (wrapped by QwenAdapter in Phase 6)

# Initialize CC-CEDICT dictionary for OCR fusion tie-breaking
# ENABLED: Provides intelligent tie-breaking when OCR engines have equal confidence
# Testing confirmed: No negative impact when not needed, potential benefit in tie scenarios
cc_dictionary: Optional[CCDictionary] = None
try:
    # Use path relative to this file's location
    cc_dict_path = Path(__file__).parent / "data" / "cc_cedict.json"
    cc_dictionary = CCDictionary(str(cc_dict_path))
    print(f"✅ CC-CEDICT dictionary loaded successfully with {len(cc_dictionary):,} entries.")
    logger.info("CC-CEDICT dictionary loaded successfully with %d entries.", len(cc_dictionary))
except Exception as e:
    print(f"⚠️  Failed to load CC-CEDICT: {e}. Falling back to translator for OCR fusion.")
    logger.warning("Failed to load CC-CEDICT: %s. Falling back to translator for OCR fusion.", e)
    cc_dictionary = None

# Initialize CC-CEDICT translator for character translation (replaces RuleBasedTranslator)
# Note: This loads its own CCDictionary instance for translation purposes only
cc_translator: Optional[CCDictionaryTranslator] = None
try:
    cc_dict_path = Path(__file__).parent / "data" / "cc_cedict.json"
    translation_dictionary = CCDictionary(str(cc_dict_path))
    cc_translator = CCDictionaryTranslator(translation_dictionary, default_strategy=DefinitionStrategy.FIRST)
    print(f"✅ CC-CEDICT translator initialized ({len(cc_translator):,} entries, strategy: {cc_translator.default_strategy.value}).")
    logger.info("CCDictionaryTranslator initialized with %d entries (strategy: %s)", 
               len(cc_translator), cc_translator.default_strategy.value)
except Exception as e:
    print(f"⚠️  Failed to initialize CCDictionaryTranslator: {e}. Falling back to RuleBasedTranslator.")
    logger.warning("Failed to initialize CCDictionaryTranslator: %s. Falling back to RuleBasedTranslator.", e)
    cc_translator = None

# Initialize MarianAdapter (Phase 5 Step 4: Token locking enabled)
# Must be initialized after cc_dictionary and cc_translator are available
marian_adapter = get_marian_adapter(
    cc_dictionary=cc_dictionary,  # Phase 5 Step 4: For token locking
    cc_translator=cc_translator,  # Phase 5 Step 4: Alternative dictionary source
)  # Phase 5: MarianMT adapter layer (wraps sentence_translator)

# Initialize QwenAdapter (Phase 6 Step 3: Wrap QwenRefiner)
qwen_adapter = get_qwen_adapter(qwen_refiner=qwen_refiner)

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

if qwen_adapter is None:
    logger.warning("QwenAdapter not available. Phase 6 refinement will fall back to direct QwenRefiner (if available).")
else:
    logger.info("QwenAdapter ready (Phase 6)")


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
        # Use CC-CEDICT for intelligent tie-breaking (when OCR engines have equal confidence)
        # Testing confirmed: Harmless when not needed, helpful in true tie scenarios
        fusion_dictionary = cc_dictionary if cc_dictionary is not None else None
        
        # Add lookup_character method wrapper if dictionary doesn't have it
        if fusion_dictionary and not hasattr(fusion_dictionary, "lookup_character"):
            # Wrap lookup_entry to match expected API
            fusion_dictionary.lookup_character = lambda char: fusion_dictionary.lookup_entry(char)
        
        glyphs, full_text, ocr_confidence, ocr_coverage = fuse_character_candidates(
            fused_positions, translator=fusion_dictionary
        )
        
        # Capture dictionary metadata for API response
        if fusion_dictionary == cc_dictionary and cc_dictionary is not None:
            # Using CC-CEDICT
            ocr_dict_source = "CC-CEDICT"
            ocr_dict_metadata = cc_dictionary.get_metadata()
            ocr_dict_version = ocr_dict_metadata.get("format_version", "1.0")
        else:
            # No dictionary (confidence-based)
            ocr_dict_source = "None (Confidence-Based)"
            ocr_dict_version = None
        
        if not full_text or not full_text.strip():
            raise HTTPException(
                status_code=422,
                detail="No text could be extracted from the image."
            )
        
        logger.info(
            "Fused %d positions into %d glyphs, text length: %d (confidence: %.2f%%, coverage: %.1f%%) [Dict: %s]",
            len(fused_positions), len(glyphs), len(full_text),
            ocr_confidence * 100, ocr_coverage, ocr_dict_source
        )
        
        # Log dictionary performance stats (debug level)
        if cc_dictionary is not None:
            cc_dictionary.log_performance_stats(level="debug")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fusing OCR results: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process OCR results: {str(e)}"
        ) from e
    
    # Translate text using dictionary
    # Priority: CC-CEDICT Translator (120k entries) → RuleBasedTranslator (276 entries)
    translation_source = "Unknown"
    try:
        glyph_dicts = [
            {
                "symbol": g.symbol,
                "bbox": g.bbox,
                "confidence": g.confidence
            }
            for g in glyphs
        ]
        
        # Try CC-CEDICT translator first (if available)
        if cc_translator is not None:
            try:
                logger.debug("Using CCDictionaryTranslator for translation (120,474 entries)")
                result = cc_translator.translate_text(full_text, glyphs)
                translation_result = result.to_dict()  # Convert to dict format
                translation_source = "CC-CEDICT"
                logger.info("CC-CEDICT translation completed: %.1f%% coverage (%d/%d characters)", 
                           result.coverage, result.mapped_characters, result.total_characters)
                # Log performance statistics (debug level)
                cc_translator.log_translation_stats(level="debug")
            except Exception as cc_error:
                logger.warning("CCDictionaryTranslator failed: %s. Falling back to RuleBasedTranslator.", cc_error)
                # Fall back to RuleBasedTranslator
                translation_result = translator.translate_text(full_text, glyph_dicts)
                translation_source = "RuleBasedTranslator"
                logger.info("RuleBasedTranslator (fallback) completed: %.1f%% coverage", 
                           translation_result.get('coverage', 0))
        else:
            # CC-CEDICT not available, use RuleBasedTranslator
            logger.debug("Using RuleBasedTranslator for translation (276 entries)")
            translation_result = translator.translate_text(full_text, glyph_dicts)
            translation_source = "RuleBasedTranslator"
            logger.info("RuleBasedTranslator translation completed: %.1f%% coverage", 
                       translation_result.get('coverage', 0))
        
    except Exception as e:
        logger.error("Translation failed: %s", e)
        translation_result = {
            "glyphs": glyph_dicts,
            "translation": "",
            "unmapped": [],
            "coverage": 0.0,
            "dictionary_version": "1.0.0"
        }
        translation_source = "Error"
    
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
    
    # Use OCR metrics from fusion step (computed during fuse_character_candidates)
    # ocr_confidence: Average confidence of OCR detections (0.0-1.0)
    # ocr_coverage: Percentage of characters with dictionary entries (0.0-100.0)
    
    logger.info(
        "Processing complete: %d glyphs, OCR confidence: %.2f%%, coverage: %.1f%%",
        len(enriched_glyphs), ocr_confidence * 100, ocr_coverage
    )
    
    # Log the extracted OCR text for debugging
    logger.info("Extracted OCR text (first 200 chars): %s", full_text[:200] if full_text else "Empty")
    logger.info("Extracted OCR text length: %d characters", len(full_text))
    
    # Phase 5: Perform sentence-level neural translation (MarianMT) via adapter
    # Build canonical input string from glyphs preserving token boundaries
    # Verify glyph order matches full_text order
    canonical_text_from_glyphs = "".join(g.symbol for g in glyphs)
    if canonical_text_from_glyphs != full_text:
        logger.warning(
            "Glyph order mismatch: glyph text (%d chars) != full_text (%d chars). "
            "Using full_text for canonical input.",
            len(canonical_text_from_glyphs), len(full_text)
        )
        logger.debug("Glyph text: %s", canonical_text_from_glyphs[:100])
        logger.debug("Full text: %s", full_text[:100])
    else:
        logger.debug(
            "Glyph order verified: %d glyphs match %d characters in full_text",
            len(glyphs), len(full_text)
        )
    
    sentence_translation = None
    adapter_output = None
    
    # Phase 5: Use MarianAdapter instead of direct sentence_translator call
    if marian_adapter and marian_adapter.is_available():
        try:
            logger.info(
                "Phase 5: Calling MarianAdapter with structured input: "
                "%d glyphs, confidence=%.2f, dictionary_coverage=%.1f%%",
                len(glyphs), ocr_confidence, ocr_coverage
            )
            
            # Build structured input preserving token boundaries
            adapter_output = marian_adapter.translate(
                glyphs=glyphs,
                confidence=ocr_confidence,
                dictionary_coverage=ocr_coverage,
                locked_tokens=None,  # Step 4 (Phase 5): Auto-populated by adapter using semantic contract
                raw_text=full_text  # Use full_text to ensure consistency
            )
            
            sentence_translation = adapter_output.translation if adapter_output else None
            
            logger.info(
                "Phase 5: MarianAdapter translation completed: %s",
                sentence_translation[:200] if sentence_translation else "None"
            )
            
            # Debug logging: Confirm no data loss
            if adapter_output:
                logger.debug(
                    "Phase 5: Adapter output metadata: %s",
                    adapter_output.metadata
                )
                logger.debug(
                    "Phase 5: Locked tokens: %d, Changed tokens: %d, Preserved tokens: %d",
                    len(adapter_output.locked_tokens),
                    len(adapter_output.changed_tokens),
                    len(adapter_output.preserved_tokens)
                )
            
        except Exception as e:
            logger.error("Phase 5: MarianAdapter translation failed: %s", e, exc_info=True)
            sentence_translation = None
            adapter_output = None
            
            # Fallback to direct sentence_translator if adapter fails
            logger.info("Falling back to direct sentence_translator...")
            if sentence_translator and sentence_translator.is_available():
                try:
                    sentence_translation = sentence_translator.translate(full_text)
                    logger.info("Fallback translation completed")
                except Exception as fallback_error:
                    logger.error("Fallback translation also failed: %s", fallback_error)
                    sentence_translation = None
    elif sentence_translator and sentence_translator.is_available():
        # Fallback: Use direct sentence_translator if adapter not available
        logger.debug("MarianAdapter not available, using direct sentence_translator (fallback)")
        try:
            logger.info("Calling MarianMT translator with text: %s", full_text[:100] if full_text else "Empty")
            sentence_translation = sentence_translator.translate(full_text)
            logger.info("Sentence translation completed: %s", sentence_translation[:200] if sentence_translation else "None")
        except Exception as e:
            logger.error("Sentence translation failed: %s", e)
            sentence_translation = None
    else:
        logger.debug("MarianAdapter and sentence_translator not available, skipping neural translation")
    
    # Perform Qwen refinement on MarianMT translation (Phase 6: via QwenAdapter)
    refined_translation = None
    qwen_status = None
    qwen_output = None
    
    if sentence_translation and qwen_adapter and qwen_adapter.is_available():
        try:
            logger.info(
                "Phase 6: Calling QwenAdapter with structured input: %d glyphs, %d locked tokens (Chinese)",
                len(glyphs),
                len(adapter_output.locked_tokens) if adapter_output else 0,
            )
            
            # Build structured input for QwenAdapter from MarianAdapterOutput
            qwen_input = QwenAdapterInput(
                text=sentence_translation,
                glyphs=glyphs,
                locked_tokens=adapter_output.locked_tokens if adapter_output else [],
                preserved_tokens=adapter_output.preserved_tokens if adapter_output else [],
                changed_tokens=adapter_output.changed_tokens if adapter_output else [],
                semantic_metadata=adapter_output.metadata if adapter_output else {},
                ocr_text=full_text,
            )
            
            qwen_output = qwen_adapter.translate(qwen_input)
            refined_translation = qwen_output.refined_text if qwen_output else None
            
            if refined_translation:
                logger.info("Phase 6: QwenAdapter refinement completed: %s", refined_translation[:50])
                qwen_status = "available"
            else:
                logger.warning("Phase 6: QwenAdapter returned None, using MarianMT translation")
                qwen_status = "failed"
        except Exception as e:
            logger.error("Phase 6: QwenAdapter refinement failed: %s", e, exc_info=True)
            refined_translation = None
            qwen_status = "failed"
            
            # Fallback to direct QwenRefiner if adapter fails
            if sentence_translation and qwen_refiner and qwen_refiner.is_available():
                try:
                    logger.info("Phase 6: Falling back to direct QwenRefiner...")
                    refined_translation = qwen_refiner.refine_translation_with_qwen(
                        nmt_translation=sentence_translation,
                        ocr_text=full_text,
                    )
                    if refined_translation:
                        logger.info("Fallback Qwen refinement completed: %s", refined_translation[:50])
                        qwen_status = "available"
                    else:
                        logger.warning("Fallback Qwen refinement returned None, using MarianMT translation")
                        qwen_status = "failed"
                except Exception as fallback_error:
                    logger.error("Fallback Qwen refinement also failed: %s", fallback_error, exc_info=True)
                    refined_translation = None
                    qwen_status = "failed"
    else:
        if not sentence_translation:
            logger.debug("No MarianMT translation available, skipping Qwen refinement")
            qwen_status = "skipped"
        elif not (qwen_adapter and qwen_adapter.is_available()) and not (qwen_refiner and qwen_refiner.is_available()):
            logger.debug("QwenAdapter and QwenRefiner not available, skipping refinement")
            qwen_status = "unavailable"
    
    # Step 7 (Phase 5): Extract semantic metadata from adapter output
    semantic_metadata = None
    if adapter_output and adapter_output.metadata:
        semantic_metadata = {
            "engine": "MarianMT",
            "semantic_confidence": adapter_output.semantic_confidence,
            "tokens_modified": len(adapter_output.changed_tokens),
            "tokens_locked": len(adapter_output.locked_tokens),
            "tokens_preserved": len(adapter_output.preserved_tokens),
            "tokens_modified_percent": adapter_output.metadata.get("tokens_modified_percent", 0.0),
            "tokens_locked_percent": adapter_output.metadata.get("tokens_locked_percent", 0.0),
            "tokens_preserved_percent": adapter_output.metadata.get("tokens_preserved_percent", 0.0),
            "dictionary_override_count": adapter_output.metadata.get("dictionary_override_count", 0),
        }
        logger.debug("Step 7: Semantic metadata prepared for API response: %s", semantic_metadata)
    
    # Step 7 (Phase 6): Extract Qwen metadata from QwenAdapter output
    qwen_metadata: Optional[Dict[str, Any]] = None
    if qwen_output and qwen_output.metadata:
        # Basic counts and confidence
        qwen_conf = qwen_output.qwen_confidence
        changed_tokens = qwen_output.changed_tokens or []
        preserved_tokens = qwen_output.preserved_tokens or []
        locked_tokens = qwen_output.locked_tokens or []

        total_tokens = len(changed_tokens) + len(preserved_tokens)
        tokens_modified_percent = (
            (len(changed_tokens) / total_tokens) * 100.0 if total_tokens > 0 else 0.0
        )
        tokens_locked_percent = (
            (len(locked_tokens) / total_tokens) * 100.0 if total_tokens > 0 else 0.0
        )
        tokens_preserved_percent = (
            (len(preserved_tokens) / total_tokens) * 100.0 if total_tokens > 0 else 0.0
        )

        meta = qwen_output.metadata or {}

        qwen_metadata = {
            "engine": "Qwen2.5-1.5B-Instruct",
            "qwen_confidence": qwen_conf,
            "tokens_modified": len(changed_tokens),
            "tokens_locked": len(locked_tokens),
            "tokens_preserved": len(preserved_tokens),
            "tokens_modified_percent": tokens_modified_percent,
            "tokens_locked_percent": tokens_locked_percent,
            "tokens_preserved_percent": tokens_preserved_percent,
            "phrase_spans_refined": meta.get("unlocked_phrases_count", 0),
            "phrase_spans_locked": meta.get("locked_phrases_count", 0),
        }

        logger.debug("Phase 6 Step 7: Qwen metadata prepared for API response: %s", qwen_metadata)

    return InferenceResponse(
        text=full_text,
        translation=translation_result.get("translation", ""),  # Dictionary-based
        sentence_translation=sentence_translation,  # Neural sentence translation (MarianMT)
        refined_translation=refined_translation,  # Qwen-refined translation
        qwen_status=qwen_status,  # Status: "available", "unavailable", "failed", "skipped"
        confidence=ocr_confidence,  # OCR fusion average confidence (0.0-1.0)
        glyphs=enriched_glyphs,
        unmapped=translation_result.get("unmapped", []),
        coverage=ocr_coverage,  # OCR fusion dictionary coverage (0.0-100.0 percentage)
        dictionary_source=ocr_dict_source,  # OCR fusion dictionary source (CC-CEDICT or Translator)
        dictionary_version=ocr_dict_version,  # OCR fusion dictionary version
        translation_source=translation_source,  # Translation dictionary source (CC-CEDICT, RuleBasedTranslator, or Error)
        semantic=semantic_metadata,  # Phase 5 Step 7: Semantic refinement metadata (optional)
        qwen=qwen_metadata,  # Phase 6 Step 7: Qwen refinement metadata (optional)
    )
