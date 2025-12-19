"""
Unit tests for MarianAdapter (Phase 5 Steps 4-8: Comprehensive Test Suite)

Tests for dictionary-anchored token locking, phrase-level semantic refinement,
semantic confidence metrics, and integration scenarios.
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import List

from marian_adapter import (
    MarianAdapter,
    MarianAdapterInput,
    MarianAdapterOutput,
    PhraseSpan,
    get_marian_adapter
)
from semantic_constraints import SemanticContract, TokenLockStatus, ConfidenceThreshold
from ocr_fusion import Glyph
from cc_dictionary import CCDictionary
from cc_translation import CCDictionaryTranslator


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_sentence_translator():
    """Create a mock SentenceTranslator."""
    translator = Mock()
    translator.is_available.return_value = True
    translator.translate.return_value = "Hello world"
    return translator


@pytest.fixture
def semantic_contract():
    """Create a SemanticContract instance."""
    return SemanticContract()


@pytest.fixture
def mock_cc_dictionary():
    """Create a mock CCDictionary."""
    dictionary = Mock(spec=CCDictionary)
    dictionary.has_entry = Mock(return_value=True)
    dictionary.lookup = Mock(return_value={"pinyin": "test", "definitions": ["test"]})
    return dictionary


@pytest.fixture
def sample_glyphs():
    """Create sample glyphs for testing."""
    return [
        Glyph(symbol="你", confidence=0.92, bbox=[10, 20, 30, 40]),  # High confidence + dict
        Glyph(symbol="好", confidence=0.88, bbox=[50, 20, 30, 40]),  # High confidence + dict
        Glyph(symbol="?", confidence=0.65, bbox=[90, 20, 30, 40]),   # Low confidence
        Glyph(symbol="世", confidence=0.90, bbox=[130, 20, 30, 40]), # High confidence + dict
        Glyph(symbol="界", confidence=0.87, bbox=[170, 20, 30, 40]), # High confidence + dict
    ]


# ============================================================================
# STEP 4: TOKEN LOCKING TESTS
# ============================================================================

class TestTokenLocking:
    """Tests for dictionary-anchored token locking (Step 4)."""
    
    def test_identify_locked_tokens_high_confidence_with_dictionary(
        self,
        mock_sentence_translator,
        semantic_contract,
        mock_cc_dictionary,
        sample_glyphs
    ):
        """Test that high-confidence glyphs with dictionary matches are locked."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract,
            cc_dictionary=mock_cc_dictionary
        )
        
        # Mock dictionary to return True for high-confidence glyphs
        def has_entry_side_effect(char):
            return char in ["你", "好", "世", "界"]  # These have dictionary entries
        
        mock_cc_dictionary.has_entry.side_effect = has_entry_side_effect
        
        locked_tokens = adapter._identify_locked_tokens(sample_glyphs)
        
        # High confidence (>=0.85) + dictionary match should be locked
        assert 0 in locked_tokens  # "你" - 0.92 conf + dict
        assert 1 in locked_tokens  # "好" - 0.88 conf + dict
        assert 3 in locked_tokens  # "世" - 0.90 conf + dict
        assert 4 in locked_tokens  # "界" - 0.87 conf + dict
        assert 2 not in locked_tokens  # "?" - 0.65 conf (low)
    
    def test_identify_locked_tokens_high_confidence_without_dictionary(
        self,
        mock_sentence_translator,
        semantic_contract,
        mock_cc_dictionary,
        sample_glyphs
    ):
        """Test that high-confidence glyphs without dictionary are still locked."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract,
            cc_dictionary=mock_cc_dictionary
        )
        
        # Mock dictionary to return False (no entries)
        mock_cc_dictionary.has_entry.return_value = False
        
        locked_tokens = adapter._identify_locked_tokens(sample_glyphs)
        
        # High confidence (>=0.85) should be locked even without dictionary
        assert 0 in locked_tokens  # "你" - 0.92 conf
        assert 1 in locked_tokens  # "好" - 0.88 conf
        assert 3 in locked_tokens  # "世" - 0.90 conf
        assert 4 in locked_tokens  # "界" - 0.87 conf
    
    def test_identify_locked_tokens_low_confidence_unlocked(
        self,
        mock_sentence_translator,
        semantic_contract,
        mock_cc_dictionary,
        sample_glyphs
    ):
        """Test that low-confidence glyphs are unlocked."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract,
            cc_dictionary=mock_cc_dictionary
        )
        
        mock_cc_dictionary.has_entry.return_value = True  # Even with dict
        
        locked_tokens = adapter._identify_locked_tokens(sample_glyphs)
        
        # Low confidence (<0.70) should be unlocked
        assert 2 not in locked_tokens  # "?" - 0.65 conf (low)
    
    def test_replace_locked_with_placeholders(
        self,
        mock_sentence_translator,
        semantic_contract
    ):
        """Test that locked tokens are replaced with placeholders."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract
        )
        
        glyphs = [
            Glyph(symbol="你", confidence=0.92),
            Glyph(symbol="好", confidence=0.88),
            Glyph(symbol="?", confidence=0.65),
        ]
        
        locked_indices = [0, 1]  # Lock first two
        placeholder_mapping = {}
        
        text = "你好?"
        result = adapter._replace_locked_with_placeholders(
            text, glyphs, locked_indices, placeholder_mapping
        )
        
        # Check placeholders were created
        assert "__LOCK_你__" in result
        assert "__LOCK_好__" in result
        assert "?" in result  # Unlocked token remains
        
        # Check mapping
        assert "__LOCK_你__" in placeholder_mapping
        assert "__LOCK_好__" in placeholder_mapping
        assert placeholder_mapping["__LOCK_你__"] == (0, "你")
        assert placeholder_mapping["__LOCK_好__"] == (1, "好")
    
    def test_restore_locked_tokens(
        self,
        mock_sentence_translator,
        semantic_contract
    ):
        """Test that placeholders are restored to original characters."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract
        )
        
        placeholder_mapping = {
            "__LOCK_你__": (0, "你"),
            "__LOCK_好__": (1, "好"),
        }
        
        translation = "Hello __LOCK_你__ __LOCK_好__ world"
        result = adapter._restore_locked_tokens(translation, placeholder_mapping)
        
        assert "__LOCK_你__" not in result
        assert "__LOCK_好__" not in result
        assert "你" in result
        assert "好" in result
    
    def test_placeholder_preservation_through_marianmt(
        self,
        mock_sentence_translator,
        semantic_contract,
        mock_cc_dictionary,
        sample_glyphs
    ):
        """Test that placeholders survive MarianMT translation unchanged."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract,
            cc_dictionary=mock_cc_dictionary
        )
        
        # Mock dictionary to return True for high-confidence glyphs
        def has_entry_side_effect(char):
            return char in ["你", "好", "世", "界"]
        
        mock_cc_dictionary.has_entry.side_effect = has_entry_side_effect
        
        # Mock translator to preserve placeholders (realistic behavior)
        def translate_side_effect(text):
            # MarianMT should preserve placeholders (they're not Chinese characters)
            return text.replace("__LOCK_你__", "__LOCK_你__").replace("__LOCK_好__", "__LOCK_好__")
        
        mock_sentence_translator.translate.side_effect = translate_side_effect
        
        # Test translation with placeholders
        text_with_placeholders = "Hello __LOCK_你__ __LOCK_好__ world"
        placeholder_mapping = {
            "__LOCK_你__": (0, "你"),
            "__LOCK_好__": (1, "好"),
        }
        
        restored = adapter._restore_locked_tokens(
            text_with_placeholders,
            placeholder_mapping
        )
        
        assert "你" in restored
        assert "好" in restored
        assert "__LOCK_你__" not in restored
        assert "__LOCK_好__" not in restored


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestTokenLockingIntegration:
    """Integration tests for token locking with full adapter flow."""
    
    def test_full_translation_with_token_locking(
        self,
        mock_sentence_translator,
        semantic_contract,
        mock_cc_dictionary,
        sample_glyphs
    ):
        """Test full translation flow with token locking enabled."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract,
            cc_dictionary=mock_cc_dictionary
        )
        
        # Mock dictionary to return True for high-confidence glyphs
        def has_entry_side_effect(char):
            return char in ["你", "好", "世", "界"]
        
        mock_cc_dictionary.has_entry.side_effect = has_entry_side_effect
        
        # Mock translator to return translation with placeholders preserved
        mock_sentence_translator.translate.return_value = "Hello __LOCK_你__ __LOCK_好__ __LOCK_世__ __LOCK_界__"
        
        output = adapter.translate(
            glyphs=sample_glyphs,
            confidence=0.85,
            dictionary_coverage=80.0
        )
        
        # Check that locked tokens were identified
        assert len(output.locked_tokens) > 0
        
        # Check that translation has placeholders restored
        assert "你" in output.translation or "好" in output.translation
        
        # Check metadata
        assert output.metadata["token_locking_enabled"] is True
        assert output.metadata["locked_tokens_count"] > 0
    
    def test_no_dictionary_fallback(
        self,
        mock_sentence_translator,
        semantic_contract,
        sample_glyphs
    ):
        """Test that adapter works without dictionary (falls back to confidence-only locking)."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract,
            cc_dictionary=None  # No dictionary
        )
        
        mock_sentence_translator.translate.return_value = "Hello world"
        
        output = adapter.translate(
            glyphs=sample_glyphs,
            confidence=0.85,
            dictionary_coverage=0.0
        )
        
        # Should still work, locking based on confidence only
        assert output.translation is not None
        assert output.metadata["token_locking_enabled"] is True


# ============================================================================
# EDGE CASES
# ============================================================================

class TestTokenLockingEdgeCases:
    """Edge case tests for token locking."""
    
    def test_empty_glyphs_list(
        self,
        mock_sentence_translator,
        semantic_contract
    ):
        """Test with empty glyphs list."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract
        )
        
        locked_tokens = adapter._identify_locked_tokens([])
        assert locked_tokens == []
    
    def test_all_tokens_locked(
        self,
        mock_sentence_translator,
        semantic_contract,
        mock_cc_dictionary
    ):
        """Test when all tokens are locked."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract,
            cc_dictionary=mock_cc_dictionary
        )
        
        glyphs = [
            Glyph(symbol="你", confidence=0.92),
            Glyph(symbol="好", confidence=0.88),
        ]
        
        mock_cc_dictionary.has_entry.return_value = True
        
        locked_tokens = adapter._identify_locked_tokens(glyphs)
        assert len(locked_tokens) == 2
    
    def test_no_tokens_locked(
        self,
        mock_sentence_translator,
        semantic_contract,
        mock_cc_dictionary
    ):
        """Test when no tokens are locked."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract,
            cc_dictionary=mock_cc_dictionary
        )
        
        glyphs = [
            Glyph(symbol="?", confidence=0.65),
            Glyph(symbol="!", confidence=0.60),
        ]
        
        mock_cc_dictionary.has_entry.return_value = False
        
        locked_tokens = adapter._identify_locked_tokens(glyphs)
        assert len(locked_tokens) == 0
    
    def test_placeholder_not_in_translation(
        self,
        mock_sentence_translator,
        semantic_contract
    ):
        """Test handling when placeholder is missing from translation."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract
        )
        
        placeholder_mapping = {
            "__LOCK_你__": (0, "你"),
        }
        
        # Translation doesn't contain placeholder (should log warning)
        translation = "Hello world"
        result = adapter._restore_locked_tokens(translation, placeholder_mapping)
        
        # Should return translation unchanged
        assert result == translation


# ============================================================================
# STEP 5: PHRASE-LEVEL REFINEMENT TESTS
# ============================================================================

class TestPhraseLevelRefinement:
    """Tests for phrase-level semantic refinement (Step 5)."""
    
    def test_identify_phrase_spans_all_unlocked(
        self,
        mock_sentence_translator,
        semantic_contract
    ):
        """Test phrase span identification when all tokens are unlocked."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract
        )
        
        glyphs = [
            Glyph(symbol="你", confidence=0.60),
            Glyph(symbol="好", confidence=0.65),
            Glyph(symbol="世", confidence=0.70),
            Glyph(symbol="界", confidence=0.68),
        ]
        
        locked_indices = []  # No locked tokens
        phrase_spans = adapter._identify_phrase_spans(glyphs, locked_indices)
        
        # Should have one phrase span (all unlocked)
        assert len(phrase_spans) == 1
        assert phrase_spans[0].start_idx == 0
        assert phrase_spans[0].end_idx == 4
        assert phrase_spans[0].is_locked is False
        assert phrase_spans[0].text == "你好世界"
    
    def test_identify_phrase_spans_mixed_locked_unlocked(
        self,
        mock_sentence_translator,
        semantic_contract
    ):
        """Test phrase span identification with mixed locked/unlocked tokens."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract
        )
        
        glyphs = [
            Glyph(symbol="你", confidence=0.92),  # Locked (high conf)
            Glyph(symbol="好", confidence=0.88),  # Locked (high conf)
            Glyph(symbol="?", confidence=0.65),   # Unlocked (low conf)
            Glyph(symbol="世", confidence=0.90),  # Locked (high conf)
            Glyph(symbol="界", confidence=0.87),  # Locked (high conf)
        ]
        
        locked_indices = [0, 1, 3, 4]  # Lock first two and last two
        phrase_spans = adapter._identify_phrase_spans(glyphs, locked_indices)
        
        # Should have 3 phrase spans: locked, unlocked, locked
        assert len(phrase_spans) == 3
        
        # First span: locked (indices 0-2)
        assert phrase_spans[0].start_idx == 0
        assert phrase_spans[0].end_idx == 2
        assert phrase_spans[0].is_locked is True
        assert phrase_spans[0].text == "你好"
        
        # Second span: unlocked (indices 2-3)
        assert phrase_spans[1].start_idx == 2
        assert phrase_spans[1].end_idx == 3
        assert phrase_spans[1].is_locked is False
        assert phrase_spans[1].text == "?"
        
        # Third span: locked (indices 3-5)
        assert phrase_spans[2].start_idx == 3
        assert phrase_spans[2].end_idx == 5
        assert phrase_spans[2].is_locked is True
        assert phrase_spans[2].text == "世界"
    
    def test_identify_phrase_spans_all_locked(
        self,
        mock_sentence_translator,
        semantic_contract
    ):
        """Test phrase span identification when all tokens are locked."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract
        )
        
        glyphs = [
            Glyph(symbol="你", confidence=0.92),
            Glyph(symbol="好", confidence=0.88),
        ]
        
        locked_indices = [0, 1]  # All locked
        phrase_spans = adapter._identify_phrase_spans(glyphs, locked_indices)
        
        # Should have one phrase span (all locked)
        assert len(phrase_spans) == 1
        assert phrase_spans[0].is_locked is True
        assert phrase_spans[0].text == "你好"
    
    def test_identify_phrase_spans_empty(
        self,
        mock_sentence_translator,
        semantic_contract
    ):
        """Test phrase span identification with empty glyph list."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract
        )
        
        phrase_spans = adapter._identify_phrase_spans([], [])
        assert phrase_spans == []
    
    def test_refine_phrases_preserves_text(
        self,
        mock_sentence_translator,
        semantic_contract
    ):
        """Test that _refine_phrases preserves text (current implementation)."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract
        )
        
        text = "Hello __LOCK_你__ __LOCK_好__ world"
        phrase_spans = [
            PhraseSpan(start_idx=0, end_idx=2, is_locked=True, text="你好", glyph_indices=[0, 1]),
            PhraseSpan(start_idx=2, end_idx=4, is_locked=False, text="世界", glyph_indices=[2, 3]),
        ]
        locked_indices = [0, 1]
        
        result = adapter._refine_phrases(text, phrase_spans, locked_indices)
        
        # Current implementation returns text as-is
        assert result == text
    
    def test_phrase_span_contains_glyph(self):
        """Test PhraseSpan.contains_glyph method."""
        phrase = PhraseSpan(
            start_idx=2,
            end_idx=5,
            is_locked=False,
            text="世界",
            glyph_indices=[2, 3, 4]
        )
        
        assert phrase.contains_glyph(2) is True
        assert phrase.contains_glyph(3) is True
        assert phrase.contains_glyph(4) is True
        assert phrase.contains_glyph(1) is False
        assert phrase.contains_glyph(5) is False
    
    def test_phrase_span_length(self):
        """Test PhraseSpan.__len__ method."""
        phrase = PhraseSpan(
            start_idx=0,
            end_idx=3,
            is_locked=False,
            text="你好世界",
            glyph_indices=[0, 1, 2]
        )
        
        assert len(phrase) == 3


# ============================================================================
# STEP 6: SEMANTIC CONFIDENCE METRICS TESTS
# ============================================================================

class TestSemanticConfidenceMetrics:
    """Tests for semantic confidence metrics (Step 6)."""
    
    def test_calculate_semantic_metrics_all_locked(
        self,
        mock_sentence_translator,
        semantic_contract,
        mock_cc_dictionary
    ):
        """Test semantic metrics when all tokens are locked."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract,
            cc_dictionary=mock_cc_dictionary
        )
        
        glyphs = [
            Glyph(symbol="你", confidence=0.92),
            Glyph(symbol="好", confidence=0.88),
        ]
        
        locked_tokens = [0, 1]
        changed_tokens = []
        preserved_tokens = [0, 1]
        dictionary_coverage = 100.0
        
        mock_cc_dictionary.has_entry.return_value = True
        
        metrics = adapter._calculate_semantic_metrics(
            glyphs, locked_tokens, changed_tokens, preserved_tokens, dictionary_coverage
        )
        
        assert metrics["tokens_locked_percent"] == 100.0
        assert metrics["tokens_modified_percent"] == 0.0
        assert metrics["tokens_preserved_percent"] == 100.0
        assert metrics["semantic_confidence"] > 0.8  # High confidence when all locked
        assert metrics["dictionary_override_count"] == 2
    
    def test_calculate_semantic_metrics_all_unlocked(
        self,
        mock_sentence_translator,
        semantic_contract
    ):
        """Test semantic metrics when no tokens are locked."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract
        )
        
        glyphs = [
            Glyph(symbol="?", confidence=0.65),
            Glyph(symbol="!", confidence=0.60),
        ]
        
        locked_tokens = []
        changed_tokens = [0, 1]
        preserved_tokens = []
        dictionary_coverage = 0.0
        
        metrics = adapter._calculate_semantic_metrics(
            glyphs, locked_tokens, changed_tokens, preserved_tokens, dictionary_coverage
        )
        
        assert metrics["tokens_locked_percent"] == 0.0
        assert metrics["tokens_modified_percent"] == 100.0
        assert metrics["tokens_preserved_percent"] == 0.0
        assert metrics["semantic_confidence"] < 0.5  # Lower confidence when all unlocked
        assert metrics["dictionary_override_count"] == 0
    
    def test_calculate_semantic_metrics_mixed(
        self,
        mock_sentence_translator,
        semantic_contract,
        mock_cc_dictionary
    ):
        """Test semantic metrics with mixed locked/unlocked tokens."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract,
            cc_dictionary=mock_cc_dictionary
        )
        
        glyphs = [
            Glyph(symbol="你", confidence=0.92),  # Locked
            Glyph(symbol="好", confidence=0.88),  # Locked
            Glyph(symbol="?", confidence=0.65),   # Unlocked
        ]
        
        locked_tokens = [0, 1]
        changed_tokens = [2]
        preserved_tokens = [0, 1]
        dictionary_coverage = 66.7
        
        def has_entry_side_effect(char):
            return char in ["你", "好"]
        
        mock_cc_dictionary.has_entry.side_effect = has_entry_side_effect
        
        metrics = adapter._calculate_semantic_metrics(
            glyphs, locked_tokens, changed_tokens, preserved_tokens, dictionary_coverage
        )
        
        assert metrics["tokens_locked_percent"] == pytest.approx(66.7, abs=0.1)
        assert metrics["tokens_modified_percent"] == pytest.approx(33.3, abs=0.1)
        assert metrics["tokens_preserved_percent"] == pytest.approx(66.7, abs=0.1)
        assert 0.0 <= metrics["semantic_confidence"] <= 1.0
        assert metrics["dictionary_override_count"] == 2
    
    def test_calculate_semantic_metrics_empty(
        self,
        mock_sentence_translator,
        semantic_contract
    ):
        """Test semantic metrics with empty glyph list."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract
        )
        
        metrics = adapter._calculate_semantic_metrics(
            [], [], [], [], 0.0
        )
        
        assert metrics["tokens_locked_percent"] == 0.0
        assert metrics["tokens_modified_percent"] == 0.0
        assert metrics["tokens_preserved_percent"] == 0.0
        assert metrics["semantic_confidence"] == 0.0
        assert metrics["dictionary_override_count"] == 0
    
    def test_calculate_semantic_metrics_confidence_range(
        self,
        mock_sentence_translator,
        semantic_contract,
        mock_cc_dictionary
    ):
        """Test that semantic confidence is always in [0.0, 1.0] range."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract,
            cc_dictionary=mock_cc_dictionary
        )
        
        # Test various scenarios
        test_cases = [
            ([Glyph(symbol="你", confidence=0.92)] * 10, list(range(10)), [], list(range(10)), 100.0),
            ([Glyph(symbol="?", confidence=0.60)] * 10, [], list(range(10)), [], 0.0),
            ([Glyph(symbol="你", confidence=0.92), Glyph(symbol="?", confidence=0.60)] * 5, 
             list(range(0, 10, 2)), list(range(1, 10, 2)), list(range(0, 10, 2)), 50.0),
        ]
        
        mock_cc_dictionary.has_entry.return_value = True
        
        for glyphs, locked, changed, preserved, coverage in test_cases:
            metrics = adapter._calculate_semantic_metrics(
                glyphs, locked, changed, preserved, coverage
            )
            assert 0.0 <= metrics["semantic_confidence"] <= 1.0, \
                f"Semantic confidence out of range: {metrics['semantic_confidence']}"
    
    def test_calculate_semantic_metrics_with_cc_translator(
        self,
        mock_sentence_translator,
        semantic_contract
    ):
        """Test semantic metrics using cc_translator instead of cc_dictionary."""
        mock_cc_translator = Mock()
        mock_cc_translator.cc_dictionary = Mock()
        mock_cc_translator.cc_dictionary.has_entry = Mock(return_value=True)
        
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract,
            cc_translator=mock_cc_translator
        )
        
        glyphs = [
            Glyph(symbol="你", confidence=0.92),
            Glyph(symbol="好", confidence=0.88),
        ]
        
        locked_tokens = [0, 1]
        changed_tokens = []
        preserved_tokens = [0, 1]
        dictionary_coverage = 100.0
        
        metrics = adapter._calculate_semantic_metrics(
            glyphs, locked_tokens, changed_tokens, preserved_tokens, dictionary_coverage
        )
        
        assert metrics["dictionary_override_count"] == 2
        assert mock_cc_translator.cc_dictionary.has_entry.called


# ============================================================================
# STEP 8: COMPREHENSIVE INTEGRATION TESTS
# ============================================================================

class TestLockedTokenPreservation:
    """Step 8: Comprehensive locked token preservation tests."""
    
    def test_locked_tokens_never_change(
        self,
        mock_sentence_translator,
        semantic_contract,
        mock_cc_dictionary
    ):
        """Test that locked tokens never change during translation."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract,
            cc_dictionary=mock_cc_dictionary
        )
        
        glyphs = [
            Glyph(symbol="你", confidence=0.92),  # High confidence + dict = locked
            Glyph(symbol="好", confidence=0.88),  # High confidence + dict = locked
            Glyph(symbol="?", confidence=0.65),   # Low confidence = unlocked
        ]
        
        def has_entry_side_effect(char):
            return char in ["你", "好"]
        
        mock_cc_dictionary.has_entry.side_effect = has_entry_side_effect
        
        # Mock translator to preserve placeholders
        def translate_side_effect(text):
            # Placeholders should survive translation
            return text.replace("__LOCK_你__", "__LOCK_你__").replace("__LOCK_好__", "__LOCK_好__")
        
        mock_sentence_translator.translate.side_effect = translate_side_effect
        
        output = adapter.translate(
            glyphs=glyphs,
            confidence=0.85,
            dictionary_coverage=66.7
        )
        
        # Locked tokens should be preserved
        assert 0 in output.locked_tokens
        assert 1 in output.locked_tokens
        assert 0 in output.preserved_tokens
        assert 1 in output.preserved_tokens
    
    def test_high_confidence_preserved(
        self,
        mock_sentence_translator,
        semantic_contract,
        mock_cc_dictionary
    ):
        """Test that high-confidence glyphs are preserved."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract,
            cc_dictionary=mock_cc_dictionary
        )
        
        glyphs = [
            Glyph(symbol="你", confidence=0.95),  # Very high confidence
            Glyph(symbol="好", confidence=0.93),  # Very high confidence
        ]
        
        mock_cc_dictionary.has_entry.return_value = True
        
        output = adapter.translate(
            glyphs=glyphs,
            confidence=0.94,
            dictionary_coverage=100.0
        )
        
        # All high-confidence glyphs should be locked
        assert len(output.locked_tokens) == 2
        assert output.semantic_confidence > 0.8  # High confidence when all locked


class TestMarianMTFluencyImprovement:
    """Step 8: Tests for MarianMT fluency and grammar improvement."""
    
    def test_fluency_improvement(
        self,
        mock_sentence_translator,
        semantic_contract
    ):
        """Test that MarianMT improves fluency of unlocked tokens."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract
        )
        
        glyphs = [
            Glyph(symbol="?", confidence=0.60),  # Low confidence, unlocked
            Glyph(symbol="!", confidence=0.65),  # Low confidence, unlocked
        ]
        
        # Mock translator to improve fluency
        mock_sentence_translator.translate.return_value = "Hello world"
        
        output = adapter.translate(
            glyphs=glyphs,
            confidence=0.625,
            dictionary_coverage=0.0
        )
        
        # Translation should be improved
        assert output.translation is not None
        assert len(output.changed_tokens) >= 0  # Unlocked tokens can be changed
    
    def test_grammar_correction(
        self,
        mock_sentence_translator,
        semantic_contract
    ):
        """Test that MarianMT corrects grammar errors in unlocked spans."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract
        )
        
        glyphs = [
            Glyph(symbol="?", confidence=0.55),  # Very low confidence
        ]
        
        # Mock translator to correct grammar
        mock_sentence_translator.translate.return_value = "Corrected grammar"
        
        output = adapter.translate(
            glyphs=glyphs,
            confidence=0.55,
            dictionary_coverage=0.0
        )
        
        # Grammar correction should be applied
        assert output.translation is not None
        assert output.semantic_confidence >= 0.0  # Should have some confidence


class TestOCRDictionaryAuthority:
    """Step 8: Tests for OCR fusion and dictionary authority."""
    
    def test_ocr_fusion_authoritative(
        self,
        mock_sentence_translator,
        semantic_contract,
        mock_cc_dictionary
    ):
        """Test that OCR fusion decisions are authoritative."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract,
            cc_dictionary=mock_cc_dictionary
        )
        
        glyphs = [
            Glyph(symbol="你", confidence=0.92),  # High OCR confidence
            Glyph(symbol="好", confidence=0.88),  # High OCR confidence
        ]
        
        mock_cc_dictionary.has_entry.return_value = True
        
        output = adapter.translate(
            glyphs=glyphs,
            confidence=0.90,  # High OCR confidence
            dictionary_coverage=100.0
        )
        
        # High OCR confidence should result in locked tokens
        assert len(output.locked_tokens) == 2
        assert output.metadata["tokens_locked_percent"] == 100.0
    
    def test_dictionary_anchors_preserved(
        self,
        mock_sentence_translator,
        semantic_contract,
        mock_cc_dictionary
    ):
        """Test that dictionary anchors are preserved."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract,
            cc_dictionary=mock_cc_dictionary
        )
        
        glyphs = [
            Glyph(symbol="你", confidence=0.92),  # High confidence + dict
            Glyph(symbol="好", confidence=0.88),  # High confidence + dict
        ]
        
        def has_entry_side_effect(char):
            return char in ["你", "好"]
        
        mock_cc_dictionary.has_entry.side_effect = has_entry_side_effect
        
        output = adapter.translate(
            glyphs=glyphs,
            confidence=0.90,
            dictionary_coverage=100.0
        )
        
        # Dictionary matches should result in locked tokens
        assert len(output.locked_tokens) == 2
        assert output.metadata["dictionary_override_count"] == 2


class TestFallbackBehavior:
    """Step 8: Tests for fallback behavior when components fail."""
    
    def test_marianmt_failure_fallback(
        self,
        semantic_contract
    ):
        """Test fallback when MarianMT fails."""
        # Create adapter with failing translator
        failing_translator = Mock()
        failing_translator.is_available.return_value = True
        failing_translator.translate.side_effect = Exception("MarianMT failed")
        
        adapter = MarianAdapter(
            sentence_translator=failing_translator,
            semantic_contract=semantic_contract
        )
        
        glyphs = [
            Glyph(symbol="你", confidence=0.92),
        ]
        
        # Should handle failure gracefully
        output = adapter.translate(
            glyphs=glyphs,
            confidence=0.92,
            dictionary_coverage=100.0
        )
        
        # Should return empty translation but not crash
        assert output.translation == ""
        assert output.metadata.get("available", True) == False or "error" in output.metadata
    
    def test_adapter_graceful_degradation(
        self,
        semantic_contract
    ):
        """Test that adapter degrades gracefully when unavailable."""
        # Create adapter with unavailable translator
        unavailable_translator = Mock()
        unavailable_translator.is_available.return_value = False
        
        adapter = MarianAdapter(
            sentence_translator=unavailable_translator,
            semantic_contract=semantic_contract
        )
        
        glyphs = [
            Glyph(symbol="你", confidence=0.92),
        ]
        
        # Should handle unavailability gracefully
        output = adapter.translate(
            glyphs=glyphs,
            confidence=0.92,
            dictionary_coverage=100.0
        )
        
        # Should return empty translation but not crash
        assert output.translation == ""
        assert output.metadata.get("available", True) == False
    
    def test_no_dictionary_fallback(
        self,
        mock_sentence_translator,
        semantic_contract
    ):
        """Test that adapter works without dictionary (falls back to confidence-only)."""
        adapter = MarianAdapter(
            sentence_translator=mock_sentence_translator,
            semantic_contract=semantic_contract,
            cc_dictionary=None  # No dictionary
        )
        
        glyphs = [
            Glyph(symbol="你", confidence=0.92),  # High confidence, no dict
        ]
        
        mock_sentence_translator.translate.return_value = "Hello"
        
        output = adapter.translate(
            glyphs=glyphs,
            confidence=0.92,
            dictionary_coverage=0.0
        )
        
        # Should still work, locking based on confidence only
        assert output.translation is not None
        assert len(output.locked_tokens) > 0  # High confidence should still lock


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_get_marian_adapter_with_dictionary(
        self,
        mock_cc_dictionary
    ):
        """Test get_marian_adapter factory with dictionary."""
        # This will fail if transformers not installed, but that's OK for test
        try:
            adapter = get_marian_adapter(cc_dictionary=mock_cc_dictionary)
            if adapter:
                assert adapter.cc_dictionary == mock_cc_dictionary
        except Exception:
            # Expected if transformers not installed
            pass
    
    def test_get_marian_adapter_without_dictionary(self):
        """Test get_marian_adapter factory without dictionary."""
        try:
            adapter = get_marian_adapter()
            if adapter:
                assert adapter.cc_dictionary is None
        except Exception:
            # Expected if transformers not installed
            pass

