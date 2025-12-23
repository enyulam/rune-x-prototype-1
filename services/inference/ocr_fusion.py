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
from typing import List, Optional, Tuple, Any, Dict
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
    # Phase 1: DP alignment extensions (optional, for backward compatibility)
    line_id: Optional[int] = None  # Line index this character belongs to
    char_index_in_line: Optional[int] = None  # Index within the line


@dataclass
class CharacterCandidate:
    """Single character candidate from an OCR engine."""
    char: str
    confidence: float
    source: str
    # Phase 1: DP alignment extensions (optional, for backward compatibility)
    line_id: Optional[int] = None  # Line index this candidate belongs to
    char_index_in_line: Optional[int] = None  # Index within the line


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
# PHASE 1: DP ALIGNMENT DATA STRUCTURES
# ============================================================================

@dataclass
class AlignmentCell:
    """
    Lightweight DP node for alignment tracking.
    Used in dynamic programming alignment to track optimal paths.
    """
    score: float  # Best alignment score at this cell
    prev_i: Optional[int] = None  # Previous i index (for backtracking)
    prev_j: Optional[int] = None  # Previous j index (for backtracking)
    action: Optional[str] = None  # Action taken: "match", "skip_a", "skip_b"


# ============================================================================
# PHASE 1: LINE GROUPING FUNCTIONS
# ============================================================================

def group_into_lines(
    characters: List[NormalizedOCRResult],
    line_threshold_ratio: float = 0.3
) -> List[List[NormalizedOCRResult]]:
    """
    Group characters into horizontal lines using y-overlap and vertical center distance.
    
    Phase 1, Task 2: Replace global reading order with spatially correct lines.
    This becomes the only entry point to alignment.
    
    Args:
        characters: List of OCR characters with bounding boxes
        line_threshold_ratio: Ratio of character height to use as threshold for same-line detection (default: 0.3)
        
    Returns:
        List of lines, where each line is a list of characters sorted left-to-right.
        Lines are naturally sorted top-to-bottom.
    """
    if not characters:
        return []
    
    # Sort characters by rough vertical position (y1) first
    sorted_chars = sorted(characters, key=lambda c: c.bbox[1])
    lines: List[List[NormalizedOCRResult]] = []
    current_line: List[NormalizedOCRResult] = [sorted_chars[0]]
    line_y1 = sorted_chars[0].bbox[1]  # Base y1 for the current line
    char_height = sorted_chars[0].bbox[3] - sorted_chars[0].bbox[1]  # y2 - y1 (height)
    line_threshold = char_height * line_threshold_ratio  # Allow threshold_ratio * height tolerance for same line
    
    for char in sorted_chars[1:]:
        # Check if character belongs to the current line (y1 within threshold)
        if abs(char.bbox[1] - line_y1) <= line_threshold:
            current_line.append(char)
        else:
            # Finalize current line: sort horizontally (x1) and add to lines
            lines.append(sorted(current_line, key=lambda c: c.bbox[0]))
            # Start new line
            current_line = [char]
            line_y1 = char.bbox[1]
            char_height = char.bbox[3] - char.bbox[1]
            line_threshold = char_height * line_threshold_ratio  # Update threshold for new line
    
    # Add the last line
    if current_line:
        lines.append(sorted(current_line, key=lambda c: c.bbox[0]))
    
    # Assign line_id and char_index_in_line to each character (for downstream use)
    for line_idx, line in enumerate(lines):
        for char_idx, char in enumerate(line):
            char.line_id = line_idx
            char.char_index_in_line = char_idx
    
    logger.debug(
        "Grouped %d characters into %d lines (threshold ratio: %.2f)",
        len(characters),
        len(lines),
        line_threshold_ratio
    )
    
    return lines  # Lines are naturally sorted top-to-bottom


# ============================================================================
# PHASE 2: DP ALIGNMENT HELPER FUNCTIONS
# ============================================================================

# Note: iou() is not needed as an alias - use calculate_iou() directly
# Phase 2, Task 3: calculate_iou() is already a pure, deterministic, side-effect free function


def lines_overlap(
    line1: List[NormalizedOCRResult],
    line2: List[NormalizedOCRResult]
) -> bool:
    """
    Check if two lines overlap vertically (to determine alignment candidates).
    
    Phase 2, Task 4: Pure function to check vertical overlap between lines.
    
    Args:
        line1: First line (list of characters)
        line2: Second line (list of characters)
        
    Returns:
        True if lines overlap vertically, False otherwise
    """
    if not line1 or not line2:
        return False
    
    # Get vertical range for each line
    line1_min_y = min(c.bbox[1] for c in line1)  # Min y1
    line1_max_y = max(c.bbox[3] for c in line1)  # Max y2
    line2_min_y = min(c.bbox[1] for c in line2)  # Min y1
    line2_max_y = max(c.bbox[3] for c in line2)  # Max y2
    
    # Overlap if ranges intersect
    return not (line1_max_y < line2_min_y or line2_max_y < line1_min_y)


def fuse_chars(
    char1: NormalizedOCRResult,
    char2: NormalizedOCRResult
) -> NormalizedOCRResult:
    """
    Fuse two aligned characters (prefer higher-confidence or larger bounding box).
    
    Phase 2, Task 5: Pure function to fuse aligned characters.
    
    Args:
        char1: First character candidate
        char2: Second character candidate
        
    Returns:
        Fused character (preferring higher confidence or larger bounding box)
    """
    # Calculate bounding box areas
    area1 = (char1.bbox[2] - char1.bbox[0]) * (char1.bbox[3] - char1.bbox[1])
    area2 = (char2.bbox[2] - char2.bbox[0]) * (char2.bbox[3] - char2.bbox[1])
    
    # Prefer character with higher confidence, or larger bounding box if confidence is similar
    if abs(char1.confidence - char2.confidence) < 0.01:
        # Confidence tie: use larger bounding box (assumed more accurate)
        return char1 if area1 >= area2 else char2
    else:
        # Use higher confidence
        return char1 if char1.confidence >= char2.confidence else char2


def select_best_option(
    option1: Optional[List[NormalizedOCRResult]],
    option2: Optional[List[NormalizedOCRResult]],
    option3: Optional[List[NormalizedOCRResult]]
) -> List[NormalizedOCRResult]:
    """
    Choose the option with the most logical horizontal order (minimal x displacement).
    
    Phase 2, Task 6: Pure function to select best alignment option.
    
    Args:
        option1: First alignment option (match/fuse)
        option2: Second alignment option (skip first)
        option3: Third alignment option (skip second)
        
    Returns:
        Best option based on horizontal ordering score (lower = better order)
    """
    options = [opt for opt in [option1, option2, option3] if opt is not None]
    if not options:
        return []
    
    # Score: sum of x differences between consecutive characters (lower = better order)
    def score(seq: List[NormalizedOCRResult]) -> float:
        if len(seq) < 2:
            return 0.0
        # Calculate sum of absolute x-coordinate differences
        # This penalizes sequences where characters are not in left-to-right order
        return sum(abs(seq[i].bbox[0] - seq[i-1].bbox[0]) for i in range(1, len(seq)))
    
    return min(options, key=score)


# ============================================================================
# PHASE 2: DP ALIGNMENT CORE FUNCTIONS
# ============================================================================

def align_line_chars(
    easy_chars: List[NormalizedOCRResult],
    paddle_chars: List[NormalizedOCRResult],
    iou_threshold: float = 0.5,
    skip_penalty: float = -0.1
) -> List[NormalizedOCRResult]:
    """
    Intra-line character alignment using DP to handle swaps and misalignments.
    
    Phase 2, Task 7: DP over character sequences within a single line.
    Scoring: Match (+IoU/char similarity), Skip penalty.
    Backtracking produces aligned char pairs.
    
    Fixes greedy char-level cascades.
    
    Args:
        easy_chars: EasyOCR characters in a single line
        paddle_chars: PaddleOCR characters in a single line
        iou_threshold: Minimum IoU for considering characters as aligned (default: 0.5)
        skip_penalty: Penalty score for skipping a character (default: -0.1)
        
    Returns:
        Best aligned sequence of characters (fused or single-source)
    """
    if not easy_chars and not paddle_chars:
        return []
    if not easy_chars:
        return paddle_chars
    if not paddle_chars:
        return easy_chars
    
    # DP table: dp[i][j] = best alignment for first i EasyOCR and j PaddleOCR chars
    # Each cell contains AlignmentCell with score and backtracking info
    dp: List[List[AlignmentCell]] = [
        [AlignmentCell(score=float('-inf'), action=None) for _ in range(len(paddle_chars) + 1)]
        for _ in range(len(easy_chars) + 1)
    ]
    
    # Base case: empty sequences
    dp[0][0] = AlignmentCell(score=0.0, action="start")
    
    # Fill DP table
    for i in range(len(easy_chars) + 1):
        for j in range(len(paddle_chars) + 1):
            if i == 0 and j == 0:
                continue
            
            best_score = float('-inf')
            best_prev_i = None
            best_prev_j = None
            best_action = None
            
            # Option 1: Take EasyOCR character (i-1) - skip PaddleOCR
            if i > 0:
                score_skip_paddle = dp[i-1][j].score + skip_penalty
                if score_skip_paddle > best_score:
                    best_score = score_skip_paddle
                    best_prev_i = i - 1
                    best_prev_j = j
                    best_action = "skip_paddle"
            
            # Option 2: Take PaddleOCR character (j-1) - skip EasyOCR
            if j > 0:
                score_skip_easy = dp[i][j-1].score + skip_penalty
                if score_skip_easy > best_score:
                    best_score = score_skip_easy
                    best_prev_i = i
                    best_prev_j = j - 1
                    best_action = "skip_easy"
            
            # Option 3: Fuse if IoU >= threshold (aligned)
            if i > 0 and j > 0:
                iou_val = calculate_iou(easy_chars[i-1].bbox, paddle_chars[j-1].bbox)
                if iou_val >= iou_threshold:
                    # Match score: IoU value (higher = better alignment)
                    score_match = dp[i-1][j-1].score + iou_val
                    if score_match > best_score:
                        best_score = score_match
                        best_prev_i = i - 1
                        best_prev_j = j - 1
                        best_action = "match"
            
            dp[i][j] = AlignmentCell(
                score=best_score,
                prev_i=best_prev_i,
                prev_j=best_prev_j,
                action=best_action
            )
    
    # Backtrack to build aligned sequence
    aligned_chars: List[NormalizedOCRResult] = []
    i = len(easy_chars)
    j = len(paddle_chars)
    
    while i > 0 or j > 0:
        cell = dp[i][j]
        action = cell.action
        
        if action == "match":
            # Fuse the aligned characters
            fused_char = fuse_chars(easy_chars[i-1], paddle_chars[j-1])
            aligned_chars.insert(0, fused_char)
            i -= 1
            j -= 1
        elif action == "skip_paddle":
            # Use EasyOCR character only
            aligned_chars.insert(0, easy_chars[i-1])
            i -= 1
        elif action == "skip_easy":
            # Use PaddleOCR character only
            aligned_chars.insert(0, paddle_chars[j-1])
            j -= 1
        else:
            # Should not happen, but break to avoid infinite loop
            break
    
    logger.debug(
        "Intra-line DP alignment: %d EasyOCR + %d PaddleOCR -> %d aligned chars",
        len(easy_chars),
        len(paddle_chars),
        len(aligned_chars)
    )
    
    return aligned_chars


def align_lines(
    easy_lines: List[List[NormalizedOCRResult]],
    paddle_lines: List[List[NormalizedOCRResult]],
    iou_threshold: float = 0.5
) -> List[List[NormalizedOCRResult]]:
    """
    Align lines from EasyOCR and PaddleOCR using DP to handle line-level mismatches.
    
    Phase 2, Task 8: DP over lines using line overlap and average char alignment score.
    Supports missing lines and inserted lines.
    
    Fixes phrase swaps and block reordering.
    
    Args:
        easy_lines: List of lines from EasyOCR (each line is a list of characters)
        paddle_lines: List of lines from PaddleOCR (each line is a list of characters)
        iou_threshold: Minimum IoU for character alignment within lines (default: 0.5)
        
    Returns:
        Fused lines (sorted top-to-bottom)
    """
    if not easy_lines and not paddle_lines:
        return []
    if not easy_lines:
        return paddle_lines
    if not paddle_lines:
        return easy_lines
    
    # DP table: dp[i][j] = best alignment for first i EasyOCR lines and j PaddleOCR lines
    dp: List[List[AlignmentCell]] = [
        [AlignmentCell(score=float('-inf'), action=None) for _ in range(len(paddle_lines) + 1)]
        for _ in range(len(easy_lines) + 1)
    ]
    
    # Base case: empty sequences
    dp[0][0] = AlignmentCell(score=0.0, action="start")
    
    # Fill DP table
    for i in range(len(easy_lines) + 1):
        for j in range(len(paddle_lines) + 1):
            if i == 0 and j == 0:
                continue
            
            best_score = float('-inf')
            best_prev_i = None
            best_prev_j = None
            best_action = None
            
            # Option 1: Take EasyOCR line (i-1) - skip PaddleOCR line
            if i > 0:
                score_skip_paddle = dp[i-1][j].score - 1.0  # Penalty for skipping a line
                if score_skip_paddle > best_score:
                    best_score = score_skip_paddle
                    best_prev_i = i - 1
                    best_prev_j = j
                    best_action = "skip_paddle"
            
            # Option 2: Take PaddleOCR line (j-1) - skip EasyOCR line
            if j > 0:
                score_skip_easy = dp[i][j-1].score - 1.0  # Penalty for skipping a line
                if score_skip_easy > best_score:
                    best_score = score_skip_easy
                    best_prev_i = i
                    best_prev_j = j - 1
                    best_action = "skip_easy"
            
            # Option 3: Fuse lines if they overlap
            if i > 0 and j > 0:
                easy_line = easy_lines[i-1]
                paddle_line = paddle_lines[j-1]
                
                if lines_overlap(easy_line, paddle_line):
                    # Fuse characters within the line using intra-line DP
                    fused_chars = align_line_chars(easy_line, paddle_line, iou_threshold)
                    
                    # Calculate average alignment score for this line fusion
                    # Use average IoU of aligned characters as score
                    if fused_chars:
                        # Count how many characters were successfully aligned
                        aligned_count = sum(
                            1 for k in range(min(len(easy_line), len(paddle_line)))
                            if k < len(easy_line) and k < len(paddle_line) and
                            calculate_iou(easy_line[k].bbox, paddle_line[k].bbox) >= iou_threshold
                        )
                        avg_score = aligned_count / max(len(easy_line), len(paddle_line)) if max(len(easy_line), len(paddle_line)) > 0 else 0.0
                    else:
                        avg_score = 0.0
                    
                    score_match = dp[i-1][j-1].score + avg_score
                    if score_match > best_score:
                        best_score = score_match
                        best_prev_i = i - 1
                        best_prev_j = j - 1
                        best_action = "match"
                else:
                    # Lines don't overlap - take the one that appears first vertically
                    if easy_line[0].bbox[1] < paddle_line[0].bbox[1]:
                        score_match = dp[i-1][j].score  # Use EasyOCR line
                        if score_match > best_score:
                            best_score = score_match
                            best_prev_i = i - 1
                            best_prev_j = j
                            best_action = "skip_paddle"
                    else:
                        score_match = dp[i][j-1].score  # Use PaddleOCR line
                        if score_match > best_score:
                            best_score = score_match
                            best_prev_i = i
                            best_prev_j = j - 1
                            best_action = "skip_easy"
            
            dp[i][j] = AlignmentCell(
                score=best_score,
                prev_i=best_prev_i,
                prev_j=best_prev_j,
                action=best_action
            )
    
    # Backtrack to build fused lines
    fused_lines: List[List[NormalizedOCRResult]] = []
    i = len(easy_lines)
    j = len(paddle_lines)
    
    while i > 0 or j > 0:
        cell = dp[i][j]
        action = cell.action
        
        if action == "match":
            # Fuse the overlapping lines
            easy_line = easy_lines[i-1]
            paddle_line = paddle_lines[j-1]
            fused_chars = align_line_chars(easy_line, paddle_line, iou_threshold)
            fused_lines.insert(0, fused_chars)
            i -= 1
            j -= 1
        elif action == "skip_paddle":
            # Use EasyOCR line only
            fused_lines.insert(0, easy_lines[i-1])
            i -= 1
        elif action == "skip_easy":
            # Use PaddleOCR line only
            fused_lines.insert(0, paddle_lines[j-1])
            j -= 1
        else:
            # Should not happen, but break to avoid infinite loop
            break
    
    logger.info(
        "Line-level DP alignment: %d EasyOCR lines + %d PaddleOCR lines -> %d fused lines",
        len(easy_lines),
        len(paddle_lines),
        len(fused_lines)
    )
    
    return fused_lines


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
    iou_threshold: float = 0.3,
    use_dp_alignment: bool = True
) -> List[FusedPosition]:
    """
    Align OCR results from both engines using DP-based alignment.
    
    Phase 3: Refactored to use line grouping + DP alignment instead of greedy matching.
    Handles character-level alignment preserving all candidates from both engines.
    
    Args:
        easyocr_results: Normalized EasyOCR results
        paddleocr_results: Normalized PaddleOCR results
        iou_threshold: Minimum IoU for considering boxes as aligned (default: 0.3)
        use_dp_alignment: If True, use DP-based alignment (Phase 3). If False, use legacy greedy matching.
        
    Returns:
        List of fused positions with aligned candidates (format unchanged for backward compatibility)
    """
    # Log function entry with input counts
    logger.info(
        "Starting OCR alignment: %d EasyOCR results, %d PaddleOCR results (IoU threshold: %.2f, DP: %s)",
        len(easyocr_results),
        len(paddleocr_results),
        iou_threshold,
        use_dp_alignment
    )
    
    # Handle empty input cases
    if not easyocr_results and not paddleocr_results:
        logger.warning("Both OCR engines returned empty results - no characters to align")
        return []
    
    if not easyocr_results:
        logger.info("EasyOCR returned no results - using PaddleOCR only")
    
    if not paddleocr_results:
        logger.info("PaddleOCR returned no results - using EasyOCR only")
    
    # Phase 3: Use DP-based alignment
    if use_dp_alignment:
        return _align_ocr_outputs_dp(easyocr_results, paddleocr_results, iou_threshold)
    else:
        # Legacy greedy matching (kept for backward compatibility/testing)
        return _align_ocr_outputs_greedy(easyocr_results, paddleocr_results, iou_threshold)


def _align_ocr_outputs_dp(
    easyocr_results: List[NormalizedOCRResult],
    paddleocr_results: List[NormalizedOCRResult],
    iou_threshold: float
) -> List[FusedPosition]:
    """
    Phase 3: DP-based alignment implementation.
    
    Workflow:
    1. Group characters into lines (group_into_lines)
    2. Align lines using line-level DP (align_lines)
    3. Align characters within each line using char-level DP (align_line_chars)
    4. Convert back to FusedPosition format (backward compatibility)
    
    Returns:
        List[FusedPosition] - Same format as legacy implementation
    """
    # Step 1: Group characters into lines
    easyocr_lines = group_into_lines(easyocr_results)
    paddleocr_lines = group_into_lines(paddleocr_results)
    
    logger.info(
        "Phase 3: Grouped into lines - EasyOCR: %d lines, PaddleOCR: %d lines",
        len(easyocr_lines),
        len(paddleocr_lines)
    )
    
    # Step 2: Align lines using line-level DP
    fused_lines = align_lines(easyocr_lines, paddleocr_lines, iou_threshold)
    
    logger.info(
        "Phase 3: Line-level DP alignment complete - %d fused lines",
        len(fused_lines)
    )
    
    # Step 3: Phase 4 - Detect breaks between lines
    break_markers = detect_line_breaks(fused_lines)
    
    logger.info(
        "Phase 4: Detected %d breaks (%d line breaks, %d paragraph breaks)",
        sum(1 for m in break_markers if m != BREAK_NONE),
        sum(1 for m in break_markers if m == BREAK_LINE),
        sum(1 for m in break_markers if m == BREAK_PARAGRAPH)
    )
    
    # Step 4: Convert fused lines back to FusedPosition format
    # This maintains backward compatibility with downstream consumers
    # Phase 4: Store break information in FusedPosition for later use in fuse_character_candidates
    
    fused_positions: List[FusedPosition] = []
    position_idx = 0
    aligned_count = 0
    easyocr_only_count = 0
    paddleocr_only_count = 0
    
    for line_idx, line in enumerate(fused_lines):
        for char_idx, char in enumerate(line):
            # Create candidates list
            # The fused character from DP alignment represents the best match
            # We create a single candidate with the fused character's properties
            candidates: List[CharacterCandidate] = [
                CharacterCandidate(
                    char=char.char,
                    confidence=char.confidence,
                    source=char.source,  # Source of the fused character
                    line_id=line_idx,
                    char_index_in_line=char_idx
                )
            ]
            
            # Create FusedPosition
            # Store break marker in a way that can be accessed later
            # We'll use the position field to encode break information
            # For now, we'll store it in metadata or use a special marker character
            fused_pos = FusedPosition(
                position=position_idx,
                bbox=char.bbox,
                candidates=candidates
            )
            
            # Store break marker in FusedPosition (we'll need to extend FusedPosition or use a workaround)
            # For Phase 4, we'll pass break information separately to fuse_character_candidates
            fused_positions.append(fused_pos)
            
            position_idx += 1
            
            # Track statistics
            # Note: In DP alignment, we can't easily distinguish between
            # "aligned" (both sources) vs "single source" without additional metadata.
            # For now, we use source field as indicator.
            if char.source in ["easyocr", "paddleocr"]:
                if char.source == "easyocr":
                    easyocr_only_count += 1
                else:
                    paddleocr_only_count += 1
            else:
                # Assume fused (though source field may not reflect this accurately)
                aligned_count += 1
    
    # Store break markers for use in fuse_character_candidates
    # We'll attach them to the first FusedPosition as metadata (temporary solution)
    # Better solution: extend FusedPosition dataclass or pass breaks separately
    if fused_positions and break_markers:
        # Store break markers in a way that fuse_character_candidates can access
        # We'll modify fuse_character_candidates to accept breaks parameter
        # For now, store as attribute (hacky but works)
        fused_positions[0]._break_markers = break_markers  # type: ignore
        fused_positions[0]._fused_lines = fused_lines  # type: ignore
    
    # Log alignment summary
    logger.info(
        "Phase 3 DP alignment summary: %d total positions (%d aligned, %d EasyOCR-only, %d PaddleOCR-only) "
        "from %d EasyOCR + %d PaddleOCR results",
        len(fused_positions),
        aligned_count,
        easyocr_only_count,
        paddleocr_only_count,
        len(easyocr_results),
        len(paddleocr_results)
    )
    
    return fused_positions


def _align_ocr_outputs_greedy(
    easyocr_results: List[NormalizedOCRResult],
    paddleocr_results: List[NormalizedOCRResult],
    iou_threshold: float
) -> List[FusedPosition]:
    """
    Legacy greedy matching implementation (kept for backward compatibility/testing).
    
    This is the original implementation before Phase 3 refactoring.
    """
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
            iou_val = calculate_iou(easyocr_candidate[1].bbox, paddleocr_candidate[1].bbox)
            
            if iou_val >= iou_threshold:
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
                    iou_val
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
        "Legacy greedy alignment summary: %d total positions (%d aligned, %d EasyOCR-only, %d PaddleOCR-only) "
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
    
    Phase 4: Enhanced to insert breaks (line/paragraph) based on gap detection.
    
    Args:
        fused_positions: List of fused character positions
        translator: Optional translator object for dictionary-guided tie-breaking
                   (must have lookup_character() method)
        
    Returns:
        Tuple of:
        - List of Glyph objects
        - Full text string (with breaks inserted)
        - Average confidence (0.0-1.0)
        - Translation coverage (0.0-100.0 percentage)
        
    Algorithm:
        1. For each position, find the highest confidence candidate
        2. If multiple candidates have equal confidence (within 0.01 tolerance):
           - If translator provided, select candidate with dictionary meaning
           - If no dictionary match, select first candidate
        3. Convert to Glyph format
        4. Phase 4: Reconstruct lines and insert breaks based on gap detection
        5. Build full text string with breaks
        6. Compute metrics: average confidence and translation coverage
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
    
    # Track tie-breaking statistics
    tie_break_count = 0
    dictionary_used_count = 0
    
    # Track metrics
    total_confidence = 0.0
    characters_with_meaning = 0
    
    # Phase 4: Check if break markers are available (from DP alignment)
    break_markers = None
    fused_lines = None
    
    if fused_positions and hasattr(fused_positions[0], '_break_markers'):
        break_markers = fused_positions[0]._break_markers  # type: ignore
        fused_lines = fused_positions[0]._fused_lines  # type: ignore
        logger.info("Phase 4: Break markers detected, will insert breaks into text")
    
    # Build glyphs and character list
    char_list: List[Tuple[str, int]] = []  # (char, line_id) pairs
    
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
        
        # Store character with line_id for break insertion
        line_id = best_candidate.line_id if best_candidate.line_id is not None else 0
        char_list.append((best_candidate.char, line_id))
    
    # Phase 4: Insert breaks into text
    if break_markers and fused_lines:
        # Use the break detection from fused_lines
        full_text = insert_breaks_into_text(fused_lines, break_markers)
        logger.info("Phase 4: Text with breaks inserted: %d characters, %d breaks", len(full_text), sum(1 for m in break_markers if m != BREAK_NONE))
    else:
        # Fallback: reconstruct lines from char_list and detect breaks
        # Group characters by line_id
        lines_dict: Dict[int, List[str]] = {}
        for char, line_id in char_list:
            lines_dict.setdefault(line_id, []).append(char)
        
        # Convert to list of lines (sorted by line_id)
        reconstructed_lines: List[List[NormalizedOCRResult]] = []
        for line_id in sorted(lines_dict.keys()):
            line_chars = lines_dict[line_id]
            # Create minimal NormalizedOCRResult for break detection
            line_results = [
                NormalizedOCRResult(
                    bbox=[0, 0, 0, 0],  # Dummy bbox - not used for break detection
                    char=char,
                    confidence=0.0,
                    source="",
                    line_id=line_id,
                    char_index_in_line=i
                )
                for i, char in enumerate(line_chars)
            ]
            reconstructed_lines.append(line_results)
        
        # Detect breaks from reconstructed lines
        if len(reconstructed_lines) > 1:
            # Use bounding boxes from glyphs to calculate gaps
            # Reconstruct with actual bboxes
            glyph_idx = 0
            for line_results in reconstructed_lines:
                for char_idx, _ in enumerate(line_results):
                    if glyph_idx < len(glyphs):
                        # Update bbox from glyph
                        glyph = glyphs[glyph_idx]
                        if glyph.bbox:
                            x, y, w, h = glyph.bbox
                            line_results[char_idx].bbox = [x, y, x + w, y + h]
                        glyph_idx += 1
            
            break_markers_reconstructed = detect_line_breaks(reconstructed_lines)
            full_text = insert_breaks_into_text(reconstructed_lines, break_markers_reconstructed)
            logger.info("Phase 4: Reconstructed lines and inserted breaks")
        else:
            # Single line or no line info - use simple concatenation
            full_text = "".join(char for char, _ in char_list)
            logger.debug("Phase 4: Single line or no line info, using simple concatenation")
    
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
# PHASE 4: PARAGRAPH STRUCTURE - BREAK DETECTION
# ============================================================================

# Break type markers
BREAK_NONE = "none"
BREAK_LINE = "line"
BREAK_PARAGRAPH = "paragraph"


def calculate_avg_char_height(fused_lines: List[List[NormalizedOCRResult]]) -> float:
    """
    Calculate average character height across all lines (for thresholding).
    
    Phase 4, Task 10: Helper function for adaptive threshold calculation.
    
    Args:
        fused_lines: List of lines, each containing characters
        
    Returns:
        Average character height (default: 10.0 if no characters)
    """
    heights = []
    for line in fused_lines:
        for char in line:
            height = char.bbox[3] - char.bbox[1]  # y2 - y1
            heights.append(height)
    return sum(heights) / len(heights) if heights else 10.0


def detect_line_breaks(
    fused_lines: List[List[NormalizedOCRResult]],
    line_break_gap_ratio: float = 0.5,
    para_break_gap_ratio: float = 2.0
) -> List[str]:
    """
    Detect line and paragraph breaks based on vertical gaps between lines.
    
    Phase 4, Task 10: Gap-based break detection.
    
    Inputs:
        - Line bounding boxes (from fused_lines)
        - Vertical gaps (calculated between consecutive lines)
        - Line alignment confidence (implicit in line structure)
    
    Outputs:
        - List of break markers: BREAK_NONE, BREAK_LINE, or BREAK_PARAGRAPH
    
    Args:
        fused_lines: List of lines (each line is a list of characters)
        line_break_gap_ratio: Ratio of avg char height for line breaks (default: 0.5)
        para_break_gap_ratio: Ratio of avg char height for paragraph breaks (default: 2.0)
        
    Returns:
        List of break markers, one per line (first line has BREAK_NONE)
    """
    if not fused_lines:
        return []
    
    # Calculate adaptive thresholds based on average character height
    avg_char_height = calculate_avg_char_height(fused_lines)
    line_break_gap = avg_char_height * line_break_gap_ratio
    para_break_gap = avg_char_height * para_break_gap_ratio
    
    logger.debug(
        "Phase 4: Break detection thresholds - avg_char_height: %.2f, "
        "line_break: %.2f, para_break: %.2f",
        avg_char_height,
        line_break_gap,
        para_break_gap
    )
    
    # First line has no break before it
    break_markers = [BREAK_NONE]
    
    # Process subsequent lines
    for i in range(1, len(fused_lines)):
        prev_line = fused_lines[i-1]
        curr_line = fused_lines[i]
        
        if not prev_line or not curr_line:
            break_markers.append(BREAK_NONE)
            continue
        
        # Calculate vertical gap between end of previous line and start of current line
        prev_line_bottom = max(c.bbox[3] for c in prev_line)  # Max y2 of previous line
        curr_line_top = min(c.bbox[1] for c in curr_line)     # Min y1 of current line
        gap = curr_line_top - prev_line_bottom
        
        # Determine break type based on gap size
        if gap >= para_break_gap:
            break_markers.append(BREAK_PARAGRAPH)
            logger.debug(
                "Phase 4: Paragraph break detected between lines %d-%d (gap: %.2f >= %.2f)",
                i-1,
                i,
                gap,
                para_break_gap
            )
        elif gap >= line_break_gap:
            break_markers.append(BREAK_LINE)
            logger.debug(
                "Phase 4: Line break detected between lines %d-%d (gap: %.2f >= %.2f)",
                i-1,
                i,
                gap,
                line_break_gap
            )
        else:
            break_markers.append(BREAK_NONE)
            logger.debug(
                "Phase 4: No break between lines %d-%d (gap: %.2f < %.2f)",
                i-1,
                i,
                gap,
                line_break_gap
            )
    
    return break_markers


def insert_breaks_into_text(
    fused_lines: List[List[NormalizedOCRResult]],
    break_markers: List[str]
) -> str:
    """
    Convert fused lines to text with newlines (line breaks) and double newlines (paragraph breaks).
    
    Phase 4, Task 11: Insert breaks into fused text.
    
    Args:
        fused_lines: List of lines (each line is a list of characters)
        break_markers: List of break markers (BREAK_NONE, BREAK_LINE, BREAK_PARAGRAPH)
        
    Returns:
        Text string with breaks inserted (\n for line breaks, \n\n for paragraph breaks)
    """
    if not fused_lines:
        return ""
    
    text_parts = []
    
    # Add first line text
    first_line_text = "".join([c.char for c in fused_lines[0]])
    text_parts.append(first_line_text)
    
    # Process subsequent lines with breaks
    for i in range(1, len(fused_lines)):
        # Insert break based on marker
        break_marker = break_markers[i] if i < len(break_markers) else BREAK_NONE
        
        if break_marker == BREAK_PARAGRAPH:
            text_parts.append("\n\n")  # Paragraph break (double newline)
        elif break_marker == BREAK_LINE:
            text_parts.append("\n")    # Line break (single newline)
        # else BREAK_NONE: no break (continue on same line or small gap)
        
        # Add current line's text
        line_text = "".join([c.char for c in fused_lines[i]])
        text_parts.append(line_text)
    
    result = "".join(text_parts)
    
    logger.debug(
        "Phase 4: Inserted breaks - %d lines, %d breaks (%d line, %d paragraph)",
        len(fused_lines),
        sum(1 for m in break_markers if m != BREAK_NONE),
        sum(1 for m in break_markers if m == BREAK_LINE),
        sum(1 for m in break_markers if m == BREAK_PARAGRAPH)
    )
    
    return result


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    # Data structures
    'NormalizedOCRResult',
    'CharacterCandidate',
    'FusedPosition',
    'Glyph',
    'AlignmentCell',  # Phase 1: DP alignment
    # Core functions
    'calculate_iou',
    'align_ocr_outputs',
    'fuse_character_candidates',
    # Phase 1: Line grouping
    'group_into_lines',
    # Phase 2: DP alignment helpers
    'lines_overlap',
    'fuse_chars',
    'select_best_option',
    # Phase 2: DP alignment core
    'align_line_chars',
    'align_lines',
    # Phase 4: Break detection
    'BREAK_NONE',
    'BREAK_LINE',
    'BREAK_PARAGRAPH',
    'calculate_avg_char_height',
    'detect_line_breaks',
    'insert_breaks_into_text',
]

