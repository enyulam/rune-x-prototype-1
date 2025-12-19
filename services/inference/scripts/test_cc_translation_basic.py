"""
Quick verification script for cc_translation.py module.

Tests basic functionality:
- Module imports correctly
- CCDictionaryTranslator initializes
- Character translation works
- Text translation works
- All data models are accessible
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cc_dictionary import CCDictionary
from cc_translation import (
    CCDictionaryTranslator,
    DefinitionStrategy,
    TranslationCandidate,
    CharacterTranslation,
    TranslationResult
)

def main():
    print("=" * 60)
    print("CC-CEDICT Translation Module - Basic Verification")
    print("=" * 60)
    print()
    
    # Test 1: Load CC-CEDICT
    print("[1/6] Loading CC-CEDICT dictionary...")
    try:
        cc_dict_path = Path(__file__).parent.parent / "data" / "cc_cedict.json"
        cc_dict = CCDictionary(str(cc_dict_path))
        print(f"[OK] CC-CEDICT loaded: {len(cc_dict):,} entries")
    except Exception as e:
        print(f"[FAIL] Failed to load CC-CEDICT: {e}")
        return
    
    print()
    
    # Test 2: Initialize translator
    print("[2/6] Initializing CCDictionaryTranslator...")
    try:
        translator = CCDictionaryTranslator(cc_dict)
        print(f"[OK] Translator initialized: {translator}")
    except Exception as e:
        print(f"[FAIL] Failed to initialize translator: {e}")
        return
    
    print()
    
    # Test 3: Translate single character
    print("[3/6] Testing single character translation...")
    try:
        char_trans = translator.translate_character("好")
        print(f"[OK] Character translated successfully")
        print(f"     Primary: {char_trans.primary_definition}")
        print(f"     Definition count: {len(char_trans.all_definitions)}")
        print(f"     Pinyin: {char_trans.pinyin}")
        print(f"     Found: {char_trans.found_in_dictionary}")
    except Exception as e:
        print(f"[FAIL] Character translation failed: {e}")
        return
    
    print()
    
    # Test 4: Translate text
    print("[4/6] Testing text translation...")
    try:
        result = translator.translate_text("你好世界")
        print(f"[OK] Text translated successfully (4 characters)")
        print(f"     Translation: {result.translation}")
        print(f"     Coverage: {result.coverage:.1f}%")
        print(f"     Mapped: {result.mapped_characters}/{result.total_characters}")
        print(f"     Unmapped count: {len(result.unmapped)}")
    except Exception as e:
        print(f"[FAIL] Text translation failed: {e}")
        return
    
    print()
    
    # Test 5: Test different strategies
    print("[5/6] Testing definition selection strategies...")
    try:
        test_char = "好"
        for strategy in [DefinitionStrategy.FIRST, DefinitionStrategy.SHORTEST]:
            char_trans = translator.translate_character(test_char, strategy)
            print(f"[OK] Strategy '{strategy.value}': {char_trans.primary_definition}")
    except Exception as e:
        print(f"[FAIL] Strategy test failed: {e}")
        return
    
    print()
    
    # Test 6: Get metadata
    print("[6/6] Testing metadata retrieval...")
    try:
        metadata = translator.get_translation_metadata()
        print(f"[OK] Translation source: {metadata['translation_source']}")
        print(f"     Dictionary size: {metadata['dictionary_size']:,}")
        print(f"     Default strategy: {metadata['default_strategy']}")
        print(f"     Available strategies: {metadata['available_strategies']}")
    except Exception as e:
        print(f"[FAIL] Metadata retrieval failed: {e}")
        return
    
    print()
    print("=" * 60)
    print("[SUCCESS] ALL TESTS PASSED - Module is working correctly!")
    print("=" * 60)

if __name__ == "__main__":
    main()

