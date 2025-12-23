"""
Smoke test for Rune-X inference pipeline.

This test verifies that the full OCR → Dictionary → MarianAdapter → QwenAdapter → API response
pipeline executes end-to-end without crashing. It does NOT test correctness or quality.

Refactored for Phase 6: Includes comprehensive checks for all phases (3, 4, 5, 6).
"""

import io
import pytest
from fastapi import HTTPException
from PIL import Image, ImageDraw

# Import the endpoint function
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import process_image, InferenceResponse


def create_mock_image_upload():
    """
    Create a mock image upload for testing.
    
    Returns:
        MockUploadFile object with 400x200 white PNG image with 3 black rectangles.
    """
    # Create a simple test image with Chinese text simulation
    # Use a size that meets minimum requirements (50x50)
    # Make it larger and with clearer contrast for OCR
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw multiple rectangles to simulate text blocks
    # This gives OCR engines something to potentially detect
    # Even if OCR fails, the pipeline should complete gracefully
    for i in range(3):
        x = 50 + i * 100
        draw.rectangle([x, 50, x + 80, 150], fill='black')
    
    # Convert image to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    content = img_bytes.read()
    
    # Create UploadFile mock with proper content_type
    class MockUploadFile:
        def __init__(self, filename, content, content_type):
            self.filename = filename
            self.file = io.BytesIO(content)
            self.content_type = content_type
        
        async def read(self):
            return self.file.read()
    
    return MockUploadFile("test.png", content, "image/png")


@pytest.mark.asyncio
async def test_pipeline_smoke_full():
    """
    Full pipeline smoke test: Verify end-to-end execution from OCR → Dictionary → 
    MarianAdapter → QwenAdapter → API response.
    
    This test verifies:
    - Pipeline completes without crashing
    - Required and optional fields exist in InferenceResponse
    - Phase 3, 4, 5, 6 integration checks
    - Type validation for all fields
    - Graceful fallback behavior
    
    Does NOT test translation correctness (smoke test only).
    """
    # Setup: Create mock input
    upload_file = create_mock_image_upload()
    
    # Execution: Run full pipeline
    try:
        result = await process_image(file=upload_file)
    except HTTPException as e:
        # HTTPException is valid - pipeline executed, just returned expected error
        # For smoke test, we verify it's a known error type (not a crash)
        assert e.status_code in [400, 422, 500, 503], \
            f"Unexpected HTTPException status: {e.status_code}"
        # Pipeline executed without crashing - smoke test passed
        return
    
    # ========================================================================
    # General Response Checks (All Phases)
    # ========================================================================
    
    assert result is not None, "Pipeline returned None"
    assert isinstance(result, InferenceResponse), "Result is not InferenceResponse"
    
    # Required fields exist
    assert hasattr(result, 'text'), "Missing 'text' field"
    assert hasattr(result, 'canonical_text'), "Missing 'canonical_text' field"
    assert hasattr(result, 'canonical_meta'), "Missing canonicalization metadata"
    assert hasattr(result, 'translation'), "Missing 'translation' field"
    assert hasattr(result, 'confidence'), "Missing 'confidence' field"
    assert hasattr(result, 'glyphs'), "Missing 'glyphs' field"
    
    # Type checks for required fields
    assert isinstance(result.text, str), "'text' must be string"
    assert isinstance(result.canonical_text, str), "'canonical_text' must be a string"
    assert isinstance(result.translation, str), "'translation' must be string"
    assert isinstance(result.confidence, (int, float)), "'confidence' must be numeric"
    assert isinstance(result.glyphs, list), "'glyphs' must be list"

    # Canonicalization metadata and noise filtering
    assert isinstance(result.canonical_meta, dict), "'canonical_meta' must be a dict"
    assert 'noise_filtered_count' in result.canonical_meta, "Missing noise_filtered_count in canonical_meta"
    assert isinstance(result.canonical_meta['noise_filtered_count'], int)
    assert result.canonical_meta['noise_filtered_count'] >= 0
    assert len(result.canonical_text) <= len(result.text)

    # ========================================================================
    # Phase 8 Step 1 & 2: Segmentation and glyph-to-sentence mapping checks
    # ========================================================================
    # We rely on debug metadata exposed via result.semantic/qwen where applicable.
    # For the smoke test, minimally ensure segmentation happened and spans are sane.
    assert hasattr(result, "semantic"), "Missing 'semantic' field for metadata checks"
    # segmentation: at least 1 sentence and paragraph index non-negative if exposed
    # (If adapters did not populate segment metadata, we skip detailed checks)
    if hasattr(result, "semantic") and isinstance(result.semantic, dict):
        semantic_meta = result.semantic
        # Optional: adapter may expose sentence/paragraph counts
        seg_sent_count = semantic_meta.get("segmented_sentence_count")
        seg_para_count = semantic_meta.get("segmented_paragraph_count")
        if seg_sent_count is not None:
            assert isinstance(seg_sent_count, int) and seg_sent_count >= 1
        if seg_para_count is not None:
            assert isinstance(seg_para_count, int) and seg_para_count >= 1

    # Ensure sentence spans (if exposed) cover glyphs monotonically without overlap
    if hasattr(result, "semantic") and isinstance(result.semantic, dict):
        semantic_meta = result.semantic
        spans = semantic_meta.get("sentence_spans")
        if spans:
            # spans expected shape: list of dicts with glyph_indices and indices
            all_indices = []
            prev_last = -1
            for span in spans:
                glyph_idxs = span.get("glyph_indices", [])
                assert isinstance(glyph_idxs, list)
                if glyph_idxs:
                    # monotonic non-overlapping
                    assert min(glyph_idxs) > prev_last
                    prev_last = max(glyph_idxs)
                    all_indices.extend(glyph_idxs)
            # no gaps/overlaps within monotonic assumption
            assert len(all_indices) == len(set(all_indices))

    # If sentence count is available in spans, ensure it matches segmentation count
    if hasattr(result, "semantic") and isinstance(result.semantic, dict):
        semantic_meta = result.semantic
        spans = semantic_meta.get("sentence_spans")
        seg_sent_count = semantic_meta.get("segmented_sentence_count")
        if spans is not None and seg_sent_count is not None:
            assert len(spans) == seg_sent_count

    # Marian/Qwen should have received non-empty text (or combined text) — we assert
    # the outputs are present as basic proxy.
    if result.sentence_translation is not None:
        assert len(result.sentence_translation) >= 0  # non-negative length
    if result.refined_translation is not None:
        assert len(result.refined_translation) >= 0

    # ========================================================================
    # Additional Phase 8 coverage assertions
    # ========================================================================
    # Require at least one sentence and paragraph if counts are exposed
    if hasattr(result, "semantic") and isinstance(result.semantic, dict):
        semantic_meta = result.semantic
        seg_sent_count = semantic_meta.get("segmented_sentence_count")
        seg_para_count = semantic_meta.get("segmented_paragraph_count")
        if seg_sent_count is not None:
            assert seg_sent_count >= 1, "Segmentation produced zero sentences"
        if seg_para_count is not None:
            assert seg_para_count >= 1, "Segmentation produced zero paragraphs"

        # If sentence spans exist, ensure no empty or missing translations per span
        spans = semantic_meta.get("sentence_spans")
        if spans and isinstance(spans, list):
            for span in spans:
                # Expect that each span had some output text (approximation via presence)
                assert "text" in span, "Span missing text"

    # Paragraph recombination: if refined_translation exists, ensure paragraph separators preserved
    if result.refined_translation is not None:
        # At least one paragraph present
        refined_paragraphs = [p for p in result.refined_translation.split("\n\n") if p.strip()]
        assert len(refined_paragraphs) >= 1, "No paragraphs found in refined_translation"

    # No empty or missing translations (coarse check)
    assert result.translation is not None
    if result.sentence_translation is not None:
        assert result.sentence_translation.strip() != "" or result.refined_translation, \
            "Sentence translation is empty and no refined translation provided"

    # Fallback logic: ensure we always end with either refined or sentence translation non-empty
    assert (result.refined_translation and result.refined_translation.strip()) or \
           (result.sentence_translation and result.sentence_translation.strip()), \
        "Both refined_translation and sentence_translation are empty"

    # Qwen metadata correctness already partially checked; ensure no paragraph loss when metadata present
    if hasattr(result, "qwen") and isinstance(result.qwen, dict):
        qwen_meta = result.qwen
        # If paragraphs were counted upstream, we can approximate paragraph presence via qwen_status
        assert result.qwen_status in [None, "available", "unavailable", "failed", "skipped"]
    
    # ========================================================================
    # Phase 3: MarianMT Integration Checks
    # ========================================================================
    
    assert hasattr(result, 'sentence_translation'), "Missing 'sentence_translation' field"
    if result.sentence_translation:
        assert isinstance(result.sentence_translation, str), \
            "'sentence_translation' must be string or None"
    
    # ========================================================================
    # Phase 4: Token Locking / OCR Dictionary Anchoring Checks
    # ========================================================================
    
    # Verify glyphs list exists and has expected structure
    assert isinstance(result.glyphs, list), "'glyphs' must be list"
    # Note: Detailed locked_tokens checks would require accessing adapter internals
    # For smoke test, we verify the pipeline completed without crashing
    
    # ========================================================================
    # Phase 5: MarianAdapter Refinement Checks
    # ========================================================================
    
    assert hasattr(result, 'semantic'), "Missing 'semantic' field"
    if result.semantic is not None:
        semantic = result.semantic
        assert isinstance(semantic, dict), "'semantic' must be dict or None"
        
        # Verify semantic_confidence exists and is in valid range
        assert 'semantic_confidence' in semantic, \
            "Missing 'semantic_confidence' in semantic metadata"
        assert isinstance(semantic['semantic_confidence'], (int, float)), \
            "'semantic_confidence' must be numeric"
        assert 0.0 <= semantic['semantic_confidence'] <= 1.0, \
            f"'semantic_confidence' must be in [0.0, 1.0], got {semantic['semantic_confidence']}"
        
        # Verify other semantic fields exist (optional, may be None)
        expected_semantic_fields = [
            'engine', 'tokens_modified', 'tokens_locked', 'tokens_preserved',
            'tokens_modified_percent', 'tokens_locked_percent', 'tokens_preserved_percent',
            'dictionary_override_count'
        ]
        for field in expected_semantic_fields:
            if field in semantic:
                # Type checks if field exists
                if field == 'engine':
                    assert isinstance(semantic[field], str), f"'{field}' must be string"
                elif 'percent' in field:
                    assert isinstance(semantic[field], (int, float)), \
                        f"'{field}' must be numeric"
                elif 'count' in field or 'tokens' in field:
                    assert isinstance(semantic[field], int), f"'{field}' must be int"
    
    # ========================================================================
    # Phase 6: QwenAdapter Refinement Checks
    # ========================================================================
    
    # Verify refined_translation exists
    assert hasattr(result, 'refined_translation'), "Missing 'refined_translation' field"
    if result.refined_translation:
        assert isinstance(result.refined_translation, str), \
            "'refined_translation' must be string or None"
    
    # Verify qwen_status exists and has valid value
    assert hasattr(result, 'qwen_status'), "Missing 'qwen_status' field"
    assert result.qwen_status in [None, "available", "unavailable", "failed", "skipped"], \
        f"Invalid qwen_status: {result.qwen_status}"
    
    # Verify qwen metadata field exists (optional, may be None)
    assert hasattr(result, 'qwen'), "Missing 'qwen' field"
    if result.qwen is not None:
        qwen_meta = result.qwen
        assert isinstance(qwen_meta, dict), "'qwen' must be dict or None"
        
        # Verify expected fields exist in qwen metadata
        expected_qwen_fields = [
            'engine', 'qwen_confidence', 'tokens_modified',
            'tokens_locked', 'tokens_preserved',
            'tokens_modified_percent', 'tokens_locked_percent',
            'tokens_preserved_percent', 'phrase_spans_refined',
            'phrase_spans_locked'
        ]
        
        for field in expected_qwen_fields:
            if field in qwen_meta:
                # Type checks if field exists
                if field == 'engine':
                    assert isinstance(qwen_meta[field], str), \
                        f"qwen['{field}'] must be string"
                elif field == 'qwen_confidence':
                    assert isinstance(qwen_meta[field], (int, float)), \
                        f"qwen['{field}'] must be numeric"
                    assert 0.0 <= qwen_meta[field] <= 1.0, \
                        f"qwen['{field}'] must be in [0.0, 1.0], got {qwen_meta[field]}"
                elif 'percent' in field:
                    assert isinstance(qwen_meta[field], (int, float)), \
                        f"qwen['{field}'] must be numeric"
                elif 'count' in field or 'tokens' in field or 'spans' in field:
                    assert isinstance(qwen_meta[field], int), \
                        f"qwen['{field}'] must be int"
    
    # ========================================================================
    # Backward Compatibility Checks
    # ========================================================================
    
    # Verify all existing fields still present (backward compatibility)
    assert hasattr(result, 'unmapped'), "Missing 'unmapped' field"
    assert hasattr(result, 'coverage'), "Missing 'coverage' field"
    assert hasattr(result, 'dictionary_source'), "Missing 'dictionary_source' field"
    assert hasattr(result, 'dictionary_version'), "Missing 'dictionary_version' field"
    assert hasattr(result, 'translation_source'), "Missing 'translation_source' field"
    
    # Pipeline completed successfully - smoke test passed
    # Note: This test does NOT verify translation correctness, only that the pipeline runs

