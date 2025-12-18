"""
Diagnostic script to show RAW outputs from EasyOCR and PaddleOCR BEFORE fusion.
This helps identify which OCR engine is producing incorrect results.
"""

import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import easyocr
from paddlex import create_pipeline

def print_separator(title):
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)

def diagnose_ocr(image_path: str):
    """Run both OCR engines and display raw outputs."""
    
    print_separator("OCR DIAGNOSTIC TOOL")
    print(f"Image: {image_path}\n")
    
    # Load image
    try:
        image = Image.open(image_path)
        print(f"[OK] Image loaded: {image.size[0]}x{image.size[1]} pixels")
    except Exception as e:
        print(f"[ERROR] Failed to load image: {e}")
        return
    
    # Initialize EasyOCR
    print_separator("1. INITIALIZING EASYOCR")
    try:
        easy_reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
        print("[OK] EasyOCR initialized")
    except Exception as e:
        print(f"[ERROR] EasyOCR initialization failed: {e}")
        return
    
    # Initialize PaddleOCR
    print_separator("2. INITIALIZING PADDLEOCR")
    try:
        paddle_pipeline = create_pipeline(pipeline="OCR")
        print("[OK] PaddleOCR initialized")
    except Exception as e:
        print(f"[ERROR] PaddleOCR initialization failed: {e}")
        return
    
    # Run EasyOCR
    print_separator("3. EASYOCR RAW OUTPUT")
    try:
        easy_results = easy_reader.readtext(image_path)
        print(f"Found {len(easy_results)} text regions\n")
        
        for idx, (bbox, text, conf) in enumerate(easy_results, 1):
            # Extract coordinates safely
            try:
                if len(bbox) == 4:
                    x1 = min(p[0] for p in bbox)
                    y1 = min(p[1] for p in bbox)
                    x2 = max(p[0] for p in bbox)
                    y2 = max(p[1] for p in bbox)
                else:
                    x1, y1, x2, y2 = bbox
            except:
                x1, y1, x2, y2 = 0, 0, 0, 0
            
            print(f"  [{idx}] Position: ({x1:.0f}, {y1:.0f}) → ({x2:.0f}, {y2:.0f})")
            print(f"      Text: '{text}'")
            print(f"      Confidence: {conf:.3f}")
            print()
        
        # Extract just characters for full text
        easy_full_text = "".join([text for _, text, _ in easy_results])
        print(f"[TEXT] EasyOCR Full Text: {easy_full_text}")
        print(f"       Character count: {len(easy_full_text)}")
        
    except Exception as e:
        print(f"[ERROR] EasyOCR execution failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Run PaddleOCR
    print_separator("4. PADDLEOCR RAW OUTPUT")
    try:
        paddle_results = paddle_pipeline.predict(image_path)
        
        if hasattr(paddle_results, 'text') and paddle_results.text:
            text_regions = paddle_results.text
            print(f"Found {len(text_regions)} text regions\n")
            
            paddle_chars = []
            for idx, region in enumerate(text_regions, 1):
                bbox = region.get('bbox', [])
                text = region.get('text', '')
                score = region.get('score', 0.0)
                
                if bbox and len(bbox) >= 4:
                    x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
                    print(f"  [{idx}] Position: ({x1:.0f}, {y1:.0f}) → ({x2:.0f}, {y2:.0f})")
                    print(f"      Text: '{text}'")
                    print(f"      Score: {score:.3f}")
                    print()
                    paddle_chars.append(text)
            
            paddle_full_text = "".join(paddle_chars)
            print(f"[TEXT] PaddleOCR Full Text: {paddle_full_text}")
            print(f"       Character count: {len(paddle_full_text)}")
        else:
            print("[WARNING] No text detected by PaddleOCR")
            paddle_full_text = ""
            
    except Exception as e:
        print(f"[ERROR] PaddleOCR execution failed: {e}")
        import traceback
        traceback.print_exc()
        paddle_full_text = ""
    
    # Comparison
    print_separator("5. COMPARISON")
    print(f"EasyOCR:   {easy_full_text}")
    print(f"PaddleOCR: {paddle_full_text}")
    
    if easy_full_text == paddle_full_text:
        print("\n[OK] Both engines produced IDENTICAL results")
    else:
        print("\n[WARNING] Engines produced DIFFERENT results")
        print(f"          EasyOCR length: {len(easy_full_text)}")
        print(f"          PaddleOCR length: {len(paddle_full_text)}")
    
    print_separator("DIAGNOSIS COMPLETE")
    print("\nNOTE: The fusion module will combine these results.")
    print("If BOTH engines show corrupted text, the problem is upstream (preprocessing).")
    print("If ONE engine shows corrupted text, that engine is the issue.")
    print("="*80 + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_ocr_raw.py <image_path>")
        print("\nExample:")
        print("  python scripts/diagnose_ocr_raw.py test_image.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not Path(image_path).exists():
        print(f"[ERROR] Image not found: {image_path}")
        sys.exit(1)
    
    diagnose_ocr(image_path)

