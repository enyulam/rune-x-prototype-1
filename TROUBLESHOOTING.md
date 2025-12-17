# Troubleshooting Guide

## Common Issues and Solutions

### Issue: Processing returns 503
Processing endpoints are temporarily disabled while we integrate the new Chinese-handwriting OCR backend. This is expected in the current phase.

### Issue: "Failed to extract text from image"

This means OCR couldn't read any text from your image.

**Check:**
- Image quality (should be clear, not blurry)
- Text visibility (text should be clearly visible)
- Image format (JPG, PNG, WebP supported)
- File size (should be reasonable, not too large)

**Try:**
- Using a higher resolution image
- Ensuring good lighting/contrast in the image
- Using Google Gemini API for better OCR

### Issue: Module not found errors

If you see errors about missing modules:
```bash
npm install
```

This will install all required dependencies including:
- `tesseract.js`
- `@google/generative-ai`

### Issue: Hugging Face 410/404 errors

These mean the model endpoint doesn't exist or was removed.

**Solution**: The system automatically tries multiple models. If all fail, use Google Gemini API instead.

## Getting Help

1. **Check Console Logs**: The system now provides detailed error messages
2. **Check Network**: Ensure your server has internet access
3. **Image Quality**: Ensure your images are clear and readable

## Recommended Setup for Best Results

```env
# Required
DATABASE_URL="file:./prisma/db/dev.db"
NEXTAUTH_URL="http://localhost:3001"
NEXTAUTH_SECRET="your-secret-key"
```

## Testing Without OCR

If you want to test the system without OCR working:

```env
ENABLE_OCR_FALLBACK=true
```

This fallback only affects development; the primary OCR pipeline is currently disabled during refactor.







