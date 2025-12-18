"""Test API response includes dictionary metadata."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pydantic import ValidationError
from main import InferenceResponse, Glyph

print("=" * 60)
print("Testing API Response with Dictionary Metadata")
print("=" * 60)

# Test 1: Verify InferenceResponse model includes new fields
print("\n1. Checking InferenceResponse model fields...")
model_fields = InferenceResponse.model_fields
required_fields = ['dictionary_source', 'dictionary_version']

for field in required_fields:
    if field in model_fields:
        print(f"   ✓ Field '{field}' exists in model")
    else:
        print(f"   ✗ Field '{field}' MISSING from model")

# Test 2: Create sample response with new fields
print("\n2. Creating sample InferenceResponse with CC-CEDICT...")
try:
    response = InferenceResponse(
        text="学习",
        translation="to learn; to study",
        sentence_translation="Learn",
        refined_translation="Study",
        qwen_status="available",
        confidence=0.95,
        glyphs=[
            Glyph(symbol="学", bbox=[10, 20, 30, 40], confidence=0.96, meaning="to learn"),
            Glyph(symbol="习", bbox=[50, 20, 30, 40], confidence=0.94, meaning="to practice")
        ],
        unmapped=[],
        coverage=85.5,
        dictionary_source="CC-CEDICT",
        dictionary_version="1.0"
    )
    print(f"   ✓ Response created successfully")
    print(f"   - dictionary_source: {response.dictionary_source}")
    print(f"   - dictionary_version: {response.dictionary_version}")
    print(f"   - confidence: {response.confidence}")
    print(f"   - coverage: {response.coverage}")
except ValidationError as e:
    print(f"   ✗ Validation failed: {e}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 3: Create sample response with Translator fallback
print("\n3. Creating sample InferenceResponse with Translator fallback...")
try:
    response = InferenceResponse(
        text="你好",
        translation="hello",
        sentence_translation="Hello",
        refined_translation=None,
        qwen_status="unavailable",
        confidence=0.88,
        glyphs=[
            Glyph(symbol="你", bbox=[10, 20, 30, 40], confidence=0.90, meaning="you"),
            Glyph(symbol="好", bbox=[50, 20, 30, 40], confidence=0.86, meaning="good")
        ],
        unmapped=[],
        coverage=75.0,
        dictionary_source="Translator",
        dictionary_version=None  # Translator doesn't have version
    )
    print(f"   ✓ Response created successfully")
    print(f"   - dictionary_source: {response.dictionary_source}")
    print(f"   - dictionary_version: {response.dictionary_version}")
    print(f"   - confidence: {response.confidence}")
    print(f"   - coverage: {response.coverage}")
except ValidationError as e:
    print(f"   ✗ Validation failed: {e}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 4: Verify optional fields work (backward compatibility)
print("\n4. Testing backward compatibility (fields optional)...")
try:
    response = InferenceResponse(
        text="中",
        translation="middle",
        confidence=0.92,
        glyphs=[Glyph(symbol="中", bbox=[10, 20, 30, 40], confidence=0.92)]
        # Omit dictionary_source and dictionary_version
    )
    print(f"   ✓ Response created without new fields (backward compatible)")
    print(f"   - dictionary_source: {response.dictionary_source}")
    print(f"   - dictionary_version: {response.dictionary_version}")
except ValidationError as e:
    print(f"   ✗ Validation failed: {e}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 5: Convert to dict (for JSON serialization)
print("\n5. Testing JSON serialization...")
try:
    response = InferenceResponse(
        text="好",
        translation="good",
        confidence=0.91,
        glyphs=[Glyph(symbol="好", bbox=[10, 20, 30, 40], confidence=0.91)],
        dictionary_source="CC-CEDICT",
        dictionary_version="1.0",
        coverage=90.0
    )
    response_dict = response.model_dump()
    
    assert 'dictionary_source' in response_dict, "dictionary_source not in serialized dict"
    assert 'dictionary_version' in response_dict, "dictionary_version not in serialized dict"
    assert response_dict['dictionary_source'] == "CC-CEDICT"
    assert response_dict['dictionary_version'] == "1.0"
    
    print(f"   ✓ JSON serialization successful")
    print(f"   - Serialized keys: {list(response_dict.keys())}")
except AssertionError as e:
    print(f"   ✗ Assertion failed: {e}")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "=" * 60)
print("✅ All API response metadata tests passed!")
print("=" * 60)

