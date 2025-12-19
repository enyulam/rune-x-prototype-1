"""
CC-CEDICT Download Helper

Downloads the latest CC-CEDICT dictionary from MDBG.net.

Usage:
    python download_cedict.py [--output <output_path>]

Example:
    python download_cedict.py --output ../data/cedict_ts.u8
"""

import argparse
import urllib.request
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# CC-CEDICT download URLs (try multiple sources)
CEDICT_URLS = [
    "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.zip",
    "https://raw.githubusercontent.com/skishore/makemeahanzi/master/cedict_ts.u8",
    "https://www.mdbg.net/chinese/export/cedict/cedict_ts.u8"
]


def download_cedict(output_path: str) -> bool:
    """
    Download CC-CEDICT from multiple sources.
    
    Args:
        output_path: Where to save the downloaded file
        
    Returns:
        True if successful, False otherwise
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("CC-CEDICT Download Helper")
    logger.info("=" * 60)
    logger.info(f"Output: {output_file}")
    logger.info("Trying multiple sources...")
    
    # Try each URL
    for idx, url in enumerate(CEDICT_URLS, 1):
        logger.info(f"\n[{idx}/{len(CEDICT_URLS)}] Trying: {url}")
        
        try:
            # Download file
            urllib.request.urlretrieve(url, output_file)
            
            # Verify download
            if output_file.exists() and output_file.stat().st_size > 0:
                file_size_mb = output_file.stat().st_size / (1024 * 1024)
                logger.info(f"✅ Download successful! File size: {file_size_mb:.2f} MB")
                
                # Count lines to verify
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        line_count = sum(1 for _ in f)
                    logger.info(f"📊 Total lines: {line_count:,}")
                except:
                    logger.warning("Could not count lines (may need to extract from archive)")
                
                return True
                
        except Exception as e:
            logger.warning(f"Failed: {e}")
            continue
    
    # All sources failed
    logger.error("\n❌ All download sources failed")
    logger.info("\n💡 Please download manually:")
    logger.info("   1. Visit: https://www.mdbg.net/chinese/dictionary?page=cedict")
    logger.info("   2. Click 'Download' for the UTF-8 version")
    logger.info(f"   3. Save to: {output_file.absolute()}")
    return False


def main():
    """Main download script."""
    parser = argparse.ArgumentParser(description='Download CC-CEDICT dictionary')
    parser.add_argument(
        '--output', '-o',
        help='Output file path',
        default='../data/cedict_ts.u8'
    )
    
    args = parser.parse_args()
    
    success = download_cedict(args.output)
    
    if success:
        logger.info("=" * 60)
        logger.info("✅ Next steps:")
        logger.info("1. Convert to JSON:")
        logger.info(f"   python convert_cedict.py {args.output} --output ../data/cc_cedict.json")
        logger.info("2. Backup old dictionary:")
        logger.info("   mv ../data/dictionary.json ../data/dictionary_old.json")
        logger.info("3. Use new dictionary:")
        logger.info("   mv ../data/cc_cedict.json ../data/dictionary.json")
        logger.info("=" * 60)
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())

