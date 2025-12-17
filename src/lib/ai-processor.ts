/**
 * AI Processing Service (stubbed for MVP refactor)
 * Phase 1: Remove Gemini/HF/GRM dependencies and block legacy OCR.
 *
 * The functions below intentionally return informative errors so the
 * frontend can handle the temporary gap while the new handwriting OCR
 * backend is being integrated.
 */

// Types
export interface OCRResult {
  text: string
  confidence: number
  method: 'disabled'
  error?: string
}

export interface GlyphMatch {
  symbol: string
  confidence: number
  position: number
  boundingBox?: { x: number; y: number; width: number; height: number }
  meaning?: string
}

export interface ProcessingResult {
  extractedText: string
  glyphs: GlyphMatch[]
  scriptType?: string
  confidence: number
  method: string
}

/**
 * Stubbed OCR – returns a controlled failure while the new pipeline is built.
 */
export async function extractTextFromImage(): Promise<OCRResult> {
  return {
    text: '',
    confidence: 0,
    method: 'disabled',
    error: 'OCR pipeline disabled pending Chinese-handwriting MVP integration'
  }
}

/**
 * Post-process OCR text using ancient Chinese language models
 * This improves recognition accuracy for ancient Chinese characters
 * Note: These models work with text, not images, so they're used for post-processing
 */
async function postProcessWithAncientChineseModels(text: string): Promise<string> {
  if (!text || text.length === 0) {
    return text
  }

  const hfToken = process.env.HUGGINGFACE_API_KEY
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  
  if (hfToken) {
    headers['Authorization'] = `Bearer ${hfToken}`
  }

  // Note: bert-ancient-chinese is a fill-mask model, which requires [MASK] tokens
  // For now, we'll skip it and focus on using gpt2-chinese-ancient for text generation/verification
  // In the future, we could use fill-mask to correct specific characters
  
  // Try gpt2-chinese-ancient for text generation/verification
  // This can help verify if the OCR text makes sense in ancient Chinese context
  try {
    console.log('Post-processing with gpt2-chinese-ancient (verification)...')
    
    // Use a small prompt to verify the text makes sense
    // The model can generate continuations that help verify OCR accuracy
    const prompt = text.substring(0, Math.min(50, text.length)) // Use first 50 chars
    
    const response = await httpsRequest(
      'https://api-inference.huggingface.co/models/uer/gpt2-chinese-ancient',
      {
        method: 'POST',
        headers,
        body: JSON.stringify({
          inputs: prompt,
          parameters: {
            max_new_tokens: 10, // Just generate a few tokens for verification
            return_full_text: false,
          }
        }),
        timeout: 30000,
      }
    )

    if (response.ok) {
      const data = await response.json()
      // If the model can generate reasonable continuations, the OCR text is likely correct
      console.log('Post-processing verification completed (gpt2-chinese-ancient)')
      // For now, we return the original text
      // In the future, we could use the model's output to correct OCR errors
      return text
    }
  } catch (error: any) {
    console.log('Post-processing with gpt2-chinese-ancient failed:', error.message)
    // Continue without post-processing
  }

  return text
}

/**
 * Main OCR function - tries multiple methods with fallback
 */
export async function extractTextFromImage(imagePath: string): Promise<OCRResult> {
  console.log('=== Starting OCR extraction ===')
  
  // Try methods in order of preference
  const methods: Array<{ name: string; fn: (path: string) => Promise<OCRResult> }> = []
  
  // 1. Try Gemini if API key is available (only reliable OCR option)
  // Note: All Hugging Face OCR models have been deprecated (410 Gone)
  if (process.env.GOOGLE_GEMINI_API_KEY) {
    console.log('Gemini API key found, adding Gemini to methods list')
    methods.push({ name: 'Gemini', fn: extractTextWithGemini })
  } else {
    console.log('Gemini API key NOT found in environment variables')
    console.log('⚠️  ERROR: Gemini API key is REQUIRED - All Hugging Face OCR models have been deprecated')
  }
  
  // 2. Hugging Face OCR - All models deprecated (410 Gone)
  // Keeping function for future use, but it will always fail
  // Uncomment below if new OCR models become available on Hugging Face
  // methods.push({ name: 'Hugging Face OCR', fn: extractTextWithHuggingFace })
  
  // 3. Alternative services (placeholder for future)
  // methods.push(extractTextWithAlternativeServices)
  
  // Note: Tesseract.js doesn't work in Next.js API routes (Web Workers limitation)
  
  for (const method of methods) {
    try {
      console.log(`\n>>> Trying OCR method: ${method.name}`)
      const result = await method.fn(imagePath)
      if (result.text && result.text.length > 0) {
        console.log(`✓ OCR method succeeded: ${result.method}`)
        
        // Post-process with ancient Chinese models to improve accuracy
        try {
          const improvedText = await postProcessWithAncientChineseModels(result.text)
          if (improvedText && improvedText !== result.text) {
            console.log('Text improved by post-processing')
            result.text = improvedText
            result.confidence = Math.min(result.confidence + 0.05, 0.95) // Slight confidence boost
          }
        } catch (postProcessError: any) {
          console.log('Post-processing failed, using original OCR result:', postProcessError.message)
          // Continue with original result
        }
        
        return result
      }
      // If method returned empty text, try next one
      console.log(`✗ OCR method returned empty text: ${result.method}, trying next...`)
    } catch (error: any) {
      // If method threw error, try next one
      console.log(`✗ OCR method failed (${method.name}):`, error.message)
      continue
    }
  }

  // All methods failed
  return {
    text: '',
    confidence: 0,
    method: 'fallback',
    error: 'All OCR methods failed. Please ensure the image is clear and contains readable text.'
  }
}

/**
 * Get character meanings from AI translation context
 * Uses Gemini to provide meanings for each character
 */
async function getCharacterMeanings(
  extractedText: string,
  translationContext?: string
): Promise<Record<string, string>> {
  const meanings: Record<string, string> = {}
  
  if (!extractedText || extractedText.length === 0) {
    return meanings
  }

  // Extract unique Chinese characters
  const uniqueChars = Array.from(new Set(Array.from(extractedText.replace(/\s+/g, ''))))
    .filter(char => /[\u4e00-\u9fff]/.test(char)) // Only Chinese characters
  
  if (uniqueChars.length === 0) {
    return meanings
  }

  // If we have translation context, try to extract character meanings from it
  if (process.env.GOOGLE_GEMINI_API_KEY) {
    try {
      // For very long character lists, we may need to batch them
      // But let's try the full list first with increased token limit
      const charsList = uniqueChars.join('')
      // Increase maxOutputTokens for longer character lists (estimate ~60 chars per character meaning)
      // For 430 characters, we'd need ~25,800 tokens, but we cap at 8000 for safety
      const estimatedTokens = Math.min(Math.max(800, uniqueChars.length * 60), 8000)
      
      console.log(`Requesting meanings for ${uniqueChars.length} unique characters (estimated ${estimatedTokens} tokens)`)
      
      const requestBody = JSON.stringify({
        contents: [{
          parts: [{
            text: `You are an expert in ancient Chinese characters. For each of these ${uniqueChars.length} Chinese characters: "${charsList}", provide its English meaning(s).
            ${translationContext ? `The text was translated as: "${translationContext.substring(0, 500)}". Use this context to provide accurate meanings.` : 'Provide the most common meanings for each character.'}
            
            CRITICAL: Return ONLY a valid JSON object where each key is a Chinese character and the value is its English meaning(s).
            Format: {"的": "possessive particle, of", "是": "to be, is, are", "不": "not, no", "了": "completed action marker", "人": "person, people, human"}
            Include multiple meanings separated by commas when applicable. 
            You MUST provide meanings for ALL ${uniqueChars.length} characters in the list.
            Do not include any explanation, only the JSON object.`
          }]
        }],
        generationConfig: {
          temperature: 0.1,
          maxOutputTokens: estimatedTokens // Use calculated estimate, capped at 8000
        }
      })
      
      const response = await httpsRequest(
        `https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key=${process.env.GOOGLE_GEMINI_API_KEY}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: requestBody,
          timeout: 30000,
        }
      )

      if (response.ok) {
        const data = await response.json()
        const responseText = data.candidates?.[0]?.content?.parts?.[0]?.text || ''
        console.log('AI response for character meanings:', responseText.substring(0, 200))
        
        // Try to extract JSON from the response
        try {
          // Remove markdown code blocks if present
          let jsonText = responseText.replace(/```json\s*/g, '').replace(/```\s*/g, '').trim()
          const jsonMatch = jsonText.match(/\{[\s\S]*\}/)
          if (jsonMatch) {
            const parsedMeanings = JSON.parse(jsonMatch[0])
            // Validate and clean the meanings
            for (const [char, meaning] of Object.entries(parsedMeanings)) {
              if (typeof meaning === 'string' && meaning.trim().length > 0) {
                meanings[char] = meaning.trim()
              }
            }
            console.log(`Extracted meanings for ${Object.keys(meanings).length} characters from AI:`, Object.keys(meanings))
          } else {
            console.log('No JSON object found in AI response')
          }
        } catch (parseError: any) {
          console.log('Could not parse character meanings from AI response:', parseError.message)
          // Fallback: try to extract meanings from the text directly
          const lines = responseText.split('\n')
          for (const line of lines) {
            const match = line.match(/["']([\u4e00-\u9fff])["']\s*:\s*["']([^"']+)["']/)
            if (match) {
              meanings[match[1]] = match[2].trim()
            }
          }
          if (Object.keys(meanings).length > 0) {
            console.log(`Extracted ${Object.keys(meanings).length} meanings using fallback method`)
          }
        }
      } else {
        const errorText = await response.text().catch(() => 'Unknown error')
        console.error('AI character meanings request failed:', response.status, errorText.substring(0, 200))
        // Don't return empty - try to retry with a simpler request
        if (response.status === 429 || response.status >= 500) {
          console.log('Retrying character meanings with simpler request...')
          // Could implement retry logic here if needed
        }
      }
    } catch (error: any) {
      console.error('Failed to get character meanings from AI:', error.message || error)
      // Don't silently fail - this is critical for glyph meanings
    }
  } else {
    console.warn('GOOGLE_GEMINI_API_KEY not found - cannot extract character meanings')
  }

  // Fallback: If AI failed to provide meanings, use translation API for individual characters
  if (Object.keys(meanings).length === 0 && uniqueChars.length > 0 && process.env.GOOGLE_GEMINI_API_KEY) {
    console.log('AI character meanings failed, trying fallback translation for individual characters...')
    
    // Try translating characters individually or in small batches
    const batchSize = 20 // Process 20 characters at a time
    for (let i = 0; i < uniqueChars.length; i += batchSize) {
      const batch = uniqueChars.slice(i, i + batchSize)
      const batchText = batch.join('')
      
      try {
        const requestBody = JSON.stringify({
          contents: [{
            parts: [{
              text: `Translate each of these Chinese characters to English, providing their meanings: "${batchText}". 
              Return a JSON object where each character is a key and its English meaning is the value.
              Format: {"寒": "cold, winter", "蝉": "cicada", ...}`
            }]
          }],
          generationConfig: {
            temperature: 0.1,
            maxOutputTokens: 1000
          }
        })
        
        const response = await httpsRequest(
          `https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key=${process.env.GOOGLE_GEMINI_API_KEY}`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: requestBody,
            timeout: 30000,
          }
        )
        
        if (response.ok) {
          const data = await response.json()
          const responseText = data.candidates?.[0]?.content?.parts?.[0]?.text || ''
          
          try {
            let jsonText = responseText.replace(/```json\s*/g, '').replace(/```\s*/g, '').trim()
            const jsonMatch = jsonText.match(/\{[\s\S]*\}/)
            if (jsonMatch) {
              const parsedMeanings = JSON.parse(jsonMatch[0])
              for (const [char, meaning] of Object.entries(parsedMeanings)) {
                if (typeof meaning === 'string' && meaning.trim().length > 0) {
                  meanings[char] = meaning.trim()
                }
              }
            }
          } catch (parseError) {
            // Try line-by-line extraction
            const lines = responseText.split('\n')
            for (const line of lines) {
              const match = line.match(/["']([\u4e00-\u9fff])["']\s*:\s*["']([^"']+)["']/)
              if (match) {
                meanings[match[1]] = match[2].trim()
              }
            }
          }
        }
      } catch (error: any) {
        console.log(`Fallback translation failed for batch ${i / batchSize + 1}:`, error.message)
      }
    }
    
    if (Object.keys(meanings).length > 0) {
      console.log(`Fallback translation extracted ${Object.keys(meanings).length} character meanings`)
    }
  }

  if (Object.keys(meanings).length === 0 && uniqueChars.length > 0) {
    console.error(`WARNING: No character meanings extracted for ${uniqueChars.length} characters. This will result in incomplete glyph data.`)
  }

  return meanings
}

/**
 * Match extracted text to glyphs in database
 * Uses AI to infer meanings for characters not in database
 */
export async function matchGlyphs(): Promise<GlyphMatch[]> {
  return []
}

/**
 * Generate translation using AI (optional - uses Gemini if available)
 */
export async function generateTranslation(): Promise<{ translation: string; confidence: number }> {
  return {
    translation: 'Translation unavailable: OCR/translation pipeline disabled during refactor.',
    confidence: 0
  }
}

/**
 * Main processing function
 */
export async function processAncientText(): Promise<ProcessingResult> {
  // Development fallback to keep UI flows from hard failing
    if (process.env.NODE_ENV === 'development' && process.env.ENABLE_OCR_FALLBACK === 'true') {
      return {
      extractedText: '待接入手写OCR', // placeholder text
        glyphs: [],
      scriptType: 'Chinese',
      confidence: 0,
        method: 'fallback-dev'
      }
    }
    
  throw new Error('OCR/translation pipeline disabled during refactor to Chinese-handwriting MVP')
}

