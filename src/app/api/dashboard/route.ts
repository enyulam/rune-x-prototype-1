import { NextResponse } from 'next/server'
import { db } from '@/lib/db'
import { getSession } from '@/lib/get-session'

export async function GET() {
  try {
    const session = await getSession()

    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    const userId = session.user.id

    // Get user's uploads
    const uploads = await db.upload.findMany({
      where: { userId },
      include: {
        translations: true
      }
    })

    const totalUploads = uploads.length
    const completedUploads = uploads.filter(u => u.status === 'COMPLETED').length
    const pendingUploads = uploads.filter(u => u.status === 'PENDING' || u.status === 'PROCESSING').length
    const totalTranslations = uploads.reduce((sum, u) => sum + u.translations.length, 0)

    // Calculate average confidence
    const allConfidences = uploads.flatMap(u => 
      u.translations.map(t => t.confidence)
    )
    const averageConfidence = allConfidences.length > 0
      ? allConfidences.reduce((sum, c) => sum + c, 0) / allConfidences.length
      : 0

    return NextResponse.json({
      success: true,
      stats: {
        totalUploads,
        completedUploads,
        pendingUploads,
        totalTranslations,
        averageConfidence
      }
    })
  } catch (error) {
    console.error('Dashboard error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch dashboard data' },
      { status: 500 }
    )
  }
}



