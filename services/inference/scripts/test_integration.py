"""Test CC-CEDICT integration in main.py."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

print("Testing CC-CEDICT integration in main.py...")
print("=" * 60)

# Import main to trigger initialization
import main

print(f"\nTranslator type: {type(main.translator)}")
print(f"Translator entries: {len(main.translator) if hasattr(main.translator, '__len__') else 'N/A'}")

print(f"\nCC-Dictionary type: {type(main.cc_dictionary)}")
if main.cc_dictionary:
    print(f"CC-Dictionary entries: {len(main.cc_dictionary):,}")
    print(f"CC-Dictionary source: {main.cc_dictionary.metadata.get('source', 'Unknown')}")
    
    # Test lookup
    test_char = "学"
    entry = main.cc_dictionary.lookup(test_char)
    if entry:
        print(f"\nTest lookup '{test_char}':")
        print(f"  Pinyin: {entry.get('pinyin')}")
        print(f"  Definitions: {entry.get('definitions', [])[:2]}")
        print(f"  ✓ CC-CEDICT is working!")
    else:
        print(f"\n✗ Lookup failed for '{test_char}'")
else:
    print("CC-Dictionary is None (fallback to translator)")

print("\n" + "=" * 60)
print("Integration test complete!")

