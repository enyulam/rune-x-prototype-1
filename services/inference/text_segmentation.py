"""
Chinese paragraph and sentence segmentation utilities (Phase 8 Step 1).

This module provides lightweight segmentation for downstream per-sentence /
per-paragraph translation. It is intentionally conservative: it uses simple
punctuation and newline cues to avoid dropping or merging content.
"""

from dataclasses import dataclass
from typing import List
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class SegmentedUnit:
    paragraph_index: int
    sentence_index: int
    text: str


_SENTENCE_SPLIT_REGEX = re.compile(r"([。！？!?])")


def segment_paragraphs(text: str) -> List[str]:
    """
    Segment text into paragraphs using double newlines as the primary signal.
    Falls back to a single paragraph if none found.
    """
    if not text:
        return []
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    return parts if parts else [text.strip()]


def segment_sentences(paragraph: str) -> List[str]:
    """
    Segment a paragraph into sentences using Chinese punctuation and newlines.
    Keeps delimiters attached to the sentence for fidelity.
    """
    if not paragraph:
        return []

    # First, split on explicit newlines inside the paragraph
    lines = [ln.strip() for ln in paragraph.split("\n") if ln.strip()]
    segments: List[str] = []

    for line in lines:
        tokens = _SENTENCE_SPLIT_REGEX.split(line)
        buffer = ""
        for token in tokens:
            if not token:
                continue
            buffer += token
            if _SENTENCE_SPLIT_REGEX.fullmatch(token):
                segments.append(buffer.strip())
                buffer = ""
        if buffer.strip():
            segments.append(buffer.strip())

    # If nothing was split, return the line as-is
    return segments if segments else [paragraph.strip()]


def segment_text_into_units(text: str) -> List[SegmentedUnit]:
    """
    Produce ordered SegmentedUnit entries for the entire text.
    """
    units: List[SegmentedUnit] = []
    paragraphs = segment_paragraphs(text)

    for p_idx, para in enumerate(paragraphs):
        sentences = segment_sentences(para)
        for s_idx, sentence in enumerate(sentences):
            units.append(
                SegmentedUnit(
                    paragraph_index=p_idx,
                    sentence_index=s_idx,
                    text=sentence,
                )
            )

    logger.debug(
        "Segmentation complete: %d paragraphs, %d sentences",
        len(paragraphs),
        sum(1 for _ in units),
    )
    return units

