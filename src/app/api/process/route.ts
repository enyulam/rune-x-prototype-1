import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'
import { readFile } from 'fs/promises'
import { basename } from 'path'

// Call out to the new external inference service (Phase 2)
const INFERENCE_API_URL = process.env.INFERENCE_API_URL

export async function POST(request: NextRequest) {
  let uploadId: string | undefined
  try {
    const body = await request.json()
    uploadId = body.uploadId

    if (!uploadId) {
      return NextResponse.json({ error: 'Upload ID is required' }, { status: 400 })
    }

    // Get upload record to find file path
    const upload = await db.upload.findUnique({
      where: { id: uploadId }
    })

    if (!upload) {
      return NextResponse.json({ error: 'Upload not found' }, { status: 404 })
    }

    if (!INFERENCE_API_URL) {
      await db.upload.update({
        where: { id: uploadId },
        data: { status: 'FAILED' }
      })
      return NextResponse.json(
        {
          error: 'Processing unavailable',
          details: 'INFERENCE_API_URL is not configured. Set it to your FastAPI/PaddleOCR service.'
        },
        { status: 503 }
      )
    }

    // Update status
    await db.upload.update({
      where: { id: uploadId },
      data: { status: 'PROCESSING' }
    })

    // Prepare file form-data
    const buffer = await readFile(upload.filePath)
    const form = new FormData()
    form.append('file', new Blob([buffer]), basename(upload.filePath))

    const inferenceUrl = `${INFERENCE_API_URL.replace(/\/$/, '')}/process-image`
    console.log(`Calling inference API: ${inferenceUrl}`)
    
    let inferenceResp: Response
    try {
      inferenceResp = await fetch(inferenceUrl, {
        method: 'POST',
        body: form,
        // Add timeout to prevent hanging
        signal: AbortSignal.timeout(60000) // 60 seconds
      })
    } catch (fetchError: any) {
      console.error('Failed to connect to inference API:', fetchError)
      await db.upload.update({
        where: { id: uploadId },
        data: { status: 'FAILED' }
      })
      return NextResponse.json(
        {
          error: 'Inference service unavailable',
          details: fetchError.message || 'Could not connect to the inference backend. Please ensure it is running on ' + INFERENCE_API_URL
        },
        { status: 503 }
      )
    }

    if (!inferenceResp.ok) {
      const text = await inferenceResp.text().catch(() => '')
      await db.upload.update({
        where: { id: uploadId },
        data: { status: 'FAILED' }
      })
      return NextResponse.json(
        { 
          error: 'Inference failed',
          details: text || `Status ${inferenceResp.status}`
        },
        { status: 502 }
      )
    }

    const result = await inferenceResp.json().catch(() => ({}))

    const extractedText: string = result.text || result.extractedText || ''
    const translationText: string = result.translation || 'Translation unavailable'
    const glyphs = Array.isArray(result.glyphs) ? result.glyphs : []
    const unmapped: string[] = Array.isArray(result.unmapped) ? result.unmapped : []
    const coverage: number = typeof result.coverage === 'number' ? result.coverage : 0
    const dictionaryVersion: string = result.dictionary_version || result.dictionaryVersion || 'unknown'

    // Create/ensure script record
    const scriptName = 'Chinese Handwriting'
    let scriptRecord = await db.ancientScript.findFirst({ where: { name: scriptName } })
    if (!scriptRecord) {
      scriptRecord = await db.ancientScript.create({
        data: { name: scriptName, description: 'Chinese handwriting script' }
      })
    }

    // Persist glyphs
    const createdGlyphMatches = []
    for (let i = 0; i < glyphs.length; i++) {
      const g = glyphs[i] || {}
      const symbol = g.symbol || g.text || ''
      const confidence = typeof g.confidence === 'number' ? g.confidence : 0
      const meaning = g.meaning || null
      const bboxArray = Array.isArray(g.bbox) ? g.bbox : Array.isArray(g.boundingBox) ? g.boundingBox : null
      const bbox =
        bboxArray && bboxArray.length >= 4
          ? { x: bboxArray[0], y: bboxArray[1], width: bboxArray[2], height: bboxArray[3] }
          : null

      // Find or create glyph
      let glyphRecord = await db.glyph.findFirst({
        where: { symbol, scriptId: scriptRecord.id }
      })

      if (!glyphRecord) {
        glyphRecord = await db.glyph.create({
          data: {
            scriptId: scriptRecord.id,
            symbol,
            name: symbol || 'glyph',
            description: meaning || `Character: ${symbol || 'unknown'}`,
            confidence
          }
        })
      } else if (meaning && (!glyphRecord.description || glyphRecord.description.includes('Character:'))) {
          await db.glyph.update({
            where: { id: glyphRecord.id },
            data: {
            description: meaning,
            confidence: Math.max(glyphRecord.confidence || 0, confidence)
            }
          })
      }

      const match = await db.glyphMatch.create({
        data: {
          uploadId,
          glyphId: glyphRecord.id,
          confidence,
          boundingBox: bbox ? JSON.stringify(bbox) : null,
          position: i
        }
      })

      createdGlyphMatches.push({ ...match, glyph: glyphRecord })
    }

    // Store translation with enhanced context
    const translationContext = [
      `Processed via external inference service`,
      `Dictionary coverage: ${coverage}%`,
      `Dictionary version: ${dictionaryVersion}`,
      unmapped.length > 0 ? `Unmapped characters: ${unmapped.length}` : 'All characters mapped'
    ].join(' | ')
    
    const translation = await db.translation.create({
      data: {
        uploadId,
        originalText: extractedText,
        translatedText: translationText,
        confidence: typeof result.confidence === 'number' ? result.confidence : 0,
        language: 'English',
        context: translationContext
      }
    })

    // Store inference metadata (coverage, unmapped, dictionary version)
    const inferenceMetadata = {
      coverage,
      unmapped,
      dictionaryVersion,
      method: 'external-inference',
      processedAt: new Date().toISOString()
    }
    
    // Mark completed and store metadata
    await db.upload.update({
      where: { id: uploadId },
      data: { 
        status: 'COMPLETED',
        processedAt: new Date(),
        scriptType: scriptName,
        metadata: JSON.stringify(inferenceMetadata)
      }
    })

    return NextResponse.json({
      success: true,
      message: 'Processing completed via external inference service',
      results: {
        extractedText,
        glyphs: createdGlyphMatches.map((gm) => ({
          symbol: gm.glyph.symbol,
          meaning: gm.glyph.description,
          confidence: gm.confidence
        })),
        translation: translation.translatedText,
        confidence: translation.confidence,
        scriptType: scriptName,
        method: 'external-inference',
        coverage,
        unmapped,
        dictionaryVersion
      }
    })

  } catch (error: any) {
    console.error('Processing error:', error)
    console.error('Error stack:', error.stack)
    
    // Update upload status to failed
    // uploadId is available from the outer scope
    try {
      if (uploadId) {
        await db.upload.update({
          where: { id: uploadId },
          data: { status: 'FAILED' }
        })
      }
    } catch (updateError) {
      console.error('Failed to update status:', updateError)
    }

    return NextResponse.json(
      { 
        error: 'Failed to process image',
        details: error.message || 'An unexpected error occurred during processing',
        // Include more details in development
        ...(process.env.NODE_ENV === 'development' && { 
          stack: error.stack,
          name: error.name 
        })
      },
      { status: 500 }
    )
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const uploadId = searchParams.get('uploadId')

    if (!uploadId) {
      return NextResponse.json({ error: 'Upload ID is required' }, { status: 400 })
    }

    // Get upload with related data
    const upload = await db.upload.findUnique({
      where: { id: uploadId },
      include: {
        glyphs: {
          include: {
            glyph: true
          }
        },
        translations: true
      }
    })

    if (!upload) {
      return NextResponse.json({ error: 'Upload not found' }, { status: 404 })
    }

    return NextResponse.json({
      success: true,
      upload
    })

  } catch (error) {
    console.error('Get processing status error:', error)
    return NextResponse.json(
      { error: 'Failed to get processing status' },
      { status: 500 }
    )
  }
}