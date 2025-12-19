"""
Qwen Adapter Layer for Phase 6 Refactoring

This module wraps the existing qwen_refiner.py to provide a controlled,
inspectable interface for Qwen translation refinement with semantic constraints.

Phase 6 Design:
--------------
The adapter accepts structured input (MarianAdapterOutput + metadata) and produces annotated
output (refined translation + change tracking). This enables:
- Token locking (Step 4)
- Phrase-level refinement (Step 5)
- Semantic confidence metrics (Step 6)

Current Implementation (Step 2):
- Basic adapter structure
- Structured input/output
- Logging hooks
- Token locking will be added in Step 4
- Phrase-level refinement will be added in Step 5
"""

from typing import List, Dict, Optional, Any
from typing import Tuple  # For type hints
from dataclasses import dataclass, field
import logging

from qwen_refiner import QwenRefiner, get_qwen_refiner
from semantic_constraints_qwen import QwenSemanticContract
from ocr_fusion import Glyph
from marian_adapter import PhraseSpan  # Reuse PhraseSpan from Phase 5

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class QwenAdapterInput:
    """
    Structured input to QwenAdapter.
    
    Attributes:
        text: MarianMT English translation from MarianAdapterOutput.translation
        glyphs: List of Glyph objects from OCR fusion
        locked_tokens: List of Chinese glyph indices locked by MarianAdapter
        preserved_tokens: List of Chinese glyph indices preserved by MarianAdapter
        changed_tokens: List of Chinese glyph indices changed by MarianAdapter
        semantic_metadata: Metadata from MarianAdapterOutput.metadata
        ocr_text: Original OCR text for context
        english_locked_tokens: Optional list of English token indices (populated in Step 5)
    """
    text: str  # MarianMT English translation
    glyphs: List[Glyph]
    locked_tokens: List[int]  # Chinese glyph indices from MarianAdapter
    preserved_tokens: List[int] = field(default_factory=list)
    changed_tokens: List[int] = field(default_factory=list)
    semantic_metadata: Dict[str, Any] = field(default_factory=dict)
    ocr_text: str = ""
    english_locked_tokens: Optional[List[int]] = None  # For Step 5 alignment mapping
    
    def __post_init__(self):
        """Validate input."""
        if not self.text:
            logger.warning("QwenAdapterInput: Empty text provided")
        if not self.glyphs:
            logger.warning("QwenAdapterInput: Empty glyphs list provided")


@dataclass
class QwenAdapterOutput:
    """
    Annotated output from QwenAdapter.
    
    Attributes:
        refined_text: Qwen-refined English translation
        changed_tokens: List of English token indices modified by Qwen
        preserved_tokens: List of English token indices preserved by Qwen
        locked_tokens: List of English token indices locked (from alignment mapping)
        qwen_confidence: Confidence score for Qwen refinement (0.0-1.0, calculated in Step 6)
        metadata: Additional metadata about the refinement process
    """
    refined_text: str
    changed_tokens: List[int] = field(default_factory=list)  # English token indices
    preserved_tokens: List[int] = field(default_factory=list)  # English token indices
    locked_tokens: List[int] = field(default_factory=list)  # English token indices
    qwen_confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert output to dictionary format."""
        return {
            "refined_text": self.refined_text,
            "changed_tokens": self.changed_tokens,
            "preserved_tokens": self.preserved_tokens,
            "locked_tokens": self.locked_tokens,
            "qwen_confidence": self.qwen_confidence,
            "metadata": self.metadata
        }


# ============================================================================
# QWEN ADAPTER CLASS
# ============================================================================

class QwenAdapter:
    """
    Adapter layer that wraps QwenRefiner with semantic constraints.
    
    This adapter provides:
    - Structured input/output (MarianAdapterOutput + metadata)
    - Token locking enforcement (Step 4)
    - Phrase-level refinement (Step 5)
    - Semantic confidence metrics (Step 6)
    - Change tracking (changed vs preserved tokens)
    
    Current Implementation (Step 2):
    - Basic wrapper around QwenRefiner
    - Structured input/output
    - Logging hooks
    - Token locking logic will be added in Step 4
    - Phrase-level refinement will be added in Step 5
    """
    
    def __init__(
        self,
        qwen_refiner: Optional[QwenRefiner] = None,
        semantic_contract: Optional[QwenSemanticContract] = None
    ):
        """
        Initialize QwenAdapter.
        
        Args:
            qwen_refiner: QwenRefiner instance (if None, will get singleton)
            semantic_contract: QwenSemanticContract instance (if None, will create new)
        """
        # Wrap existing QwenRefiner (do not modify it)
        if qwen_refiner is None:
            qwen_refiner = get_qwen_refiner()
        
        self.qwen_refiner = qwen_refiner
        
        # Initialize semantic contract
        if semantic_contract is None:
            from semantic_constraints_qwen import QwenSemanticContract
            semantic_contract = QwenSemanticContract()
        
        self.semantic_contract = semantic_contract
        
        logger.info("QwenAdapter initialized (Step 2: Basic adapter structure)")

    # ========================================================================
    # INTERNAL HELPERS - STEP 4 (TOKEN LOCKING)
    # ========================================================================

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """
        Basic tokenization for English text.

        For now, we use simple whitespace splitting. This is sufficient for
        smoke-testing token locking behavior and will be refined later if needed.
        """
        return text.split() if text else []

    def _replace_locked_with_placeholders(
        self,
        text: str,
        locked_token_indices: List[int],
    ) -> (str, Dict[str, str]):
        """
        Replace locked English tokens with placeholders before Qwen refinement.

        Args:
            text: Original MarianMT English translation
            locked_token_indices: List of token indices that must be preserved

        Returns:
            Tuple of:
            - text_with_placeholders: Text where locked tokens are replaced
            - placeholder_map: Mapping from placeholder -> original token
        """
        tokens = self._tokenize(text)
        placeholder_map: Dict[str, str] = {}

        if not tokens or not locked_token_indices:
            return text, placeholder_map

        for idx in locked_token_indices:
            if 0 <= idx < len(tokens):
                placeholder = f"__LOCK_T{idx}__"
                placeholder_map[placeholder] = tokens[idx]
                tokens[idx] = placeholder

        text_with_placeholders = " ".join(tokens)

        logger.debug(
            "QwenAdapter Step 4: Replaced %d locked tokens with placeholders",
            len(placeholder_map),
        )

        return text_with_placeholders, placeholder_map

    @staticmethod
    def _restore_locked_tokens(
        text: str,
        placeholder_map: Dict[str, str],
    ) -> str:
        """
        Restore original tokens from placeholders after Qwen refinement.

        Args:
            text: Refined text potentially containing placeholders
            placeholder_map: Mapping from placeholder -> original token

        Returns:
            Text with placeholders restored to original tokens
        """
        if not placeholder_map or not text:
            return text

        restored_text = text
        for placeholder, original in placeholder_map.items():
            if placeholder in restored_text:
                restored_text = restored_text.replace(placeholder, original)

        return restored_text

    def _track_qwen_changes(
        self,
        original_text: str,
        refined_text: str,
        locked_token_indices: List[int],
    ) -> (List[int], List[int]):
        """
        Track which tokens were changed vs preserved by Qwen.

        Locked tokens are always considered preserved and must not be marked
        as changed.

        Args:
            original_text: Original MarianMT translation
            refined_text: Qwen-refined translation (after placeholder restoration)
            locked_token_indices: List of locked token indices

        Returns:
            Tuple of:
            - changed_tokens: List[int] of token indices modified by Qwen
            - preserved_tokens: List[int] of token indices preserved by Qwen
        """
        original_tokens = self._tokenize(original_text)
        refined_tokens = self._tokenize(refined_text)

        changed_tokens: List[int] = []
        preserved_tokens: List[int] = []

        max_len = max(len(original_tokens), len(refined_tokens))

        locked_set = set(locked_token_indices or [])

        for idx in range(max_len):
            orig = original_tokens[idx] if idx < len(original_tokens) else None
            ref = refined_tokens[idx] if idx < len(refined_tokens) else None

            if idx in locked_set:
                # Locked tokens must be preserved; log if they are not
                if orig is not None and ref is not None and orig != ref:
                    logger.warning(
                        "QwenAdapter Step 4: Locked token at index %d was modified "
                        "(original='%s', refined='%s')",
                        idx,
                        orig,
                        ref,
                    )
                preserved_tokens.append(idx)
                continue

            # For unlocked tokens, track changes vs preservation
            if orig is None or ref is None or orig != ref:
                changed_tokens.append(idx)
            else:
                preserved_tokens.append(idx)

        logger.debug(
            "QwenAdapter Step 4: Tracked %d changed tokens, %d preserved tokens",
            len(changed_tokens),
            len(preserved_tokens),
        )

        return changed_tokens, preserved_tokens
    
    # ========================================================================
    # INTERNAL HELPERS - STEP 5 (PHRASE-LEVEL & ALIGNMENT PREPARATION)
    # ========================================================================

    def _map_glyphs_to_english_tokens(
        self,
        glyphs: List[Glyph],
        english_tokens: List[str],
        locked_glyph_indices: List[int],
    ) -> (Dict[int, List[int]], List[int]):
        """
        Map Chinese glyph indices to English token indices (heuristic).

        This is a lightweight heuristic mapping used for smoke-testing the
        alignment path. It assumes a roughly monotonic alignment between glyphs
        and English tokens:

        - Each English token is assigned to a glyph based on proportional index:
          glyph_index ≈ round(token_index * (len(glyphs) / len(tokens)))

        Args:
            glyphs: List of Glyph objects from OCR fusion
            english_tokens: Tokenized English translation
            locked_glyph_indices: List of locked glyph indices from MarianAdapter

        Returns:
            Tuple of:
            - glyph_to_tokens: Dict[glyph_index, List[token_index]]
            - locked_english_tokens: List[int] of English token indices that correspond
              to locked glyphs
        """
        glyph_to_tokens: Dict[int, List[int]] = {}
        locked_english_tokens: List[int] = []

        if not glyphs or not english_tokens:
            return glyph_to_tokens, locked_english_tokens

        num_glyphs = len(glyphs)
        num_tokens = len(english_tokens)

        # Assign each English token to a glyph index based on proportional position
        for token_idx in range(num_tokens):
            # Map token index into glyph index range [0, num_glyphs-1]
            glyph_idx = int(token_idx * num_glyphs / max(num_tokens, 1))
            glyph_idx = max(0, min(num_glyphs - 1, glyph_idx))

            glyph_to_tokens.setdefault(glyph_idx, []).append(token_idx)

        # Derive locked English tokens from locked glyph indices
        locked_set = set(locked_glyph_indices or [])
        english_locked_set: set[int] = set()

        for glyph_idx, token_indices in glyph_to_tokens.items():
            if glyph_idx in locked_set:
                for ti in token_indices:
                    english_locked_set.add(ti)

        locked_english_tokens = sorted(english_locked_set)

        logger.debug(
            "QwenAdapter Step 5: Mapped %d glyphs to %d English tokens "
            "(%d locked glyphs → %d locked English tokens)",
            len(glyphs),
            len(english_tokens),
            len(locked_set),
            len(locked_english_tokens),
        )

        return glyph_to_tokens, locked_english_tokens

    def _identify_phrase_spans(
        self,
        english_tokens: List[str],
        locked_english_tokens: List[int],
        glyph_to_tokens: Dict[int, List[int]],
    ) -> List[PhraseSpan]:
        """
        Identify contiguous spans of English tokens that form candidate phrases.

        This is the Step 5 analogue of phrase grouping in MarianAdapter, but
        operating on English tokens rather than Chinese glyphs.

        Args:
            english_tokens: List of English tokens from MarianMT output
            locked_english_tokens: List of locked English token indices
            glyph_to_tokens: Mapping from glyph index to English token indices

        Returns:
            List[PhraseSpan]: List of identified phrase spans
        """
        phrase_spans: List[PhraseSpan] = []

        if not english_tokens:
            return phrase_spans

        locked_set = set(locked_english_tokens or [])

        start_idx = 0
        current_locked = 0 in locked_set

        # Helper to collect glyph indices for a token span
        def collect_glyph_indices(token_start: int, token_end: int) -> List[int]:
            indices: List[int] = []
            for glyph_idx, token_indices in glyph_to_tokens.items():
                for ti in token_indices:
                    if token_start <= ti < token_end:
                        indices.append(glyph_idx)
                        break
            return sorted(set(indices))

        for idx in range(1, len(english_tokens)):
            is_locked = idx in locked_set
            if is_locked != current_locked:
                # Close current span
                phrase_text = " ".join(english_tokens[start_idx:idx])
                glyph_indices = collect_glyph_indices(start_idx, idx)
                phrase_spans.append(
                    PhraseSpan(
                        start_idx=start_idx,
                        end_idx=idx,
                        is_locked=current_locked,
                        text=phrase_text,
                        glyph_indices=glyph_indices,
                    )
                )
                # Start new span
                start_idx = idx
                current_locked = is_locked

        # Add final span
        end_idx = len(english_tokens)
        phrase_text = " ".join(english_tokens[start_idx:end_idx])
        glyph_indices = collect_glyph_indices(start_idx, end_idx)
        phrase_spans.append(
            PhraseSpan(
                start_idx=start_idx,
                end_idx=end_idx,
                is_locked=current_locked,
                text=phrase_text,
                glyph_indices=glyph_indices,
            )
        )

        locked_spans = sum(1 for p in phrase_spans if p.is_locked)
        unlocked_spans = len(phrase_spans) - locked_spans

        logger.debug(
            "QwenAdapter Step 5: Identified %d phrase spans (%d locked, %d unlocked)",
            len(phrase_spans),
            locked_spans,
            unlocked_spans,
        )

        return phrase_spans

    def _refine_phrases(
        self,
        phrase_spans: List[PhraseSpan],
        english_tokens: List[str],
    ) -> str:
        """
        Placeholder for phrase-level refinement.

        Current implementation:
        - Does NOT call Qwen per phrase yet (to keep Step 5 lightweight).
        - Logs unlocked phrases for debugging.
        - Returns the original text reconstructed from tokens.

        Future enhancement:
        - Call Qwen on each unlocked phrase separately.
        - Merge refined phrases back into final text.
        """
        if not phrase_spans or not english_tokens:
            return " ".join(english_tokens)

        unlocked_phrases = [p for p in phrase_spans if not p.is_locked]
        if unlocked_phrases:
            logger.debug(
                "QwenAdapter Step 5: Found %d unlocked phrases for potential refinement",
                len(unlocked_phrases),
            )
            for phrase in unlocked_phrases:
                logger.debug(
                    "QwenAdapter Step 5: Unlocked phrase[%d:%d]: '%s'",
                    phrase.start_idx,
                    phrase.end_idx,
                    phrase.text,
                )

        # For now, we simply reconstruct the original text
        return " ".join(english_tokens)

    # ========================================================================
    # INTERNAL HELPERS - STEP 6 (QWEN SEMANTIC CONFIDENCE)
    # ========================================================================

    def _calculate_qwen_confidence(
        self,
        original_text: str,
        refined_text: str,
        locked_tokens: List[int],
        phrase_spans: List[PhraseSpan],
        changed_tokens: List[int],
        preserved_tokens: List[int],
    ) -> (float, Dict[str, float]):
        """
        Calculate semantic confidence score for Qwen refinement.

        Heuristic:
        - 40% weight: locked token preservation rate
        - 30% weight: unlocked token stability (1 - modification_ratio)
        - 30% weight: phrase-level refinement score (dummy metric)

        Returns:
            Tuple of:
            - qwen_confidence in [0.0, 1.0]
            - factors dict for debugging
        """
        # Locked token preservation
        locked_set = set(locked_tokens or [])
        preserved_set = set(preserved_tokens or [])
        if locked_set:
            locked_preserved = len(locked_set & preserved_set)
            locked_preservation_rate = locked_preserved / len(locked_set)
        else:
            # If no locked tokens, treat as fully preserved for this term
            locked_preservation_rate = 1.0

        # Modification ratio for all tokens (changed vs total)
        total_tokens = len(changed_tokens) + len(preserved_tokens)
        modification_ratio = (
            len(changed_tokens) / total_tokens if total_tokens > 0 else 0.0
        )
        unlocked_stability = 1.0 - modification_ratio  # fewer changes → higher stability

        # Phrase-level score: simple heuristic based on unlocked phrases
        unlocked_phrases = [p for p in phrase_spans if not p.is_locked]
        if unlocked_phrases:
            phrase_score = 0.8  # some phrase-level refinement structure in place
        else:
            phrase_score = 0.5  # no unlocked phrases identified

        # Weighted combination
        confidence = (
            0.4 * locked_preservation_rate
            + 0.3 * unlocked_stability
            + 0.3 * phrase_score
        )

        # Clamp to [0.0, 1.0]
        confidence = max(0.0, min(1.0, confidence))

        factors = {
            "locked_preservation_rate": locked_preservation_rate,
            "modification_ratio": modification_ratio,
            "unlocked_stability": unlocked_stability,
            "phrase_score": phrase_score,
        }

        logger.debug(
            "QwenAdapter Step 6: qwen_confidence=%.3f "
            "(locked_preservation_rate=%.3f, modification_ratio=%.3f, "
            "unlocked_stability=%.3f, phrase_score=%.3f)",
            confidence,
            locked_preservation_rate,
            modification_ratio,
            unlocked_stability,
            phrase_score,
        )

        return confidence, factors

    def is_available(self) -> bool:
        """
        Check if Qwen refinement is available.
        
        Returns:
            bool: True if QwenRefiner is available, False otherwise
        """
        if self.qwen_refiner is None:
            return False
        return self.qwen_refiner.is_available()
    
    def translate(
        self,
        input: QwenAdapterInput
    ) -> Optional[QwenAdapterOutput]:
        """
        Refine translation using Qwen with semantic constraints.
        
        This is the main entry point for Phase 6 refactored Qwen refinement.
        
        Args:
            input: QwenAdapterInput with MarianMT translation and metadata
            
        Returns:
            QwenAdapterOutput with refined translation and metadata, or None if refinement fails
        """
        if not self.is_available():
            logger.warning("QwenAdapter: QwenRefiner not available, cannot refine translation")
            return None
        
        if not input.text or not input.text.strip():
            logger.warning("QwenAdapter: Empty translation text, skipping refinement")
            return None
        
        logger.info(
            "Phase 6: QwenAdapter refining translation: %d glyphs, %d locked tokens (Chinese)",
            len(input.glyphs),
            len(input.locked_tokens),
        )

        # --------------------------------------------------------------------
        # Step 5: Glyph → English token alignment & phrase spans
        # --------------------------------------------------------------------
        english_tokens = self._tokenize(input.text)
        glyph_to_tokens, mapped_locked_english = self._map_glyphs_to_english_tokens(
            glyphs=input.glyphs,
            english_tokens=english_tokens,
            locked_glyph_indices=input.locked_tokens,
        )

        # If english_locked_tokens not explicitly provided, use mapped values
        english_locked_tokens = input.english_locked_tokens or mapped_locked_english

        phrase_spans = self._identify_phrase_spans(
            english_tokens=english_tokens,
            locked_english_tokens=english_locked_tokens,
            glyph_to_tokens=glyph_to_tokens,
        )

        # --------------------------------------------------------------------
        # Step 4: Token Locking Enforcement (English tokens)
        # --------------------------------------------------------------------
        try:
            # Replace locked tokens with placeholders before refinement
            text_for_refinement, placeholder_map = self._replace_locked_with_placeholders(
                text=input.text,
                locked_token_indices=english_locked_tokens,
            )

            # Call QwenRefiner with text that includes placeholders
            refined_text_raw = self.qwen_refiner.refine_translation_with_qwen(
                nmt_translation=text_for_refinement,
                ocr_text=input.ocr_text,
            )
            
            if not refined_text_raw:
                logger.warning("QwenAdapter: QwenRefiner returned None, refinement failed")
                return None

            # Restore locked tokens from placeholders
            restored_text = self._restore_locked_tokens(refined_text_raw, placeholder_map)

            # (Optional) Phrase-level refinement hook (currently no-op, logs only)
            refined_text = self._refine_phrases(
                phrase_spans=phrase_spans,
                english_tokens=self._tokenize(restored_text),
            )

            # Track changed vs preserved tokens (after restoration and phrase-level step)
            changed_tokens, preserved_tokens = self._track_qwen_changes(
                original_text=input.text,
                refined_text=refined_text,
                locked_token_indices=english_locked_tokens,
            )
            
            # Step 6: Compute semantic confidence for Qwen refinement
            qwen_confidence, confidence_factors = self._calculate_qwen_confidence(
                original_text=input.text,
                refined_text=refined_text,
                locked_tokens=english_locked_tokens,
                phrase_spans=phrase_spans,
                changed_tokens=changed_tokens,
                preserved_tokens=preserved_tokens,
            )

            # Basic output with token locking, phrase metadata, and semantic confidence
            locked_tokens_count = len(english_locked_tokens)
            changed_tokens_count = len(changed_tokens)
            preserved_tokens_count = len(preserved_tokens)
            
            locked_spans = sum(1 for p in phrase_spans if p.is_locked)
            unlocked_spans = len(phrase_spans) - locked_spans

            output = QwenAdapterOutput(
                refined_text=refined_text,
                changed_tokens=changed_tokens,
                preserved_tokens=preserved_tokens,
                locked_tokens=english_locked_tokens,
                qwen_confidence=qwen_confidence,
                metadata={
                    "step": 6,
                    "phase": 6,
                    "refinement_enabled": True,
                    "token_locking_enabled": bool(english_locked_tokens),
                    "phrase_refinement_enabled": True,
                    "semantic_confidence_enabled": True,
                    "locked_tokens_count": locked_tokens_count,
                    "changed_tokens_count": changed_tokens_count,
                    "preserved_tokens_count": preserved_tokens_count,
                    "phrase_spans_count": len(phrase_spans),
                    "locked_phrases_count": locked_spans,
                    "unlocked_phrases_count": unlocked_spans,
                    # Step 6 factors
                    "qwen_locked_preservation_rate": confidence_factors[
                        "locked_preservation_rate"
                    ],
                    "qwen_modification_ratio": confidence_factors[
                        "modification_ratio"
                    ],
                    "qwen_unlocked_stability": confidence_factors[
                        "unlocked_stability"
                    ],
                    "qwen_phrase_score": confidence_factors["phrase_score"],
                },
            )
            
            logger.info(
                "Phase 6: QwenAdapter refinement completed: %s",
                refined_text[:100] if refined_text else "None",
            )
            
            return output
            
        except Exception as e:
            logger.error("Phase 6: QwenAdapter refinement failed: %s", e, exc_info=True)
            return None


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

_qwen_adapter_instance: Optional[QwenAdapter] = None


def get_qwen_adapter(
    qwen_refiner: Optional[QwenRefiner] = None
) -> Optional[QwenAdapter]:
    """
    Get or create QwenAdapter instance (singleton pattern).
    
    Args:
        qwen_refiner: Optional QwenRefiner instance (if None, will get singleton)
        
    Returns:
        QwenAdapter instance, or None if QwenRefiner is not available
    """
    global _qwen_adapter_instance
    
    # If no instance exists or qwen_refiner is provided, create new instance
    if _qwen_adapter_instance is None or qwen_refiner is not None:
        if qwen_refiner is None:
            qwen_refiner = get_qwen_refiner()
        
        if qwen_refiner is None or not qwen_refiner.is_available():
            logger.debug("QwenAdapter: QwenRefiner not available, cannot create adapter")
            return None
        
        _qwen_adapter_instance = QwenAdapter(qwen_refiner=qwen_refiner)
        logger.info("QwenAdapter instance created")
    
    return _qwen_adapter_instance

