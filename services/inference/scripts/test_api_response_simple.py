"""Test API response includes dictionary metadata - simple version."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import InferenceResponse, Glyph

print("Testing API Response with Dictionary Metadata")
print("-" * 60)

# Test 1: Verify model fields
print("\n1. Checking model fields...")
model_fields = InferenceResponse.model_fields
has_source = 'dictionary_source' in model_fields
has_version = 'dictionary_version' in model_fields
print(f"   dictionary_source: {'EXISTS' if has_source else 'MISSING'}")
print(f"   dictionary_version: {'EXISTS' if has_version else 'MISSING'}")

# Test 2: Create response with CC-CEDICT
print("\n2. Creating response with CC-CEDICT...")
try:
    response = InferenceResponse(
        text="test",
        translation="test translation",
        confidence=0.95,
        glyphs=[Glyph(symbol="t", bbox=[10, 20, 30, 40], confidence=0.96)],
        dictionary_source="CC-CEDICT",
        dictionary_version="1.0",
        coverage=85.5
    )
    print(f"   SUCCESS - Created with CC-CEDICT")
    print(f"   dictionary_source: {response.dictionary_source}")
    print(f"   dictionary_version: {response.dictionary_version}")
except Exception as e:
    print(f"   FAILED: {e}")

# Test 3: Create response with Translator
print("\n3. Creating response with Translator...")
try:
    response = InferenceResponse(
        text="test",
        translation="test",
        confidence=0.88,
        glyphs=[Glyph(symbol="t", bbox=[10, 20, 30, 40], confidence=0.90)],
        dictionary_source="Translator",
        dictionary_version=None
    )
    print(f"   SUCCESS - Created with Translator")
    print(f"   dictionary_source: {response.dictionary_source}")
    print(f"   dictionary_version: {response.dictionary_version}")
except Exception as e:
    print(f"   FAILED: {e}")

# Test 4: Backward compatibility
print("\n4. Testing backward compatibility...")
try:
    response = InferenceResponse(
        text="test",
        translation="test",
        confidence=0.92,
        glyphs=[Glyph(symbol="t", bbox=[10, 20, 30, 40], confidence=0.92)]
    )
    print(f"   SUCCESS - Fields are optional (backward compatible)")
    print(f"   dictionary_source: {response.dictionary_source}")
    print(f"   dictionary_version: {response.dictionary_version}")
except Exception as e:
    print(f"   FAILED: {e}")

# Test 5: JSON serialization
print("\n5. Testing JSON serialization...")
try:
    response = InferenceResponse(
        text="test",
        translation="test",
        confidence=0.91,
        glyphs=[Glyph(symbol="t", bbox=[10, 20, 30, 40], confidence=0.91)],
        dictionary_source="CC-CEDICT",
        dictionary_version="1.0"
    )
    response_dict = response.model_dump()
    
    has_source_in_dict = 'dictionary_source' in response_dict
    has_version_in_dict = 'dictionary_version' in response_dict
    source_correct = response_dict.get('dictionary_source') == "CC-CEDICT"
    version_correct = response_dict.get('dictionary_version') == "1.0"
    
    print(f"   dictionary_source in dict: {has_source_in_dict}")
    print(f"   dictionary_version in dict: {has_version_in_dict}")
    print(f"   dictionary_source value correct: {source_correct}")
    print(f"   dictionary_version value correct: {version_correct}")
    
    if all([has_source_in_dict, has_version_in_dict, source_correct, version_correct]):
        print(f"   SUCCESS - JSON serialization working")
    else:
        print(f"   FAILED - Some checks failed")
except Exception as e:
    print(f"   FAILED: {e}")

print("\n" + "-" * 60)
print("All API response metadata tests completed!")

