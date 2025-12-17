import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { db } from '@/lib/db'
import { exportToTEI, exportToJSONLD, exportToCSV, getExportExtension, getExportMimeType } from '@/lib/export'

export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const searchParams = request.nextUrl.searchParams
    const uploadId = searchParams.get('uploadId')
    const format = searchParams.get('format') || 'JSON_LD'

    if (!uploadId) {
      return NextResponse.json({ error: 'uploadId is required' }, { status: 400 })
    }

    // Fetch upload with all related data
    const upload = await db.upload.findUnique({
      where: { id: uploadId },
      include: {
        glyphs: {
          include: {
            glyph: {
              include: {
                script: true
              }
            }
          },
          orderBy: {
            position: 'asc'
          }
        },
        translations: {
          orderBy: {
            createdAt: 'desc'
          }
        },
        versions: {
          orderBy: {
            versionNumber: 'desc'
          }
        }
      }
    })

    if (!upload) {
      return NextResponse.json({ error: 'Upload not found' }, { status: 404 })
    }

    // Check ownership
    if (upload.userId !== session.user.id && session.user.role !== 'ADMIN') {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 })
    }

    // Generate export based on format
    let content: string
    switch (format.toUpperCase()) {
      case 'TEI_XML':
      case 'XML':
        content = exportToTEI({ upload })
        break
      case 'JSON_LD':
      case 'JSON':
        content = exportToJSONLD({ upload })
        break
      case 'CSV':
        content = exportToCSV({ upload })
        break
      default:
        return NextResponse.json({ error: 'Unsupported format' }, { status: 400 })
    }

    // Save export record
    await db.export.create({
      data: {
        uploadId: upload.id,
        format: format.toUpperCase() as any,
        exportedAt: new Date()
      }
    })

    // Return file with appropriate headers
    const extension = getExportExtension(format.toUpperCase())
    const mimeType = getExportMimeType(format.toUpperCase())
    const filename = `${upload.originalName.replace(/\.[^/.]+$/, '')}_export.${extension}`

    return new NextResponse(content, {
      headers: {
        'Content-Type': mimeType,
        'Content-Disposition': `attachment; filename="${filename}"`
      }
    })
  } catch (error: any) {
    console.error('Export error:', error)
    return NextResponse.json(
      { error: 'Failed to export', details: error.message },
      { status: 500 }
    )
  }
}
