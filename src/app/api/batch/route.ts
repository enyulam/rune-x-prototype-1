import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { db } from '@/lib/db'
import { readFile } from 'fs/promises'
import { basename } from 'path'

/**
 * Batch processing endpoint for Rune-X
 * Uses external inference service; no reconstruction.
 */
export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { uploadIds } = body

    if (!uploadIds || !Array.isArray(uploadIds) || uploadIds.length === 0) {
      return NextResponse.json({ error: 'uploadIds array is required' }, { status: 400 })
    }

    const results: Array<{
      uploadId: string
      status: 'success' | 'failed'
      error?: string
    }> = []

    for (const uploadId of uploadIds) {
      try {
        await processSingle(uploadId, session.user.id)
        results.push({ uploadId, status: 'success' })
      } catch (err: any) {
        results.push({ uploadId, status: 'failed', error: err?.message || 'Processing failed' })
      }
    }

    return NextResponse.json({
      success: true,
      processed: results.filter(r => r.status === 'success').length,
      failed: results.filter(r => r.status === 'failed').length,
      results
    })
  } catch (error: any) {
    console.error('Batch processing error:', error)
    return NextResponse.json(
      { error: 'Batch processing failed', details: error.message },
      { status: 500 }
    )
  }
}

async function processSingle(uploadId: string, userId: string) {
  const INFERENCE_API_URL = process.env.INFERENCE_API_URL
  if (!INFERENCE_API_URL) {
    throw new Error('INFERENCE_API_URL is not configured')
  }

  const upload = await db.upload.findFirst({
    where: { id: uploadId, userId }
  })
  if (!upload) throw new Error('Upload not found')

  await db.upload.update({ where: { id: uploadId }, data: { status: 'PROCESSING' } })

  const buffer = await readFile(upload.filePath)
  const form = new FormData()
  form.append('file', new Blob([buffer]), basename(upload.filePath))

  const inferenceResp = await fetch(`${INFERENCE_API_URL.replace(/\/$/, '')}/process-image`, {
    method: 'POST',
    body: form,
  })

  if (!inferenceResp.ok) {
    const text = await inferenceResp.text().catch(() => '')
    await db.upload.update({ where: { id: uploadId }, data: { status: 'FAILED' } })
    throw new Error(text || `Status ${inferenceResp.status}`)
  }

  const result = await inferenceResp.json().catch(() => ({}))
  const extractedText: string = result.text || result.extractedText || ''
  const translationText: string = result.translation || 'Translation unavailable'
  const glyphs = Array.isArray(result.glyphs) ? result.glyphs : []

  const scriptName = 'Chinese Handwriting'
  let scriptRecord = await db.ancientScript.findFirst({ where: { name: scriptName } })
  if (!scriptRecord) {
    scriptRecord = await db.ancientScript.create({
      data: { name: scriptName, description: 'Chinese handwriting script' }
    })
  }

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

      await db.glyphMatch.create({
        data: {
        uploadId,
        glyphId: glyphRecord.id,
        confidence,
        boundingBox: bbox ? JSON.stringify(bbox) : null,
        position: i
        }
      })
  }

      await db.translation.create({
        data: {
      uploadId,
      originalText: extractedText,
      translatedText: translationText,
      confidence: typeof result.confidence === 'number' ? result.confidence : 0,
      language: 'English',
      context: `Processed via external inference service`
    }
  })

    await db.upload.update({
      where: { id: uploadId },
    data: {
      status: 'COMPLETED',
      processedAt: new Date(),
      scriptType: 'Chinese Handwriting'
    }
    })
}
