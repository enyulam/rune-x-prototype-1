"""
Semantic Constraints for Qwen Translation Refinement

This module defines the semantic contract that governs how Qwen operates within
the Rune-X translation pipeline. Qwen is refactored from a direct refinement call
into a controlled, inspectable adapter that respects locked tokens and provides
structured input/output.

Phase 6 Design Philosophy:
--------------------------
Qwen is no longer "the refiner." It becomes a fluency and coherence optimizer that:
- Respects MarianMT translation output
- Respects locked tokens from OCR/CC-CEDICT (via MarianAdapter)
- Improves fluency, grammar, and coherence
- Never contradicts high-confidence locked tokens

Think of Qwen as: "Fluency and coherence optimizer under constraints"
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIDENCE THRESHOLDS
# ============================================================================

class QwenConfidenceThreshold:
    """
    Confidence thresholds for Qwen refinement operations.
    
    These thresholds define when Qwen should be conservative vs. aggressive
    in its refinements.
    """
    
    # Locked Token Preservation Rate
    # If this percentage of locked tokens are preserved, confidence is high
    LOCKED_PRESERVATION_RATE_HIGH = 0.95  # 95%+ preserved = high confidence
    
    # Token Modification Rate
    # Lower modification rate generally indicates better refinement
    MODIFICATION_RATE_LOW = 0.20  # <20% modified = good refinement
    
    # Phrase-Level Refinement Score
    # Dummy metric for phrase-level improvements
    PHRASE_REFINEMENT_SCORE_HIGH = 0.8  # High score if phrases refined
    PHRASE_REFINEMENT_SCORE_LOW = 0.5   # Low score if no phrase refinement


# ============================================================================
# SEMANTIC CONSTRAINTS
# ============================================================================

class QwenSemanticConstraint(Enum):
    """
    Types of semantic constraints that can be applied to Qwen.
    """
    PRESERVE_LOCKED_TOKENS = "preserve_locked_tokens"
    PRESERVE_MARIANMT_OUTPUT = "preserve_marianmt_output"
    PRESERVE_DICTIONARY_ANCHORS = "preserve_dictionary_anchors"
    ALLOW_GRAMMAR_CORRECTIONS = "allow_grammar"
    ALLOW_FLUENCY_IMPROVEMENTS = "allow_fluency"
    ALLOW_COHERENCE_IMPROVEMENTS = "allow_coherence"
    ALLOW_IDIOM_RESOLUTION = "allow_idioms"


@dataclass
class QwenTokenLockStatus:
    """
    Represents the lock status of an English token in Qwen refinement.
    
    Attributes:
        locked: Whether this token is locked and cannot be modified by Qwen
        reason: Why this token is locked (e.g., "locked_from_marian_adapter", "high_confidence")
        token_index: Index of the token in the English translation
        glyph_indices: List of Chinese glyph indices that map to this token (from alignment)
    """
    locked: bool
    reason: Optional[str] = None
    token_index: int = -1
    glyph_indices: List[int] = None
    
    def __post_init__(self):
        """Initialize glyph_indices if None."""
        if self.glyph_indices is None:
            self.glyph_indices = []
    
    def __repr__(self) -> str:
        status = "🔒" if self.locked else "🔓"
        return f"{status} Token[{self.token_index}] (reason={self.reason}, glyphs={self.glyph_indices})"


# ============================================================================
# QWEN ROLE DEFINITION
# ============================================================================

class QwenRole:
    """
    Defines what Qwen is allowed to do and what it must never override.
    
    This class encapsulates the semantic contract for Qwen's role in the pipeline.
    """
    
    # ========================================================================
    # ALLOWED OPERATIONS
    # ========================================================================
    
    ALLOWED_OPERATIONS = {
        "grammar_correction": True,
        "fluency_improvement": True,
        "idiom_resolution": True,
        "coherence_improvement": True,
    }
    
    # ========================================================================
    # FORBIDDEN OPERATIONS
    # ========================================================================
    
    FORBIDDEN_OPERATIONS = {
        "modify_locked_tokens": True,
        "invent_characters": True,
        "override_dictionary": True,
        "change_placeholders": True,
    }
    
    @staticmethod
    def can_modify_token(
        token_locked: bool,
        token_index: int = -1
    ) -> bool:
        """
        Determine if a token can be modified by Qwen.
        
        Rules:
        1. Never modify locked tokens (from MarianAdapter)
        2. Can modify unlocked tokens for fluency/grammar improvements
        
        Args:
            token_locked: Whether the token is locked (from MarianAdapter)
            token_index: Index of the token (for logging)
            
        Returns:
            bool: True if token can be modified, False otherwise
        """
        if token_locked:
            logger.debug(
                "Token[%d] is locked, cannot be modified by Qwen",
                token_index
            )
            return False
        
        return True
    
    @staticmethod
    def explain_action(token_index: int, token_locked: bool) -> str:
        """
        Explain why a token can or cannot be modified.
        
        Args:
            token_index: Index of the token
            token_locked: Whether the token is locked
            
        Returns:
            str: Explanation of the action
        """
        if token_locked:
            return f"Token[{token_index}] is locked (from MarianAdapter), preserving original"
        else:
            return f"Token[{token_index}] is unlocked, allowing Qwen refinement"


# ============================================================================
# QWEN SEMANTIC CONTRACT
# ============================================================================

class QwenSemanticContract:
    """
    Semantic contract that enforces rules for Qwen refinement.
    
    This contract ensures that Qwen respects locked tokens and dictionary anchors
    while allowing fluency and coherence improvements.
    """
    
    def __init__(self):
        """Initialize Qwen semantic contract."""
        self.qwen_role = QwenRole()
        logger.debug("QwenSemanticContract initialized")
    
    def can_modify_token(
        self,
        token_index: int,
        token_locked: bool
    ) -> bool:
        """
        Check if Qwen can modify a specific token.
        
        Args:
            token_index: Index of the token in the English translation
            token_locked: Whether the token is locked (from MarianAdapter)
            
        Returns:
            bool: True if token can be modified, False otherwise
        """
        return self.qwen_role.can_modify_token(
            token_locked=token_locked,
            token_index=token_index
        )
    
    def explain_action(
        self,
        token_index: int,
        token_locked: bool
    ) -> str:
        """
        Explain why a token can or cannot be modified.
        
        Args:
            token_index: Index of the token
            token_locked: Whether the token is locked
            
        Returns:
            str: Explanation of the action
        """
        return self.qwen_role.explain_action(
            token_index=token_index,
            token_locked=token_locked
        )
    
    def validate_refinement(
        self,
        original_text: str,
        refined_text: str,
        locked_token_indices: List[int]
    ) -> Dict[str, any]:
        """
        Validate that Qwen refinement respects locked tokens.
        
        Args:
            original_text: Original MarianMT translation
            refined_text: Qwen-refined translation
            locked_token_indices: List of locked token indices
            
        Returns:
            Dict with validation results:
            - valid: bool
            - violations: List of violations (if any)
            - preserved_count: Number of locked tokens preserved
        """
        # Tokenize both texts (simple whitespace splitting for now)
        original_tokens = original_text.split()
        refined_tokens = refined_text.split()
        
        violations = []
        preserved_count = 0
        
        # Check if locked tokens were preserved
        for token_idx in locked_token_indices:
            if token_idx < len(original_tokens) and token_idx < len(refined_tokens):
                original_token = original_tokens[token_idx]
                refined_token = refined_tokens[token_idx]
                
                if original_token == refined_token:
                    preserved_count += 1
                else:
                    violations.append({
                        "token_index": token_idx,
                        "original": original_token,
                        "refined": refined_token,
                        "reason": "Locked token was modified"
                    })
        
        valid = len(violations) == 0
        
        return {
            "valid": valid,
            "violations": violations,
            "preserved_count": preserved_count,
            "total_locked": len(locked_token_indices),
            "preservation_rate": preserved_count / len(locked_token_indices) if locked_token_indices else 1.0
        }

