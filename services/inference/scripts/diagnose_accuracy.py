"""
Diagnostic script to check CC-CEDICT vs RuleBasedTranslator accuracy.

This script helps identify if accuracy issues are from:
1. OCR fusion (Phase 3)
2. Translation (Phase 4)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cc_dictionary import CCDictionary
from cc_translation import CCDictionaryTranslator
from translator import get_translator

def test_translation_comparison():
    """Compare CC-CEDICT vs RuleBasedTranslator translation."""
    
    print("=" * 70)
    print("TRANSLATION ACCURACY DIAGNOSTIC")
    print("=" * 70)
    print()
    
    # Load both translators
    print("[1/3] Loading dictionaries...")
    cc_dict = CCDictionary(str(Path(__file__).parent.parent / "data" / "cc_cedict.json"))
    cc_translator = CCDictionaryTranslator(cc_dict)
    rule_translator = get_translator()
    print(f"  [OK] CC-CEDICT: {len(cc_dict):,} entries")
    print(f"  [OK] RuleBasedTranslator: 276 entries")
    print()
    
    # Test common characters
    test_chars = ["你", "好", "世", "界", "我", "的", "是", "不", "人", "有"]
    
    print("[2/3] Testing common characters...")
    print()
    print(f"{'Char':<6} {'CC-CEDICT':<30} {'RuleBasedTranslator':<30} {'Match?':<8}")
    print("-" * 80)
    
    matches = 0
    differences = []
    
    for char in test_chars:
        # CC-CEDICT translation
        cc_result = cc_translator.translate_character(char)
        cc_trans = cc_result.primary_definition if cc_result.found_in_dictionary else "[NOT FOUND]"
        
        # RuleBasedTranslator translation
        rule_result = rule_translator.translate_text(char, [{"symbol": char, "bbox": [0,0,1,1], "confidence": 1.0}])
        rule_glyphs = rule_result.get("glyphs", [])
        rule_trans = rule_glyphs[0].get("meaning", "[NOT FOUND]") if rule_glyphs else "[NOT FOUND]"
        
        # Compare
        match = "MATCH" if cc_trans.lower().startswith(rule_trans.lower()[:3]) or rule_trans.lower().startswith(cc_trans.lower()[:3]) else "DIFF"
        
        print(f"{char:<6} {cc_trans[:28]:<30} {rule_trans[:28]:<30} {match:<8}")
        
        if match == "MATCH":
            matches += 1
        else:
            differences.append({
                "char": char,
                "cc": cc_trans,
                "rule": rule_trans
            })
    
    print()
    print(f"Match rate: {matches}/{len(test_chars)} ({matches/len(test_chars)*100:.1f}%)")
    print()
    
    if differences:
        print("[3/3] Significant differences found:")
        print()
        for diff in differences:
            print(f"  Character: {diff['char']}")
            print(f"    CC-CEDICT:          {diff['cc']}")
            print(f"    RuleBasedTranslator: {diff['rule']}")
            print()
    else:
        print("[3/3] No significant differences found.")
        print()
    
    print("=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)
    print()
    
    # Coverage comparison
    print("Coverage Comparison:")
    test_text = "你好世界欢迎来到中国"
    
    cc_result = cc_translator.translate_text(test_text)
    rule_result = rule_translator.translate_text(test_text, [
        {"symbol": c, "bbox": [i,0,i+1,1], "confidence": 1.0} 
        for i, c in enumerate(test_text)
    ])
    
    print(f"  CC-CEDICT Coverage:          {cc_result.coverage:.1f}%")
    print(f"  RuleBasedTranslator Coverage: {rule_result.get('coverage', 0):.1f}%")
    print()
    
    print("RECOMMENDATION:")
    if matches >= len(test_chars) * 0.8:  # 80% match
        print("  [OK] Translations are similar between both systems.")
        print("  [OK] CC-CEDICT should provide BETTER coverage.")
        print()
        print("  If you're seeing accuracy issues, they may be from:")
        print("    1. OCR fusion (Phase 3) - check 'text' field in API")
        print("    2. Different definition selection (Phase 4) - check 'translation' field")
        print()
    else:
        print("  [WARNING] Significant differences detected!")
        print("  [WARNING] CC-CEDICT may be selecting different definitions.")
        print()
        print("  To use RuleBasedTranslator instead, in main.py set:")
        print("    cc_translator = None  # Force fallback")
        print()

if __name__ == "__main__":
    test_translation_comparison()

