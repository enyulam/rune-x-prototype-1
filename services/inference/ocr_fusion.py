"""
OCR Fusion Module for Rune-X Inference Service

This module provides fusion logic for combining OCR results from multiple engines
(EasyOCR and PaddleOCR) using IoU-based alignment and confidence-weighted selection.

Key Features:
- IoU-based bounding box alignment
- Character-level fusion preserving all candidates
- Reading order sorting (top-to-bottom, left-to-right)
- Dictionary-guided tie-breaking for equal confidence candidates
- Comprehensive logging of alignment and fusion decisions

Usage:
    from ocr_fusion import align_ocr_outputs, fuse_character_candidates
    
    # Align OCR results
    fused_positions = align_ocr_outputs(easyocr_results, paddleocr_results)
    
    # Fuse into final glyphs and text
    glyphs, full_text = fuse_character_candidates(fused_positions, translator=translator)
"""

import logging
from typing import List, Optional, Tuple, Any
from dataclasses import dataclass
from pydantic import BaseModel

# Configure module logger
logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class NormalizedOCRResult:
    """Normalized OCR result from any engine."""
    bbox: List[float]  # [x1, y1, x2, y2]
    char: str
    confidence: float
    source: str  # "easyocr" or "paddleocr"


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


# Glyph model for compatibility with main.py
class Glyph(BaseModel):
    symbol: str
    bbox: Optional[List[float]] = None  # [x, y, w, h]
    confidence: float
    meaning: Optional[str] = None


# ============================================================================
# CORE FUSION FUNCTIONS
# ============================================================================

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
        iou_threshold: Minimum IoU for considering boxes as aligned (default: 0.3)
        
    Returns:
        List of fused positions with aligned candidates
    """
    # Log function entry with input counts
    logger.info(
        "Starting OCR alignment: %d EasyOCR results, %d PaddleOCR results (IoU threshold: %.2f)",
        len(easyocr_results),
        len(paddleocr_results),
        iou_threshold
    )
    
    # Handle empty input cases
    if not easyocr_results and not paddleocr_results:
        logger.warning("Both OCR engines returned empty results - no characters to align")
        return []
    
    if not easyocr_results:
        logger.info("EasyOCR returned no results - using PaddleOCR only")
    
    if not paddleocr_results:
        logger.info("PaddleOCR returned no results - using EasyOCR only")
    
    fused_positions = []
    used_easyocr = set()
    used_paddleocr = set()
    
    # Alignment statistics for logging
    aligned_count = 0
    easyocr_only_count = 0
    paddleocr_only_count = 0
    
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
                
                # Log alignment decision
                logger.debug(
                    "Position %d: Aligned EasyOCR '%s' + PaddleOCR '%s' (IoU: %.3f)",
                    position_idx,
                    easyocr_candidate[1].char,
                    paddleocr_candidate[1].char,
                    iou
                )
                
                used_easyocr.add(easyocr_candidate[0])
                used_paddleocr.add(paddleocr_candidate[0])
                easyocr_ptr += 1
                paddleocr_ptr += 1
                position_idx += 1
                aligned_count += 1
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
                
                logger.debug(
                    "Position %d: No alignment, selecting EasyOCR '%s' (reading order)",
                    position_idx,
                    easyocr_candidate[1].char
                )
                
                used_easyocr.add(easyocr_candidate[0])
                easyocr_ptr += 1
                easyocr_only_count += 1
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
                
                logger.debug(
                    "Position %d: No alignment, selecting PaddleOCR '%s' (reading order)",
                    position_idx,
                    paddleocr_candidate[1].char
                )
                
                used_paddleocr.add(paddleocr_candidate[0])
                paddleocr_ptr += 1
                paddleocr_only_count += 1
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
            
            logger.debug(
                "Position %d: Only EasyOCR candidate '%s' available",
                position_idx,
                easyocr_candidate[1].char
            )
            
            used_easyocr.add(easyocr_candidate[0])
            easyocr_ptr += 1
            position_idx += 1
            easyocr_only_count += 1
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
            
            logger.debug(
                "Position %d: Only PaddleOCR candidate '%s' available",
                position_idx,
                paddleocr_candidate[1].char
            )
            
            used_paddleocr.add(paddleocr_candidate[0])
            paddleocr_ptr += 1
            position_idx += 1
            paddleocr_only_count += 1
        else:
            # Both are used, advance both pointers
            easyocr_ptr += 1
            paddleocr_ptr += 1
    
    # Log alignment summary
    logger.info(
        "Alignment summary: %d total positions (%d aligned, %d EasyOCR-only, %d PaddleOCR-only) "
        "from %d EasyOCR + %d PaddleOCR results",
        len(fused_positions),
        aligned_count,
        easyocr_only_count,
        paddleocr_only_count,
        len(easyocr_results),
        len(paddleocr_results)
    )
    
    return fused_positions


def fuse_character_candidates(
    fused_positions: List[FusedPosition],
    translator: Optional[Any] = None
) -> Tuple[List[Glyph], str, float, float]:
    """
    Convert fused positions to Glyph objects and full text string.
    For each position, use the highest-confidence candidate as the primary character.
    If multiple candidates have equal confidence, use dictionary lookup for tie-breaking.
    
    Args:
        fused_positions: List of fused character positions
        translator: Optional translator object for dictionary-guided tie-breaking
                   (must have lookup_character() method)
        
    Returns:
        Tuple of:
        - List of Glyph objects
        - Full text string
        - Average confidence (0.0-1.0)
        - Translation coverage (0.0-100.0 percentage)
        
    Algorithm:
        1. For each position, find the highest confidence candidate
        2. If multiple candidates have equal confidence (within 0.01 tolerance):
           - If translator provided, select candidate with dictionary meaning
           - If no dictionary match, select first candidate
        3. Convert to Glyph format and build full text string
        4. Compute metrics: average confidence and translation coverage
    """
    # Log function entry
    logger.info(
        "Starting character fusion: %d positions, translator: %s",
        len(fused_positions),
        "enabled" if translator is not None else "disabled"
    )
    
    # Handle empty input
    if not fused_positions:
        logger.warning("No fused positions to process - returning empty result")
        return [], "", 0.0, 0.0
    
    glyphs = []
    full_text_parts = []
    
    # Track tie-breaking statistics
    tie_break_count = 0
    dictionary_used_count = 0
    
    # Track metrics
    total_confidence = 0.0
    characters_with_meaning = 0
    
    for pos in fused_positions:
        if not pos.candidates:
            continue
        
        # Select highest confidence candidate as primary
        # For tie-breaking, use dictionary lookup if translator provided
        best_candidate = None
        
        if len(pos.candidates) == 1:
            # Only one candidate, simple selection
            best_candidate = pos.candidates[0]
            logger.debug(
                "Position %d: Selected '%s' from %s (conf: %.3f) - single candidate",
                pos.position,
                best_candidate.char,
                best_candidate.source,
                best_candidate.confidence
            )
        else:
            # Multiple candidates - check for confidence ties
            max_conf = max(c.confidence for c in pos.candidates)
            top_candidates = [c for c in pos.candidates if abs(c.confidence - max_conf) < 0.01]
            
            if len(top_candidates) == 1:
                # Clear winner by confidence
                best_candidate = top_candidates[0]
                logger.debug(
                    "Position %d: Selected '%s' from %s (conf: %.3f) - highest confidence",
                    pos.position,
                    best_candidate.char,
                    best_candidate.source,
                    best_candidate.confidence
                )
            else:
                # Confidence tie - use dictionary if available
                tie_break_count += 1
                
                if translator is not None:
                    logger.debug(
                        "Position %d: Confidence tie detected (%d candidates at %.3f)",
                        pos.position,
                        len(top_candidates),
                        max_conf
                    )
                    logger.debug(
                        "Candidates: %s",
                        [f"{c.char}({c.source})" for c in top_candidates]
                    )
                    
                    # Try to find candidate with dictionary meaning
                    for candidate in top_candidates:
                        try:
                            if translator.lookup_character(candidate.char):
                                best_candidate = candidate
                                dictionary_used_count += 1
                                logger.info(
                                    "Position %d: Dictionary-guided selection '%s' (tie-broken)",
                                    pos.position,
                                    best_candidate.char
                                )
                                break
                        except Exception as e:
                            logger.warning(
                                "Dictionary lookup failed for '%s': %s",
                                candidate.char,
                                e
                            )
                    
                    if best_candidate is None:
                        # No dictionary match, use first candidate
                        best_candidate = top_candidates[0]
                        logger.info(
                            "Position %d: Dictionary tie-break failed, using first candidate '%s'",
                            pos.position,
                            best_candidate.char
                        )
                else:
                    # No translator, use first of tied candidates
                    best_candidate = top_candidates[0]
                    logger.debug(
                        "Position %d: Multiple candidates at %.3f, selected '%s' (no translator)",
                        pos.position,
                        max_conf,
                        best_candidate.char
                    )
        
        # Convert bbox from [x1, y1, x2, y2] to [x, y, w, h] for Glyph
        x1, y1, x2, y2 = pos.bbox
        bbox_glyph = [x1, y1, x2 - x1, y2 - y1]
        
        # Track confidence for metrics
        total_confidence += best_candidate.confidence
        
        # Check if character has dictionary meaning for coverage metric
        if translator is not None:
            try:
                if translator.lookup_character(best_candidate.char):
                    characters_with_meaning += 1
            except Exception:
                # Ignore lookup errors for metrics calculation
                pass
        
        glyphs.append(
            Glyph(
                symbol=best_candidate.char,
                bbox=bbox_glyph,
                confidence=best_candidate.confidence,
                meaning=None  # Will be filled in by translator in main.py
            )
        )
        full_text_parts.append(best_candidate.char)
    
    full_text = "".join(full_text_parts)
    
    # Compute metrics
    average_confidence = total_confidence / len(glyphs) if glyphs else 0.0
    translation_coverage = (characters_with_meaning / len(glyphs) * 100.0) if glyphs else 0.0
    
    # Log comprehensive fusion summary with metrics
    if tie_break_count > 0:
        logger.info(
            "Fusion complete: %d glyphs, %d characters | "
            "Tie-breaks: %d (dictionary-guided: %d, fallback: %d) | "
            "Avg confidence: %.2f%%, Coverage: %.1f%%",
            len(glyphs),
            len(full_text),
            tie_break_count,
            dictionary_used_count,
            tie_break_count - dictionary_used_count,
            average_confidence * 100,
            translation_coverage
        )
    else:
        logger.info(
            "Fusion complete: %d glyphs, %d characters | No tie-breaks needed | "
            "Avg confidence: %.2f%%, Coverage: %.1f%%",
            len(glyphs),
            len(full_text),
            average_confidence * 100,
            translation_coverage
        )
    
    return glyphs, full_text, average_confidence, translation_coverage


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    # Data structures
    'NormalizedOCRResult',
    'CharacterCandidate',
    'FusedPosition',
    'Glyph',
    # Core functions
    'calculate_iou',
    'align_ocr_outputs',
    'fuse_character_candidates',
]

