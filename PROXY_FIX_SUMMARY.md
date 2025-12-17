# Proxy Support Fix Summary

## Status
Gemini calls have been removed during the Chinese-handwriting OCR refactor. Proxy guidance here is currently inactive and retained only for historical reference.

## Historical Problem
The application was failing to make Gemini API calls because Node.js native `fetch()` doesn't support SOCKS5 proxies. Even though the endpoints were reachable through the proxy, the application code couldn't use them.

## Changes Made

### 1. Added Proxy Support Infrastructure
- Added imports for `https`, `SocksProxyAgent`, and `Agent` types
- Created `getProxyAgent()` function to create a SOCKS5 proxy agent when `SOCKS5_PROXY` or `SOCKS_PROXY` environment variable is set
- Created `httpsRequest()` helper function that wraps `https.request()` with proxy support

### 2. Updated Gemini API Calls
- **OCR Function** (`extractTextWithGemini`): Replaced `fetch()` with `httpsRequest()` 
- **Translation Function** (`generateTranslation`): Replaced `fetch()` with `httpsRequest()`

### 3. Fixed Type Issues
- Added `'alternative'` to the `OCRResult.method` type union to fix linting error

### 4. Updated Dependencies
- Moved `socks-proxy-agent` from `devDependencies` to `dependencies` since it's used in production code

## Configuration

The proxy is automatically detected from environment variables:
- `SOCKS5_PROXY` or `SOCKS_PROXY` - SOCKS5 proxy URL (e.g., `socks5://127.0.0.1:1080`)

If these variables are not set, the code will work without a proxy (direct connection).

## Testing

1. **Test connectivity** (already working):
   ```bash
   npx tsx scripts/test-gemini-connectivity.ts
   ```

2. **Test the application**:
   - Set `SOCKS5_PROXY=socks5://127.0.0.1:1080` in your environment
   - Set `GOOGLE_GEMINI_API_KEY=your_key` in your `.env` file
   - Run the application and try uploading an image

## Remaining Considerations

The `src/lib/grm.ts` file uses the `@google/generative-ai` SDK which may also need proxy support. The SDK internally makes HTTP requests that might not use the proxy. If glyph reconstruction fails, you may need to:

1. Configure the SDK to use a proxy (if it supports it)
2. Or use `proxychains4` to make the proxy transparent to all applications

## Files Modified

- `src/lib/ai-processor.ts` - Added proxy support for Gemini API calls
- `package.json` - Moved `socks-proxy-agent` to dependencies

## Next Steps

If you still experience issues:

1. **Verify environment variables are set**:
   ```bash
   echo $SOCKS5_PROXY
   ```

2. **Check if proxy is working**:
   ```bash
   npx tsx scripts/test-gemini-connectivity.ts
   ```

3. **For complete transparency**, use `proxychains4`:
   ```bash
   proxychains4 npm run dev
   ```

