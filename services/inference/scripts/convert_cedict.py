"""
CC-CEDICT to JSON Converter

Converts CC-CEDICT dictionary format to JSON for use in Rune-X OCR fusion.

Usage:
    python convert_cedict.py <input_file> [--output <output_file>]

Example:
    python convert_cedict.py ../data/cedict_ts.u8 --output ../data/cc_cedict.json

Input Format (CEDICT):
    Traditional Simplified [pinyin] /definition1/definition2/definition3/

Output Format (JSON):
    {
        "学": {
            "simplified": "学",
            "traditional": "學",
            "pinyin": "xué",
            "definitions": ["to learn", "to study", "learning", "science"]
        }
    }
"""

import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def parse_cedict_line(line: str) -> tuple[str, Dict[str, Any]] | None:
    """
    Parse a single line from CC-CEDICT format.
    
    Format: Traditional Simplified [pinyin] /definition1/definition2/
    Example: 學 学 [xue2] /to learn/to study/learning/science/
    
    Args:
        line: Single line from CEDICT file
        
    Returns:
        Tuple of (simplified_key, entry_dict) or None if line is invalid
    """
    # Skip comments and empty lines
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    
    # Parse CEDICT format using regex
    # Pattern: Traditional Simplified [pinyin] /def1/def2/.../
    pattern = r'^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.+)/$'
    match = re.match(pattern, line)
    
    if not match:
        logger.debug(f"Skipping malformed line: {line[:50]}...")
        return None
    
    traditional, simplified, pinyin, definitions_raw = match.groups()
    
    # Split definitions
    definitions = [d.strip() for d in definitions_raw.split('/') if d.strip()]
    
    # Create entry
    entry = {
        "simplified": simplified,
        "traditional": traditional,
        "pinyin": pinyin,
        "definitions": definitions
    }
    
    # Use simplified as the key
    return simplified, entry


def convert_cedict_to_json(
    input_path: str,
    output_path: str,
    include_metadata: bool = True
) -> Dict[str, Any]:
    """
    Convert CC-CEDICT file to JSON format.
    
    Args:
        input_path: Path to cedict_ts.u8 file
        output_path: Path to output JSON file
        include_metadata: Whether to include metadata header
        
    Returns:
        Dictionary with all entries
    """
    input_file = Path(input_path)
    output_file = Path(output_path)
    
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    logger.info(f"Reading CC-CEDICT from: {input_file}")
    logger.info("This may take a minute for large dictionaries...")
    
    dictionary = {}
    total_lines = 0
    parsed_lines = 0
    skipped_lines = 0
    
    # Read and parse CEDICT file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                total_lines += 1
                
                result = parse_cedict_line(line)
                if result:
                    key, entry = result
                    
                    # Handle duplicate keys (multi-character words vs single chars)
                    if key in dictionary:
                        # Keep the entry with more definitions or first one encountered
                        if len(entry['definitions']) > len(dictionary[key]['definitions']):
                            dictionary[key] = entry
                            logger.debug(f"Replaced '{key}' with more detailed entry")
                    else:
                        dictionary[key] = entry
                    
                    parsed_lines += 1
                    
                    if parsed_lines % 10000 == 0:
                        logger.info(f"Processed {parsed_lines:,} entries...")
                else:
                    skipped_lines += 1
                    
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error at line {total_lines}: {e}")
        logger.info("Try downloading a fresh copy of CC-CEDICT")
        raise
    
    logger.info(f"Parsing complete: {parsed_lines:,} entries extracted from {total_lines:,} lines")
    logger.info(f"Skipped {skipped_lines:,} lines (comments, empty, malformed)")
    
    # Add metadata header
    if include_metadata:
        dictionary["_metadata"] = {
            "source": "CC-CEDICT",
            "source_url": "https://www.mdbg.net/chinese/dictionary?page=cedict",
            "original_file": input_file.name,
            "conversion_date": datetime.now().isoformat(),
            "total_entries": parsed_lines,
            "total_lines_processed": total_lines,
            "format_version": "1.0"
        }
    
    # Write to JSON
    logger.info(f"Writing JSON to: {output_file}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dictionary, f, ensure_ascii=False, indent=2)
    
    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    logger.info(f"Conversion complete! Output size: {file_size_mb:.2f} MB")
    logger.info(f"Total entries in dictionary: {parsed_lines:,}")
    
    return dictionary


def validate_dictionary(dictionary: Dict[str, Any]) -> bool:
    """
    Validate the converted dictionary structure.
    
    Args:
        dictionary: Converted dictionary
        
    Returns:
        True if valid, raises exception otherwise
    """
    logger.info("Validating dictionary structure...")
    
    # Check metadata
    if "_metadata" not in dictionary:
        logger.warning("Metadata not found in dictionary")
    
    # Check sample entries
    required_fields = {"simplified", "traditional", "pinyin", "definitions"}
    sample_count = 0
    
    for key, entry in dictionary.items():
        if key == "_metadata":
            continue
            
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid entry for '{key}': not a dictionary")
        
        missing_fields = required_fields - set(entry.keys())
        if missing_fields:
            raise ValueError(f"Entry '{key}' missing fields: {missing_fields}")
        
        if not isinstance(entry["definitions"], list):
            raise ValueError(f"Entry '{key}' definitions must be a list")
        
        sample_count += 1
        if sample_count >= 100:
            break
    
    logger.info(f"Validation passed! Checked {sample_count} sample entries")
    return True


def main():
    """Main conversion script."""
    parser = argparse.ArgumentParser(description='Convert CC-CEDICT to JSON format')
    parser.add_argument('input', help='Input CEDICT file (cedict_ts.u8)')
    parser.add_argument('--output', '-o', help='Output JSON file', default=None)
    parser.add_argument('--no-metadata', action='store_true', help='Skip metadata header')
    parser.add_argument('--validate', action='store_true', help='Validate output JSON', default=True)
    
    args = parser.parse_args()
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        input_path = Path(args.input)
        output_path = input_path.parent / 'cc_cedict.json'
    
    logger.info("=" * 60)
    logger.info("CC-CEDICT to JSON Converter")
    logger.info("=" * 60)
    
    try:
        # Convert
        dictionary = convert_cedict_to_json(
            args.input,
            output_path,
            include_metadata=not args.no_metadata
        )
        
        # Validate
        if args.validate:
            validate_dictionary(dictionary)
        
        logger.info("=" * 60)
        logger.info("✅ Conversion successful!")
        logger.info(f"📁 Output file: {output_path}")
        logger.info(f"📊 Entries: {len(dictionary) - 1:,} (excluding metadata)")
        logger.info("=" * 60)
        
        # Print sample entries
        logger.info("\n📖 Sample entries:")
        sample_keys = list(k for k in list(dictionary.keys())[:5] if k != "_metadata")
        for key in sample_keys:
            entry = dictionary[key]
            logger.info(f"  {key}: {entry['pinyin']} - {entry['definitions'][0]}")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Conversion failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())

