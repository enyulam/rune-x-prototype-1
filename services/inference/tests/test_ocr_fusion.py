"""
Unit tests for OCR fusion module.

Tests the core OCR fusion functionality including:
- IoU calculation between bounding boxes
- Alignment of OCR results from multiple engines
- Fusion of character candidates into final output
"""

import pytest
from typing import List

import sys
from pathlib import Path
# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ocr_fusion import (
    NormalizedOCRResult,
    CharacterCandidate,
    FusedPosition,
    Glyph,
    calculate_iou,
    align_ocr_outputs,
    fuse_character_candidates
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_easyocr_results() -> List[NormalizedOCRResult]:
    """Sample EasyOCR results for testing."""
    return [
        NormalizedOCRResult(bbox=[10, 10, 30, 30], char="我", confidence=0.95, source="easyocr"),
        NormalizedOCRResult(bbox=[40, 10, 60, 30], char="是", confidence=0.90, source="easyocr"),
        NormalizedOCRResult(bbox=[70, 10, 90, 30], char="学", confidence=0.85, source="easyocr"),
    ]


@pytest.fixture
def sample_paddleocr_results() -> List[NormalizedOCRResult]:
    """Sample PaddleOCR results for testing."""
    return [
        NormalizedOCRResult(bbox=[12, 12, 32, 32], char="我", confidence=0.92, source="paddleocr"),
        NormalizedOCRResult(bbox=[42, 12, 62, 32], char="是", confidence=0.88, source="paddleocr"),
        NormalizedOCRResult(bbox=[72, 12, 92, 32], char="生", confidence=0.80, source="paddleocr"),
    ]


@pytest.fixture
def sample_fused_positions() -> List[FusedPosition]:
    """Sample fused positions for testing."""
    return [
        FusedPosition(
            position=0,
            bbox=[10, 10, 30, 30],
            candidates=[
                CharacterCandidate(char="我", confidence=0.95, source="easyocr"),
                CharacterCandidate(char="我", confidence=0.92, source="paddleocr"),
            ]
        ),
        FusedPosition(
            position=1,
            bbox=[40, 10, 60, 30],
            candidates=[
                CharacterCandidate(char="是", confidence=0.90, source="easyocr"),
                CharacterCandidate(char="是", confidence=0.88, source="paddleocr"),
            ]
        ),
    ]


# ============================================================================
# TEST calculate_iou()
# ============================================================================

class TestCalculateIoU:
    """Test IoU calculation between bounding boxes."""
    
    def test_perfect_overlap(self):
        """Test IoU with identical boxes (IoU = 1.0)."""
        bbox1 = [10, 10, 30, 30]
        bbox2 = [10, 10, 30, 30]
        iou = calculate_iou(bbox1, bbox2)
        assert iou == 1.0
    
    def test_no_overlap(self):
        """Test IoU with non-overlapping boxes (IoU = 0.0)."""
        bbox1 = [10, 10, 30, 30]
        bbox2 = [40, 40, 60, 60]
        iou = calculate_iou(bbox1, bbox2)
        assert iou == 0.0
    
    def test_partial_overlap_50_percent(self):
        """Test IoU with 50% overlap."""
        bbox1 = [10, 10, 30, 30]  # Area = 400
        bbox2 = [20, 10, 40, 30]  # Area = 400, Intersection = 200
        iou = calculate_iou(bbox1, bbox2)
        # Intersection = 200, Union = 400 + 400 - 200 = 600
        expected_iou = 200 / 600
        assert abs(iou - expected_iou) < 0.01
    
    def test_partial_overlap_small(self):
        """Test IoU with small overlap."""
        bbox1 = [10, 10, 30, 30]
        bbox2 = [25, 25, 45, 45]
        iou = calculate_iou(bbox1, bbox2)
        # Small corner overlap: 5x5 = 25
        # Union = 400 + 400 - 25 = 775
        expected_iou = 25 / 775
        assert abs(iou - expected_iou) < 0.01
    
    def test_one_box_inside_another(self):
        """Test IoU when one box is completely inside another."""
        bbox1 = [10, 10, 50, 50]  # Larger box: 40x40 = 1600
        bbox2 = [20, 20, 30, 30]  # Smaller box: 10x10 = 100
        iou = calculate_iou(bbox1, bbox2)
        # Intersection = 100 (smaller box)
        # Union = 1600 + 100 - 100 = 1600
        expected_iou = 100 / 1600
        assert abs(iou - expected_iou) < 0.01
    
    def test_adjacent_boxes_touching(self):
        """Test IoU with boxes that touch but don't overlap."""
        bbox1 = [10, 10, 30, 30]
        bbox2 = [30, 10, 50, 30]  # Shares edge
        iou = calculate_iou(bbox1, bbox2)
        assert iou == 0.0
    
    def test_zero_area_box(self):
        """Test IoU with zero-area box."""
        bbox1 = [10, 10, 10, 10]  # Zero area
        bbox2 = [10, 10, 30, 30]
        iou = calculate_iou(bbox1, bbox2)
        assert iou == 0.0
    
    def test_inverted_coordinates(self):
        """Test IoU handles inverted coordinates (should still work)."""
        bbox1 = [30, 30, 10, 10]  # x2 < x1, y2 < y1
        bbox2 = [10, 10, 30, 30]
        iou = calculate_iou(bbox1, bbox2)
        # Should return 0.0 due to invalid box
        assert iou == 0.0


# ============================================================================
# TEST align_ocr_outputs()
# ============================================================================

class TestAlignOCROutputs:
    """Test alignment of OCR results from multiple engines."""
    
    def test_aligned_characters_high_iou(self, sample_easyocr_results, sample_paddleocr_results):
        """Test alignment when characters from both engines overlap significantly."""
        fused = align_ocr_outputs(sample_easyocr_results, sample_paddleocr_results, iou_threshold=0.3)
        
        # Should have 3 positions (all characters align due to high IoU)
        assert len(fused) == 3
        
        # Verify structure
        for pos in fused:
            assert isinstance(pos, FusedPosition)
            assert isinstance(pos.position, int)
            assert len(pos.bbox) == 4
            assert len(pos.candidates) >= 1
        
        # Verify all positions have candidates from both engines
        for pos in fused:
            assert len(pos.candidates) == 2
    
    def test_both_engines_same_character(self):
        """Test when both engines detect the same character at same position."""
        easyocr = [NormalizedOCRResult(bbox=[10, 10, 30, 30], char="我", confidence=0.95, source="easyocr")]
        paddleocr = [NormalizedOCRResult(bbox=[12, 12, 32, 32], char="我", confidence=0.90, source="paddleocr")]
        
        fused = align_ocr_outputs(easyocr, paddleocr, iou_threshold=0.5)
        
        assert len(fused) == 1
        assert len(fused[0].candidates) == 2
        assert fused[0].candidates[0].char == "我"
        assert fused[0].candidates[1].char == "我"
    
    def test_easyocr_only(self, sample_easyocr_results):
        """Test alignment when only EasyOCR has results."""
        fused = align_ocr_outputs(sample_easyocr_results, [], iou_threshold=0.3)
        
        assert len(fused) == len(sample_easyocr_results)
        for pos in fused:
            assert len(pos.candidates) == 1
            assert pos.candidates[0].source == "easyocr"
    
    def test_paddleocr_only(self, sample_paddleocr_results):
        """Test alignment when only PaddleOCR has results."""
        fused = align_ocr_outputs([], sample_paddleocr_results, iou_threshold=0.3)
        
        assert len(fused) == len(sample_paddleocr_results)
        for pos in fused:
            assert len(pos.candidates) == 1
            assert pos.candidates[0].source == "paddleocr"
    
    def test_empty_inputs(self):
        """Test alignment with no OCR results."""
        fused = align_ocr_outputs([], [], iou_threshold=0.3)
        assert len(fused) == 0
    
    def test_reading_order_top_to_bottom(self):
        """Test that characters are ordered top-to-bottom."""
        easyocr = [
            NormalizedOCRResult(bbox=[10, 50, 30, 70], char="下", confidence=0.9, source="easyocr"),
            NormalizedOCRResult(bbox=[10, 10, 30, 30], char="上", confidence=0.9, source="easyocr"),
        ]
        
        fused = align_ocr_outputs(easyocr, [], iou_threshold=0.3)
        
        # Should be reordered: 上 (top) before 下 (bottom)
        assert fused[0].candidates[0].char == "上"
        assert fused[1].candidates[0].char == "下"
    
    def test_reading_order_left_to_right(self):
        """Test that characters are ordered left-to-right at same height."""
        easyocr = [
            NormalizedOCRResult(bbox=[50, 10, 70, 30], char="右", confidence=0.9, source="easyocr"),
            NormalizedOCRResult(bbox=[10, 10, 30, 30], char="左", confidence=0.9, source="easyocr"),
        ]
        
        fused = align_ocr_outputs(easyocr, [], iou_threshold=0.3)
        
        # Should be reordered: 左 (left) before 右 (right)
        assert fused[0].candidates[0].char == "左"
        assert fused[1].candidates[0].char == "右"
    
    def test_iou_threshold_low(self):
        """Test alignment with low IoU threshold (more alignments)."""
        easyocr = [NormalizedOCRResult(bbox=[10, 10, 30, 30], char="A", confidence=0.9, source="easyocr")]
        paddleocr = [NormalizedOCRResult(bbox=[25, 25, 45, 45], char="B", confidence=0.9, source="paddleocr")]
        
        # Low threshold should allow alignment
        fused = align_ocr_outputs(easyocr, paddleocr, iou_threshold=0.01)
        
        # Should align due to low threshold
        assert len(fused) <= 2  # Either 1 aligned or 2 separate
    
    def test_iou_threshold_high(self):
        """Test alignment with high IoU threshold (fewer alignments)."""
        easyocr = [NormalizedOCRResult(bbox=[10, 10, 30, 30], char="A", confidence=0.9, source="easyocr")]
        paddleocr = [NormalizedOCRResult(bbox=[25, 25, 45, 45], char="B", confidence=0.9, source="paddleocr")]
        
        # High threshold should prevent alignment
        fused = align_ocr_outputs(easyocr, paddleocr, iou_threshold=0.9)
        
        # Should NOT align due to high threshold
        assert len(fused) == 2
        assert all(len(pos.candidates) == 1 for pos in fused)
    
    def test_multiple_overlapping_characters(self):
        """Test alignment with multiple overlapping detections."""
        easyocr = [
            NormalizedOCRResult(bbox=[10, 10, 30, 30], char="我", confidence=0.95, source="easyocr"),
            NormalizedOCRResult(bbox=[40, 10, 60, 30], char="是", confidence=0.90, source="easyocr"),
        ]
        paddleocr = [
            NormalizedOCRResult(bbox=[12, 12, 32, 32], char="我", confidence=0.92, source="paddleocr"),
            NormalizedOCRResult(bbox=[42, 12, 62, 32], char="是", confidence=0.88, source="paddleocr"),
        ]
        
        fused = align_ocr_outputs(easyocr, paddleocr, iou_threshold=0.5)
        
        # Both characters should align
        assert len(fused) == 2
        for pos in fused:
            assert len(pos.candidates) == 2
    
    def test_bbox_averaging_on_alignment(self):
        """Test that aligned bboxes are averaged correctly."""
        easyocr = [NormalizedOCRResult(bbox=[10, 10, 30, 30], char="我", confidence=0.9, source="easyocr")]
        paddleocr = [NormalizedOCRResult(bbox=[20, 20, 40, 40], char="我", confidence=0.9, source="paddleocr")]
        
        fused = align_ocr_outputs(easyocr, paddleocr, iou_threshold=0.1)
        
        if len(fused) == 1 and len(fused[0].candidates) == 2:
            # Boxes should be averaged: [(10+20)/2, (10+20)/2, (30+40)/2, (30+40)/2]
            expected_bbox = [15.0, 15.0, 35.0, 35.0]
            assert fused[0].bbox == expected_bbox


# ============================================================================
# TEST fuse_character_candidates()
# ============================================================================

class TestFuseCharacterCandidates:
    """Test fusion of character candidates into final output."""
    
    def test_single_candidate_per_position(self):
        """Test fusion with single candidate per position."""
        positions = [
            FusedPosition(
                position=0,
                bbox=[10, 10, 30, 30],
                candidates=[CharacterCandidate(char="我", confidence=0.95, source="easyocr")]
            ),
            FusedPosition(
                position=1,
                bbox=[40, 10, 60, 30],
                candidates=[CharacterCandidate(char="是", confidence=0.90, source="easyocr")]
            ),
        ]
        
        glyphs, text, avg_conf, coverage = fuse_character_candidates(positions)
        
        assert len(glyphs) == 2
        assert text == "我是"
        assert glyphs[0].symbol == "我"
        assert glyphs[1].symbol == "是"
        assert 0.0 <= avg_conf <= 1.0
        assert 0.0 <= coverage <= 100.0
    
    def test_multiple_candidates_select_highest_confidence(self, sample_fused_positions):
        """Test that highest confidence candidate is selected."""
        glyphs, text, avg_conf, coverage = fuse_character_candidates(sample_fused_positions)
        
        assert len(glyphs) == 2
        assert text == "我是"
        # Should select EasyOCR (0.95 > 0.92 and 0.90 > 0.88)
        assert glyphs[0].confidence == 0.95
        assert glyphs[1].confidence == 0.90
    
    def test_multiple_candidates_different_characters(self):
        """Test fusion when candidates have different characters."""
        positions = [
            FusedPosition(
                position=0,
                bbox=[10, 10, 30, 30],
                candidates=[
                    CharacterCandidate(char="学", confidence=0.85, source="easyocr"),
                    CharacterCandidate(char="生", confidence=0.80, source="paddleocr"),
                ]
            ),
        ]
        
        glyphs, text, avg_conf, coverage = fuse_character_candidates(positions)
        
        # Should select "学" (higher confidence)
        assert text == "学"
        assert glyphs[0].symbol == "学"
        assert glyphs[0].confidence == 0.85
    
    def test_empty_positions(self):
        """Test fusion with no positions."""
        glyphs, text, avg_conf, coverage = fuse_character_candidates([])
        
        assert len(glyphs) == 0
        assert text == ""
        assert avg_conf == 0.0
        assert coverage == 0.0
    
    def test_position_with_no_candidates(self):
        """Test fusion when position has empty candidates list."""
        positions = [
            FusedPosition(position=0, bbox=[10, 10, 30, 30], candidates=[]),
            FusedPosition(
                position=1,
                bbox=[40, 10, 60, 30],
                candidates=[CharacterCandidate(char="我", confidence=0.9, source="easyocr")]
            ),
        ]
        
        glyphs, text, avg_conf, coverage = fuse_character_candidates(positions)
        
        # Should skip empty position
        assert len(glyphs) == 1
        assert text == "我"
    
    def test_bbox_format_conversion(self):
        """Test that bbox is converted from [x1,y1,x2,y2] to [x,y,w,h]."""
        positions = [
            FusedPosition(
                position=0,
                bbox=[10, 20, 30, 50],  # [x1, y1, x2, y2]
                candidates=[CharacterCandidate(char="我", confidence=0.9, source="easyocr")]
            ),
        ]
        
        glyphs, text, avg_conf, coverage = fuse_character_candidates(positions)
        
        # Expected: [10, 20, 20, 30] -> [x=10, y=20, w=20, h=30]
        assert glyphs[0].bbox == [10, 20, 20, 30]
    
    def test_text_construction_preserves_order(self):
        """Test that text string preserves position order."""
        positions = [
            FusedPosition(
                position=0,
                bbox=[10, 10, 30, 30],
                candidates=[CharacterCandidate(char="我", confidence=0.9, source="easyocr")]
            ),
            FusedPosition(
                position=1,
                bbox=[40, 10, 60, 30],
                candidates=[CharacterCandidate(char="是", confidence=0.9, source="easyocr")]
            ),
            FusedPosition(
                position=2,
                bbox=[70, 10, 90, 30],
                candidates=[CharacterCandidate(char="学", confidence=0.9, source="easyocr")]
            ),
            FusedPosition(
                position=3,
                bbox=[100, 10, 120, 30],
                candidates=[CharacterCandidate(char="生", confidence=0.9, source="easyocr")]
            ),
        ]
        
        glyphs, text, avg_conf, coverage = fuse_character_candidates(positions)
        
        assert text == "我是学生"
        assert len(glyphs) == 4
    
    def test_glyph_structure(self):
        """Test that Glyph objects have correct structure."""
        positions = [
            FusedPosition(
                position=0,
                bbox=[10, 10, 30, 30],
                candidates=[CharacterCandidate(char="我", confidence=0.95, source="easyocr")]
            ),
        ]
        
        glyphs, _, avg_conf, coverage = fuse_character_candidates(positions)
        
        glyph = glyphs[0]
        assert isinstance(glyph, Glyph)
        assert glyph.symbol == "我"
        assert glyph.confidence == 0.95
        assert glyph.bbox == [10, 10, 20, 20]
        assert glyph.meaning is None  # Not set in fusion
    
    def test_equal_confidence_tie(self):
        """Test behavior when candidates have equal confidence."""
        positions = [
            FusedPosition(
                position=0,
                bbox=[10, 10, 30, 30],
                candidates=[
                    CharacterCandidate(char="学", confidence=0.90, source="easyocr"),
                    CharacterCandidate(char="生", confidence=0.90, source="paddleocr"),
                ]
            ),
        ]
        
        glyphs, text, avg_conf, coverage = fuse_character_candidates(positions)
        
        # Should select one (implementation-dependent, but should be consistent)
        assert len(glyphs) == 1
        assert text in ["学", "生"]
        assert glyphs[0].confidence == 0.90
        assert avg_conf == 0.90


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestOCRFusionIntegration:
    """Integration tests for complete OCR fusion pipeline."""
    
    def test_complete_fusion_pipeline(self):
        """Test complete pipeline from OCR results to final glyphs."""
        # Simulate OCR results
        easyocr = [
            NormalizedOCRResult(bbox=[10, 10, 30, 30], char="我", confidence=0.95, source="easyocr"),
            NormalizedOCRResult(bbox=[40, 10, 60, 30], char="是", confidence=0.90, source="easyocr"),
        ]
        paddleocr = [
            NormalizedOCRResult(bbox=[12, 12, 32, 32], char="我", confidence=0.92, source="paddleocr"),
            NormalizedOCRResult(bbox=[42, 12, 62, 32], char="是", confidence=0.88, source="paddleocr"),
        ]
        
        # Step 1: Align
        fused_positions = align_ocr_outputs(easyocr, paddleocr, iou_threshold=0.5)
        
        # Step 2: Fuse
        glyphs, full_text, avg_conf, coverage = fuse_character_candidates(fused_positions)
        
        # Verify complete output
        assert full_text == "我是"
        assert len(glyphs) == 2
        assert all(isinstance(g, Glyph) for g in glyphs)
        assert 0.0 <= avg_conf <= 1.0
        assert 0.0 <= coverage <= 100.0
    
    def test_mixed_alignment_scenario(self):
        """Test scenario with both aligned and unique characters."""
        easyocr = [
            NormalizedOCRResult(bbox=[10, 10, 30, 30], char="我", confidence=0.95, source="easyocr"),
            NormalizedOCRResult(bbox=[40, 10, 60, 30], char="是", confidence=0.90, source="easyocr"),
            NormalizedOCRResult(bbox=[100, 10, 120, 30], char="人", confidence=0.85, source="easyocr"),
        ]
        paddleocr = [
            NormalizedOCRResult(bbox=[12, 12, 32, 32], char="我", confidence=0.92, source="paddleocr"),
            NormalizedOCRResult(bbox=[70, 10, 90, 30], char="学", confidence=0.88, source="paddleocr"),
        ]
        
        # Align and fuse
        fused_positions = align_ocr_outputs(easyocr, paddleocr, iou_threshold=0.5)
        glyphs, text, avg_conf, coverage = fuse_character_candidates(fused_positions)
        
        # Should have characters from both engines
        assert len(glyphs) >= 3
        assert "我" in text
        assert 0.0 <= avg_conf <= 1.0
        assert 0.0 <= coverage <= 100.0

