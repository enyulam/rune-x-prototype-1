"""Test script for CCDictionary class."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from cc_dictionary import CCDictionary
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_dictionary(dict_path):
    """Test dictionary loading and operations."""
    print("=" * 60)
    print(f"Testing CCDictionary with: {dict_path}")
    print("=" * 60)
    
    try:
        # Load dictionary
        dictionary = CCDictionary(dict_path)
        print(f"\nDictionary loaded successfully!")
        print(f"Total entries: {len(dictionary):,}")
        print(f"Source: {dictionary.metadata.get('source', 'Unknown')}")
        
        # Test existence checks
        test_chars = ["学", "你", "好", "不存在的字"]
        found_count = sum(1 for char in test_chars if dictionary.has_entry(char))
        print(f"\nExistence check: {found_count}/{len(test_chars)} characters found")
        
        # Test lookup functionality
        print("\nTesting lookup methods:")
        test_char = "学"
        
        # Full lookup
        entry = dictionary.lookup(test_char)
        if entry:
            print(f"  - Full lookup: OK (found {len(entry)} fields)")
            print(f"    Pinyin: {entry.get('pinyin', 'N/A')}")
            print(f"    Definitions: {len(entry.get('definitions', []))} found")
        
        # Character lookup (simplified)
        meaning = dictionary.lookup_character(test_char)
        if meaning:
            print(f"  - Character lookup: OK (primary meaning found)")
        
        # Pinyin lookup
        pinyin = dictionary.get_pinyin(test_char)
        if pinyin:
            print(f"  - Pinyin lookup: OK ({pinyin})")
        
        # Traditional lookup
        trad = dictionary.get_traditional(test_char)
        if trad:
            print(f"  - Traditional lookup: OK")
        
        # Batch lookup
        batch_chars = ["学", "你", "好"]
        results = dictionary.batch_lookup(batch_chars)
        batch_found = sum(1 for v in results.values() if v)
        print(f"  - Batch lookup: OK ({batch_found}/{len(batch_chars)} found)")
        
        # Test statistics
        stats = dictionary.get_stats()
        print(f"\nDictionary statistics:")
        print(f"  - Entries: {stats['entry_count']:,}")
        print(f"  - Cache hits: {stats['cache_hits']}")
        print(f"  - Cache misses: {stats['cache_misses']}")
        print(f"  - Cache size: {stats['cache_size']}/{stats['cache_maxsize']}")
        
        # Test operators
        print(f"\nOperator tests:")
        print(f"  - __len__: {len(dictionary):,}")
        print(f"  - __contains__: {'学' in dictionary}")
        print(f"  - __repr__: {repr(dictionary)}")
        
        print("\n" + "=" * 60)
        print("PASS: All tests completed successfully!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\nFAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Test with demo dictionary
    demo_path = "../data/demo_cedict.json"
    success_demo = test_dictionary(demo_path)
    
    print("\n\n")
    
    # Test with full dictionary
    full_path = "../data/cc_cedict.json"
    if os.path.exists(full_path):
        success_full = test_dictionary(full_path)
    else:
        print(f"Full dictionary not found: {full_path}")
        success_full = True  # Don't fail if not available
    
    # Exit with appropriate code
    exit(0 if (success_demo and success_full) else 1)

