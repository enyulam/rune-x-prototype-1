/**
 * Generative Reconstruction Module (GRM)
 * Reconstructs damaged or incomplete glyphs using evidence-driven synthesis
 */

import { GoogleGenerativeAI } from '@google/generative-ai'
import { readFile } from 'fs/promises'

export interface ReconstructionResult {
  reconstructedGlyph: string
  confidence: number
  method: string
  originalGlyph?: string
  reconstructionDetails?: string
}

/**
 * Reconstruct a damaged glyph using generative AI
 * This simulates the GRM functionality described in the Rune-X document
 */
export async function reconstructGlyph(
  imagePath: string,
  boundingBox: { x: number; y: number; width: number; height: number },
  context?: {
    surroundingGlyphs?: string[]
    scriptType?: string
    historicalPeriod?: string
  }
): Promise<ReconstructionResult> {
  const apiKey = process.env.GOOGLE_GEMINI_API_KEY
  if (!apiKey) {
    throw new Error('Google Gemini API key required for glyph reconstruction')
  }

  try {
    const genAI = new GoogleGenerativeAI(apiKey)
    const model = genAI.getGenerativeModel({ model: 'gemini-2.0-flash-exp' })
    
    // Read the image
    const imageBuffer = await readFile(imagePath)
    const base64Image = imageBuffer.toString('base64')

    // Create a prompt for reconstruction
    const prompt = `You are an expert in ancient script reconstruction. Analyze this image region containing a potentially damaged or incomplete ancient glyph.

${context?.scriptType ? `Script Type: ${context.scriptType}` : ''}
${context?.historicalPeriod ? `Historical Period: ${context.historicalPeriod}` : ''}
${context?.surroundingGlyphs ? `Surrounding Context: ${context.surroundingGlyphs.join(', ')}` : ''}

Tasks:
1. Identify if the glyph appears damaged or incomplete
2. If damaged, reconstruct the most likely complete form based on:
   - Visible stroke patterns
   - Historical script evolution
   - Context from surrounding glyphs
   - Known patterns in this script type
3. Provide the reconstructed glyph symbol
4. Explain your reconstruction reasoning

Return your response in JSON format:
{
  "isDamaged": boolean,
  "reconstructedGlyph": "symbol",
  "confidence": 0.0-1.0,
  "reasoning": "explanation",
  "originalVisibleStrokes": "description"
}`

    const result = await model.generateContent([
      {
        inlineData: {
          data: base64Image,
          mimeType: 'image/jpeg'
        }
      },
      { text: prompt }
    ])

    const response = await result.response
    const text = response.text()

    // Try to parse JSON from the response
    let reconstructionData: any
    try {
      // Extract JSON from markdown code blocks if present
      const jsonMatch = text.match(/```json\s*([\s\S]*?)\s*```/) || text.match(/\{[\s\S]*\}/)
      if (jsonMatch) {
        reconstructionData = JSON.parse(jsonMatch[1] || jsonMatch[0])
      } else {
        // Fallback: try to parse the entire response
        reconstructionData = JSON.parse(text)
      }
    } catch {
      // If JSON parsing fails, create a structured response from text
      reconstructionData = {
        isDamaged: text.toLowerCase().includes('damaged') || text.toLowerCase().includes('incomplete'),
        reconstructedGlyph: extractGlyphFromText(text),
        confidence: 0.75,
        reasoning: text,
        originalVisibleStrokes: 'Could not parse from response'
      }
    }

    return {
      reconstructedGlyph: reconstructionData.reconstructedGlyph || '?',
      confidence: reconstructionData.confidence || 0.75,
      method: 'gemini-grm',
      reconstructionDetails: reconstructionData.reasoning || text
    }
  } catch (error: any) {
    console.error('GRM reconstruction error:', error)
    throw new Error(`Failed to reconstruct glyph: ${error.message}`)
  }
}

/**
 * Batch reconstruct multiple glyphs
 */
export async function batchReconstructGlyphs(
  imagePath: string,
  glyphs: Array<{
    boundingBox: { x: number; y: number; width: number; height: number }
    symbol?: string
    confidence?: number
  }>,
  context?: {
    scriptType?: string
    historicalPeriod?: string
  }
): Promise<ReconstructionResult[]> {
  const results: ReconstructionResult[] = []
  
  // Process glyphs with low confidence or missing symbols as candidates for reconstruction
  const candidatesForReconstruction = glyphs.filter(
    g => !g.symbol || (g.confidence && g.confidence < 0.7)
  )

  for (const glyph of candidatesForReconstruction) {
    try {
      const surroundingGlyphs = glyphs
        .filter(g => g !== glyph)
        .map(g => g.symbol)
        .filter(Boolean) as string[]

      const result = await reconstructGlyph(imagePath, glyph.boundingBox, {
        ...context,
        surroundingGlyphs
      })
      
      results.push(result)
    } catch (error: any) {
      console.error(`Failed to reconstruct glyph at position:`, error)
      results.push({
        reconstructedGlyph: '?',
        confidence: 0,
        method: 'failed',
        reconstructionDetails: error.message
      })
    }
  }

  return results
}

/**
 * Helper to extract glyph symbol from text response
 */
function extractGlyphFromText(text: string): string {
  // Look for Chinese characters, symbols, or Unicode patterns
  const chineseCharMatch = text.match(/[\u4e00-\u9fff]/)
  if (chineseCharMatch) {
    return chineseCharMatch[0]
  }

  // Look for quoted symbols
  const quotedMatch = text.match(/["']([^"']+)["']/)
  if (quotedMatch) {
    return quotedMatch[1]
  }

  // Look for "symbol:" patterns
  const symbolMatch = text.match(/symbol[:\s]+([^\s,\.]+)/i)
  if (symbolMatch) {
    return symbolMatch[1]
  }

  return '?'
}

/**
 * Determine if a glyph needs reconstruction based on confidence and completeness
 */
export function needsReconstruction(
  glyph: {
    symbol?: string
    confidence?: number
    boundingBox?: { x: number; y: number; width: number; height: number }
  }
): boolean {
  // Reconstruct if:
  // 1. No symbol detected
  // 2. Low confidence (< 0.7)
  // 3. Very small bounding box (might be incomplete)
  if (!glyph.symbol) return true
  if (glyph.confidence && glyph.confidence < 0.7) return true
  if (glyph.boundingBox && (glyph.boundingBox.width < 10 || glyph.boundingBox.height < 10)) {
    return true
  }
  return false
}
