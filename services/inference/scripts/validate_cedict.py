"""Validate CC-CEDICT file."""
import re
import sys

def validate_cedict(filepath):
    """Validate a CC-CEDICT file."""
    print("=" * 60)
    print("CC-CEDICT File Validation")
    print("=" * 60)
    print(f"File: {filepath}\n")
    
    total_lines = 0
    comment_lines = 0
    empty_lines = 0
    valid_entries = 0
    invalid_entries = 0
    
    # CEDICT format pattern
    pattern = r'^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.+)/$'
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                total_lines += 1
                line = line.strip()
                
                if not line:
                    empty_lines += 1
                elif line.startswith('#'):
                    comment_lines += 1
                elif re.match(pattern, line):
                    valid_entries += 1
                else:
                    invalid_entries += 1
                    if invalid_entries <= 5:  # Show first 5 invalid
                        print(f"Invalid line {line_num}: {line[:60]}...")
        
        print(f"Total lines: {total_lines:,}")
        print(f"Comment lines: {comment_lines:,}")
        print(f"Empty lines: {empty_lines:,}")
        print(f"Valid entries: {valid_entries:,}")
        print(f"Invalid entries: {invalid_entries:,}")
        
        # Calculate percentage
        if valid_entries > 0:
            entry_pct = (valid_entries / (valid_entries + invalid_entries)) * 100
            print(f"\nEntry validity: {entry_pct:.1f}%")
        
        # Verdict
        print("\n" + "=" * 60)
        if valid_entries > 100000 and entry_pct > 99:
            print("✅ VALID: File is a complete CC-CEDICT dictionary!")
            print(f"✅ Ready to convert {valid_entries:,} entries to JSON")
            return 0
        elif valid_entries > 1000:
            print("⚠️  PARTIAL: File contains dictionary entries but may be incomplete")
            return 0
        else:
            print("❌ INVALID: File does not appear to be a valid CC-CEDICT")
            return 1
            
    except UnicodeDecodeError as e:
        print(f"❌ ENCODING ERROR: {e}")
        print("File must be UTF-8 encoded")
        return 1
    except FileNotFoundError:
        print(f"❌ FILE NOT FOUND: {filepath}")
        return 1
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 1

if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "../data/cedict_ts.u8"
    exit(validate_cedict(filepath))

