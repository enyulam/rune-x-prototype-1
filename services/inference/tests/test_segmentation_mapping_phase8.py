import pytest
import sys
from pathlib import Path

# Ensure the services/inference package is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from text_segmentation import (
    segment_paragraphs,
    segment_sentences,
    segment_text_into_units,
    SegmentedUnit,
)
from sentence_mapping import build_sentence_spans
from ocr_fusion import Glyph


def test_segment_paragraphs_and_sentences_basic():
    text = "第一句。\n第二句！\n\n第三句？"
    paragraphs = segment_paragraphs(text)
    assert len(paragraphs) == 2
    sentences_p0 = segment_sentences(paragraphs[0])
    sentences_p1 = segment_sentences(paragraphs[1])
    assert sentences_p0 == ["第一句。", "第二句！"]
    assert sentences_p1 == ["第三句？"]


def test_segment_text_into_units_ordering():
    text = "甲。乙？\n\n丙！丁。"
    units = segment_text_into_units(text)
    assert len(units) == 4
    # Ensure ordering and paragraph indices
    assert [u.paragraph_index for u in units] == [0, 0, 1, 1]
    assert [u.sentence_index for u in units] == [0, 1, 0, 1]
    assert [u.text for u in units] == ["甲。", "乙？", "丙！", "丁。"]


def test_build_sentence_spans_monotonic_mapping():
    # glyphs correspond exactly to "甲乙丙丁"
    glyphs = [
        Glyph(symbol="甲", bbox=[0, 0, 1, 1], confidence=1.0),
        Glyph(symbol="乙", bbox=[1, 0, 2, 1], confidence=1.0),
        Glyph(symbol="丙", bbox=[2, 0, 3, 1], confidence=1.0),
        Glyph(symbol="丁", bbox=[3, 0, 4, 1], confidence=1.0),
    ]
    units = [
        SegmentedUnit(paragraph_index=0, sentence_index=0, text="甲乙"),
        SegmentedUnit(paragraph_index=0, sentence_index=1, text="丙丁"),
    ]
    spans, warnings = build_sentence_spans(glyphs, units)
    assert not warnings
    assert len(spans) == 2
    assert spans[0].glyph_indices == [0, 1]
    assert spans[1].glyph_indices == [2, 3]
    # Monotonic and non-overlapping
    assert spans[0].glyph_indices[-1] < spans[1].glyph_indices[0]


def test_build_sentence_spans_fuzzy_allows_minor_mismatch():
    glyphs = [
        Glyph(symbol="你", bbox=[0, 0, 1, 1], confidence=1.0),
        Glyph(symbol="好", bbox=[1, 0, 2, 1], confidence=1.0),
        Glyph(symbol="吗", bbox=[2, 0, 3, 1], confidence=1.0),
    ]
    units = [SegmentedUnit(paragraph_index=0, sentence_index=0, text="你好 吗")]
    spans, warnings = build_sentence_spans(glyphs, units, max_mismatch_ratio=0.34)
    assert len(spans) == 1
    # Fuzzy match should still return indices
    assert spans[0].glyph_indices == [0, 1, 2]
    # Warning may or may not be produced depending on ratio; accept either
    assert len(warnings) in (0, 1)

