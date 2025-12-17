"""
Basic tests for RuleBasedTranslator
Run with: pytest services/inference/tests/test_translator.py
Or: python services/inference/tests/test_translator.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from translator import RuleBasedTranslator


def test_translator_initialization():
    """Test translator can be initialized."""
    translator = RuleBasedTranslator()
    assert translator is not None
    assert translator.dictionary is not None
    print("✓ Translator initialized successfully")


def test_lookup_meaning():
    """Test meaning lookup for known characters."""
    translator = RuleBasedTranslator()
    
    # Test known character
    meaning = translator.lookup_meaning("人")
    assert meaning is not None
    assert "person" in meaning.lower() or "people" in meaning.lower() or "human" in meaning.lower()
    print(f"✓ Lookup test passed: '人' = '{meaning}'")
    
    # Test unknown character
    meaning = translator.lookup_meaning("")
    assert meaning is None
    print("✓ Empty lookup handled correctly")


def test_lookup_entry():
    """Test full entry lookup."""
    translator = RuleBasedTranslator()
    
    entry = translator.lookup_entry("人")
    assert entry is not None
    assert "meaning" in entry
    assert "notes" in entry or "alts" in entry
    print(f"✓ Entry lookup passed: {entry}")


def test_translate_text():
    """Test full text translation."""
    translator = RuleBasedTranslator()
    
    # Test with known characters from dictionary
    text = "人天"
    glyphs = [
        {"symbol": "人", "bbox": [0, 0, 50, 50], "confidence": 0.95},
        {"symbol": "天", "bbox": [50, 0, 50, 50], "confidence": 0.92}
    ]
    
    result = translator.translate_text(text, glyphs)
    
    assert "glyphs" in result
    assert "translation" in result
    assert "unmapped" in result
    assert "coverage" in result
    
    assert len(result["glyphs"]) == 2
    assert all("meaning" in g for g in result["glyphs"])
    assert result["translation"] is not None
    assert isinstance(result["coverage"], (int, float))
    assert result["coverage"] > 0  # Should have some coverage
    
    print(f"✓ Translation test passed: '{text}' -> '{result['translation']}'")
    print(f"  Coverage: {result['coverage']}%")


def test_statistics():
    """Test dictionary statistics."""
    translator = RuleBasedTranslator()
    stats = translator.get_statistics()
    
    assert "total_entries" in stats
    assert "version" in stats
    assert isinstance(stats["total_entries"], int)
    assert stats["total_entries"] > 0  # Dictionary should have entries
    
    print(f"✓ Statistics test passed: {stats['total_entries']} entries")


def test_alternative_forms():
    """Test that alternative forms are recognized."""
    translator = RuleBasedTranslator()
    
    # Test if alternative forms work (if dictionary has them)
    # This depends on your dictionary structure
    entry = translator.lookup_entry("人")
    if entry and "alts" in entry:
        print(f"✓ Alternative forms found: {entry.get('alts', [])}")
    else:
        print("  (No alternatives to test)")


if __name__ == "__main__":
    # Simple test runner
    print("Running basic translator tests...")
    print("="*60)
    
    try:
        test_translator_initialization()
        test_lookup_meaning()
        test_lookup_entry()
        test_translate_text()
        test_statistics()
        test_alternative_forms()
        
        print("="*60)
        print("All tests passed! ✓")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

