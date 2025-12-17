# Hugging Face OCR Models Deprecation

## Issue

All the TrOCR (Transformer-based OCR) models on Hugging Face Inference API have been **deprecated** and return **410 Gone** status codes:

- ❌ `microsoft/trocr-base-handwritten` - 410 Gone
- ❌ `microsoft/trocr-base-printed` - 410 Gone  
- ❌ `microsoft/trocr-small-handwritten` - 410 Gone
- ❌ `microsoft/trocr-small-printed` - 410 Gone

## Current Status (Phase 1)

- All Hugging Face OCR usage has been removed.
- Gemini OCR has been removed.
- Processing endpoints are disabled until the new Chinese-handwriting OCR backend is in place.

## Next Steps

- Integrate the new Chinese-handwriting OCR backend (self-hosted).
- Restore processing endpoints once the new pipeline is wired.

## References

- [Google Gemini API](https://aistudio.google.com/app/apikey)
- [Hugging Face Inference API](https://huggingface.co/docs/api-inference/index)
- [Tencent HunyuanOCR](https://huggingface.co/tencent/HunyuanOCR)


