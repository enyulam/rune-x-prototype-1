"""Simple verification for cc_translation.py without Unicode printing issues."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cc_dictionary import CCDictionary
from cc_translation import CCDictionaryTranslator, DefinitionStrategy

def main():
    print("="* 60)
    print("CC-CEDICT Translation Module - Verification")
    print("=" * 60)
    
    # Load CC-CEDICT
    cc_dict_path = Path(__file__).parent.parent / "data" / "cc_cedict.json"
    cc_dict = CCDictionary(str(cc_dict_path))
    print(f"[1/5] CC-CEDICT loaded: {len(cc_dict):,} entries")
    
    # Initialize translator
    translator = CCDictionaryTranslator(cc_dict)
    print(f"[2/5] Translator initialized: {translator}")
    
    # Test single character
    char_trans = translator.translate_character("好")
    assert char_trans.found_in_dictionary == True
    assert char_trans.primary_definition == "good"
    assert len(char_trans.all_definitions) > 1
    print(f"[3/5] Single character translation: PASS")
    print(f"      Primary definition: {char_trans.primary_definition}")
    print(f"      Total definitions: {len(char_trans.all_definitions)}")
    
    # Test text translation
    result = translator.translate_text("你好世界")
    assert result.total_characters == 4
    assert result.coverage > 90.0  # Should be high coverage
    print(f"[4/5] Text translation: PASS")
    print(f"      Characters: {result.total_characters}")
    print(f"      Coverage: {result.coverage:.1f}%")
    print(f"      English words: {len(result.translation.split())}")
    
    # Test strategies
    first_trans = translator.translate_character("好", DefinitionStrategy.FIRST)
    shortest_trans = translator.translate_character("好", DefinitionStrategy.SHORTEST)
    assert first_trans.primary_definition == "good"
    assert len(shortest_trans.primary_definition) <= len(first_trans.primary_definition)
    print(f"[5/5] Strategy selection: PASS")
    print(f"      FIRST: '{first_trans.primary_definition}'")
    print(f"      SHORTEST: '{shortest_trans.primary_definition}'")
    
    print()
    print("=" * 60)
    print("[SUCCESS] All tests passed!")
    print("=" * 60)
    print()
    print("Module details:")
    metadata = translator.get_translation_metadata()
    print(f"  - Translation source: {metadata['translation_source']}")
    print(f"  - Dictionary size: {metadata['dictionary_size']:,}")
    print(f"  - Default strategy: {metadata['default_strategy']}")
    print(f"  - Available strategies: {', '.join(metadata['available_strategies'])}")

if __name__ == "__main__":
    main()

