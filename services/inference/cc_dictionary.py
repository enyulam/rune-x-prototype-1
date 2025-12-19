"""
CC-CEDICT Dictionary Module

Provides efficient lookup and management of the CC-CEDICT Chinese-English dictionary
for use in OCR fusion and translation pipelines.

Features:
- Fast character/word lookups
- LRU caching for frequently accessed entries
- Graceful handling of missing entries
- Metadata access (source, version, statistics)
- Traditional/Simplified Chinese support
- Pinyin and multiple definitions per entry

Usage:
    from cc_dictionary import CCDictionary
    
    # Load dictionary
    dictionary = CCDictionary("data/cc_cedict.json")
    
    # Lookup a character
    entry = dictionary.lookup("学")
    if entry:
        print(f"Pinyin: {entry['pinyin']}")
        print(f"Definitions: {entry['definitions']}")
    
    # Check if character exists
    if dictionary.has_entry("好"):
        print("Character found in dictionary")
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from functools import lru_cache
from datetime import datetime

logger = logging.getLogger(__name__)


class CCDictionary:
    """
    CC-CEDICT Chinese-English Dictionary Manager.
    
    Loads and provides efficient access to the CC-CEDICT dictionary
    for character/word lookups during OCR fusion and translation.
    
    Attributes:
        dictionary_path (Path): Path to the JSON dictionary file
        data (Dict): Loaded dictionary data
        metadata (Dict): Dictionary metadata (source, version, etc.)
        entry_count (int): Number of entries in dictionary
    """
    
    def __init__(self, dictionary_path: str):
        """
        Initialize the CC-CEDICT dictionary.
        
        Args:
            dictionary_path: Path to the CC-CEDICT JSON file
            
        Raises:
            FileNotFoundError: If dictionary file doesn't exist
            json.JSONDecodeError: If dictionary file is invalid JSON
            ValueError: If dictionary structure is invalid
        """
        self.dictionary_path = Path(dictionary_path)
        self.data: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        self.entry_count: int = 0
        
        logger.info(f"Initializing CCDictionary from: {self.dictionary_path}")
        self._load_dictionary()
        logger.info(f"CCDictionary loaded: {self.entry_count:,} entries")
    
    def _load_dictionary(self) -> None:
        """
        Load the dictionary from JSON file.
        
        Raises:
            FileNotFoundError: If dictionary file doesn't exist
            json.JSONDecodeError: If JSON is malformed
            ValueError: If dictionary structure is invalid
        """
        if not self.dictionary_path.exists():
            raise FileNotFoundError(
                f"Dictionary file not found: {self.dictionary_path}"
            )
        
        try:
            logger.debug(f"Loading dictionary file: {self.dictionary_path}")
            start_time = datetime.now()
            
            with open(self.dictionary_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            
            # Extract and validate metadata
            self.metadata = self.data.get('_metadata', {})
            if not self.metadata:
                logger.warning("Dictionary metadata not found")
            
            # Count entries (excluding metadata)
            self.entry_count = len([k for k in self.data.keys() if k != '_metadata'])
            
            # Validate structure with a sample entry
            self._validate_structure()
            
            load_time = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Dictionary loaded successfully in {load_time:.2f}s: "
                f"{self.entry_count:,} entries"
            )
            
            # Log metadata if available
            if self.metadata:
                logger.debug(f"Dictionary source: {self.metadata.get('source', 'Unknown')}")
                logger.debug(f"Dictionary version: {self.metadata.get('format_version', 'Unknown')}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in dictionary file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading dictionary: {e}")
            raise
    
    def _validate_structure(self) -> None:
        """
        Validate dictionary structure by checking sample entries.
        
        Raises:
            ValueError: If dictionary structure is invalid
        """
        required_fields = {'simplified', 'traditional', 'pinyin', 'definitions'}
        
        # Check first non-metadata entry
        for key, value in self.data.items():
            if key == '_metadata':
                continue
            
            if not isinstance(value, dict):
                raise ValueError(f"Invalid entry format for '{key}': not a dictionary")
            
            missing_fields = required_fields - set(value.keys())
            if missing_fields:
                raise ValueError(
                    f"Entry '{key}' missing required fields: {missing_fields}"
                )
            
            if not isinstance(value['definitions'], list):
                raise ValueError(
                    f"Entry '{key}' definitions must be a list, got {type(value['definitions'])}"
                )
            
            # Only validate first entry
            logger.debug(f"Dictionary structure validated (sample: '{key}')")
            break
        else:
            if self.entry_count == 0:
                raise ValueError("Dictionary contains no entries")
    
    def lookup(self, character: str) -> Optional[Dict[str, Any]]:
        """
        Look up a character or word in the dictionary.
        
        Args:
            character: Chinese character or word to look up
            
        Returns:
            Dictionary entry with keys:
                - simplified (str): Simplified Chinese
                - traditional (str): Traditional Chinese
                - pinyin (str): Pinyin pronunciation
                - definitions (List[str]): List of English definitions
            Returns None if character not found.
        """
        if not character:
            return None
        
        return self._cached_lookup(character)
    
    @lru_cache(maxsize=2000)  # Increased from 1000 for better performance
    def _cached_lookup(self, character: str) -> Optional[Dict[str, Any]]:
        """
        Cached lookup implementation.
        
        Uses LRU cache to speed up repeated lookups of the same characters.
        Increased cache size to 2000 for better hit rate on longer documents.
        
        Args:
            character: Chinese character or word to look up
            
        Returns:
            Dictionary entry or None if not found
        """
        entry = self.data.get(character)
        
        if entry and isinstance(entry, dict) and 'pinyin' in entry:
            return entry
        
        return None
    
    def lookup_character(self, character: str) -> Optional[str]:
        """
        Look up a character and return its primary meaning.
        
        This is a simplified lookup method for OCR fusion tie-breaking.
        Returns just the first definition as a string.
        
        Args:
            character: Chinese character to look up
            
        Returns:
            First definition string, or None if not found
        """
        entry = self.lookup(character)
        if entry and entry.get('definitions'):
            return entry['definitions'][0]
        return None
    
    def lookup_entry(self, character: str) -> Optional[Dict[str, Any]]:
        """
        Alias for lookup() to maintain compatibility with Translator API.
        
        Args:
            character: Chinese character or word to look up
            
        Returns:
            Dictionary entry or None if not found
        """
        return self.lookup(character)
    
    def has_entry(self, character: str) -> bool:
        """
        Check if a character exists in the dictionary.
        
        Args:
            character: Chinese character or word to check
            
        Returns:
            True if character exists in dictionary, False otherwise
        """
        if not character:
            return False
        return character in self.data and character != '_metadata'
    
    def get_pinyin(self, character: str) -> Optional[str]:
        """
        Get the pinyin pronunciation for a character.
        
        Args:
            character: Chinese character or word
            
        Returns:
            Pinyin string or None if not found
        """
        entry = self.lookup(character)
        return entry.get('pinyin') if entry else None
    
    def get_definitions(self, character: str) -> List[str]:
        """
        Get all definitions for a character.
        
        Args:
            character: Chinese character or word
            
        Returns:
            List of definition strings (empty list if not found)
        """
        entry = self.lookup(character)
        return entry.get('definitions', []) if entry else []
    
    def get_traditional(self, simplified: str) -> Optional[str]:
        """
        Get the traditional form of a simplified character.
        
        Args:
            simplified: Simplified Chinese character or word
            
        Returns:
            Traditional form or None if not found
        """
        entry = self.lookup(simplified)
        return entry.get('traditional') if entry else None
    
    def get_simplified(self, traditional: str) -> Optional[str]:
        """
        Get the simplified form of a traditional character.
        
        Note: This searches through entries, which is slower than direct lookup.
        For efficiency, consider building a reverse index if needed frequently.
        
        Args:
            traditional: Traditional Chinese character or word
            
        Returns:
            Simplified form or None if not found
        """
        # First try direct lookup (in case traditional is also the key)
        entry = self.lookup(traditional)
        if entry:
            return entry.get('simplified')
        
        # If not found, search through entries (slower)
        for key, entry in self.data.items():
            if key == '_metadata':
                continue
            if isinstance(entry, dict) and entry.get('traditional') == traditional:
                return entry.get('simplified')
        
        return None
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get dictionary metadata.
        
        Returns:
            Dictionary containing metadata fields:
                - source: Dictionary source name
                - source_url: URL to source
                - conversion_date: When it was converted
                - total_entries: Number of entries
                - format_version: Format version
        """
        return self.metadata.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get dictionary statistics.
        
        Returns:
            Dictionary containing:
                - entry_count: Total number of entries
                - cache_info: LRU cache statistics
                - metadata: Dictionary metadata
        """
        cache_info = self._cached_lookup.cache_info()
        
        return {
            'entry_count': self.entry_count,
            'cache_hits': cache_info.hits,
            'cache_misses': cache_info.misses,
            'cache_size': cache_info.currsize,
            'cache_maxsize': cache_info.maxsize,
            'metadata': self.metadata
        }
    
    def clear_cache(self) -> None:
        """Clear the LRU lookup cache."""
        self._cached_lookup.cache_clear()
        logger.debug("Dictionary lookup cache cleared")
    
    def log_performance_stats(self, level: str = "info") -> None:
        """
        Log detailed performance statistics.
        
        Useful for monitoring dictionary performance and cache effectiveness.
        
        Args:
            level: Logging level ("info" or "debug")
        """
        stats = self.get_stats()
        
        # Calculate cache hit rate
        total_requests = stats['cache_hits'] + stats['cache_misses']
        hit_rate = (stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0.0
        
        log_func = logger.info if level == "info" else logger.debug
        
        log_func(
            "CCDictionary Performance Stats: "
            "entries=%d, cache_hits=%d, cache_misses=%d, "
            "cache_size=%d/%d, hit_rate=%.1f%%",
            stats['entry_count'],
            stats['cache_hits'],
            stats['cache_misses'],
            stats['cache_size'],
            stats['cache_maxsize'],
            hit_rate
        )
    
    def batch_lookup(self, characters: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Look up multiple characters at once.
        
        Args:
            characters: List of characters/words to look up
            
        Returns:
            Dictionary mapping each character to its entry (or None if not found)
        """
        results = {}
        for char in characters:
            results[char] = self.lookup(char)
        return results
    
    def __len__(self) -> int:
        """Return number of entries in dictionary."""
        return self.entry_count
    
    def __contains__(self, character: str) -> bool:
        """Support 'in' operator for checking if character exists."""
        return self.has_entry(character)
    
    def __repr__(self) -> str:
        """String representation of dictionary."""
        source = self.metadata.get('source', 'Unknown')
        return f"CCDictionary(entries={self.entry_count:,}, source='{source}')"


# Singleton instance for global access
_global_dictionary: Optional[CCDictionary] = None


def get_dictionary(dictionary_path: str = "data/cc_cedict.json") -> CCDictionary:
    """
    Get the global dictionary instance (singleton pattern).
    
    This ensures only one dictionary is loaded in memory across the application.
    
    Args:
        dictionary_path: Path to dictionary file (only used on first call)
        
    Returns:
        Global CCDictionary instance
    """
    global _global_dictionary
    
    if _global_dictionary is None:
        logger.info("Initializing global dictionary instance")
        _global_dictionary = CCDictionary(dictionary_path)
    
    return _global_dictionary


def reset_dictionary() -> None:
    """Reset the global dictionary instance (useful for testing)."""
    global _global_dictionary
    _global_dictionary = None
    logger.debug("Global dictionary instance reset")


# Example usage and testing
if __name__ == "__main__":
    # Configure logging for standalone testing
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Test with demo dictionary
    demo_path = "data/demo_cedict.json"
    
    print("=" * 60)
    print("CC-CEDICT Dictionary Test")
    print("=" * 60)
    
    try:
        # Load dictionary
        dictionary = CCDictionary(demo_path)
        print(f"\nLoaded: {dictionary}")
        print(f"Entries: {len(dictionary):,}")
        
        # Test lookups
        test_chars = ["学", "你", "好", "不存在"]
        print(f"\nTesting lookups for: {test_chars}")
        
        for char in test_chars:
            print(f"\n'{char}':")
            if char in dictionary:
                entry = dictionary.lookup(char)
                print(f"  Pinyin: {entry['pinyin']}")
                print(f"  Traditional: {entry['traditional']}")
                print(f"  Definitions: {entry['definitions'][:2]}")  # First 2
            else:
                print("  Not found")
        
        # Test batch lookup
        print("\nBatch lookup test:")
        results = dictionary.batch_lookup(["学", "你", "好"])
        print(f"  Found {sum(1 for v in results.values() if v)} / {len(results)}")
        
        # Show statistics
        print("\nDictionary statistics:")
        stats = dictionary.get_stats()
        for key, value in stats.items():
            if key != 'metadata':
                print(f"  {key}: {value}")
        
        print("\n" + "=" * 60)
        print("✅ Dictionary test complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

