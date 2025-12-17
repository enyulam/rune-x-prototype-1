#!/usr/bin/env python3
"""
Script to analyze unmapped characters from OCR results and suggest dictionary updates.
Reads from log files or processes recent uploads to identify missing dictionary entries.
"""

import json
import sys
from pathlib import Path
from collections import Counter
from typing import List, Dict

# Add parent directory to path to import translator
sys.path.insert(0, str(Path(__file__).parent.parent))

from translator import get_translator


def analyze_unmapped_chars(unmapped_lists: List[List[str]]) -> Dict:
    """
    Analyze unmapped characters and generate statistics.
    
    Args:
        unmapped_lists: List of unmapped character lists from multiple OCR runs
        
    Returns:
        Dictionary with analysis results
    """
    # Flatten and count occurrences
    all_unmapped = []
    for unmapped in unmapped_lists:
        all_unmapped.extend(unmapped)
    
    char_counts = Counter(all_unmapped)
    
    # Filter out punctuation and whitespace
    filtered_chars = {
        char: count for char, count in char_counts.items()
        if char.strip() and not char.isspace()
    }
    
    # Sort by frequency
    sorted_chars = sorted(
        filtered_chars.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    return {
        "total_occurrences": len(all_unmapped),
        "unique_chars": len(filtered_chars),
        "most_common": sorted_chars[:20],  # Top 20
        "all_chars": sorted_chars
    }


def generate_dictionary_suggestions(chars: List[str], output_path: Path) -> None:
    """
    Generate a template JSON file with unmapped characters for manual completion.
    
    Args:
        chars: List of unmapped characters
        output_path: Path to save suggestion file
    """
    suggestions = {}
    for char in set(chars):
        if char.strip() and not char.isspace():
            suggestions[char] = {
                "meaning": "",  # To be filled manually
                "alts": [],     # To be filled manually
                "notes": ""     # To be filled manually
            }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(suggestions, f, ensure_ascii=False, indent=2)
    
    print(f"Generated dictionary suggestions file: {output_path}")
    print(f"Found {len(suggestions)} unique unmapped characters")
    print("Please fill in the meanings, alts, and notes, then merge into dictionary.json")


def main():
    """Main function to process unmapped characters."""
    if len(sys.argv) < 2:
        print("Usage: python report_unmapped.py <unmapped_json_file> [output_suggestions.json]")
        print("\nExample:")
        print("  python report_unmapped.py unmapped_chars.json suggestions.json")
        print("\nInput file format:")
        print("  Option 1: JSON array of unmapped chars: [\"字\", \"符\", ...]")
        print("  Option 2: JSON object with 'unmapped' field: {\"unmapped\": [...]}")
        print("  Option 3: JSON array of result objects: [{\"unmapped\": [...]}, ...]")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("dictionary_suggestions.json")
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    
    # Load unmapped characters
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different input formats
        if isinstance(data, list):
            # Check if it's a list of strings or list of objects
            if len(data) > 0 and isinstance(data[0], str):
                unmapped_lists = [data]
            else:
                # List of result objects
                unmapped_lists = [item.get("unmapped", []) for item in data if isinstance(item, dict)]
        elif isinstance(data, dict) and "unmapped" in data:
            unmapped_lists = [data["unmapped"]]
        else:
            print("Error: Unrecognized input format")
            print("Expected: JSON array of strings, or object with 'unmapped' field, or array of result objects")
            sys.exit(1)
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}")
        sys.exit(1)
    
    # Analyze
    analysis = analyze_unmapped_chars(unmapped_lists)
    
    print("\n" + "="*60)
    print("Unmapped Characters Analysis")
    print("="*60)
    print(f"Total occurrences: {analysis['total_occurrences']}")
    print(f"Unique characters: {analysis['unique_chars']}")
    print("\nTop 20 most common unmapped characters:")
    print("-" * 60)
    for char, count in analysis['most_common']:
        print(f"  {char}: {count} occurrences")
    
    # Generate suggestions
    all_chars = [char for char, _ in analysis['all_chars']]
    generate_dictionary_suggestions(all_chars, output_file)
    
    print("\n" + "="*60)
    print("Next steps:")
    print("1. Review the suggestions file")
    print("2. Fill in meanings, alts, and notes")
    print("3. Merge into services/inference/data/dictionary.json")
    print("="*60)


if __name__ == "__main__":
    main()

