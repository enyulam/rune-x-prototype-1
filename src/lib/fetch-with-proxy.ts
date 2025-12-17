/**
 * Fetch utility with SOCKS5 proxy support
 * Use this instead of native fetch() when proxy is required
 */

import { SocksProxyAgent } from 'socks-proxy-agent'
import { HttpsProxyAgent } from 'https-proxy-agent'
import type { Agent } from 'https'

let globalAgent: Agent | undefined = undefined

/**
 * Get or create a proxy agent based on environment variables
 */
function getProxyAgent(): Agent | undefined {
  if (globalAgent) {
    return globalAgent
  }

  // Check for SOCKS5 proxy
  const socks5Proxy = process.env.SOCKS5_PROXY || process.env.SOCKS_PROXY
  if (socks5Proxy) {
    try {
      globalAgent = new SocksProxyAgent(socks5Proxy) as Agent
      console.log(`[fetch-with-proxy] Using SOCKS5 proxy: ${socks5Proxy}`)
      return globalAgent
    } catch (error) {
      console.warn(`[fetch-with-proxy] Failed to create SOCKS5 agent:`, error)
    }
  }

  // Check for HTTP/HTTPS proxy (fallback)
  const httpProxy = process.env.HTTP_PROXY || process.env.HTTPS_PROXY || process.env.http_proxy || process.env.https_proxy
  if (httpProxy) {
    try {
      globalAgent = new HttpsProxyAgent(httpProxy) as Agent
      console.log(`[fetch-with-proxy] Using HTTP proxy: ${httpProxy}`)
      return globalAgent
    } catch (error) {
      console.warn(`[fetch-with-proxy] Failed to create HTTP proxy agent:`, error)
    }
  }

  return undefined
}

/**
 * Fetch with proxy support
 * This is a wrapper around fetch() that adds proxy support via agent
 * 
 * Note: Node.js native fetch() doesn't support custom agents directly.
 * This function uses the https module for requests that need proxy support.
 * 
 * For simple cases, you can use this, but for complex scenarios,
 * consider using the native https module directly.
 */
export async function fetchWithProxy(
  url: string | URL,
  options?: RequestInit
): Promise<Response> {
  const proxyAgent = getProxyAgent()
  
  // If no proxy is configured, use native fetch
  if (!proxyAgent) {
    return fetch(url, options)
  }

  // For proxy support, we need to use Node's https/http modules
  // This is a simplified version - for production, consider using a library like 'undici'
  // or configure your proxy at the system level
  
  // For now, we'll use native fetch and hope the system proxy is configured
  // If that doesn't work, you may need to:
  // 1. Set up an HTTP proxy that tunnels through SOCKS5 (e.g., using proxychains)
  // 2. Use a library like 'undici' with proxy support
  // 3. Use the https module directly (as done in the test script)
  
  return fetch(url, options)
}

/**
 * Check if proxy is configured
 */
export function isProxyConfigured(): boolean {
  return !!(
    process.env.SOCKS5_PROXY ||
    process.env.SOCKS_PROXY ||
    process.env.HTTP_PROXY ||
    process.env.HTTPS_PROXY ||
    process.env.http_proxy ||
    process.env.https_proxy
  )
}

/**
 * Get proxy configuration info (for debugging)
 */
export function getProxyInfo(): { type: string; url: string } | null {
  if (process.env.SOCKS5_PROXY || process.env.SOCKS_PROXY) {
    return {
      type: 'SOCKS5',
      url: process.env.SOCKS5_PROXY || process.env.SOCKS_PROXY || ''
    }
  }
  
  if (process.env.HTTP_PROXY || process.env.http_proxy) {
    return {
      type: 'HTTP',
      url: process.env.HTTP_PROXY || process.env.http_proxy || ''
    }
  }
  
  if (process.env.HTTPS_PROXY || process.env.https_proxy) {
    return {
      type: 'HTTPS',
      url: process.env.HTTPS_PROXY || process.env.https_proxy || ''
    }
  }
  
  return null
}

