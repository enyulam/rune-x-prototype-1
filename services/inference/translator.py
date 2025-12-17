"""
Rule-Based Translation Module for Chinese Handwriting OCR
Provides dictionary-based character meaning lookup and translation
"""

import json
from typing import Dict, List, Optional
from pathlib import Path


class RuleBasedTranslator:
    """
    Translates Chinese text using a dictionary-based approach.
    Provides per-character meanings and concatenated full-text translation.
    """
    
    def __init__(self, dictionary_path: Optional[str] = None):
        """
        Initialize translator with dictionary.
        
        Args:
            dictionary_path: Path to dictionary JSON file. 
                           Defaults to data/dictionary.json relative to this file.
        """
        if dictionary_path is None:
            # Default to data/dictionary.json relative to this module
            base_dir = Path(__file__).parent
            dictionary_path = base_dir / "data" / "dictionary.json"
        
        self.dictionary_path = Path(dictionary_path)
        self.dictionary: Dict = {}
        self.version = "1.0.0"
        self.load_dictionary()
    
    def load_dictionary(self) -> None:
        """Load dictionary from JSON file."""
        try:
            if not self.dictionary_path.exists():
                print(f"Warning: Dictionary not found at {self.dictionary_path}")
                print("Creating empty dictionary. Add dictionary.json to enable translation.")
                self.dictionary = {}
                return
            
            with open(self.dictionary_path, 'r', encoding='utf-8') as f:
                self.dictionary = json.load(f)
            
            print(f"Loaded dictionary with {len(self.dictionary)} entries from {self.dictionary_path}")
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in dictionary file: {e}")
            self.dictionary = {}
        except Exception as e:
            print(f"Error loading dictionary: {e}")
            self.dictionary = {}
    
    def lookup_meaning(self, char: str) -> Optional[str]:
        """
        Look up meaning for a single character or phrase.
        Also checks alternative/variant forms.
        
        Args:
            char: Chinese character or phrase to look up
            
        Returns:
            Meaning string if found, None otherwise
        """
        if not char or not char.strip():
            return None
        
        char = char.strip()
        
        # First try exact match
        if char in self.dictionary:
            entry = self.dictionary[char]
            if isinstance(entry, dict):
                return entry.get("meaning", None)
            elif isinstance(entry, str):
                return entry
        
        # Check alternative forms in all dictionary entries
        for key, entry in self.dictionary.items():
            if isinstance(entry, dict) and "alts" in entry:
                alts = entry.get("alts", [])
                # Check if char matches any alternative (exact match or contains)
                for alt in alts:
                    if isinstance(alt, str) and char in alt or alt == char:
                        return entry.get("meaning", None)
        
        return None
    
    def lookup_entry(self, char: str) -> Optional[Dict]:
        """
        Look up full dictionary entry for a character.
        
        Args:
            char: Chinese character to look up
            
        Returns:
            Full entry dict with meaning, alts, notes if found, None otherwise
        """
        if not char or char not in self.dictionary:
            # Check alternatives
            for key, entry in self.dictionary.items():
                if isinstance(entry, dict) and "alts" in entry:
                    alts = entry.get("alts", [])
                    for alt in alts:
                        if isinstance(alt, str) and char in alt or alt == char:
                            return entry
            return None
        
        entry = self.dictionary[char]
        if isinstance(entry, dict):
            return entry
        elif isinstance(entry, str):
            return {"meaning": entry}
        
        return None
    
    def translate_text(
        self, 
        text: str, 
        glyphs: List[Dict],
        separator: str = " | "
    ) -> Dict:
        """
        Translate text using dictionary lookup and enrich glyphs with meanings.
        
        Args:
            text: Full text string from OCR
            glyphs: List of glyph dictionaries with symbol, bbox, confidence
            separator: String to separate character meanings in translation
            
        Returns:
            Dictionary with:
            - glyphs: Enriched glyph list with meanings
            - translation: Concatenated translation string
            - unmapped: List of unmapped characters
            - coverage: Percentage of characters with meanings
        """
        if not text or not text.strip():
            return {
                "glyphs": [],
                "translation": "",
                "unmapped": [],
                "coverage": 0.0
            }
        
        # Split text into characters (handles both single chars and phrases)
        chars = list(text.replace(" ", "").replace("\n", ""))
        
        enriched_glyphs = []
        unmapped = []
        mapped_count = 0
        
        # Match glyphs to characters
        glyph_index = 0
        
        for i, char in enumerate(chars):
            # Try to find matching glyph (by position or symbol)
            glyph = None
            if glyph_index < len(glyphs):
                # Try to match by symbol first
                for g in glyphs[glyph_index:]:
                    if g.get("symbol", "").strip() == char:
                        glyph = g
                        glyph_index = glyphs.index(g) + 1
                        break
                
                # If no match, use next glyph by position
                if glyph is None and glyph_index < len(glyphs):
                    glyph = glyphs[glyph_index]
                    glyph_index += 1
            
            # Look up meaning and full entry
            entry = self.lookup_entry(char)
            meaning = entry.get("meaning") if entry else None
            
            if meaning:
                mapped_count += 1
            else:
                unmapped.append(char)
                meaning = "(unmapped)"
            
            # Build enriched glyph entry
            enriched_glyph = {
                "symbol": char,
                "meaning": meaning,
                "confidence": glyph.get("confidence", 0.0) if glyph else 0.0,
                "position": i
            }
            
            # Add bbox if available
            if glyph and "bbox" in glyph:
                enriched_glyph["bbox"] = glyph["bbox"]
            
            # Add notes if available
            if entry and "notes" in entry:
                enriched_glyph["notes"] = entry.get("notes")
            
            # Add alternatives if available
            if entry and "alts" in entry:
                enriched_glyph["alts"] = entry.get("alts", [])
            
            enriched_glyphs.append(enriched_glyph)
        
        # Build translation string
        meanings = [g["meaning"] for g in enriched_glyphs]
        translation = separator.join(meanings)
        
        # Calculate coverage
        total_chars = len(chars)
        coverage = (mapped_count / total_chars * 100) if total_chars > 0 else 0.0
        
        return {
            "glyphs": enriched_glyphs,
            "translation": translation,
            "unmapped": list(set(unmapped)),  # Unique unmapped chars
            "coverage": round(coverage, 1),
            "dictionary_version": self.version
        }
    
    def get_statistics(self) -> Dict:
        """
        Get dictionary statistics.
        
        Returns:
            Dictionary with stats about loaded dictionary
        """
        total_entries = len(self.dictionary)
        entries_with_alts = sum(
            1 for entry in self.dictionary.values()
            if isinstance(entry, dict) and "alts" in entry and entry["alts"]
        )
        entries_with_notes = sum(
            1 for entry in self.dictionary.values()
            if isinstance(entry, dict) and "notes" in entry and entry["notes"]
        )
        
        return {
            "total_entries": total_entries,
            "entries_with_alts": entries_with_alts,
            "entries_with_notes": entries_with_notes,
            "version": self.version,
            "dictionary_path": str(self.dictionary_path)
        }


# Global translator instance (singleton pattern)
_translator_instance: Optional[RuleBasedTranslator] = None


def get_translator(dictionary_path: Optional[str] = None) -> RuleBasedTranslator:
    """
    Get or create global translator instance.
    
    Args:
        dictionary_path: Optional path to dictionary file
        
    Returns:
        RuleBasedTranslator instance
    """
    global _translator_instance
    
    if _translator_instance is None:
        _translator_instance = RuleBasedTranslator(dictionary_path)
    
    return _translator_instance

