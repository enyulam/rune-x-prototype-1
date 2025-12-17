# Ancient Chinese Models Integration

## Overview

I've integrated support for ancient Chinese language models from Hugging Face to improve OCR accuracy for ancient Chinese text. The models are used for post-processing OCR results to improve recognition accuracy.

## Models Integrated

### 1. Jihuai/bert-ancient-chinese
- **Type**: Fill-Mask model
- **Purpose**: Corrects and improves OCR results for ancient Chinese text
- **API**: Available via Hugging Face Inference API
- **Link**: https://huggingface.co/Jihuai/bert-ancient-chinese

### 2. uer/gpt2-chinese-ancient
- **Type**: Text Generation model
- **Purpose**: Verifies OCR results by generating continuations (helps validate if OCR text makes sense)
- **API**: Available via Hugging Face Inference API
- **Link**: https://huggingface.co/uer/gpt2-chinese-ancient

## How It Works

### Processing Pipeline

```
1. OCR Extraction (Hugging Face OCR models)
   ↓
2. Post-Processing (Ancient Chinese models)
   - Uses gpt2-chinese-ancient to verify OCR text
   - Can be extended to use bert-ancient-chinese for corrections
   ↓
3. Return Improved Result
```

### Current Implementation

1. **OCR Phase**: 
   - Tries Hugging Face OCR models first (TrOCR models)
   - Falls back to Gemini if available
   - All OCR models now use proxy-aware requests

2. **Post-Processing Phase**:
   - After successful OCR, uses `gpt2-chinese-ancient` to verify the text
   - If verification succeeds, slightly boosts confidence score
   - Currently returns original text (can be enhanced to use model suggestions)

## API Usage

Both models are available via Hugging Face Inference API:

### Endpoint Format
```
https://api-inference.huggingface.co/models/{model_id}
```

### Authentication
- **Free tier**: No API key required for public models
- **Optional**: Set `HUGGINGFACE_API_KEY` in environment for higher rate limits

### Example Request (gpt2-chinese-ancient)
```json
POST https://api-inference.huggingface.co/models/uer/gpt2-chinese-ancient
{
  "inputs": "当是时",
  "parameters": {
    "max_new_tokens": 10,
    "return_full_text": false
  }
}
```

## Configuration

### Environment Variables

```bash
# Optional: For higher rate limits
HUGGINGFACE_API_KEY=your_huggingface_token_here

# Required for proxy support (if needed)
SOCKS5_PROXY=socks5://127.0.0.1:1080
```

### OCR Models Used

The system now tries these Hugging Face OCR models in order:
1. `microsoft/trocr-base-handwritten` - For handwritten text
2. `microsoft/trocr-base-printed` - For printed text
3. `microsoft/trocr-small-handwritten` - Smaller model for handwritten
4. `microsoft/trocr-small-printed` - Smaller model for printed

## Limitations

### Current Limitations

1. **Text Models, Not OCR**: 
   - `bert-ancient-chinese` and `gpt2-chinese-ancient` are text processing models
   - They cannot extract text from images directly
   - They are used for post-processing OCR results

2. **Post-Processing is Basic**:
   - Currently only verifies text with `gpt2-chinese-ancient`
   - Does not yet use model suggestions to correct OCR errors
   - Can be enhanced in the future

3. **Fill-Mask Usage**:
   - `bert-ancient-chinese` requires `[MASK]` tokens to work
   - Not yet integrated for automatic error correction
   - Can be added for targeted character correction

## Future Enhancements

### Potential Improvements

1. **Error Correction**:
   - Use `bert-ancient-chinese` fill-mask to correct specific OCR errors
   - Identify low-confidence characters and use model to suggest corrections

2. **Text Validation**:
   - Use `gpt2-chinese-ancient` to generate continuations
   - Compare with OCR results to identify inconsistencies
   - Flag potential OCR errors for manual review

3. **Confidence Scoring**:
   - Use model outputs to adjust confidence scores
   - Higher confidence if models generate reasonable continuations

4. **Batch Processing**:
   - Process multiple characters at once
   - Use models to verify entire sentences/phrases

## Testing

To test the integration:

1. **Set up environment** (optional):
   ```bash
   export HUGGINGFACE_API_KEY=your_token
   export SOCKS5_PROXY=socks5://127.0.0.1:1080  # If needed
   ```

2. **Upload an image** with ancient Chinese text

3. **Check logs** for:
   - `Post-processing with gpt2-chinese-ancient (verification)...`
   - `Post-processing verification completed`

## References

- [Jihuai/bert-ancient-chinese](https://huggingface.co/Jihuai/bert-ancient-chinese)
- [uer/gpt2-chinese-ancient](https://huggingface.co/uer/gpt2-chinese-ancient)
- [Hugging Face Inference API](https://huggingface.co/docs/api-inference/index)

## Notes

- Both models are available via the free Inference API
- No API key required for basic usage
- Models work with text, not images (post-processing only)
- Proxy support is included for all Hugging Face API calls


