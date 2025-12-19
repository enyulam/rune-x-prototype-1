"""
Backward compatibility tests for API response schema (Phase 5 Step 7)

Tests that existing clients still work after adding semantic field.
"""

import pytest
from main import InferenceResponse


def test_inference_response_schema_backward_compatible():
    """
    Test that InferenceResponse schema is backward compatible.
    
    Old clients should still work even if they don't expect the semantic field.
    """
    # Create a minimal response (old client expectations)
    response = InferenceResponse(
        text="你好",
        translation="hello",
        confidence=0.85,
        glyphs=[]
    )
    
    # Old clients should be able to access all original fields
    assert response.text == "你好"
    assert response.translation == "hello"
    assert response.confidence == 0.85
    assert response.glyphs == []
    
    # Semantic field should be optional (None by default)
    assert response.semantic is None
    
    # All optional fields should work
    assert response.sentence_translation is None
    assert response.refined_translation is None
    assert response.qwen_status is None
    assert response.unmapped is None
    assert response.coverage is None
    assert response.dictionary_source is None
    assert response.dictionary_version is None
    assert response.translation_source is None


def test_inference_response_with_semantic_field():
    """
    Test that InferenceResponse works with semantic field populated.
    
    New clients should be able to access semantic metadata.
    """
    semantic_metadata = {
        "engine": "MarianMT",
        "semantic_confidence": 0.85,
        "tokens_modified": 2,
        "tokens_locked": 3,
        "tokens_preserved": 3,
        "tokens_modified_percent": 40.0,
        "tokens_locked_percent": 60.0,
        "tokens_preserved_percent": 60.0,
        "dictionary_override_count": 2,
    }
    
    response = InferenceResponse(
        text="你好世界",
        translation="hello world",
        confidence=0.90,
        glyphs=[],
        semantic=semantic_metadata
    )
    
    # Original fields still work
    assert response.text == "你好世界"
    assert response.translation == "hello world"
    assert response.confidence == 0.90
    
    # Semantic field is populated
    assert response.semantic is not None
    assert response.semantic["engine"] == "MarianMT"
    assert response.semantic["semantic_confidence"] == 0.85
    assert response.semantic["tokens_modified"] == 2
    assert response.semantic["tokens_locked"] == 3
    assert response.semantic["tokens_preserved"] == 3


def test_inference_response_semantic_field_optional():
    """
    Test that semantic field is truly optional.
    
    Response should work whether semantic is None or populated.
    """
    # Test with None (old client scenario)
    response1 = InferenceResponse(
        text="test",
        translation="test",
        confidence=0.5,
        glyphs=[],
        semantic=None
    )
    assert response1.semantic is None
    
    # Test with empty dict (should also work)
    response2 = InferenceResponse(
        text="test",
        translation="test",
        confidence=0.5,
        glyphs=[],
        semantic={}
    )
    assert response2.semantic == {}
    
    # Test with populated dict (new client scenario)
    response3 = InferenceResponse(
        text="test",
        translation="test",
        confidence=0.5,
        glyphs=[],
        semantic={"engine": "MarianMT", "semantic_confidence": 0.8}
    )
    assert response3.semantic["engine"] == "MarianMT"


def test_inference_response_json_serialization():
    """
    Test that InferenceResponse can be serialized to JSON (for API responses).
    
    Both with and without semantic field should serialize correctly.
    """
    # Without semantic field
    response1 = InferenceResponse(
        text="你好",
        translation="hello",
        confidence=0.85,
        glyphs=[]
    )
    
    # Should serialize to dict
    response_dict1 = response1.model_dump()
    assert "text" in response_dict1
    assert "translation" in response_dict1
    assert "semantic" in response_dict1  # Field exists
    assert response_dict1["semantic"] is None  # But is None
    
    # With semantic field
    response2 = InferenceResponse(
        text="你好",
        translation="hello",
        confidence=0.85,
        glyphs=[],
        semantic={"engine": "MarianMT", "semantic_confidence": 0.8}
    )
    
    response_dict2 = response2.model_dump()
    assert response_dict2["semantic"] is not None
    assert response_dict2["semantic"]["engine"] == "MarianMT"

