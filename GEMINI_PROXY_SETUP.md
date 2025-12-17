# Gemini API Proxy Configuration

## Status
Gemini calls have been removed during the Chinese-handwriting OCR refactor. The connectivity guidance below is inactive and retained for historical reference.

## Important Note About fetch()

⚠️ **Node.js native `fetch()` does NOT support SOCKS5 proxies directly.**

The test script uses Node's `https` module which supports proxy agents, but your application code uses `fetch()` which doesn't. This means:

1. ✅ **Connectivity is working** - The test confirms endpoints are reachable
2. ⚠️ **Application may not use proxy** - `fetch()` calls in your code might not route through the proxy

## Solutions

### Option 1: Use proxychains (Recommended for Development)

Make the proxy transparent to all applications:

```bash
# Install proxychains
sudo apt-get install proxychains4  # Ubuntu/Debian
# or
brew install proxychains-ng        # macOS

# Configure proxychains
sudo nano /etc/proxychains4.conf
# Add: socks5 127.0.0.1 1080

# Run your app through proxychains
proxychains4 npm run dev
```

### Option 2: Set HTTP_PROXY Environment Variable

Some tools respect HTTP_PROXY. You can set up an HTTP-to-SOCKS5 bridge:

```bash
# Using a tool like privoxy or similar to bridge HTTP to SOCKS5
export HTTP_PROXY=http://127.0.0.1:8118  # If you set up a bridge
export HTTPS_PROXY=http://127.0.0.1:8118
```

### Option 3: Use undici (For Production)

Replace `fetch()` with `undici` which has better proxy support:

```bash
npm install undici
```

Then use `undici.fetch()` instead of native `fetch()`.

### Option 4: Modify Code to Use https Module

For critical API calls, you can modify the code to use the `https` module directly (as done in the test script) when a proxy is detected.

## Testing Connectivity

Run the connectivity test anytime:

```bash
npx tsx scripts/test-gemini-connectivity.ts
```

### Environment Variables

- `SOCKS5_PROXY` - SOCKS5 proxy URL (default: `socks5://127.0.0.1:1080`)
- `USE_PROXY` - Set to `false` to disable proxy (default: `true`)
- `GOOGLE_GEMINI_API_KEY` - Optional, for more accurate API testing

### Example

```bash
# Test with custom proxy
SOCKS5_PROXY=socks5://127.0.0.1:1080 npx tsx scripts/test-gemini-connectivity.ts

# Test without proxy
USE_PROXY=false npx tsx scripts/test-gemini-connectivity.ts

# Test with API key (more accurate)
GOOGLE_GEMINI_API_KEY=your_key npx tsx scripts/test-gemini-connectivity.ts
```

## Current Status

Based on the test results:
- ✅ Base domain is reachable
- ✅ All 6 endpoints are reachable through proxy
- ⚠️ Application `fetch()` calls may need proxy configuration

## Next Steps

1. If you're experiencing API call failures, try running the app through `proxychains4`
2. Or modify the code to use the `https` module for Gemini API calls when proxy is detected
3. Consider using `undici` for better proxy support in production

