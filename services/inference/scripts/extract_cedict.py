"""
Extract CC-CEDICT from downloaded archive.

Usage:
    python extract_cedict.py <archive_file> [--output <output_file>]
"""

import zipfile
import gzip
import shutil
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def extract_zip(archive_path: Path, output_path: Path) -> bool:
    """Extract from ZIP archive."""
    try:
        with zipfile.ZipFile(archive_path, 'r') as z:
            # List contents
            files = z.namelist()
            logger.info(f"Archive contains: {files}")
            
            # Find the CEDICT file
            cedict_file = None
            for f in files:
                if 'cedict' in f.lower() and f.endswith('.txt'):
                    cedict_file = f
                    break
            
            if not cedict_file:
                cedict_file = files[0]  # Use first file
            
            logger.info(f"Extracting: {cedict_file}")
            
            # Extract to output location
            with z.open(cedict_file) as source:
                with open(output_path, 'wb') as target:
                    shutil.copyfileobj(source, target, length=1024*1024)
            
            return True
            
    except Exception as e:
        logger.error(f"ZIP extraction failed: {e}")
        return False


def extract_gzip(archive_path: Path, output_path: Path) -> bool:
    """Extract from GZIP archive."""
    try:
        with gzip.open(archive_path, 'rb') as f_in:
            with open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out, length=1024*1024)
        return True
    except Exception as e:
        logger.error(f"GZIP extraction failed: {e}")
        return False


def extract_cedict(archive_path: str, output_path: str) -> bool:
    """Extract CC-CEDICT from archive (ZIP or GZIP)."""
    archive = Path(archive_path)
    output = Path(output_path)
    
    if not archive.exists():
        logger.error(f"Archive not found: {archive}")
        return False
    
    logger.info(f"Extracting from: {archive}")
    logger.info(f"Output to: {output}")
    
    # Try ZIP first
    if extract_zip(archive, output):
        logger.info("✅ Extraction successful (ZIP)")
        return True
    
    # Try GZIP
    if extract_gzip(archive, output):
        logger.info("✅ Extraction successful (GZIP)")
        return True
    
    logger.error("❌ All extraction methods failed")
    return False


def main():
    parser = argparse.ArgumentParser(description='Extract CC-CEDICT from archive')
    parser.add_argument('archive', help='Archive file (ZIP or GZIP)')
    parser.add_argument('--output', '-o', help='Output file', required=True)
    
    args = parser.parse_args()
    
    success = extract_cedict(args.archive, args.output)
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

