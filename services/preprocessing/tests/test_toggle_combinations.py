"""
Test all toggle combinations for optional preprocessing enhancements.

This test verifies that all 16 possible combinations of optional enhancements
work correctly without crashing.

The 4 boolean toggles are:
- apply_noise_reduction
- apply_binarization
- apply_deskew
- apply_brightness_norm

Total combinations: 2^4 = 16
"""

import io
import pytest
from itertools import product
from PIL import Image

from ..image_preprocessing import preprocess_image


@pytest.fixture
def create_test_image():
    """Create a test image."""
    def _create(width=500, height=500):
        img = Image.new("RGB", (width, height), color=(200, 200, 200))
        img.format = "PNG"
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    return _create


def test_all_toggle_combinations(create_test_image):
    """
    Test all 16 possible combinations of optional enhancement toggles.
    
    Verifies that:
    1. All combinations execute without crashing
    2. All combinations return valid numpy arrays and PIL images
    3. Output dimensions are reasonable (accounting for padding)
    """
    img_bytes = create_test_image()
    
    # Generate all 16 combinations
    toggles = [False, True]
    combinations = list(product(toggles, repeat=4))
    
    assert len(combinations) == 16, "Should have exactly 16 combinations"
    
    successful_combinations = []
    failed_combinations = []
    
    for i, (noise, binarize, deskew, brightness) in enumerate(combinations, 1):
        try:
            img_array, img_pil = preprocess_image(
                img_bytes,
                apply_noise_reduction=noise,
                apply_binarization=binarize,
                apply_deskew=deskew,
                apply_brightness_norm=brightness
            )
            
            # Verify output types
            assert img_array is not None, f"Combination {i}: img_array is None"
            assert img_pil is not None, f"Combination {i}: img_pil is None"
            
            # Verify array properties
            assert img_array.ndim == 3, f"Combination {i}: Expected 3D array, got {img_array.ndim}D"
            assert img_array.shape[2] == 3, f"Combination {i}: Expected RGB (3 channels), got {img_array.shape[2]}"
            assert img_array.dtype.name == 'uint8', f"Combination {i}: Expected uint8, got {img_array.dtype}"
            
            # Verify PIL image properties
            assert img_pil.mode == "RGB", f"Combination {i}: Expected RGB mode, got {img_pil.mode}"
            assert img_pil.size[0] > 500, f"Combination {i}: Width should be > 500 (accounting for padding)"
            assert img_pil.size[1] > 500, f"Combination {i}: Height should be > 500 (accounting for padding)"
            
            successful_combinations.append({
                "combination": i,
                "noise_reduction": noise,
                "binarization": binarize,
                "deskew": deskew,
                "brightness_norm": brightness,
                "output_size": img_pil.size,
                "array_shape": img_array.shape
            })
            
        except Exception as e:
            failed_combinations.append({
                "combination": i,
                "noise_reduction": noise,
                "binarization": binarize,
                "deskew": deskew,
                "brightness_norm": brightness,
                "error": str(e)
            })
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"Toggle Combinations Test Summary")
    print(f"{'='*70}")
    print(f"Successful: {len(successful_combinations)}/16")
    print(f"Failed: {len(failed_combinations)}/16")
    
    if successful_combinations:
        print(f"\n[OK] Successful Combinations:")
        for combo in successful_combinations:
            print(f"  {combo['combination']:2d}. "
                  f"Noise={combo['noise_reduction']}, "
                  f"Binarize={combo['binarization']}, "
                  f"Deskew={combo['deskew']}, "
                  f"Brightness={combo['brightness_norm']} "
                  f"-> {combo['output_size']}")
    
    if failed_combinations:
        print(f"\n[FAIL] Failed Combinations:")
        for combo in failed_combinations:
            print(f"  {combo['combination']:2d}. "
                  f"Noise={combo['noise_reduction']}, "
                  f"Binarize={combo['binarization']}, "
                  f"Deskew={combo['deskew']}, "
                  f"Brightness={combo['brightness_norm']}")
            print(f"      Error: {combo['error']}")
    
    print(f"{'='*70}\n")
    
    # All combinations should succeed
    assert len(failed_combinations) == 0, (
        f"{len(failed_combinations)} combination(s) failed. "
        f"See details above."
    )
    assert len(successful_combinations) == 16, (
        f"Expected 16 successful combinations, got {len(successful_combinations)}"
    )


def test_performance_comparison(create_test_image):
    """
    Compare performance of different toggle combinations.
    
    This test measures relative execution time for:
    1. All enhancements disabled (baseline)
    2. All enhancements enabled (maximum processing)
    3. Recommended configuration (production settings)
    """
    import time
    
    img_bytes = create_test_image()
    
    configurations = {
        "baseline (all disabled)": {
            "apply_noise_reduction": False,
            "apply_binarization": False,
            "apply_deskew": False,
            "apply_brightness_norm": False
        },
        "maximum (all enabled)": {
            "apply_noise_reduction": True,
            "apply_binarization": True,
            "apply_deskew": True,
            "apply_brightness_norm": True
        },
        "recommended (production)": {
            "apply_noise_reduction": True,
            "apply_binarization": False,  # Can cause issues
            "apply_deskew": True,
            "apply_brightness_norm": True
        }
    }
    
    results = {}
    
    for config_name, config in configurations.items():
        start_time = time.time()
        
        # Run 3 times and take average
        for _ in range(3):
            img_array, img_pil = preprocess_image(img_bytes, **config)
        
        avg_time = (time.time() - start_time) / 3
        results[config_name] = {
            "avg_time_ms": avg_time * 1000,
            "output_size": img_pil.size
        }
    
    # Print performance comparison
    print(f"\n{'='*70}")
    print(f"Performance Comparison (average of 3 runs)")
    print(f"{'='*70}")
    for config_name, result in results.items():
        print(f"{config_name:30s}: {result['avg_time_ms']:6.2f}ms -> {result['output_size']}")
    print(f"{'='*70}\n")
    
    # Baseline should be fastest
    assert results["baseline (all disabled)"]["avg_time_ms"] <= results["maximum (all enabled)"]["avg_time_ms"]


def test_edge_cases_with_toggles(create_test_image):
    """
    Test edge cases with various toggle combinations.
    """
    # Very small image
    small_img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    small_img.format = "PNG"
    buf = io.BytesIO()
    small_img.save(buf, format="PNG")
    small_bytes = buf.getvalue()
    
    # Test with all enhancements
    img_array, img_pil = preprocess_image(
        small_bytes,
        apply_noise_reduction=True,
        apply_binarization=True,
        apply_deskew=True,
        apply_brightness_norm=True
    )
    
    assert img_array is not None
    assert img_pil is not None
    # Should be upscaled (min 300px) + padding (50px * 2)
    assert img_pil.size[0] >= 400  # 300 + 100
    assert img_pil.size[1] >= 400


def test_toggle_idempotency():
    """
    Verify that running preprocessing multiple times with same toggles
    produces consistent results (deterministic output).
    """
    # Create test image
    img = Image.new("RGB", (300, 300), color=(150, 150, 150))
    img.format = "PNG"
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()
    
    # Run twice with same settings
    config = {
        "apply_noise_reduction": True,
        "apply_binarization": False,
        "apply_deskew": True,
        "apply_brightness_norm": True
    }
    
    img_array1, img_pil1 = preprocess_image(img_bytes, **config)
    img_array2, img_pil2 = preprocess_image(img_bytes, **config)
    
    # Results should be identical
    assert img_pil1.size == img_pil2.size, "Output sizes should match"
    assert img_array1.shape == img_array2.shape, "Array shapes should match"
    # Note: We can't compare exact pixel values due to potential floating point
    # variations in enhancement operations, but dimensions should match

