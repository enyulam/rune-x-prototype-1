"""
Glyph → sentence mapping utilities (Phase 8 Step 2).

Given segmented sentences and the ordered glyph list (already fused/aligned),
we map each sentence to the glyph indices that compose it. This version uses a
conservative greedy scan to ensure coverage without reordering.
"""

from dataclasses import dataclass
from typing import List, Tuple
import logging
import difflib

from text_segmentation import SegmentedUnit
from ocr_fusion import Glyph

logger = logging.getLogger(__name__)


@dataclass
class SentenceSpan:
    paragraph_index: int
    sentence_index: int
    glyph_indices: List[int]
    text: str
    matched: bool = True  # whether we could align text to glyphs confidently


def _normalize(text: str) -> str:
    """Trim whitespace for safer comparisons."""
    return "".join(text.split())


def build_sentence_spans(
    glyphs: List[Glyph],
    segmented_units: List[SegmentedUnit],
    max_mismatch_ratio: float = 0.15,
) -> Tuple[List[SentenceSpan], List[str]]:
    """
    Map each segmented sentence to a contiguous list of glyph indices.

    Strategy:
    - Walk glyphs in order, accumulating characters until we match the target sentence text.
    - Use whitespace-trimmed matching to be resilient to spacing differences.
    - If exact match fails, allow a small mismatch ratio; otherwise mark as unmatched.
    - Never reorder glyphs; mapping is monotonic.

    Returns:
        sentence_spans: list of SentenceSpan
        warnings: list of warning strings for logging/metadata
    """
    sentence_spans: List[SentenceSpan] = []
    warnings: List[str] = []

    glyph_text = [g.symbol for g in glyphs]
    glyph_ptr = 0

    for unit in segmented_units:
        target = _normalize(unit.text)
        collected_indices: List[int] = []
        buffer = ""

        while glyph_ptr < len(glyph_text) and len(buffer) < len(target):
            buffer += glyph_text[glyph_ptr]
            collected_indices.append(glyph_ptr)
            glyph_ptr += 1

        matched = _normalize(buffer) == target
        if not matched:
            # Fuzzy check using difflib ratio
            ratio = difflib.SequenceMatcher(None, _normalize(buffer), target).ratio()
            if ratio >= 1.0 - max_mismatch_ratio:
                matched = True
            else:
                warnings.append(
                    f"Sentence {unit.paragraph_index}:{unit.sentence_index} "
                    f"could not be matched cleanly (ratio={ratio:.2f}); using collected glyphs."
                )

        sentence_spans.append(
            SentenceSpan(
                paragraph_index=unit.paragraph_index,
                sentence_index=unit.sentence_index,
                glyph_indices=collected_indices.copy(),
                text=unit.text,
                matched=matched,
            )
        )

    if warnings:
        logger.warning("Sentence mapping warnings: %s", warnings)

    return sentence_spans, warnings

