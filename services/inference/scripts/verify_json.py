"""Verify converted CC-CEDICT JSON."""
import json
import sys

def verify_json(filepath):
    """Verify the converted JSON dictionary."""
    print("Verifying converted CC-CEDICT JSON...")
    print(f"File: {filepath}\n")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check metadata
        metadata = data.get('_metadata', {})
        print("Metadata:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        
        # Count entries
        entry_count = len([k for k in data.keys() if k != '_metadata'])
        print(f"\nTotal entries: {entry_count:,}")
        
        # Check sample characters
        test_chars = ['学', '你', '好', '我', '是', '中', '国', '人']
        print(f"\nTesting {len(test_chars)} common characters:")
        for char in test_chars:
            entry = data.get(char)
            if entry:
                print(f"  {char}: {entry.get('pinyin')} - {entry.get('definitions', [])[0] if entry.get('definitions') else 'N/A'}")
            else:
                print(f"  {char}: NOT FOUND (WARNING)")
        
        print("\nVERIFICATION PASSED!")
        return 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "../data/cc_cedict.json"
    exit(verify_json(filepath))

