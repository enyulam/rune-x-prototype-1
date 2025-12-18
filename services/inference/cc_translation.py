"""
CC-CEDICT Translation Module

This module provides character-level translation using the comprehensive CC-CEDICT dictionary.
It replaces the limited 276-entry RuleBasedTranslator with 120,474 entries from CC-CEDICT,
increasing translation coverage from ~30% to ~80%+.

Key Features:
- Character-level translation with CC-CEDICT (120,474 entries)
- Multiple definition handling with intelligent selection strategies
- Traditional/Simplified form support
- Comprehensive metadata and statistics
- Graceful fallback for unmapped characters

Usage:
    from cc_dictionary import CCDictionary
    from cc_translation import CCDictionaryTranslator
    
    cc_dict = CCDictionary("data/cc_cedict.json")
    translator = CCDictionaryTranslator(cc_dict)
    result = translator.translate_text("你好世界", glyphs)
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from cc_dictionary import CCDictionary

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class DefinitionStrategy(Enum):
    """Strategies for selecting primary definition from multiple options."""
    FIRST = "first"           # Use first definition (default, simplest)
    SHORTEST = "shortest"     # Use shortest definition (most concise)
    MOST_COMMON = "common"    # Use most common English words (future enhancement)
    CONTEXT_AWARE = "context" # Based on surrounding characters (future enhancement)


@dataclass
class TranslationCandidate:
    """
    Represents a single translation candidate for a character.
    
    Attributes:
        definition: English definition/meaning
        rank: Position in the original definition list (0 = first)
        selected: Whether this is the primary selected definition
    """
    definition: str
    rank: int
    selected: bool = False
    
    def __repr__(self) -> str:
        status = "✓" if self.selected else " "
        return f"[{status}] #{self.rank}: {self.definition}"


@dataclass
class CharacterTranslation:
    """
    Complete translation information for a single character.
    
    Attributes:
        character: The source Chinese character
        primary_definition: The selected primary English meaning
        all_definitions: List of all available definitions from CC-CEDICT
        candidates: List of TranslationCandidate objects with metadata
        pinyin: Pronunciation (if available)
        traditional_form: Traditional form (if different from character)
        simplified_form: Simplified form (if different from character)
        found_in_dictionary: Whether character exists in CC-CEDICT
        strategy_used: Which selection strategy was applied
    """
    character: str
    primary_definition: str
    all_definitions: List[str] = field(default_factory=list)
    candidates: List[TranslationCandidate] = field(default_factory=list)
    pinyin: Optional[str] = None
    traditional_form: Optional[str] = None
    simplified_form: Optional[str] = None
    found_in_dictionary: bool = False
    strategy_used: Optional[str] = None
    
    def __repr__(self) -> str:
        status = "✓" if self.found_in_dictionary else "✗"
        pinyin_str = f" [{self.pinyin}]" if self.pinyin else ""
        return f"{status} '{self.character}'{pinyin_str} → {self.primary_definition}"


@dataclass
class TranslationResult:
    """
    Complete translation result for text with metadata.
    
    This matches the structure expected by main.py's API response.
    
    Attributes:
        original_text: The source Chinese text
        translation: Space-separated English translation
        character_translations: Detailed per-character translation info
        unmapped: List of characters not found in CC-CEDICT
        coverage: Percentage of characters found (0.0-100.0)
        total_characters: Total number of characters processed
        mapped_characters: Number of characters found in dictionary
        strategy_used: Primary definition selection strategy
        translation_source: Always "CC-CEDICT" for this translator
        metadata: Additional metadata and statistics
    """
    original_text: str
    translation: str
    character_translations: List[CharacterTranslation] = field(default_factory=list)
    unmapped: List[str] = field(default_factory=list)
    coverage: float = 0.0
    total_characters: int = 0
    mapped_characters: int = 0
    strategy_used: str = "first"
    translation_source: str = "CC-CEDICT"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format compatible with main.py's translator.translate_text() return value.
        
        Returns:
            Dict with keys: translation, unmapped, coverage, metadata
        """
        return {
            "translation": self.translation,
            "unmapped": self.unmapped,
            "coverage": self.coverage,
            "metadata": {
                "translation_source": self.translation_source,
                "strategy_used": self.strategy_used,
                "total_characters": self.total_characters,
                "mapped_characters": self.mapped_characters,
                **self.metadata
            }
        }


# ============================================================================
# CC-CEDICT Translator Class
# ============================================================================

class CCDictionaryTranslator:
    """
    Character-level translator using CC-CEDICT dictionary.
    
    This class provides translation services using the comprehensive CC-CEDICT
    dictionary (120,474 entries), replacing the limited 276-entry RuleBasedTranslator.
    
    Features:
    - Multiple definition handling with configurable selection strategies
    - Traditional/Simplified form support
    - Comprehensive metadata and statistics
    - Character-level and full-text translation
    - Graceful handling of unmapped characters
    
    Example:
        translator = CCDictionaryTranslator(cc_dictionary)
        result = translator.translate_text("你好", glyphs)
        print(result.translation)  # "you good"
        print(result.coverage)      # 100.0
    """
    
    def __init__(
        self,
        cc_dictionary: Optional[CCDictionary],
        default_strategy: DefinitionStrategy = DefinitionStrategy.FIRST
    ):
        """
        Initialize the CC-CEDICT translator.
        
        Args:
            cc_dictionary: CCDictionary instance (can be None for testing/fallback)
            default_strategy: Default strategy for selecting primary definitions
            
        Raises:
            ValueError: If cc_dictionary is None (should use RuleBasedTranslator as fallback)
        """
        if cc_dictionary is None:
            logger.warning("CCDictionaryTranslator initialized with None dictionary. Translation will fail.")
            # Don't raise error - allow initialization for fallback logic
        
        self.cc_dictionary = cc_dictionary
        self.default_strategy = default_strategy
        
        # Statistics
        self._stats = {
            "total_translations": 0,
            "total_characters": 0,
            "mapped_characters": 0,
            "unmapped_characters": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        logger.info(
            "CCDictionaryTranslator initialized with %s entries (strategy: %s)",
            len(cc_dictionary) if cc_dictionary else 0,
            default_strategy.value
        )
    
    def translate_character(
        self,
        char: str,
        strategy: Optional[DefinitionStrategy] = None
    ) -> CharacterTranslation:
        """
        Translate a single Chinese character to English.
        
        Args:
            char: Single Chinese character to translate
            strategy: Definition selection strategy (uses default if None)
            
        Returns:
            CharacterTranslation object with all translation information
            
        Example:
            translation = translator.translate_character("好")
            print(translation.primary_definition)  # "good"
            print(translation.all_definitions)      # ["good", "well", "proper", ...]
        """
        self._stats["total_characters"] += 1
        
        if not char or len(char) != 1:
            logger.warning("Invalid character for translation: %r (length: %d)", char, len(char) if char else 0)
            return CharacterTranslation(
                character=char,
                primary_definition=char,  # Fallback: return character itself
                found_in_dictionary=False
            )
        
        # Handle whitespace and special characters
        if char.isspace() or not char.strip():
            return CharacterTranslation(
                character=char,
                primary_definition=" ",
                found_in_dictionary=False
            )
        
        # Check if dictionary is available
        if self.cc_dictionary is None:
            logger.debug("Dictionary not available for character: %s", char)
            return CharacterTranslation(
                character=char,
                primary_definition=char,
                found_in_dictionary=False
            )
        
        # Look up character in CC-CEDICT
        entry = self.cc_dictionary.lookup_character(char)
        
        if entry is None:
            # Character not found in dictionary
            self._stats["unmapped_characters"] += 1
            logger.debug("Character not in CC-CEDICT: %s", char)
            return CharacterTranslation(
                character=char,
                primary_definition=char,  # Fallback: return character itself
                found_in_dictionary=False
            )
        
        # Character found - extract information
        self._stats["mapped_characters"] += 1
        
        # Get definitions
        definitions = self.cc_dictionary.get_definitions(char)
        if not definitions:
            definitions = [char]  # Fallback
        
        # Get pinyin
        pinyin = self.cc_dictionary.get_pinyin(char)
        
        # Get traditional/simplified forms
        # Note: get_traditional() expects simplified char, returns traditional
        # get_simplified() expects traditional char, returns simplified
        traditional = self.cc_dictionary.get_traditional(char) if char else None
        simplified = self.cc_dictionary.get_simplified(char) if char else None
        
        # Select primary definition
        strategy_to_use = strategy or self.default_strategy
        primary_def = self.select_primary_definition(definitions, strategy_to_use)
        
        # Create candidates list
        candidates = [
            TranslationCandidate(
                definition=defn,
                rank=i,
                selected=(defn == primary_def)
            )
            for i, defn in enumerate(definitions)
        ]
        
        return CharacterTranslation(
            character=char,
            primary_definition=primary_def,
            all_definitions=definitions,
            candidates=candidates,
            pinyin=pinyin,
            traditional_form=traditional if traditional != char else None,
            simplified_form=simplified if simplified != char else None,
            found_in_dictionary=True,
            strategy_used=strategy_to_use.value
        )
    
    def select_primary_definition(
        self,
        definitions: List[str],
        strategy: DefinitionStrategy = DefinitionStrategy.FIRST
    ) -> str:
        """
        Select the primary definition from multiple options.
        
        Implements various strategies for choosing the "best" definition
        when CC-CEDICT provides multiple options for a character.
        
        Args:
            definitions: List of definition strings
            strategy: Strategy to use for selection
            
        Returns:
            Selected primary definition string
            
        Strategies:
            FIRST: Use first definition (default, most common meaning)
            SHORTEST: Use shortest definition (most concise)
            MOST_COMMON: Use definition with most common English words (future)
            CONTEXT_AWARE: Use surrounding context (future)
        """
        if not definitions:
            return ""
        
        if len(definitions) == 1:
            return definitions[0]
        
        # Strategy implementations
        if strategy == DefinitionStrategy.FIRST:
            # First definition is typically the most common/primary meaning
            return definitions[0]
        
        elif strategy == DefinitionStrategy.SHORTEST:
            # Shortest definition is typically most concise
            return min(definitions, key=len)
        
        elif strategy == DefinitionStrategy.MOST_COMMON:
            # TODO: Implement based on English word frequency
            # For now, fall back to FIRST
            logger.debug("MOST_COMMON strategy not yet implemented, using FIRST")
            return definitions[0]
        
        elif strategy == DefinitionStrategy.CONTEXT_AWARE:
            # TODO: Implement based on surrounding characters
            # For now, fall back to FIRST
            logger.debug("CONTEXT_AWARE strategy not yet implemented, using FIRST")
            return definitions[0]
        
        else:
            logger.warning("Unknown strategy: %s, using FIRST", strategy)
            return definitions[0]
    
    def translate_text(
        self,
        text: str,
        glyphs: Optional[List[Any]] = None,
        strategy: Optional[DefinitionStrategy] = None
    ) -> TranslationResult:
        """
        Translate Chinese text to English.
        
        This is the main translation method, compatible with RuleBasedTranslator's
        translate_text() method for drop-in replacement in main.py.
        
        Args:
            text: Chinese text to translate
            glyphs: Optional list of Glyph objects (for compatibility, not used in translation logic)
            strategy: Definition selection strategy (uses default if None)
            
        Returns:
            TranslationResult object with translation and metadata
            
        Example:
            result = translator.translate_text("你好世界", glyphs)
            print(result.translation)  # "you good world boundary"
            print(result.coverage)      # 100.0
            print(result.unmapped)      # []
        """
        self._stats["total_translations"] += 1
        
        logger.info("Translating text: %r (length: %d)", text[:50], len(text))
        
        if not text:
            logger.warning("Empty text provided for translation")
            return TranslationResult(
                original_text="",
                translation="",
                coverage=0.0
            )
        
        strategy_to_use = strategy or self.default_strategy
        
        # Translate each character
        char_translations = []
        for char in text:
            char_trans = self.translate_character(char, strategy_to_use)
            char_translations.append(char_trans)
        
        # Build translation string
        translation_parts = [ct.primary_definition for ct in char_translations]
        translation = " ".join(translation_parts)
        
        # Identify unmapped characters
        unmapped = [
            ct.character
            for ct in char_translations
            if not ct.found_in_dictionary and not ct.character.isspace()
        ]
        
        # Calculate coverage
        total_chars = len([c for c in text if not c.isspace()])
        mapped_chars = len([ct for ct in char_translations if ct.found_in_dictionary])
        coverage = (mapped_chars / total_chars * 100.0) if total_chars > 0 else 0.0
        
        result = TranslationResult(
            original_text=text,
            translation=translation,
            character_translations=char_translations,
            unmapped=list(set(unmapped)),  # Remove duplicates
            coverage=coverage,
            total_characters=total_chars,
            mapped_characters=mapped_chars,
            strategy_used=strategy_to_use.value,
            translation_source="CC-CEDICT",
            metadata={
                "dictionary_entries": len(self.cc_dictionary) if self.cc_dictionary else 0,
                "unique_unmapped": len(set(unmapped)),
                "total_unmapped": len(unmapped)
            }
        )
        
        logger.info(
            "Translation complete: %d/%d characters mapped (%.1f%% coverage), %d unique unmapped",
            mapped_chars, total_chars, coverage, len(set(unmapped))
        )
        
        return result
    
    def get_translation_metadata(self) -> Dict[str, Any]:
        """
        Get translator metadata and statistics.
        
        Returns:
            Dictionary containing:
            - translation_source: Always "CC-CEDICT"
            - dictionary_size: Number of entries in CC-CEDICT
            - default_strategy: Default definition selection strategy
            - statistics: Translation statistics (total, mapped, unmapped, etc.)
        """
        return {
            "translation_source": "CC-CEDICT",
            "dictionary_size": len(self.cc_dictionary) if self.cc_dictionary else 0,
            "default_strategy": self.default_strategy.value,
            "statistics": self._stats.copy(),
            "available_strategies": [s.value for s in DefinitionStrategy]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get current translation statistics.
        
        Returns:
            Dictionary with translation statistics
        """
        return self._stats.copy()
    
    def reset_stats(self) -> None:
        """Reset translation statistics."""
        self._stats = {
            "total_translations": 0,
            "total_characters": 0,
            "mapped_characters": 0,
            "unmapped_characters": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        logger.info("Translation statistics reset")
    
    def log_translation_stats(self, level: str = "info") -> None:
        """
        Log detailed translation statistics for monitoring and debugging.
        
        Args:
            level: Log level ("info" or "debug")
        """
        stats = self.get_stats()
        total_translations = stats.get("total_translations", 0)
        total_chars = stats.get("total_characters", 0)
        mapped_chars = stats.get("mapped_characters", 0)
        unmapped_chars = stats.get("unmapped_characters", 0)
        
        coverage_rate = (mapped_chars / total_chars * 100) if total_chars > 0 else 0.0
        
        log_func = logger.info if level == "info" else logger.debug
        log_func(
            "CCDictionaryTranslator Stats: translations=%d, characters=%d, "
            "mapped=%d, unmapped=%d, coverage=%.1f%%, strategy=%s",
            total_translations,
            total_chars,
            mapped_chars,
            unmapped_chars,
            coverage_rate,
            self.default_strategy.value
        )
    
    def __repr__(self) -> str:
        dict_size = len(self.cc_dictionary) if self.cc_dictionary else 0
        return f"CCDictionaryTranslator(entries={dict_size:,}, strategy={self.default_strategy.value})"
    
    def __len__(self) -> int:
        """Return number of dictionary entries."""
        return len(self.cc_dictionary) if self.cc_dictionary else 0


# ============================================================================
# Helper Functions
# ============================================================================

def create_translator(
    cc_dictionary: CCDictionary,
    strategy: str = "first"
) -> CCDictionaryTranslator:
    """
    Factory function to create CCDictionaryTranslator with string strategy.
    
    Args:
        cc_dictionary: CCDictionary instance
        strategy: Strategy name as string ("first", "shortest", "common", "context")
        
    Returns:
        Configured CCDictionaryTranslator instance
        
    Example:
        translator = create_translator(cc_dict, strategy="shortest")
    """
    try:
        strategy_enum = DefinitionStrategy(strategy)
    except ValueError:
        logger.warning("Invalid strategy: %s, using 'first'", strategy)
        strategy_enum = DefinitionStrategy.FIRST
    
    return CCDictionaryTranslator(cc_dictionary, default_strategy=strategy_enum)

