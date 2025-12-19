"""
Comprehensive unit and integration tests for QwenAdapter (Phase 6 Steps 4-8).

Tests cover:
- Locked token preservation
- Phrase-level refinement
- Glyph → English token alignment mapping
- Semantic confidence metrics
- Fallback behavior
- Integration with MarianAdapter
- Qwen fluency improvement
"""

import pytest
from unittest.mock import Mock, patch

from qwen_adapter import (
    QwenAdapter,
    QwenAdapterInput,
    QwenAdapterOutput,
    get_qwen_adapter,
)
from qwen_refiner import QwenRefiner
from marian_adapter import MarianAdapterOutput, PhraseSpan
from ocr_fusion import Glyph


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_qwen_refiner():
    """Create a mock QwenRefiner that simulates refinement behavior."""
    refiner = Mock(spec=QwenRefiner)
    refiner.is_available.return_value = True
    
    def refine_side_effect(nmt_translation: str, ocr_text: str = "") -> str:
        """Simulate Qwen refinement."""
        # If placeholders exist, preserve them (simulating locked token behavior)
        if "__LOCK_" in nmt_translation:
            # Placeholders should survive Qwen processing
            return nmt_translation
        
        # Otherwise, simulate minor refinement
        # Change "hello" to "Hello" (capitalization)
        # Change "world" to "world!" (punctuation)
        refined = nmt_translation.replace("hello", "Hello")
        refined = refined.replace("world", "world!")
        return refined
    
    refiner.refine_translation_with_qwen.side_effect = refine_side_effect
    return refiner


@pytest.fixture
def unavailable_qwen_refiner():
    """Create a mock QwenRefiner that is unavailable."""
    refiner = Mock(spec=QwenRefiner)
    refiner.is_available.return_value = False
    return refiner


@pytest.fixture
def failing_qwen_refiner():
    """Create a mock QwenRefiner that raises exceptions."""
    refiner = Mock(spec=QwenRefiner)
    refiner.is_available.return_value = True
    refiner.refine_translation_with_qwen.side_effect = Exception("Qwen refinement failed")
    return refiner


@pytest.fixture
def sample_glyphs():
    """Create sample glyphs for testing."""
    return [
        Glyph(symbol="你", bbox=[0, 0, 10, 10], confidence=0.95, meaning=None),   # High confidence
        Glyph(symbol="好", bbox=[10, 0, 20, 10], confidence=0.92, meaning=None),  # High confidence
        Glyph(symbol="世", bbox=[20, 0, 30, 10], confidence=0.60, meaning=None),   # Low confidence
        Glyph(symbol="界", bbox=[30, 0, 40, 10], confidence=0.55, meaning=None),   # Low confidence
    ]


@pytest.fixture
def sample_marian_output():
    """Create sample MarianAdapterOutput for integration testing."""
    return MarianAdapterOutput(
        translation="Hello world test",
        locked_tokens=[0, 1],  # Chinese glyph indices
        preserved_tokens=[2, 3],
        changed_tokens=[],
        semantic_confidence=0.85,
        metadata={
            "engine": "MarianMT",
            "tokens_modified_percent": 0.0,
            "tokens_locked_percent": 50.0,
        }
    )


# ============================================================================
# STEP 4: TOKEN LOCKING TESTS
# ============================================================================

class TestTokenLocking:
    """Tests for token locking enforcement (Step 4)."""
    
    def test_locked_tokens_preserved_basic(self, mock_qwen_refiner, sample_glyphs):
        """Test that locked tokens are preserved through Qwen refinement."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        input_data = QwenAdapterInput(
            text="hello world test",
            glyphs=sample_glyphs,
            locked_tokens=[0, 1],  # Chinese glyph indices
            english_locked_tokens=[0, 1],  # English token indices: "hello", "world"
            ocr_text="你好世界",
        )
        
        result = adapter.translate(input_data)
        
        assert result is not None, "QwenAdapter should return result"
        assert isinstance(result, QwenAdapterOutput), "Result should be QwenAdapterOutput"
        assert result.refined_text is not None, "Refined text should exist"
        
        # Verify locked tokens are preserved (they should be in preserved_tokens)
        assert 0 in result.preserved_tokens or 0 in result.locked_tokens, \
            "Locked token 0 should be preserved"
        assert 1 in result.preserved_tokens or 1 in result.locked_tokens, \
            "Locked token 1 should be preserved"
        
        # Verify metadata indicates token locking
        assert result.metadata["token_locking_enabled"] is True, \
            "Token locking should be enabled"
        assert result.metadata["locked_tokens_count"] == 2, \
            "Should have 2 locked tokens"
    
    def test_no_locked_tokens_all_modifiable(self, mock_qwen_refiner, sample_glyphs):
        """Test behavior when no tokens are locked."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        input_data = QwenAdapterInput(
            text="hello world test",
            glyphs=sample_glyphs,
            locked_tokens=[],  # No locked tokens
            english_locked_tokens=[],  # No locked English tokens
            ocr_text="你好世界",
        )
        
        result = adapter.translate(input_data)
        
        assert result is not None, "QwenAdapter should return result"
        assert result.metadata["token_locking_enabled"] is False, \
            "Token locking should be disabled when no locked tokens"
        assert result.metadata["locked_tokens_count"] == 0, \
            "Should have 0 locked tokens"
    
    def test_placeholder_replacement_and_restoration(self, mock_qwen_refiner):
        """Test that placeholders are correctly replaced and restored."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        text = "hello world test"
        locked_indices = [0, 2]  # Lock "hello" and "test"
        
        text_with_placeholders, placeholder_map = adapter._replace_locked_with_placeholders(
            text, locked_indices
        )
        
        # Verify placeholders were created
        assert len(placeholder_map) == 2, "Should create 2 placeholders"
        assert "__LOCK_T0__" in placeholder_map, "Placeholder for token 0 should exist"
        assert "__LOCK_T2__" in placeholder_map, "Placeholder for token 2 should exist"
        assert placeholder_map["__LOCK_T0__"] == "hello", "Placeholder should map to 'hello'"
        assert placeholder_map["__LOCK_T2__"] == "test", "Placeholder should map to 'test'"
        
        # Verify text contains placeholders
        assert "__LOCK_T0__" in text_with_placeholders, "Text should contain placeholder"
        assert "__LOCK_T2__" in text_with_placeholders, "Text should contain placeholder"
        assert "world" in text_with_placeholders, "Unlocked token should remain"
        
        # Test restoration
        restored = adapter._restore_locked_tokens(text_with_placeholders, placeholder_map)
        assert restored == text, "Restored text should match original"
    
    def test_change_tracking_identifies_modified_tokens(self, mock_qwen_refiner):
        """Test that change tracking correctly identifies modified tokens."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        original = "hello world test"
        refined = "Hello world! test"  # Tokens 0 and 1 changed
        locked_indices = [2]  # Token 2 ("test") is locked
        
        changed, preserved = adapter._track_qwen_changes(original, refined, locked_indices)
        
        # Token 0 should be in changed (capitalization change)
        assert 0 in changed, "Token 0 should be marked as changed"
        
        # Token 1 should be in changed (punctuation change)
        assert 1 in changed, "Token 1 should be marked as changed"
        
        # Token 2 should be in preserved (locked)
        assert 2 in preserved, "Locked token 2 should be preserved"
        assert 2 not in changed, "Locked token 2 should not be in changed"
    
    def test_locked_tokens_not_in_changed_list(self, mock_qwen_refiner, sample_glyphs):
        """Test that locked tokens never appear in changed_tokens list."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        input_data = QwenAdapterInput(
            text="hello world test",
            glyphs=sample_glyphs,
            locked_tokens=[0, 1],
            english_locked_tokens=[0, 1],  # Lock "hello" and "world"
            ocr_text="你好世界",
        )
        
        result = adapter.translate(input_data)
        
        assert result is not None, "QwenAdapter should return result"
        
        # Locked tokens should not be in changed_tokens
        locked_set = set(result.locked_tokens)
        changed_set = set(result.changed_tokens)
        assert len(locked_set & changed_set) == 0, \
            "Locked tokens should never appear in changed_tokens"


# ============================================================================
# STEP 5: PHRASE-LEVEL REFINEMENT TESTS
# ============================================================================

class TestPhraseLevelRefinement:
    """Tests for phrase-level refinement (Step 5)."""
    
    def test_map_glyphs_to_english_tokens_basic(self, mock_qwen_refiner, sample_glyphs):
        """Test basic glyph → English token mapping."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        english_tokens = ["Hello", "world", "test"]
        locked_glyph_indices = [0, 1]  # Lock first 2 glyphs
        
        glyph_to_tokens, locked_english = adapter._map_glyphs_to_english_tokens(
            glyphs=sample_glyphs,
            english_tokens=english_tokens,
            locked_glyph_indices=locked_glyph_indices,
        )
        
        # Verify mapping structure
        assert isinstance(glyph_to_tokens, dict), "Should return dict"
        assert isinstance(locked_english, list), "Should return list"
        
        # Verify locked English tokens are derived from locked glyphs
        assert len(locked_english) > 0, "Should have locked English tokens"
        assert all(isinstance(idx, int) for idx in locked_english), \
            "Locked English tokens should be integers"
    
    def test_map_glyphs_to_english_tokens_empty_inputs(self, mock_qwen_refiner):
        """Test mapping with empty inputs."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        glyph_to_tokens, locked_english = adapter._map_glyphs_to_english_tokens(
            glyphs=[],
            english_tokens=[],
            locked_glyph_indices=[],
        )
        
        assert isinstance(glyph_to_tokens, dict), "Should return dict"
        assert isinstance(locked_english, list), "Should return list"
        assert len(glyph_to_tokens) == 0, "Should have no mappings"
        assert len(locked_english) == 0, "Should have no locked tokens"
    
    def test_identify_phrase_spans_basic(self, mock_qwen_refiner):
        """Test basic phrase span identification."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        english_tokens = ["Hello", "world", "test", "example"]
        locked_english_tokens = [0, 1]  # First 2 tokens locked
        glyph_to_tokens = {0: [0, 1], 1: [2], 2: [3]}  # Simplified mapping
        
        phrase_spans = adapter._identify_phrase_spans(
            english_tokens=english_tokens,
            locked_english_tokens=locked_english_tokens,
            glyph_to_tokens=glyph_to_tokens,
        )
        
        assert isinstance(phrase_spans, list), "Should return list"
        assert len(phrase_spans) > 0, "Should identify at least one phrase span"
        
        # Verify PhraseSpan structure
        for span in phrase_spans:
            assert isinstance(span, PhraseSpan), "Should be PhraseSpan object"
            assert hasattr(span, 'start_idx'), "Should have start_idx"
            assert hasattr(span, 'end_idx'), "Should have end_idx"
            assert hasattr(span, 'is_locked'), "Should have is_locked"
            assert hasattr(span, 'text'), "Should have text"
            assert span.start_idx < span.end_idx, "start_idx should be < end_idx"
    
    def test_identify_phrase_spans_all_locked(self, mock_qwen_refiner):
        """Test phrase span identification when all tokens are locked."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        english_tokens = ["Hello", "world"]
        locked_english_tokens = [0, 1]  # All tokens locked
        glyph_to_tokens = {0: [0], 1: [1]}
        
        phrase_spans = adapter._identify_phrase_spans(
            english_tokens=english_tokens,
            locked_english_tokens=locked_english_tokens,
            glyph_to_tokens=glyph_to_tokens,
        )
        
        assert len(phrase_spans) > 0, "Should identify at least one phrase span"
        # All spans should be locked
        assert all(span.is_locked for span in phrase_spans), \
            "All phrase spans should be locked"
    
    def test_identify_phrase_spans_all_unlocked(self, mock_qwen_refiner):
        """Test phrase span identification when no tokens are locked."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        english_tokens = ["Hello", "world", "test"]
        locked_english_tokens = []  # No locked tokens
        glyph_to_tokens = {0: [0], 1: [1], 2: [2]}
        
        phrase_spans = adapter._identify_phrase_spans(
            english_tokens=english_tokens,
            locked_english_tokens=locked_english_tokens,
            glyph_to_tokens=glyph_to_tokens,
        )
        
        assert len(phrase_spans) > 0, "Should identify at least one phrase span"
        # All spans should be unlocked
        assert all(not span.is_locked for span in phrase_spans), \
            "All phrase spans should be unlocked"
    
    def test_refine_phrases_placeholder(self, mock_qwen_refiner):
        """Test that _refine_phrases is a placeholder (returns original text)."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        phrase_spans = [
            PhraseSpan(start_idx=0, end_idx=2, is_locked=False, text="Hello world", glyph_indices=[0, 1]),
            PhraseSpan(start_idx=2, end_idx=3, is_locked=True, text="test", glyph_indices=[2]),
        ]
        english_tokens = ["Hello", "world", "test"]
        
        result = adapter._refine_phrases(phrase_spans, english_tokens)
        
        assert isinstance(result, str), "Should return string"
        assert result == "Hello world test", "Should return original text (placeholder)"
    
    def test_phrase_spans_in_metadata(self, mock_qwen_refiner, sample_glyphs):
        """Test that phrase spans are included in output metadata."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        input_data = QwenAdapterInput(
            text="Hello world test example",
            glyphs=sample_glyphs,
            locked_tokens=[0, 1],
            english_locked_tokens=[0, 1],
            ocr_text="你好世界",
        )
        
        result = adapter.translate(input_data)
        
        assert result is not None, "QwenAdapter should return result"
        assert "phrase_spans_count" in result.metadata, \
            "Metadata should include phrase_spans_count"
        assert "locked_phrases_count" in result.metadata, \
            "Metadata should include locked_phrases_count"
        assert "unlocked_phrases_count" in result.metadata, \
            "Metadata should include unlocked_phrases_count"
        
        assert isinstance(result.metadata["phrase_spans_count"], int), \
            "phrase_spans_count should be int"
        assert result.metadata["phrase_spans_count"] >= 0, \
            "phrase_spans_count should be non-negative"


# ============================================================================
# STEP 6: SEMANTIC CONFIDENCE METRICS TESTS
# ============================================================================

class TestSemanticConfidence:
    """Tests for semantic confidence calculation (Step 6)."""
    
    def test_calculate_qwen_confidence_basic(self, mock_qwen_refiner):
        """Test basic semantic confidence calculation."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        original_text = "Hello world test"
        refined_text = "Hello world! test"
        locked_tokens = [0]  # Token 0 locked
        phrase_spans = [
            PhraseSpan(start_idx=0, end_idx=1, is_locked=True, text="Hello", glyph_indices=[0]),
            PhraseSpan(start_idx=1, end_idx=3, is_locked=False, text="world test", glyph_indices=[1, 2]),
        ]
        changed_tokens = [1]  # Token 1 changed
        preserved_tokens = [0, 2]  # Tokens 0 and 2 preserved
        
        confidence, factors = adapter._calculate_qwen_confidence(
            original_text=original_text,
            refined_text=refined_text,
            locked_tokens=locked_tokens,
            phrase_spans=phrase_spans,
            changed_tokens=changed_tokens,
            preserved_tokens=preserved_tokens,
        )
        
        assert isinstance(confidence, float), "Confidence should be float"
        assert 0.0 <= confidence <= 1.0, "Confidence should be in [0.0, 1.0]"
        
        assert isinstance(factors, dict), "Factors should be dict"
        assert "locked_preservation_rate" in factors, \
            "Factors should include locked_preservation_rate"
        assert "modification_ratio" in factors, \
            "Factors should include modification_ratio"
        assert "unlocked_stability" in factors, \
            "Factors should include unlocked_stability"
        assert "phrase_score" in factors, \
            "Factors should include phrase_score"
    
    def test_calculate_qwen_confidence_perfect_preservation(self, mock_qwen_refiner):
        """Test confidence calculation when all tokens are preserved."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        original_text = "Hello world test"
        refined_text = "Hello world test"  # No changes
        locked_tokens = [0, 1, 2]  # All tokens locked
        phrase_spans = [
            PhraseSpan(start_idx=0, end_idx=3, is_locked=True, text="Hello world test", glyph_indices=[0, 1, 2]),
        ]
        changed_tokens = []  # No changes
        preserved_tokens = [0, 1, 2]  # All preserved
        
        confidence, factors = adapter._calculate_qwen_confidence(
            original_text=original_text,
            refined_text=refined_text,
            locked_tokens=locked_tokens,
            phrase_spans=phrase_spans,
            changed_tokens=changed_tokens,
            preserved_tokens=preserved_tokens,
        )
        
        # Perfect preservation should yield high confidence
        assert confidence >= 0.8, "Perfect preservation should yield high confidence"
        assert factors["locked_preservation_rate"] == 1.0, \
            "Locked preservation rate should be 1.0"
        assert factors["modification_ratio"] == 0.0, \
            "Modification ratio should be 0.0"
    
    def test_calculate_qwen_confidence_no_locked_tokens(self, mock_qwen_refiner):
        """Test confidence calculation when no tokens are locked."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        original_text = "Hello world test"
        refined_text = "Hello world! test"  # Some changes
        locked_tokens = []  # No locked tokens
        phrase_spans = [
            PhraseSpan(start_idx=0, end_idx=3, is_locked=False, text="Hello world test", glyph_indices=[0, 1, 2]),
        ]
        changed_tokens = [1]  # Token 1 changed
        preserved_tokens = [0, 2]  # Tokens 0 and 2 preserved
        
        confidence, factors = adapter._calculate_qwen_confidence(
            original_text=original_text,
            refined_text=refined_text,
            locked_tokens=locked_tokens,
            phrase_spans=phrase_spans,
            changed_tokens=changed_tokens,
            preserved_tokens=preserved_tokens,
        )
        
        assert isinstance(confidence, float), "Confidence should be float"
        assert 0.0 <= confidence <= 1.0, "Confidence should be in [0.0, 1.0]"
        # When no locked tokens, locked_preservation_rate should be 1.0 (perfect)
        assert factors["locked_preservation_rate"] == 1.0, \
            "No locked tokens should yield perfect preservation rate"
    
    def test_qwen_confidence_in_output(self, mock_qwen_refiner, sample_glyphs):
        """Test that qwen_confidence is included in output."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        input_data = QwenAdapterInput(
            text="Hello world test",
            glyphs=sample_glyphs,
            locked_tokens=[0, 1],
            english_locked_tokens=[0, 1],
            ocr_text="你好世界",
        )
        
        result = adapter.translate(input_data)
        
        assert result is not None, "QwenAdapter should return result"
        assert hasattr(result, 'qwen_confidence'), \
            "Output should have qwen_confidence attribute"
        assert isinstance(result.qwen_confidence, float), \
            "qwen_confidence should be float"
        assert 0.0 <= result.qwen_confidence <= 1.0, \
            "qwen_confidence should be in [0.0, 1.0]"
        
        # Verify confidence factors in metadata
        assert "qwen_locked_preservation_rate" in result.metadata, \
            "Metadata should include qwen_locked_preservation_rate"
        assert "qwen_modification_ratio" in result.metadata, \
            "Metadata should include qwen_modification_ratio"
        assert "qwen_unlocked_stability" in result.metadata, \
            "Metadata should include qwen_unlocked_stability"
        assert "qwen_phrase_score" in result.metadata, \
            "Metadata should include qwen_phrase_score"


# ============================================================================
# FALLBACK BEHAVIOR TESTS
# ============================================================================

class TestFallbackBehavior:
    """Tests for fallback behavior when QwenRefiner is unavailable or fails."""
    
    def test_unavailable_qwen_refiner_returns_none(self, unavailable_qwen_refiner, sample_glyphs):
        """Test that adapter returns None when QwenRefiner is unavailable."""
        adapter = QwenAdapter(qwen_refiner=unavailable_qwen_refiner)
        
        input_data = QwenAdapterInput(
            text="Hello world test",
            glyphs=sample_glyphs,
            locked_tokens=[],
            ocr_text="你好世界",
        )
        
        result = adapter.translate(input_data)
        
        assert result is None, "Should return None when QwenRefiner is unavailable"
    
    def test_failing_qwen_refiner_returns_none(self, failing_qwen_refiner, sample_glyphs):
        """Test that adapter returns None when QwenRefiner raises exception."""
        adapter = QwenAdapter(qwen_refiner=failing_qwen_refiner)
        
        input_data = QwenAdapterInput(
            text="Hello world test",
            glyphs=sample_glyphs,
            locked_tokens=[],
            ocr_text="你好世界",
        )
        
        result = adapter.translate(input_data)
        
        assert result is None, "Should return None when QwenRefiner fails"
    
    def test_empty_text_returns_none(self, mock_qwen_refiner, sample_glyphs):
        """Test that adapter returns None when input text is empty."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        input_data = QwenAdapterInput(
            text="",  # Empty text
            glyphs=sample_glyphs,
            locked_tokens=[],
            ocr_text="你好世界",
        )
        
        result = adapter.translate(input_data)
        
        assert result is None, "Should return None when text is empty"
    
    def test_qwen_refiner_returns_none_handled(self, mock_qwen_refiner, sample_glyphs):
        """Test that adapter handles QwenRefiner returning None gracefully."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        # Clear side_effect and set return_value to None
        mock_qwen_refiner.refine_translation_with_qwen.side_effect = None
        mock_qwen_refiner.refine_translation_with_qwen.return_value = None
        
        input_data = QwenAdapterInput(
            text="Hello world test",
            glyphs=sample_glyphs,
            locked_tokens=[],
            ocr_text="你好世界",
        )
        
        result = adapter.translate(input_data)
        
        assert result is None, "Should return None when QwenRefiner returns None"
    
    def test_is_available_delegates_to_refiner(self, mock_qwen_refiner):
        """Test that is_available() delegates to QwenRefiner."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        assert adapter.is_available() is True, "Should be available when refiner is available"
        
        mock_qwen_refiner.is_available.return_value = False
        assert adapter.is_available() is False, "Should be unavailable when refiner is unavailable"
    
    def test_is_available_with_none_refiner(self):
        """Test that is_available() returns False when refiner is None."""
        # Create adapter with explicit None refiner (bypassing get_qwen_refiner call)
        # We need to patch get_qwen_refiner to return None
        with patch('qwen_adapter.get_qwen_refiner', return_value=None):
            adapter = QwenAdapter(qwen_refiner=None)
            assert adapter.is_available() is False, "Should be unavailable when refiner is None"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Tests for integration with MarianAdapter and full pipeline."""
    
    def test_integration_with_marian_output(self, mock_qwen_refiner, sample_glyphs, sample_marian_output):
        """Test that QwenAdapter works correctly with MarianAdapterOutput."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        # Build QwenAdapterInput from MarianAdapterOutput
        input_data = QwenAdapterInput(
            text=sample_marian_output.translation,
            glyphs=sample_glyphs,
            locked_tokens=sample_marian_output.locked_tokens,
            preserved_tokens=sample_marian_output.preserved_tokens,
            changed_tokens=sample_marian_output.changed_tokens,
            semantic_metadata=sample_marian_output.metadata,
            ocr_text="你好世界",
        )
        
        result = adapter.translate(input_data)
        
        assert result is not None, "QwenAdapter should return result"
        assert isinstance(result, QwenAdapterOutput), "Result should be QwenAdapterOutput"
        assert result.refined_text is not None, "Refined text should exist"
        
        # Verify that locked tokens from MarianAdapter are respected
        assert len(result.locked_tokens) > 0, \
            "Should have locked tokens from MarianAdapter"
    
    def test_full_pipeline_metadata(self, mock_qwen_refiner, sample_glyphs):
        """Test that output metadata includes all expected fields."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        input_data = QwenAdapterInput(
            text="Hello world test",
            glyphs=sample_glyphs,
            locked_tokens=[0, 1],
            english_locked_tokens=[0, 1],
            ocr_text="你好世界",
        )
        
        result = adapter.translate(input_data)
        
        assert result is not None, "QwenAdapter should return result"
        
        # Verify all expected metadata fields
        expected_fields = [
            "step", "phase", "refinement_enabled", "token_locking_enabled",
            "phrase_refinement_enabled", "semantic_confidence_enabled",
            "locked_tokens_count", "changed_tokens_count", "preserved_tokens_count",
            "phrase_spans_count", "locked_phrases_count", "unlocked_phrases_count",
            "qwen_locked_preservation_rate", "qwen_modification_ratio",
            "qwen_unlocked_stability", "qwen_phrase_score",
        ]
        
        for field in expected_fields:
            assert field in result.metadata, \
                f"Metadata should include {field}"
    
    def test_to_dict_method(self, mock_qwen_refiner, sample_glyphs):
        """Test that QwenAdapterOutput.to_dict() works correctly."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        input_data = QwenAdapterInput(
            text="Hello world test",
            glyphs=sample_glyphs,
            locked_tokens=[0, 1],
            english_locked_tokens=[0, 1],
            ocr_text="你好世界",
        )
        
        result = adapter.translate(input_data)
        
        assert result is not None, "QwenAdapter should return result"
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict), "to_dict() should return dict"
        assert "refined_text" in result_dict, "Should include refined_text"
        assert "changed_tokens" in result_dict, "Should include changed_tokens"
        assert "preserved_tokens" in result_dict, "Should include preserved_tokens"
        assert "locked_tokens" in result_dict, "Should include locked_tokens"
        assert "qwen_confidence" in result_dict, "Should include qwen_confidence"
        assert "metadata" in result_dict, "Should include metadata"


# ============================================================================
# FACTORY FUNCTION TESTS
# ============================================================================

class TestFactoryFunction:
    """Tests for get_qwen_adapter() factory function."""
    
    def test_get_qwen_adapter_creates_instance(self, mock_qwen_refiner):
        """Test that get_qwen_adapter() creates an instance."""
        adapter = get_qwen_adapter(qwen_refiner=mock_qwen_refiner)
        
        assert adapter is not None, "Should create adapter instance"
        assert isinstance(adapter, QwenAdapter), "Should be QwenAdapter instance"
    
    def test_get_qwen_adapter_returns_none_when_unavailable(self, unavailable_qwen_refiner):
        """Test that get_qwen_adapter() returns None when refiner is unavailable."""
        adapter = get_qwen_adapter(qwen_refiner=unavailable_qwen_refiner)
        
        assert adapter is None, "Should return None when refiner is unavailable"
    
    def test_get_qwen_adapter_singleton_pattern(self, mock_qwen_refiner):
        """Test that get_qwen_adapter() follows singleton pattern."""
        # Reset singleton
        from qwen_adapter import _qwen_adapter_instance
        import qwen_adapter as qa_module
        qa_module._qwen_adapter_instance = None
        
        # When qwen_refiner is None, should use singleton pattern
        with patch('qwen_adapter.get_qwen_refiner', return_value=mock_qwen_refiner):
            adapter1 = get_qwen_adapter(qwen_refiner=None)
            adapter2 = get_qwen_adapter(qwen_refiner=None)
            
            # When refiner is None, should return same instance (singleton)
            assert adapter1 is adapter2, "Should return same instance (singleton)"
        
        # Reset singleton again
        qa_module._qwen_adapter_instance = None
        
        # When qwen_refiner is explicitly provided, creates new instance each time
        adapter3 = get_qwen_adapter(qwen_refiner=mock_qwen_refiner)
        adapter4 = get_qwen_adapter(qwen_refiner=mock_qwen_refiner)
        
        # When refiner is explicitly provided, should create new instance
        # (This is expected behavior - explicit refiner bypasses singleton)
        assert adapter3 is not None, "Should create adapter instance"
        assert adapter4 is not None, "Should create adapter instance"


# ============================================================================
# EDGE CASES AND ERROR HANDLING TESTS
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_glyphs_list(self, mock_qwen_refiner):
        """Test behavior with empty glyphs list."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        input_data = QwenAdapterInput(
            text="Hello world test",
            glyphs=[],  # Empty glyphs
            locked_tokens=[],
            ocr_text="",
        )
        
        result = adapter.translate(input_data)
        
        # Should still work (glyphs are optional for basic refinement)
        assert result is not None, "Should handle empty glyphs list"
    
    def test_single_token_text(self, mock_qwen_refiner, sample_glyphs):
        """Test behavior with single token text."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        input_data = QwenAdapterInput(
            text="Hello",  # Single token
            glyphs=sample_glyphs,
            locked_tokens=[0],
            english_locked_tokens=[0],
            ocr_text="你",
        )
        
        result = adapter.translate(input_data)
        
        assert result is not None, "Should handle single token text"
        assert result.refined_text is not None, "Refined text should exist"
    
    def test_very_long_text(self, mock_qwen_refiner, sample_glyphs):
        """Test behavior with very long text."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        long_text = " ".join(["Hello"] * 100)  # 100 tokens
        input_data = QwenAdapterInput(
            text=long_text,
            glyphs=sample_glyphs,
            locked_tokens=[0],
            english_locked_tokens=[0],
            ocr_text="你好世界",
        )
        
        result = adapter.translate(input_data)
        
        assert result is not None, "Should handle very long text"
        assert result.refined_text is not None, "Refined text should exist"
    
    def test_all_tokens_locked(self, mock_qwen_refiner, sample_glyphs):
        """Test behavior when all tokens are locked."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        input_data = QwenAdapterInput(
            text="Hello world test",
            glyphs=sample_glyphs,
            locked_tokens=[0, 1, 2, 3],
            english_locked_tokens=[0, 1, 2],  # All tokens locked
            ocr_text="你好世界",
        )
        
        result = adapter.translate(input_data)
        
        assert result is not None, "Should handle all tokens locked"
        assert result.metadata["locked_tokens_count"] == 3, \
            "Should have 3 locked tokens"
        # All tokens should be preserved
        assert len(result.preserved_tokens) >= 3, \
            "All locked tokens should be preserved"
    
    def test_tokenization_handles_punctuation(self, mock_qwen_refiner):
        """Test that tokenization handles punctuation correctly."""
        adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
        
        text = "Hello, world! Test?"
        tokens = adapter._tokenize(text)
        
        assert isinstance(tokens, list), "Should return list"
        assert len(tokens) == 3, "Should tokenize into 3 tokens"
        assert "Hello," in tokens, "Should include punctuation with token"
        assert "world!" in tokens, "Should include punctuation with token"
        assert "Test?" in tokens, "Should include punctuation with token"

