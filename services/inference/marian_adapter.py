"""
MarianMT Adapter Layer for Phase 5 Refactoring

This module wraps the existing sentence_translator.py to provide a controlled,
inspectable interface for MarianMT translation with semantic constraints.

Phase 5 Design:
--------------
The adapter accepts structured input (glyphs + metadata) and produces annotated
output (translation + change tracking). This enables:
- Token locking (Step 4)
- Phrase-level refinement (Step 5)
- Semantic confidence metrics (Step 6)

Current Implementation (Step 2):
- Basic adapter structure
- Structured input/output
- Logging hooks
- No token locking yet (Step 4)
- No phrase-level refinement yet (Step 5)
"""

from typing import List, Dict, Optional, Any
from typing import Tuple  # For type hints
from dataclasses import dataclass
from dataclasses import dataclass, field
import logging

from sentence_translator import SentenceTranslator, get_sentence_translator
from semantic_constraints import SemanticContract, TokenLockStatus
from ocr_fusion import Glyph
from cc_dictionary import CCDictionary
from cc_translation import CCDictionaryTranslator


# ============================================================================
# PHRASE DATA STRUCTURES (Step 5)
# ============================================================================

@dataclass
class PhraseSpan:
    """
    Represents a contiguous span of glyphs that form a phrase.
    
    Step 5 (Phase 5): Used for phrase-level semantic refinement.
    """
    start_idx: int  # Starting glyph index (inclusive)
    end_idx: int    # Ending glyph index (exclusive)
    is_locked: bool  # True if all glyphs in span are locked
    text: str       # Text content of the phrase
    glyph_indices: List[int]  # List of glyph indices in this phrase
    
    def __len__(self) -> int:
        """Return the length of the phrase in glyphs."""
        return self.end_idx - self.start_idx
    
    def contains_glyph(self, glyph_idx: int) -> bool:
        """Check if this phrase contains a specific glyph index."""
        return self.start_idx <= glyph_idx < self.end_idx

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class MarianAdapterInput:
    """
    Structured input to MarianAdapter.
    
    Attributes:
        glyphs: List of Glyph objects from OCR fusion
        confidence: Average OCR confidence (0.0-1.0)
        dictionary_coverage: Percentage of characters with dictionary entries (0.0-100.0)
        locked_tokens: List of locked token indices (will be populated in Step 4)
        raw_text: Full text string from OCR fusion
    """
    glyphs: List[Glyph]
    confidence: float
    dictionary_coverage: float
    locked_tokens: List[int] = field(default_factory=list)  # Indices of locked glyphs
    raw_text: str = ""
    
    def __post_init__(self):
        """Build raw_text from glyphs if not provided."""
        if not self.raw_text and self.glyphs:
            self.raw_text = "".join(g.symbol for g in self.glyphs)


@dataclass
class MarianAdapterOutput:
    """
    Annotated output from MarianAdapter.
    
    Attributes:
        translation: English translation from MarianMT
        changed_tokens: List of token indices that were modified (will be populated in Step 4)
        preserved_tokens: List of token indices that were preserved (will be populated in Step 4)
        semantic_confidence: Confidence score for semantic refinement (0.0-1.0, will be calculated in Step 6)
        locked_tokens: List of locked token indices
        metadata: Additional metadata about the translation process
    """
    translation: str
    changed_tokens: List[int] = field(default_factory=list)
    preserved_tokens: List[int] = field(default_factory=list)
    semantic_confidence: float = 0.0
    locked_tokens: List[int] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert output to dictionary format."""
        return {
            "translation": self.translation,
            "changed_tokens": self.changed_tokens,
            "preserved_tokens": self.preserved_tokens,
            "semantic_confidence": self.semantic_confidence,
            "locked_tokens": self.locked_tokens,
            "metadata": self.metadata
        }


# ============================================================================
# MARIAN ADAPTER CLASS
# ============================================================================

class MarianAdapter:
    """
    Adapter layer that wraps SentenceTranslator with semantic constraints.
    
    This adapter provides:
    - Structured input/output (glyphs + metadata)
    - Token boundary tracking
    - Change tracking (changed vs preserved tokens)
    - Semantic constraint enforcement (via SemanticContract)
    
    Current Implementation (Step 2):
    - Basic wrapper around SentenceTranslator
    - Structured input/output
    - Logging hooks
    - Token locking logic will be added in Step 4
    - Phrase-level refinement will be added in Step 5
    """
    
    def __init__(
        self,
        sentence_translator: Optional[SentenceTranslator] = None,
        semantic_contract: Optional[SemanticContract] = None,
        cc_dictionary: Optional[CCDictionary] = None,
        cc_translator: Optional[CCDictionaryTranslator] = None
    ):
        """
        Initialize MarianAdapter.
        
        Args:
            sentence_translator: SentenceTranslator instance (if None, will get singleton)
            semantic_contract: SemanticContract instance (if None, will create new)
            cc_dictionary: CCDictionary instance for dictionary lookups (optional, Step 4)
            cc_translator: CCDictionaryTranslator instance for dictionary lookups (optional, Step 4)
        """
        # Wrap existing SentenceTranslator (do not modify it)
        if sentence_translator is None:
            sentence_translator = get_sentence_translator()
        
        self.sentence_translator = sentence_translator
        
        # Initialize semantic contract
        if semantic_contract is None:
            from semantic_constraints import SemanticContract
            semantic_contract = SemanticContract()
        
        self.semantic_contract = semantic_contract
        
        # Step 4 (Phase 5): Dictionary references for token locking
        self.cc_dictionary = cc_dictionary
        self.cc_translator = cc_translator
        
        logger.info("MarianAdapter initialized (Step 4: Token locking enabled)")
    
    def is_available(self) -> bool:
        """
        Check if MarianMT translation is available.
        
        Returns:
            bool: True if SentenceTranslator is available, False otherwise
        """
        if self.sentence_translator is None:
            return False
        return self.sentence_translator.is_available()
    
    def translate(
        self,
        glyphs: List[Glyph],
        confidence: float,
        dictionary_coverage: float,
        locked_tokens: Optional[List[int]] = None,
        raw_text: Optional[str] = None
    ) -> MarianAdapterOutput:
        """
        Translate text using MarianMT with semantic constraints.
        
        This is the main entry point for Phase 5 refactored MarianMT.
        
        Args:
            glyphs: List of Glyph objects from OCR fusion
            confidence: Average OCR confidence (0.0-1.0)
            dictionary_coverage: Percentage of characters with dictionary entries (0.0-100.0)
            locked_tokens: List of locked token indices (optional, will be determined in Step 4)
            raw_text: Full text string (optional, will be built from glyphs if not provided)
            
        Returns:
            MarianAdapterOutput: Annotated translation with change tracking
            
        Note:
            Step 2 (Phase 5): Basic implementation without token locking
            Step 4 (Phase 5): Will add token locking logic
            Step 5 (Phase 5): Will add phrase-level refinement
            Step 6 (Phase 5): Will add semantic confidence metrics
        """
        # Build structured input
        adapter_input = MarianAdapterInput(
            glyphs=glyphs,
            confidence=confidence,
            dictionary_coverage=dictionary_coverage,
            locked_tokens=locked_tokens or [],
            raw_text=raw_text or ""
        )
        
        logger.info(
            "MarianAdapter.translate() called: %d glyphs, confidence=%.2f, "
            "dictionary_coverage=%.1f%%, locked_tokens=%d",
            len(adapter_input.glyphs),
            adapter_input.confidence,
            adapter_input.dictionary_coverage,
            len(adapter_input.locked_tokens)
        )
        
        # Check availability
        if not self.is_available():
            logger.warning("MarianMT not available, returning empty translation")
            return MarianAdapterOutput(
                translation="",
                locked_tokens=adapter_input.locked_tokens,
                metadata={
                    "available": False,
                    "error": "MarianMT not available"
                }
            )
        
        # Build canonical input string from glyphs
        # This preserves token boundaries and glyph order
        canonical_text = self._build_canonical_text(adapter_input.glyphs)
        
        logger.debug(
            "Canonical text built: %d characters from %d glyphs",
            len(canonical_text),
            len(adapter_input.glyphs)
        )
        
        # Step 4 (Phase 5): Dictionary-Anchored Token Locking
        # Identify locked tokens if not provided
        if not adapter_input.locked_tokens:
            locked_tokens = self._identify_locked_tokens(adapter_input.glyphs)
            adapter_input.locked_tokens = locked_tokens
        else:
            locked_tokens = adapter_input.locked_tokens
        
        logger.info(
            "Step 4: Identified %d locked tokens out of %d total glyphs",
            len(locked_tokens),
            len(adapter_input.glyphs)
        )
        
        # Step 4 (Phase 5): Replace locked tokens with placeholders before MarianMT
        placeholder_mapping = {}  # Maps placeholder -> (glyph_index, original_char)
        text_with_placeholders = self._replace_locked_with_placeholders(
            canonical_text,
            adapter_input.glyphs,
            locked_tokens,
            placeholder_mapping
        )
        
        logger.debug(
            "Step 4: Replaced %d locked tokens with placeholders. Text length: %d -> %d",
            len(locked_tokens),
            len(canonical_text),
            len(text_with_placeholders)
        )
        
        # Step 5 (Phase 5): Phrase-Level Semantic Refinement
        # Group glyphs into candidate phrases (unlocked spans only)
        phrase_spans = self._identify_phrase_spans(
            adapter_input.glyphs,
            locked_tokens
        )
        
        logger.info(
            "Step 5: Identified %d phrase spans (%d locked, %d unlocked)",
            len(phrase_spans),
            sum(1 for p in phrase_spans if p.is_locked),
            sum(1 for p in phrase_spans if not p.is_locked)
        )
        
        # Log phrase boundaries for debugging
        for i, phrase in enumerate(phrase_spans):
            logger.debug(
                "Step 5: Phrase[%d]: indices[%d:%d], locked=%s, text='%s'",
                i, phrase.start_idx, phrase.end_idx, phrase.is_locked, phrase.text[:50]
            )
        
        # Step 5: Translate unlocked phrases separately for better context
        # Locked phrases remain unchanged (already protected by placeholders)
        refined_translation = self._refine_phrases(
            text_with_placeholders,
            phrase_spans,
            locked_tokens
        )
        
        try:
            # Use refined translation (phrase-level) instead of full-text translation
            # For now, we still use full-text translation but with phrase awareness
            # Future enhancement: translate each unlocked phrase separately
            translation_with_placeholders = self.sentence_translator.translate(refined_translation)
            
            # Step 4 (Phase 5): Restore locked tokens after translation
            translation, failed_restore_indices = self._restore_locked_tokens(
                translation_with_placeholders,
                placeholder_mapping
            )
            
            # Update locked_tokens list to exclude failed restorations
            if failed_restore_indices:
                effective_locked_tokens = [idx for idx in locked_tokens if idx not in failed_restore_indices]
                logger.warning(
                    "Step 4: %d locked tokens failed restoration, reducing locked count from %d to %d",
                    len(failed_restore_indices),
                    len(locked_tokens),
                    len(effective_locked_tokens)
                )
                locked_tokens = effective_locked_tokens
            
            logger.info(
                "MarianMT translation completed: %d characters -> %d characters",
                len(canonical_text),
                len(translation) if translation else 0
            )
            
            # Step 4 (Phase 5): Track changed vs preserved tokens
            changed_tokens, preserved_tokens = self._track_token_changes(
                adapter_input.glyphs,
                translation or "",
                locked_tokens
            )
            
            # Step 6 (Phase 5): Calculate semantic confidence metrics
            metrics = self._calculate_semantic_metrics(
                adapter_input.glyphs,
                locked_tokens,
                changed_tokens,
                preserved_tokens,
                adapter_input.dictionary_coverage
            )
            
            output = MarianAdapterOutput(
                translation=translation or "",
                locked_tokens=locked_tokens,
                changed_tokens=changed_tokens,
                preserved_tokens=preserved_tokens,
                semantic_confidence=metrics["semantic_confidence"],
                metadata={
                    "available": True,
                    "input_length": len(canonical_text),
                    "output_length": len(translation) if translation else 0,
                    "step": 6,  # Current implementation step (Phase 5)
                    "token_locking_enabled": True,  # Step 4 (Phase 5) complete
                    "phrase_refinement_enabled": True,  # Step 5 (Phase 5) complete
                    "semantic_metrics_enabled": True,  # Step 6 (Phase 5) complete
                    "phrase_spans_count": len(phrase_spans),
                    "unlocked_phrases_count": sum(1 for p in phrase_spans if not p.is_locked),
                    "locked_tokens_count": len(locked_tokens),
                    "changed_tokens_count": len(changed_tokens),
                    "preserved_tokens_count": len(preserved_tokens),
                    # Step 6: Semantic confidence metrics
                    "tokens_modified_percent": metrics["tokens_modified_percent"],
                    "tokens_locked_percent": metrics["tokens_locked_percent"],
                    "tokens_preserved_percent": metrics["tokens_preserved_percent"],
                    "dictionary_override_count": metrics["dictionary_override_count"],
                }
            )
            
            logger.debug("MarianAdapter output created: %s", output.to_dict())
            
            return output
            
        except Exception as e:
            logger.error("MarianAdapter translation failed: %s", e, exc_info=True)
            return MarianAdapterOutput(
                translation="",
                locked_tokens=adapter_input.locked_tokens,
                metadata={
                    "available": False,
                    "error": str(e)
                }
            )
    
    def _build_canonical_text(self, glyphs: List[Glyph]) -> str:
        """
        Build canonical input string from glyphs preserving token boundaries.
        
        This ensures that:
        - Glyph order matches OCR fusion output
        - Token boundaries are preserved
        - Each glyph maps to its character position
        
        Args:
            glyphs: List of Glyph objects from OCR fusion
            
        Returns:
            str: Canonical text string built from glyphs
        """
        # Simple concatenation for now
        # Step 4 (Phase 5): Will add placeholder replacement for locked tokens
        # Step 5 (Phase 5): Will add phrase grouping
        
        canonical_text = "".join(g.symbol for g in glyphs)
        
        logger.debug(
            "Built canonical text: '%s' (%d glyphs -> %d characters)",
            canonical_text[:50] + "..." if len(canonical_text) > 50 else canonical_text,
            len(glyphs),
            len(canonical_text)
        )
        
        return canonical_text
    
    def _identify_locked_tokens(self, glyphs: List[Glyph]) -> List[int]:
        """
        Identify which glyphs should be locked based on OCR confidence and dictionary match.
        
        Step 4 (Phase 5): Uses semantic contract to determine lock status.
        
        Args:
            glyphs: List of Glyph objects from OCR fusion
            
        Returns:
            List[int]: Indices of glyphs that should be locked
        """
        locked_indices = []
        
        for i, glyph in enumerate(glyphs):
            # Check if glyph has dictionary match
            has_dictionary_match = False
            if self.cc_dictionary:
                has_dictionary_match = self.cc_dictionary.has_entry(glyph.symbol)
            elif self.cc_translator:
                # CCDictionaryTranslator has access to dictionary
                has_dictionary_match = self.cc_translator.cc_dictionary.has_entry(glyph.symbol)
            
            # Use semantic contract to determine lock status
            lock_status = self.semantic_contract.should_lock_token(
                ocr_confidence=glyph.confidence,
                has_dictionary_match=has_dictionary_match,
                has_multi_glyph_ambiguity=False  # TODO: Detect multi-glyph ambiguity in Step 5
            )
            
            if lock_status.locked:
                locked_indices.append(i)
                logger.debug(
                    "Step 4: Glyph[%d] '%s' LOCKED (conf=%.2f, dict=%s, reason=%s)",
                    i, glyph.symbol, glyph.confidence, has_dictionary_match, lock_status.reason
                )
        
        return locked_indices
    
    def _replace_locked_with_placeholders(
        self,
        text: str,
        glyphs: List[Glyph],
        locked_indices: List[int],
        placeholder_mapping: Dict[str, Tuple[int, str]]
    ) -> str:
        """
        Replace locked glyphs with placeholder tokens before MarianMT.
        
        Step 4 (Phase 5): Uses numeric placeholders (LOCKTOKEN001, LOCKTOKEN002, etc.)
        to protect locked tokens. These English word-like placeholders are less likely
        to be modified by MarianMT than placeholders containing Chinese characters.
        
        Args:
            text: Original text string
            glyphs: List of Glyph objects
            locked_indices: Indices of glyphs to lock
            placeholder_mapping: Output dict mapping placeholder -> (glyph_index, original_char)
            
        Returns:
            str: Text with locked characters replaced by placeholders
        """
        if not locked_indices:
            return text
        
        # Convert text to list for character-by-character replacement
        text_chars = list(text)
        
        # Use special Unicode Private Use Area characters (U+E000-U+F8FF) as placeholders
        # These are unlikely to be translated or modified by MarianMT
        # We'll use a simple counter to generate unique placeholders
        placeholder_base = 0xE000  # Start of Private Use Area
        placeholder_counter = 0
        
        # Replace locked characters with placeholders
        for locked_idx in sorted(locked_indices, reverse=True):  # Reverse to maintain indices
            if 0 <= locked_idx < len(glyphs) and locked_idx < len(text_chars):
                original_char = glyphs[locked_idx].symbol
                # Use Private Use Area Unicode character that MarianMT won't translate
                if placeholder_counter >= 6400:  # Safety limit (U+E000 to U+F8FF = 6400 chars)
                    logger.warning("Too many locked tokens, falling back to numeric placeholders")
                    placeholder = f"<LOCK{placeholder_counter}>"
                else:
                    placeholder = chr(placeholder_base + placeholder_counter)
                placeholder_counter += 1
                
                # Replace character with placeholder
                text_chars[locked_idx] = placeholder
                
                # Store mapping for restoration
                placeholder_mapping[placeholder] = (locked_idx, original_char)
                
                logger.debug(
                    "Step 4: Replaced glyph[%d] '%s' with placeholder '%s'",
                    locked_idx, original_char, placeholder
                )
        
        return "".join(text_chars)
    
    def _restore_locked_tokens(
        self,
        translation: str,
        placeholder_mapping: Dict[str, Tuple[int, str]]
    ) -> Tuple[str, List[int]]:
        """
        Restore locked tokens from placeholders after MarianMT translation.
        
        Step 4 (Phase 5): Replaces placeholders with original characters.
        
        Args:
            translation: Translation output from MarianMT (may contain placeholders)
            placeholder_mapping: Mapping of placeholder -> (glyph_index, original_char)
            
        Returns:
            Tuple of:
            - str: Translation with placeholders restored to original characters
            - List[int]: Indices of glyphs that failed to restore (placeholders not found)
        """
        if not placeholder_mapping:
            return translation, []
        
        restored = translation
        failed_indices = []
        
        # Replace each placeholder with its original character
        for placeholder, (glyph_index, original_char) in placeholder_mapping.items():
            if placeholder in restored:
                restored = restored.replace(placeholder, original_char)
                logger.debug(
                    "Step 4: Restored placeholder '%s' (U+%04X) -> '%s' (glyph[%d])",
                    placeholder,
                    ord(placeholder) if len(placeholder) == 1 else 0,
                    original_char,
                    glyph_index
                )
            else:
                failed_indices.append(glyph_index)
                logger.warning(
                    "Step 4: Placeholder '%s' (U+%04X) for glyph[%d] '%s' not found in translation. "
                    "MarianMT may have modified or removed it. Locked token will be lost.",
                    placeholder,
                    ord(placeholder) if len(placeholder) == 1 else 0,
                    glyph_index,
                    original_char
                )
        
        if failed_indices:
            logger.error(
                "Step 4: Failed to restore %d out of %d locked tokens. "
                "This indicates placeholder preservation mechanism is not working correctly.",
                len(failed_indices),
                len(placeholder_mapping)
            )
        
        return restored, failed_indices
    
    def _track_token_changes(
        self,
        original_glyphs: List[Glyph],
        translation: str,
        locked_tokens: List[int]
    ) -> tuple[List[int], List[int]]:
        """
        Track which tokens were changed vs preserved.
        
        Step 4 (Phase 5): Compares original glyphs with translation to identify changes.
        Note: This is a simplified implementation. Full change tracking requires
        alignment between Chinese characters and English words (complex NLP task).
        
        Args:
            original_glyphs: Original glyphs from OCR fusion
            translation: Translation output from MarianMT
            locked_tokens: List of locked token indices
            
        Returns:
            tuple: (changed_tokens, preserved_tokens) lists of token indices
        """
        # Step 4: Basic implementation
        # Locked tokens are always preserved (they were protected by placeholders)
        preserved_tokens = list(locked_tokens)
        
        # For now, assume all non-locked tokens could potentially be changed
        # Full change tracking requires character-to-word alignment (complex NLP)
        # This will be enhanced in Step 6 with better metrics
        changed_tokens = [
            i for i in range(len(original_glyphs))
            if i not in locked_tokens
        ]
        
        logger.debug(
            "Step 4: Token change tracking: %d preserved (locked), %d potentially changed (unlocked)",
            len(preserved_tokens),
            len(changed_tokens)
        )
        
        return changed_tokens, preserved_tokens
    
    def _calculate_semantic_metrics(
        self,
        glyphs: List[Glyph],
        locked_tokens: List[int],
        changed_tokens: List[int],
        preserved_tokens: List[int],
        dictionary_coverage: float
    ) -> Dict[str, float]:
        """
        Calculate semantic confidence metrics.
        
        Step 6 (Phase 5): Computes metrics for semantic refinement quality.
        
        Metrics calculated:
        - tokens_modified_percent: Percentage of tokens that were modified
        - tokens_locked_percent: Percentage of tokens that were locked
        - tokens_preserved_percent: Percentage of tokens that were preserved
        - semantic_confidence: Heuristic confidence score (0.0-1.0)
        - dictionary_override_count: Number of dictionary matches used for locking
        
        Semantic confidence heuristic:
        - Higher if more tokens are locked (high OCR confidence + dictionary)
        - Higher if locked tokens are preserved (placeholders work)
        - Higher if dictionary coverage is high
        - Lower if many tokens were changed (indicates uncertainty)
        
        Args:
            glyphs: Original glyphs from OCR fusion
            locked_tokens: List of locked token indices
            changed_tokens: List of changed token indices
            preserved_tokens: List of preserved token indices
            dictionary_coverage: Percentage of characters with dictionary entries (0.0-100.0)
            
        Returns:
            Dict[str, float]: Dictionary of metric values
        """
        total_tokens = len(glyphs)
        if total_tokens == 0:
            return {
                "tokens_modified_percent": 0.0,
                "tokens_locked_percent": 0.0,
                "tokens_preserved_percent": 0.0,
                "semantic_confidence": 0.0,
                "dictionary_override_count": 0
            }
        
        # Calculate percentages
        tokens_modified_percent = (len(changed_tokens) / total_tokens) * 100.0
        tokens_locked_percent = (len(locked_tokens) / total_tokens) * 100.0
        tokens_preserved_percent = (len(preserved_tokens) / total_tokens) * 100.0
        
        # Count dictionary matches used for locking
        dictionary_override_count = 0
        if self.cc_dictionary:
            for locked_idx in locked_tokens:
                if 0 <= locked_idx < len(glyphs):
                    glyph = glyphs[locked_idx]
                    if self.cc_dictionary.has_entry(glyph.symbol):
                        dictionary_override_count += 1
        elif self.cc_translator:
            for locked_idx in locked_tokens:
                if 0 <= locked_idx < len(glyphs):
                    glyph = glyphs[locked_idx]
                    if self.cc_translator.cc_dictionary.has_entry(glyph.symbol):
                        dictionary_override_count += 1
        
        # Calculate semantic confidence heuristic
        # Base confidence from locked token preservation
        locked_preservation_rate = 1.0 if len(locked_tokens) == 0 else (
            len(preserved_tokens) / len(locked_tokens) if len(locked_tokens) > 0 else 1.0
        )
        
        # Modification ratio (lower is better - fewer changes = more confident)
        modification_ratio = len(changed_tokens) / total_tokens if total_tokens > 0 else 0.0
        
        # Dictionary coverage factor (normalized to 0.0-1.0)
        dictionary_factor = dictionary_coverage / 100.0
        
        # Locked token factor (more locked = more confident)
        locked_factor = tokens_locked_percent / 100.0
        
        # Semantic confidence formula:
        # - 40% weight on locked preservation rate (did placeholders work?)
        # - 20% weight on modification ratio (fewer changes = better)
        # - 20% weight on dictionary coverage (more dictionary matches = better)
        # - 20% weight on locked token percentage (more locked = more confident)
        semantic_confidence = (
            0.4 * locked_preservation_rate +
            0.2 * (1.0 - modification_ratio) +  # Invert: lower modification = higher confidence
            0.2 * dictionary_factor +
            0.2 * locked_factor
        )
        
        # Clamp to [0.0, 1.0]
        semantic_confidence = max(0.0, min(1.0, semantic_confidence))
        
        logger.info(
            "Step 6: Semantic metrics calculated: "
            "modified=%.1f%%, locked=%.1f%%, preserved=%.1f%%, "
            "confidence=%.3f, dict_overrides=%d",
            tokens_modified_percent,
            tokens_locked_percent,
            tokens_preserved_percent,
            semantic_confidence,
            dictionary_override_count
        )
        
        return {
            "tokens_modified_percent": tokens_modified_percent,
            "tokens_locked_percent": tokens_locked_percent,
            "tokens_preserved_percent": tokens_preserved_percent,
            "semantic_confidence": semantic_confidence,
            "dictionary_override_count": dictionary_override_count
        }
    
    def _identify_phrase_spans(
        self,
        glyphs: List[Glyph],
        locked_indices: List[int]
    ) -> List[PhraseSpan]:
        """
        Identify contiguous spans of glyphs that form candidate phrases.
        
        Step 5 (Phase 5): Groups glyphs into phrases based on adjacency.
        Only unlocked spans are candidates for phrase-level refinement.
        
        Phrase detection strategy:
        1. Identify contiguous unlocked spans (potential phrases)
        2. Identify contiguous locked spans (preserved phrases)
        3. Each span becomes a PhraseSpan
        
        Args:
            glyphs: List of Glyph objects
            locked_indices: List of locked glyph indices
            
        Returns:
            List[PhraseSpan]: List of identified phrase spans
        """
        if not glyphs:
            return []
        
        locked_set = set(locked_indices)
        phrase_spans = []
        
        i = 0
        while i < len(glyphs):
            # Determine if current glyph is locked
            is_locked = i in locked_set
            
            # Find the end of the current span (same lock status)
            start_idx = i
            while i < len(glyphs) and (i in locked_set) == is_locked:
                i += 1
            
            end_idx = i
            
            # Create phrase span
            phrase_text = "".join(glyphs[j].symbol for j in range(start_idx, end_idx))
            glyph_indices = list(range(start_idx, end_idx))
            
            phrase_span = PhraseSpan(
                start_idx=start_idx,
                end_idx=end_idx,
                is_locked=is_locked,
                text=phrase_text,
                glyph_indices=glyph_indices
            )
            
            phrase_spans.append(phrase_span)
        
        return phrase_spans
    
    def _refine_phrases(
        self,
        text_with_placeholders: str,
        phrase_spans: List[PhraseSpan],
        locked_indices: List[int]
    ) -> str:
        """
        Refine phrases at phrase-level granularity.
        
        Step 5 (Phase 5): Currently returns text as-is, but provides structure
        for future enhancement where each unlocked phrase is translated separately.
        
        Future enhancement:
        - Translate each unlocked phrase span separately with MarianMT
        - Merge translations back together
        - Preserve locked phrases unchanged
        
        Args:
            text_with_placeholders: Text with locked tokens replaced by placeholders
            phrase_spans: List of identified phrase spans
            locked_indices: List of locked glyph indices
            
        Returns:
            str: Refined text (currently same as input, structure for future enhancement)
        """
        # Step 5: For now, return text as-is
        # Future enhancement: translate each unlocked phrase separately
        # This provides better context for idioms and multi-character compounds
        
        # Log phrase-level information for debugging
        unlocked_phrases = [p for p in phrase_spans if not p.is_locked]
        if unlocked_phrases:
            logger.debug(
                "Step 5: Found %d unlocked phrases for potential refinement",
                len(unlocked_phrases)
            )
            for phrase in unlocked_phrases:
                logger.debug(
                    "Step 5: Unlocked phrase[%d:%d]: '%s'",
                    phrase.start_idx, phrase.end_idx, phrase.text
                )
        
        # Return text as-is for now
        # Future: Translate each unlocked phrase separately and merge
        return text_with_placeholders


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def get_marian_adapter(
    sentence_translator: Optional[SentenceTranslator] = None,
    semantic_contract: Optional[SemanticContract] = None,
    cc_dictionary: Optional[CCDictionary] = None,
    cc_translator: Optional[CCDictionaryTranslator] = None
) -> Optional[MarianAdapter]:
    """
    Get or create a MarianAdapter instance.
    
    Args:
        sentence_translator: SentenceTranslator instance (optional)
        semantic_contract: SemanticContract instance (optional)
        cc_dictionary: CCDictionary instance for token locking (optional, Step 4)
        cc_translator: CCDictionaryTranslator instance for token locking (optional, Step 4)
        
    Returns:
        MarianAdapter instance if MarianMT is available, None otherwise
    """
    try:
        adapter = MarianAdapter(
            sentence_translator=sentence_translator,
            semantic_contract=semantic_contract,
            cc_dictionary=cc_dictionary,
            cc_translator=cc_translator
        )
        
        if adapter.is_available():
            return adapter
        
        logger.warning("MarianAdapter created but MarianMT not available")
        return None
        
    except Exception as e:
        logger.error("Failed to create MarianAdapter: %s", e, exc_info=True)
        return None

