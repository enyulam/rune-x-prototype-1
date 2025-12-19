"""
Test token locking in QwenAdapter (Step 4).

This test verifies that locked tokens are properly preserved through Qwen refinement.
"""

import pytest
from qwen_adapter import QwenAdapter, QwenAdapterInput, QwenAdapterOutput
from qwen_refiner import QwenRefiner
from ocr_fusion import Glyph


class MockQwenRefiner:
    """Mock QwenRefiner that simulates refinement behavior."""
    
    def __init__(self):
        self._available = True
    
    def is_available(self) -> bool:
        return self._available
    
    def refine_translation_with_qwen(self, nmt_translation: str, ocr_text: str) -> str:
        """
        Simulate Qwen refinement.
        
        For testing: If text contains placeholders, preserve them.
        Otherwise, make minor changes to test change tracking.
        """
        # If placeholders exist, preserve them (simulating locked token behavior)
        if "__LOCK_" in nmt_translation:
            # Placeholders should survive Qwen processing
            return nmt_translation
        
        # Otherwise, simulate minor refinement
        # Change "hello" to "Hello" (capitalization)
        refined = nmt_translation.replace("hello", "Hello")
        return refined


@pytest.fixture
def mock_qwen_refiner():
    """Create a mock QwenRefiner for testing."""
    return MockQwenRefiner()


@pytest.fixture
def sample_glyphs():
    """Create sample glyphs for testing."""
    return [
        Glyph(symbol="你", bbox=[0, 0, 10, 10], confidence=0.95, meaning=None),
        Glyph(symbol="好", bbox=[10, 0, 20, 10], confidence=0.92, meaning=None),
        Glyph(symbol="世", bbox=[20, 0, 30, 10], confidence=0.60, meaning=None),
        Glyph(symbol="界", bbox=[30, 0, 40, 10], confidence=0.55, meaning=None),
    ]


def test_token_locking_basic(mock_qwen_refiner, sample_glyphs):
    """
    Test basic token locking: locked tokens should be preserved.
    
    Scenario: First 2 tokens are locked (indices 0, 1).
    Expected: Locked tokens preserved, unlocked tokens can be modified.
    """
    adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
    
    # Create input with locked tokens (indices 0, 1)
    input_data = QwenAdapterInput(
        text="hello world test",
        glyphs=sample_glyphs,
        locked_tokens=[0, 1],  # Chinese glyph indices (not used in Step 4)
        ocr_text="你好世界",
        english_locked_tokens=[0, 1]  # English token indices: "hello", "world"
    )
    
    result = adapter.translate(input_data)
    
    assert result is not None, "QwenAdapter should return result"
    assert isinstance(result, QwenAdapterOutput), "Result should be QwenAdapterOutput"
    
    # Verify locked tokens are preserved
    # Since we're using mock that preserves placeholders, check that mechanism works
    assert result.refined_text is not None, "Refined text should exist"
    
    # Verify change tracking
    assert isinstance(result.changed_tokens, list), "changed_tokens should be list"
    assert isinstance(result.preserved_tokens, list), "preserved_tokens should be list"
    assert isinstance(result.locked_tokens, list), "locked_tokens should be list"
    
    # Locked tokens should be in preserved_tokens, not changed_tokens
    assert 0 in result.preserved_tokens or 0 in result.locked_tokens, \
        "Locked token 0 should be preserved"
    assert 1 in result.preserved_tokens or 1 in result.locked_tokens, \
        "Locked token 1 should be preserved"
    
    # Verify metadata
    assert "token_locking_enabled" in result.metadata, \
        "Metadata should indicate token locking status"
    assert result.metadata["token_locking_enabled"] is True, \
        "Token locking should be enabled when locked tokens provided"


def test_token_locking_no_locked_tokens(mock_qwen_refiner, sample_glyphs):
    """
    Test behavior when no tokens are locked.
    
    Expected: All tokens can be modified, change tracking works.
    """
    adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
    
    input_data = QwenAdapterInput(
        text="hello world test",
        glyphs=sample_glyphs,
        locked_tokens=[],  # No locked tokens
        ocr_text="你好世界",
        english_locked_tokens=[]  # No locked English tokens
    )
    
    result = adapter.translate(input_data)
    
    assert result is not None, "QwenAdapter should return result"
    assert result.metadata["token_locking_enabled"] is False, \
        "Token locking should be disabled when no locked tokens"


def test_placeholder_replacement(mock_qwen_refiner):
    """Test that placeholders are correctly replaced and restored."""
    adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
    
    # Test _replace_locked_with_placeholders directly
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


def test_change_tracking(mock_qwen_refiner):
    """Test that change tracking correctly identifies modified tokens."""
    adapter = QwenAdapter(qwen_refiner=mock_qwen_refiner)
    
    original = "hello world test"
    refined = "Hello world test"  # Token 0 changed (capitalization)
    locked_indices = [1]  # Token 1 ("world") is locked
    
    changed, preserved = adapter._track_qwen_changes(original, refined, locked_indices)
    
    # Token 0 should be in changed (capitalization change)
    assert 0 in changed, "Token 0 should be marked as changed"
    
    # Token 1 should be in preserved (locked)
    assert 1 in preserved, "Locked token 1 should be preserved"
    assert 1 not in changed, "Locked token 1 should not be in changed"
    
    # Token 2 should be in preserved (unchanged)
    assert 2 in preserved, "Unchanged token 2 should be preserved"

