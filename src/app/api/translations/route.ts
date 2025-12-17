import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'
import { getSession } from '@/lib/get-session'

export async function GET(request: NextRequest) {
  try {
    const session = await getSession()

    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    const userId = session.user.id
    const { searchParams } = new URL(request.url)
    const search = searchParams.get('search')
    const filter = searchParams.get('filter') // 'all', 'high-confidence', 'recent'

    // Get user's uploads with translations
    let uploads = await db.upload.findMany({
      where: { userId },
      include: {
        translations: {
          include: {
            glyph: true
          },
          orderBy: {
            createdAt: 'desc'
          }
        },
        glyphs: {
          include: {
            glyph: {
              include: {
                script: true
              }
            }
          }
        }
      },
      orderBy: {
        createdAt: 'desc'
      }
    })

    // Filter by search term
    if (search) {
      uploads = uploads.filter(upload => 
        upload.translations.some(t => 
          t.originalText.toLowerCase().includes(search.toLowerCase()) ||
          t.translatedText.toLowerCase().includes(search.toLowerCase())
        )
      )
    }

    // Transform data for frontend
    const translations = uploads.flatMap(upload => {
      // Parse metadata if available
      let metadata: any = null
      if (upload.metadata) {
        try {
          metadata = JSON.parse(upload.metadata)
        } catch {
          // Invalid JSON, ignore
        }
      }
      
      return upload.translations.map(translation => ({
        id: translation.id,
        originalText: translation.originalText,
        translatedText: translation.translatedText,
        confidence: translation.confidence,
        language: translation.language,
        context: translation.context,
        createdAt: translation.createdAt.toISOString(),
        upload: {
          id: upload.id,
          originalName: upload.originalName,
          status: upload.status,
          imageUrl: `/api/uploads/${upload.id}`,
          // Include inference metadata if available
          coverage: metadata?.coverage,
          unmapped: metadata?.unmapped,
          dictionaryVersion: metadata?.dictionaryVersion,
          sentenceTranslation: metadata?.sentenceTranslation,  // Neural sentence translation (MarianMT)
          refinedTranslation: metadata?.refinedTranslation  // Qwen-refined translation
        },
        glyphs: upload.glyphs.map(gm => ({
          symbol: gm.glyph.symbol,
          confidence: gm.confidence,
          meaning: gm.glyph.description,
          script: gm.glyph.script.name
        }))
      }))
    })

    // Apply filters
    let filteredTranslations = translations

    if (filter === 'high-confidence') {
      filteredTranslations = translations.filter(t => t.confidence >= 0.9)
    } else if (filter === 'recent') {
      filteredTranslations = translations
        .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
        .slice(0, 5)
    }

    return NextResponse.json({
      success: true,
      translations: filteredTranslations,
      total: translations.length
    })
  } catch (error) {
    console.error('Translations API error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch translations' },
      { status: 500 }
    )
  }
}



