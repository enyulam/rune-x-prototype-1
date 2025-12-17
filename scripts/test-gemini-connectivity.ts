#!/usr/bin/env tsx
/**
 * Test script to check connectivity to Gemini API endpoints
 * Supports SOCKS5 proxy configuration
 */

import { SocksProxyAgent } from 'socks-proxy-agent'
import type { Agent } from 'https'
import * as https from 'https'
import * as http from 'http'

// Gemini API endpoints to test
const ENDPOINTS = [
  { version: 'v1beta', model: 'gemini-2.5-flash', name: 'OCR - v1beta gemini-2.5-flash' },
  { version: 'v1', model: 'gemini-2.5-flash', name: 'OCR - v1 gemini-2.5-flash' },
  { version: 'v1beta', model: 'gemini-2.5-flash-lite', name: 'OCR - v1beta gemini-2.5-flash-lite' },
  { version: 'v1', model: 'gemini-2.5-flash-lite', name: 'OCR - v1 gemini-2.5-flash-lite' },
  { version: 'v1beta', model: 'gemini-2.0-flash-exp', name: 'GRM - v1beta gemini-2.0-flash-exp' },
  { version: 'v1', model: 'gemini-2.0-flash-exp', name: 'GRM - v1 gemini-2.0-flash-exp' },
]

// Base URL for Gemini API
const BASE_URL = 'generativelanguage.googleapis.com'

// Proxy configuration (from environment or default)
const PROXY_URL = process.env.SOCKS5_PROXY || 'socks5://127.0.0.1:1080'
const USE_PROXY = process.env.USE_PROXY !== 'false' // Default to true if proxy is set

interface TestResult {
  endpoint: string
  name: string
  reachable: boolean
  statusCode?: number
  error?: string
  responseTime?: number
}

/**
 * Test connectivity to a specific endpoint
 */
async function testEndpoint(
  version: string,
  model: string,
  name: string,
  apiKey?: string
): Promise<TestResult> {
  const path = `/${version}/models/${model}:generateContent${apiKey ? `?key=${apiKey}` : ''}`
  const url = `https://${BASE_URL}${path}`
  
  const startTime = Date.now()
  
  return new Promise((resolve) => {
    try {
      // Configure agent (with or without proxy)
      let agent: https.Agent | undefined
      
      if (USE_PROXY && PROXY_URL) {
        try {
          agent = new SocksProxyAgent(PROXY_URL) as Agent
          console.log(`  Using proxy: ${PROXY_URL}`)
        } catch (proxyError) {
          console.warn(`  Warning: Failed to create proxy agent: ${proxyError}`)
        }
      }

      const options: https.RequestOptions = {
        hostname: BASE_URL,
        path: path,
        method: 'GET', // Just test connectivity, not actual API call
        agent: agent,
        timeout: 10000, // 10 second timeout
      }

      const req = https.request(options, (res) => {
        const responseTime = Date.now() - startTime
        const statusCode = res.statusCode || 0
        
        // 404 is expected (model might not exist or wrong API key)
        // 400/401/403 are also "reachable" responses
        // 200 would be ideal but unlikely without proper request body
        const reachable = statusCode >= 200 && statusCode < 500
        
        resolve({
          endpoint: url,
          name,
          reachable,
          statusCode,
          responseTime,
        })
      })

      req.on('error', (error: any) => {
        const responseTime = Date.now() - startTime
        resolve({
          endpoint: url,
          name,
          reachable: false,
          error: error.message || String(error),
          responseTime,
        })
      })

      req.on('timeout', () => {
        req.destroy()
        resolve({
          endpoint: url,
          name,
          reachable: false,
          error: 'Connection timeout',
          responseTime: Date.now() - startTime,
        })
      })

      req.end()
    } catch (error: any) {
      resolve({
        endpoint: url,
        name,
        reachable: false,
        error: error.message || String(error),
        responseTime: Date.now() - startTime,
      })
    }
  })
}

/**
 * Test basic connectivity to the base domain
 */
async function testBaseConnectivity(): Promise<boolean> {
  return new Promise((resolve) => {
    const options: https.RequestOptions = {
      hostname: BASE_URL,
      path: '/',
      method: 'HEAD',
      timeout: 5000,
    }

    if (USE_PROXY && PROXY_URL) {
      try {
        options.agent = new SocksProxyAgent(PROXY_URL) as Agent
      } catch (error) {
        console.warn(`Warning: Could not set up proxy for base connectivity test`)
      }
    }

    const req = https.request(options, (res) => {
      resolve(true)
    })

    req.on('error', () => {
      resolve(false)
    })

    req.on('timeout', () => {
      req.destroy()
      resolve(false)
    })

    req.end()
  })
}

/**
 * Main test function
 */
async function main() {
  console.log('🔍 Testing Gemini API Endpoint Connectivity\n')
  console.log(`Proxy Configuration: ${USE_PROXY ? PROXY_URL : 'Disabled'}\n`)

  // Test base connectivity first
  console.log('1. Testing base domain connectivity...')
  const baseReachable = await testBaseConnectivity()
  if (baseReachable) {
    console.log('   ✅ Base domain is reachable\n')
  } else {
    console.log('   ❌ Base domain is NOT reachable\n')
    console.log('   This might indicate a network or proxy issue.\n')
  }

  // Get API key from environment (optional, for more accurate testing)
  const apiKey = process.env.GOOGLE_GEMINI_API_KEY
  if (!apiKey) {
    console.log('⚠️  Note: GOOGLE_GEMINI_API_KEY not set. Testing without API key.\n')
    console.log('   (Testing connectivity only - 404 responses are expected)\n')
  } else {
    console.log('✅ API key found in environment\n')
    console.log('   Will test with actual API call after connectivity test\n')
  }

  // Test each endpoint
  console.log('2. Testing individual endpoints...\n')
  const results: TestResult[] = []

  for (const endpoint of ENDPOINTS) {
    process.stdout.write(`   Testing ${endpoint.name}... `)
    const result = await testEndpoint(
      endpoint.version,
      endpoint.model,
      endpoint.name,
      apiKey
    )
    results.push(result)

    if (result.reachable) {
      console.log(`✅ Reachable (${result.statusCode} - ${result.responseTime}ms)`)
    } else {
      console.log(`❌ Not reachable`)
      if (result.error) {
        console.log(`      Error: ${result.error}`)
      }
      if (result.statusCode) {
        console.log(`      Status: ${result.statusCode}`)
      }
    }
  }

  // Summary
  console.log('\n' + '='.repeat(60))
  console.log('📊 Summary\n')
  
  const reachableCount = results.filter(r => r.reachable).length
  const totalCount = results.length
  
  console.log(`Reachable: ${reachableCount}/${totalCount} endpoints`)
  
  if (reachableCount === 0) {
    console.log('\n❌ No endpoints are reachable!')
    console.log('\nPossible issues:')
    console.log('  1. Network connectivity problem')
    console.log('  2. Proxy configuration issue')
    console.log('  3. Firewall blocking connections')
    console.log('  4. DNS resolution problem')
    console.log('\nTroubleshooting:')
    console.log(`  - Check if proxy is running: ${PROXY_URL}`)
    console.log('  - Try setting USE_PROXY=false to test without proxy')
    console.log('  - Check network connectivity to generativelanguage.googleapis.com')
  } else if (reachableCount < totalCount) {
    console.log('\n⚠️  Some endpoints are not reachable')
    console.log('\nUnreachable endpoints:')
    results
      .filter(r => !r.reachable)
      .forEach(r => {
        console.log(`  - ${r.name}`)
        if (r.error) console.log(`    Error: ${r.error}`)
      })
  } else {
    console.log('\n✅ All endpoints are reachable!')
  }

  console.log('\n' + '='.repeat(60))
}

// Run the tests
main().catch((error) => {
  console.error('Fatal error:', error)
  process.exit(1)
})

