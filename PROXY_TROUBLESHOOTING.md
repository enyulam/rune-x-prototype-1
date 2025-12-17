# Proxy Troubleshooting Guide

## Status
Gemini calls were removed during the Chinese-handwriting OCR refactor. Proxychains/SOCKS guidance below is inactive and kept for reference only.

## Historical Issue: Proxychains Conflict

You're seeing errors like:
```
[proxychains] Strict chain  ...  127.0.0.1:9050  ...  timeout
connect ECONNREFUSED 224.0.0.3:443
```

This indicates:
1. **Proxychains is active** and trying to use `127.0.0.1:9050` (Tor's default port)
2. **DNS resolution is broken** (resolving to multicast address `224.0.0.3`)
3. **Proxy conflict** between proxychains and code-level proxy

## Solutions

### Option 1: Configure Proxychains to Use Your SOCKS5 Proxy (Recommended)

Edit your proxychains configuration:

```bash
sudo nano /etc/proxychains4.conf
```

Change the proxy line to use your SOCKS5 proxy:
```
socks5 127.0.0.1 1080
```

Instead of:
```
socks5 127.0.0.1 9050  # This is Tor's default port
```

Then restart your application.

### Option 2: Disable Proxychains and Use Code-Level Proxy

1. **Stop using proxychains** - Don't run your app with `proxychains4`
2. **Set environment variable**:
   ```bash
   export SOCKS5_PROXY=socks5://127.0.0.1:1080
   ```
3. **Run normally**:
   ```bash
   npm run dev
   ```

The code will automatically detect and use the proxy from the environment variable.

### Option 3: Disable All Proxies (For Testing)

If you want to test without any proxy:

```bash
unset SOCKS5_PROXY
unset SOCKS_PROXY
# Don't use proxychains
npm run dev
```

## Detection

The code now automatically detects if proxychains is active and will skip the code-level proxy to avoid conflicts. You'll see this message:

```
[Proxy] Proxychains detected, skipping code-level proxy to avoid conflicts
```

## Verification

To check which proxy is being used:

1. **Check environment variables**:
   ```bash
   echo $SOCKS5_PROXY
   echo $SOCKS_PROXY
   ```

2. **Check proxychains config**:
   ```bash
   cat /etc/proxychains4.conf | grep -E "^socks"
   ```

3. **Test connectivity**:
   ```bash
   npx tsx scripts/test-gemini-connectivity.ts
   ```

## Recommended Setup

For your setup with `socks5://127.0.0.1:1080`:

**Best approach**: Use code-level proxy (Option 2)
- Set `SOCKS5_PROXY=socks5://127.0.0.1:1080`
- Don't use proxychains
- The code will handle the proxy automatically

**Alternative**: Configure proxychains (Option 1)
- Edit `/etc/proxychains4.conf` to use port 1080
- Run with `proxychains4 npm run dev`
- The code will detect proxychains and skip its own proxy

## Error Messages Explained

- `ECONNREFUSED 224.0.0.3:443` - DNS resolution failed, hostname resolved to multicast address (proxy/DNS issue)
- `timeout` - Proxy server not responding or wrong port
- `Strict chain ... 127.0.0.1:9050` - Proxychains trying to use Tor port instead of your proxy

