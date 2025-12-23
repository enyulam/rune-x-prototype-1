"""
FastAPI inference service for Chinese handwriting OCR with dictionary-based translation.
- Uses hybrid OCR system (EasyOCR + PaddleOCR) for text extraction
- Uses RuleBasedTranslator for dictionary-based meaning lookup and translation
Run with:
  uvicorn services.inference.main:app --host 0.0.0.0 --port 8001
"""

import io
import logging
import re
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
from text_segmentation import segment_text_into_units  # Phase 8: Chinese segmentation
from sentence_mapping import build_sentence_spans  # Phase 8: Glyph-to-sentence mapping

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
    canonical_text: Optional[str] = None  # Phase 8 Step 0: Canonical OCR text after noise filtering
    canonical_meta: Optional[Dict[str, Any]] = None  # Phase 8 Step 0: Canonicalization metadata


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


def _canonicalize_ocr_text_and_filter_noise(
    glyphs: List[Glyph],
    full_text: str,
) -> Tuple[str, Dict[str, Any]]:
    """
    Build a canonical OCR text string and apply lightweight noise filtering.

    - Prefers the fused `full_text` produced by `ocr_fusion` (which already
      encodes reading order and line/paragraph breaks).
    - Falls back to concatenating glyph symbols if `full_text` is empty.
    - Strips obvious trailing non-Chinese noise (IDs, ASCII tails, etc.) while
      avoiding aggressive modification of the main content.
    """
    glyph_text = "".join(g.symbol for g in glyphs) if glyphs else ""
    base_text = full_text if full_text and full_text.strip() else glyph_text

    metadata: Dict[str, Any] = {
        "original_full_text_length": len(full_text or ""),
        "glyph_text_length": len(glyph_text),
        "chosen_source": "full_text" if full_text and full_text.strip() else "glyph_text",
        "trailing_noise_removed": 0,
    }

    # Simple trailing-noise filter:
    # - Removes trailing whitespace, digits, ASCII letters and a few symbols
    #   that commonly appear in watermarks / IDs (e.g., 608806744T#)
    # - If this would wipe out the entire string, we keep the original.
    trailing_noise_pattern = re.compile(r"[\s0-9A-Za-z#@]+$")
    cleaned_text = trailing_noise_pattern.sub("", base_text)

    if cleaned_text.strip():
        metadata["trailing_noise_removed"] = len(base_text) - len(cleaned_text)
    else:
        # Avoid over-filtering: fall back to the unmodified base_text
        cleaned_text = base_text
        metadata["trailing_noise_removed"] = 0

    if metadata["trailing_noise_removed"] > 0:
        logger.info(
            "Canonical OCR text: removed %d trailing noise characters (likely watermark/ID tail).",
            metadata["trailing_noise_removed"],
        )

    return cleaned_text, metadata


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

        # Phase 8 Step 0: Canonicalize OCR text and apply lightweight noise filtering
        full_text, canonical_meta = _canonicalize_ocr_text_and_filter_noise(
            glyphs=glyphs,
            full_text=full_text,
        )
        
        # Phase 8 Step 1: segment canonical text into paragraphs/sentences (for future per-sentence pipeline)
        segmented_units = segment_text_into_units(full_text)
        logger.info(
            "Phase 8 Step 1: Segmented text into %d sentences across %d paragraph(s)",
            len(segmented_units),
            (segmented_units[-1].paragraph_index + 1) if segmented_units else 0,
        )

        sentence_spans, span_warnings = build_sentence_spans(glyphs, segmented_units)
        if span_warnings:
            logger.warning("Phase 8 Step 2: %d sentence mapping warning(s)", len(span_warnings))
        logger.info(
            "Phase 8 Step 2: Built %d sentence span(s) covering %d glyph(s)",
            len(sentence_spans),
            sum(len(s.glyph_indices) for s in sentence_spans),
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
    
    # Log the extracted OCR text for debugging (after canonicalization / noise filtering)
    logger.info("Extracted OCR text (first 200 chars): %s", full_text[:200] if full_text else "Empty")
    logger.info("Extracted OCR text length: %d characters", len(full_text))
    
    # Phase 5: Perform sentence-level neural translation (MarianMT) via adapter
    # Build canonical input string from glyphs preserving token boundaries
    # Verify glyph order matches canonical full_text order
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
    per_sentence_outputs = None  # Phase 8 Step 3: optional per-sentence Marian outputs
    
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
                raw_text=full_text  # Use canonical full_text to ensure consistency
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

            # Phase 8 Step 3: Per-sentence MarianMT translation for coverage
            if sentence_spans:
                per_sentence_outputs = []
                from collections import defaultdict

                paragraphs: Dict[int, list] = defaultdict(list)
                for span in sentence_spans:
                    span_glyphs = [glyphs[i] for i in span.glyph_indices] if span.glyph_indices else []
                    try:
                        span_output = marian_adapter.translate(
                            glyphs=span_glyphs or glyphs,
                            confidence=ocr_confidence,
                            dictionary_coverage=ocr_coverage,
                            locked_tokens=None,
                            raw_text=span.text,
                        )
                    except Exception as span_err:  # noqa: F841
                        logger.warning(
                            "Phase 8 Step 3: MarianAdapter per-sentence call failed for %d:%d, using raw text. Error: %s",
                            span.paragraph_index,
                            span.sentence_index,
                            span_err,
                        )
                        span_output = None

                    per_sentence_outputs.append((span, span_output))
                    # Use translated sentence if available, else fall back to original Chinese sentence
                    out_text = (
                        span_output.translation
                        if span_output and getattr(span_output, "translation", None)
                        else span.text
                    )
                    paragraphs[span.paragraph_index].append(out_text)

                # Recombine into paragraph-then-sentence ordered text
                ordered_paragraph_indices = sorted(paragraphs.keys())
                recombined_paragraphs = [
                    "".join(paragraphs[p_idx]) for p_idx in ordered_paragraph_indices
                ]
                sentence_translation = "\n\n".join(recombined_paragraphs)
            
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
    qwen_outputs = []  # Phase 8 Step 4: per-paragraph Qwen outputs
    
    if sentence_translation and qwen_adapter and qwen_adapter.is_available():
        try:
            # Phase 8 Step 4: refine per paragraph to bound Qwen's scope
            paragraphs = [p for p in sentence_translation.split("\n\n") if p.strip()]
            refined_paragraphs: List[str] = []

            logger.info(
                "Phase 8 Step 4: Calling QwenAdapter per paragraph: %d paragraph(s), %d glyphs, %d locked tokens (Chinese)",
                len(paragraphs),
                len(glyphs),
                len(adapter_output.locked_tokens) if adapter_output else 0,
            )

            for idx, para in enumerate(paragraphs):
                qwen_input = QwenAdapterInput(
                    text=para,
                    glyphs=glyphs,
                    locked_tokens=adapter_output.locked_tokens if adapter_output else [],
                    preserved_tokens=adapter_output.preserved_tokens if adapter_output else [],
                    changed_tokens=adapter_output.changed_tokens if adapter_output else [],
                    semantic_metadata=adapter_output.metadata if adapter_output else {},
                    ocr_text=full_text,
                )
                para_output = qwen_adapter.translate(qwen_input)
                qwen_outputs.append(para_output)

                refined_para = para_output.refined_text if para_output and para_output.refined_text else para
                refined_paragraphs.append(refined_para)

            if refined_paragraphs:
                refined_translation = "\n\n".join(refined_paragraphs)
                logger.info(
                    "Phase 8 Step 4: QwenAdapter per-paragraph refinement completed (len=%d)",
                    len(refined_translation),
                )
                qwen_status = "available"
            else:
                logger.warning("Phase 8 Step 4: QwenAdapter produced no paragraphs, using MarianMT translation")
                refined_translation = sentence_translation
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
    
    # Step 7 (Phase 5 + Phase 8 Step 5): Extract semantic metadata from adapter output
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

        # Phase 8 Step 5: add segmentation and span coverage metadata
        if segmented_units is not None:
            semantic_metadata["segmented_sentence_count"] = len(segmented_units)
            semantic_metadata["segmented_paragraph_count"] = (
                segmented_units[-1].paragraph_index + 1 if segmented_units else 0
            )
        if sentence_spans:
            spans_meta = []
            for s in sentence_spans:
                spans_meta.append(
                    {
                        "paragraph_index": s.paragraph_index,
                        "sentence_index": s.sentence_index,
                        "glyph_indices": s.glyph_indices,
                        "matched": s.matched,
                        "text_length": len(s.text),
                    }
                )
            semantic_metadata["sentence_spans"] = spans_meta
        if per_sentence_outputs is not None:
            # Track which sentences had translations and which fell back to source
            translated_flags = []
            for span, out in per_sentence_outputs:
                translated_flags.append(
                    {
                        "paragraph_index": span.paragraph_index,
                        "sentence_index": span.sentence_index,
                        "translated": bool(out and getattr(out, "translation", None)),
                    }
                )
            semantic_metadata["per_sentence_translated_flags"] = translated_flags

        logger.debug("Step 7: Semantic metadata prepared for API response: %s", semantic_metadata)
    
    # Step 7 (Phase 6 + Phase 8): Extract Qwen metadata from QwenAdapter outputs
    qwen_metadata: Optional[Dict[str, Any]] = None
    if qwen_outputs:
        # Aggregate basic counts and confidence across paragraphs
        total_changed = 0
        total_preserved = 0
        total_locked = 0
        confidences: List[float] = []
        unlocked_phrases = 0
        locked_phrases = 0

        for out in qwen_outputs:
            if not out or not out.metadata:
                continue
            changed_tokens = out.changed_tokens or []
            preserved_tokens = out.preserved_tokens or []
            locked_tokens = out.locked_tokens or []

            total_changed += len(changed_tokens)
            total_preserved += len(preserved_tokens)
            total_locked += len(locked_tokens)
            confidences.append(out.qwen_confidence)

            meta = out.metadata or {}
            unlocked_phrases += meta.get("unlocked_phrases_count", 0)
            locked_phrases += meta.get("locked_phrases_count", 0)

        total_tokens = total_changed + total_preserved
        tokens_modified_percent = (
            (total_changed / total_tokens) * 100.0 if total_tokens > 0 else 0.0
        )
        tokens_locked_percent = (
            (total_locked / total_tokens) * 100.0 if total_tokens > 0 else 0.0
        )
        tokens_preserved_percent = (
            (total_preserved / total_tokens) * 100.0 if total_tokens > 0 else 0.0
        )

        qwen_metadata = {
            "engine": "Qwen2.5-1.5B-Instruct",
            "qwen_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
            "tokens_modified": total_changed,
            "tokens_locked": total_locked,
            "tokens_preserved": total_preserved,
            "tokens_modified_percent": tokens_modified_percent,
            "tokens_locked_percent": tokens_locked_percent,
            "tokens_preserved_percent": tokens_preserved_percent,
            "phrase_spans_refined": unlocked_phrases,
            "phrase_spans_locked": locked_phrases,
            "paragraphs_total": len(paragraphs) if "paragraphs" in locals() else None,
            "paragraphs_refined": len(qwen_outputs),
        }

        logger.debug("Phase 6 Step 7: Qwen metadata prepared for API response: %s", qwen_metadata)

    # Normalize canonicalization metadata for API consumers
    canonical_meta = canonical_meta if 'canonical_meta' in locals() else {}
    if canonical_meta is None:
        canonical_meta = {}
    # Provide a stable noise filter count field
    if "noise_filtered_count" not in canonical_meta:
        canonical_meta["noise_filtered_count"] = canonical_meta.get("trailing_noise_removed", 0)

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
        canonical_text=full_text,  # Phase 8 Step 0: canonicalized and noise-filtered text
        canonical_meta=canonical_meta,  # Phase 8 Step 0 metadata
    )
