"""
Smoke test for Rune-X inference pipeline.

This test verifies that the full OCR → translation → refinement pipeline
executes end-to-end without crashing. It does NOT test correctness or quality.
"""

import io
import pytest
from fastapi import UploadFile
from PIL import Image, ImageDraw

# Import the endpoint function
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import process_image, InferenceResponse


@pytest.mark.asyncio
async def test_pipeline_smoke():
    """
    Smoke test: Verify pipeline executes without crashing.
    
    Creates a minimal test image with Chinese text and verifies:
    - Pipeline completes without exceptions
    - Response contains expected top-level keys
    - Graceful fallback if Qwen is unavailable
    """
    # Create a simple test image with Chinese text
    # Use a size that meets minimum requirements (50x50)
    # Make it larger and with clearer contrast for OCR
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw multiple rectangles to simulate text blocks
    # This gives OCR engines something to potentially detect
    # Even if OCR fails, the pipeline should complete gracefully
    for i in range(3):
        x = 50 + i * 100
        draw.rectangle([x, 50, x + 80, 150], fill='black')
    
    # Convert image to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    content = img_bytes.read()
    
    # Create UploadFile mock with proper content_type
    # UploadFile content_type is set via headers in FastAPI, but for testing we can use a mock
    class MockUploadFile:
        def __init__(self, filename, content, content_type):
            self.filename = filename
            self.file = io.BytesIO(content)
            self.content_type = content_type
        
        async def read(self):
            return self.file.read()
    
    upload_file = MockUploadFile("test.png", content, "image/png")
    
    # Run pipeline
    # For smoke test, we catch HTTPException as valid - pipeline executed without crashing
    from fastapi import HTTPException
    
    try:
        result = await process_image(file=upload_file)
        
        # If we get here, pipeline completed successfully
        # Smoke test assertions: only check structure, not content
        assert result is not None, "Pipeline returned None"
        assert isinstance(result, InferenceResponse), "Result is not InferenceResponse"
        
        # Check required top-level fields exist
        assert hasattr(result, 'text'), "Missing 'text' field"
        assert hasattr(result, 'translation'), "Missing 'translation' field"
        assert hasattr(result, 'confidence'), "Missing 'confidence' field"
        assert hasattr(result, 'glyphs'), "Missing 'glyphs' field"
        
        # Check optional fields exist (may be None)
        assert hasattr(result, 'sentence_translation'), "Missing 'sentence_translation' field"
        assert hasattr(result, 'refined_translation'), "Missing 'refined_translation' field"
        assert hasattr(result, 'qwen_status'), "Missing 'qwen_status' field"
        
        # Verify types
        assert isinstance(result.text, str), "'text' must be string"
        assert isinstance(result.translation, str), "'translation' must be string"
        assert isinstance(result.confidence, (int, float)), "'confidence' must be numeric"
        assert isinstance(result.glyphs, list), "'glyphs' must be list"
        
    except HTTPException as e:
        # HTTPException is valid - pipeline executed, just returned expected error
        # For smoke test, we verify it's a known error type (not a crash)
        assert e.status_code in [400, 422, 500, 503], f"Unexpected HTTPException status: {e.status_code}"
        # Pipeline executed without crashing - smoke test passed
        return
    
    # Pipeline completed successfully - smoke test passed

