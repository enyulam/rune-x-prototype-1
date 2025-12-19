"""
Semantic Constraints for MarianMT Translation

This module defines the semantic contract that governs how MarianMT operates within
the Rune-X translation pipeline. MarianMT is refactored from a black-box translator
into a controlled, inspectable, dictionary-anchored semantic module.

Phase 5 Design Philosophy:
-------------------------
MarianMT is no longer "the translator." It becomes a semantic refinement engine that:
- Respects OCR fusion output
- Respects CC-CEDICT anchors
- Improves fluency, grammar, and phrase-level meaning
- Never contradicts high-confidence glyph anchors

Think of MarianMT as: "Grammar + phrasing optimizer under constraints"
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIDENCE THRESHOLDS
# ============================================================================

class ConfidenceThreshold:
    """
    Confidence thresholds for determining when glyphs should be locked.
    
    These thresholds define the boundary between modifiable and locked tokens.
    """
    
    # OCR Confidence Threshold
    # Glyphs with OCR confidence >= this value are candidates for locking
    OCR_HIGH_CONFIDENCE = 0.85
    
    # OCR Confidence Threshold (Medium)
    # Glyphs with OCR confidence >= this value but < HIGH are considered medium confidence
    OCR_MEDIUM_CONFIDENCE = 0.70
    
    # Dictionary Match Requirement
    # If a glyph has both high OCR confidence AND a dictionary match, it MUST be locked
    DICTIONARY_MATCH_REQUIRED = True
    
    # Multi-Glyph Ambiguity Threshold
    # If multiple glyph candidates exist with similar confidence, unlock for MarianMT
    MULTI_GLYPH_AMBIGUITY_THRESHOLD = 0.10  # Confidence difference < 10% = ambiguous


# ============================================================================
# SEMANTIC CONSTRAINTS
# ============================================================================

class SemanticConstraint(Enum):
    """
    Types of semantic constraints that can be applied to MarianMT.
    """
    PRESERVE_HIGH_CONFIDENCE_GLYPHS = "preserve_high_confidence"
    PRESERVE_DICTIONARY_ANCHORS = "preserve_dictionary_anchors"
    PRESERVE_OCR_FUSION_DECISIONS = "preserve_ocr_fusion"
    ALLOW_FLUENCY_IMPROVEMENTS = "allow_fluency"
    ALLOW_GRAMMAR_CORRECTIONS = "allow_grammar"
    ALLOW_PHRASE_REFINEMENT = "allow_phrases"
    ALLOW_IDIOM_RESOLUTION = "allow_idioms"


@dataclass
class TokenLockStatus:
    """
    Represents the lock status of a token (character/glyph).
    
    Attributes:
        locked: Whether this token is locked and cannot be modified by MarianMT
        reason: Why this token is locked (e.g., "high_ocr_confidence", "dictionary_match")
        confidence: OCR confidence score for this token
        dictionary_match: Whether this token has a dictionary entry
        glyph_index: Index of the glyph in the original glyph list
    """
    locked: bool
    reason: Optional[str] = None
    confidence: float = 0.0
    dictionary_match: bool = False
    glyph_index: int = -1
    
    def __repr__(self) -> str:
        status = "🔒" if self.locked else "🔓"
        return f"{status} Token[{self.glyph_index}] (conf={self.confidence:.2f}, dict={self.dictionary_match}, reason={self.reason})"


# ============================================================================
# MARIANMT ROLE DEFINITION
# ============================================================================

class MarianMTRole:
    """
    Defines what MarianMT is allowed to do and what it must never override.
    
    This class encapsulates the semantic contract for MarianMT's role in the pipeline.
    """
    
    # ========================================================================
    # ALLOWED OPERATIONS
    # ========================================================================
    
    ALLOWED_OPERATIONS = {
        "improve_sentence_fluency": True,
        "resolve_multi_character_phrases": True,
        "infer_implied_grammar": True,
        "handle_idioms_and_compounds": True,
        "correct_grammar_errors": True,
        "improve_phrase_level_meaning": True,
        "handle_contextual_ambiguity": True,
    }
    
    # ========================================================================
    # FORBIDDEN OPERATIONS
    # ========================================================================
    
    FORBIDDEN_OPERATIONS = {
        "change_glyph_meanings_with_high_dictionary_confidence": True,
        "override_ocr_fusion_decisions": True,
        "invent_characters_not_present_in_ocr_output": True,
        "modify_locked_tokens": True,
        "change_high_confidence_glyphs": True,
        "ignore_dictionary_anchors": True,
    }
    
    @staticmethod
    def can_modify_token(
        ocr_confidence: float,
        has_dictionary_match: bool,
        has_multi_glyph_ambiguity: bool = False
    ) -> bool:
        """
        Determine if a token can be modified by MarianMT.
        
        Rules:
        1. Lock if OCR confidence >= HIGH_CONFIDENCE AND dictionary match exists
        2. Lock if OCR confidence >= HIGH_CONFIDENCE (even without dictionary)
        3. Unlock if low OCR confidence (< MEDIUM_CONFIDENCE)
        4. Unlock if multi-glyph ambiguity exists (similar confidence candidates)
        5. Unlock if no dictionary match AND medium confidence
        
        Args:
            ocr_confidence: OCR confidence score (0.0-1.0)
            has_dictionary_match: Whether token has a dictionary entry
            has_multi_glyph_ambiguity: Whether multiple glyph candidates exist with similar confidence
            
        Returns:
            bool: True if token can be modified, False if it must be locked
        """
        # Rule 1: High confidence + dictionary match = LOCKED
        if (ocr_confidence >= ConfidenceThreshold.OCR_HIGH_CONFIDENCE and 
            has_dictionary_match and 
            ConfidenceThreshold.DICTIONARY_MATCH_REQUIRED):
            return False
        
        # Rule 2: High confidence (even without dictionary) = LOCKED
        if ocr_confidence >= ConfidenceThreshold.OCR_HIGH_CONFIDENCE:
            return False
        
        # Rule 3: Low confidence = UNLOCKED (allow MarianMT to improve)
        if ocr_confidence < ConfidenceThreshold.OCR_MEDIUM_CONFIDENCE:
            return True
        
        # Rule 4: Multi-glyph ambiguity = UNLOCKED (let MarianMT resolve)
        if has_multi_glyph_ambiguity:
            return True
        
        # Rule 5: Medium confidence without dictionary = UNLOCKED
        if (ocr_confidence < ConfidenceThreshold.OCR_HIGH_CONFIDENCE and 
            not has_dictionary_match):
            return True
        
        # Default: Lock for safety
        return False
    
    @staticmethod
    def get_lock_reason(
        ocr_confidence: float,
        has_dictionary_match: bool,
        has_multi_glyph_ambiguity: bool = False
    ) -> str:
        """
        Get the reason why a token is locked or unlocked.
        
        Returns:
            str: Human-readable reason for lock status
        """
        if (ocr_confidence >= ConfidenceThreshold.OCR_HIGH_CONFIDENCE and 
            has_dictionary_match):
            return "high_ocr_confidence_and_dictionary_match"
        elif ocr_confidence >= ConfidenceThreshold.OCR_HIGH_CONFIDENCE:
            return "high_ocr_confidence"
        elif ocr_confidence < ConfidenceThreshold.OCR_MEDIUM_CONFIDENCE:
            return "low_ocr_confidence"
        elif has_multi_glyph_ambiguity:
            return "multi_glyph_ambiguity"
        elif not has_dictionary_match:
            return "no_dictionary_match"
        else:
            return "default_lock"


# ============================================================================
# SEMANTIC CONTRACT
# ============================================================================

class SemanticContract:
    """
    The semantic contract that defines MarianMT's role in the translation pipeline.
    
    This contract ensures that:
    1. OCR fusion output remains authoritative
    2. Dictionary anchors are preserved
    3. MarianMT only improves fluency/grammar without semantic drift
    4. High-confidence glyphs are never overridden
    """
    
    def __init__(self):
        """Initialize the semantic contract with default constraints."""
        self.constraints: Set[SemanticConstraint] = {
            SemanticConstraint.PRESERVE_HIGH_CONFIDENCE_GLYPHS,
            SemanticConstraint.PRESERVE_DICTIONARY_ANCHORS,
            SemanticConstraint.PRESERVE_OCR_FUSION_DECISIONS,
            SemanticConstraint.ALLOW_FLUENCY_IMPROVEMENTS,
            SemanticConstraint.ALLOW_GRAMMAR_CORRECTIONS,
            SemanticConstraint.ALLOW_PHRASE_REFINEMENT,
            SemanticConstraint.ALLOW_IDIOM_RESOLUTION,
        }
    
    def is_operation_allowed(self, operation: str) -> bool:
        """
        Check if an operation is allowed under the semantic contract.
        
        Args:
            operation: Name of the operation (e.g., "improve_sentence_fluency")
            
        Returns:
            bool: True if operation is allowed, False otherwise
        """
        return MarianMTRole.ALLOWED_OPERATIONS.get(operation, False)
    
    def is_operation_forbidden(self, operation: str) -> bool:
        """
        Check if an operation is forbidden under the semantic contract.
        
        Args:
            operation: Name of the operation (e.g., "change_glyph_meanings")
            
        Returns:
            bool: True if operation is forbidden, False otherwise
        """
        return MarianMTRole.FORBIDDEN_OPERATIONS.get(operation, False)
    
    def should_lock_token(
        self,
        ocr_confidence: float,
        has_dictionary_match: bool,
        has_multi_glyph_ambiguity: bool = False
    ) -> TokenLockStatus:
        """
        Determine if a token should be locked based on the semantic contract.
        
        Args:
            ocr_confidence: OCR confidence score (0.0-1.0)
            has_dictionary_match: Whether token has a dictionary entry
            has_multi_glyph_ambiguity: Whether multiple glyph candidates exist
            
        Returns:
            TokenLockStatus: Lock status with reason
        """
        can_modify = MarianMTRole.can_modify_token(
            ocr_confidence=ocr_confidence,
            has_dictionary_match=has_dictionary_match,
            has_multi_glyph_ambiguity=has_multi_glyph_ambiguity
        )
        
        reason = MarianMTRole.get_lock_reason(
            ocr_confidence=ocr_confidence,
            has_dictionary_match=has_dictionary_match,
            has_multi_glyph_ambiguity=has_multi_glyph_ambiguity
        )
        
        return TokenLockStatus(
            locked=not can_modify,
            reason=reason,
            confidence=ocr_confidence,
            dictionary_match=has_dictionary_match
        )
    
    def validate_translation_changes(
        self,
        original_glyphs: List[Dict],
        modified_text: str,
        locked_tokens: List[TokenLockStatus]
    ) -> Dict[str, any]:
        """
        Validate that translation changes respect the semantic contract.
        
        Args:
            original_glyphs: Original glyphs from OCR fusion
            modified_text: Text after MarianMT translation
            locked_tokens: List of locked token statuses
            
        Returns:
            Dict with validation results:
                - valid: bool
                - violations: List of violations
                - preserved_count: Number of locked tokens preserved
                - modified_count: Number of tokens modified
        """
        violations = []
        preserved_count = 0
        modified_count = 0
        
        # Check that locked tokens are preserved
        for lock_status in locked_tokens:
            if lock_status.locked:
                glyph = original_glyphs[lock_status.glyph_index]
                original_char = glyph.get("symbol", "")
                
                # Check if character is preserved in modified text
                # (This is a simplified check - actual implementation will be more sophisticated)
                if original_char in modified_text:
                    preserved_count += 1
                else:
                    violations.append(
                        f"Locked token '{original_char}' (index {lock_status.glyph_index}) "
                        f"was modified or removed. Reason: {lock_status.reason}"
                    )
        
        # Count modifications (simplified - actual implementation will track changes)
        # For now, we assume all non-locked tokens could be modified
        total_tokens = len(original_glyphs)
        locked_count = sum(1 for lt in locked_tokens if lt.locked)
        modified_count = total_tokens - locked_count
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "preserved_count": preserved_count,
            "modified_count": modified_count,
            "locked_count": locked_count,
            "total_tokens": total_tokens
        }


# ============================================================================
# MODULE DOCUMENTATION
# ============================================================================

"""
MARIANMT ROLE IN THE PIPELINE
==============================

MarianMT is refactored from a black-box translator into a controlled semantic
refinement engine. Its role is to improve fluency, grammar, and phrase-level
meaning while respecting OCR fusion output and dictionary anchors.

ALLOWED OPERATIONS:
------------------
1. Improve Sentence Fluency
   - MarianMT can improve the naturalness and flow of English translations
   - Example: "I you love" → "I love you"

2. Resolve Multi-Character Phrases
   - MarianMT can handle multi-character compounds and phrases
   - Example: "你好" (hello) as a phrase, not just "你" + "好"

3. Infer Implied Grammar
   - MarianMT can add implied grammatical elements
   - Example: Adding articles, prepositions, verb tenses

4. Handle Idioms and Compounds
   - MarianMT can translate idioms and fixed expressions
   - Example: "马马虎虎" (so-so) as an idiom

5. Correct Grammar Errors
   - MarianMT can fix grammatical mistakes in OCR output
   - Example: Subject-verb agreement, word order

6. Improve Phrase-Level Meaning
   - MarianMT can refine phrase-level translations for better context
   - Example: Contextual word choice based on surrounding characters

FORBIDDEN OPERATIONS:
---------------------
1. Change Glyph Meanings with High Dictionary Confidence
   - MarianMT MUST NOT change characters that have:
     - OCR confidence >= 0.85 AND
     - Dictionary match exists
   - These are "locked tokens" that represent authoritative OCR + dictionary decisions

2. Override OCR Fusion Decisions
   - MarianMT MUST NOT contradict OCR fusion output
   - OCR fusion is the authoritative source for character recognition

3. Invent Characters Not Present in OCR Output
   - MarianMT MUST NOT add characters that weren't detected by OCR
   - All output characters must trace back to OCR input

4. Modify Locked Tokens
   - MarianMT MUST NOT modify tokens marked as locked
   - Locked tokens are protected by the semantic contract

CONFIDENCE THRESHOLDS:
----------------------
- OCR_HIGH_CONFIDENCE (0.85): Glyphs with confidence >= this are candidates for locking
- OCR_MEDIUM_CONFIDENCE (0.70): Glyphs with confidence < this are unlocked
- DICTIONARY_MATCH_REQUIRED: If high confidence + dictionary match → MUST lock
- MULTI_GLYPH_AMBIGUITY_THRESHOLD (0.10): If confidence difference < 10% → unlock for resolution

LOCKING RULES:
--------------
1. Lock if: OCR confidence >= 0.85 AND dictionary match exists
2. Lock if: OCR confidence >= 0.85 (even without dictionary)
3. Unlock if: OCR confidence < 0.70 (low confidence, allow improvement)
4. Unlock if: Multi-glyph ambiguity exists (let MarianMT resolve)
5. Unlock if: Medium confidence (0.70-0.85) without dictionary match

ARCHITECTURAL PRINCIPLES:
-------------------------
1. OCR + Dictionary are AUTHORITATIVE
   - OCR fusion output is the ground truth for character recognition
   - Dictionary anchors provide semantic grounding

2. MarianMT is REFINEMENT
   - MarianMT improves fluency and grammar
   - MarianMT does NOT override authoritative sources

3. Constraints are ENFORCEABLE
   - Token locking prevents semantic drift
   - Validation ensures contract compliance

4. System is INSPECTABLE
   - All decisions are logged and traceable
   - Lock status is visible in output

USAGE EXAMPLE:
--------------
```python
from semantic_constraints import SemanticContract, TokenLockStatus

contract = SemanticContract()

# Determine lock status for a glyph
lock_status = contract.should_lock_token(
    ocr_confidence=0.92,
    has_dictionary_match=True,
    has_multi_glyph_ambiguity=False
)

# lock_status.locked = True
# lock_status.reason = "high_ocr_confidence_and_dictionary_match"

# Validate translation changes
validation = contract.validate_translation_changes(
    original_glyphs=glyphs,
    modified_text=marianmt_output,
    locked_tokens=[lock_status]
)
```

This semantic contract ensures that MarianMT operates as a controlled refinement
engine rather than an uncontrolled translator, maintaining the integrity of OCR
fusion and dictionary anchoring while improving translation quality.
"""

