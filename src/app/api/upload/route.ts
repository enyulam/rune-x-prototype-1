import { NextRequest, NextResponse } from 'next/server'
import { writeFile, mkdir } from 'fs/promises'
import { join } from 'path'
import { db } from '@/lib/db'
import { getSession } from '@/lib/get-session'

export async function POST(request: NextRequest) {
  try {
    const session = await getSession()

    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized. Please sign in.' },
        { status: 401 }
      )
    }

    // Ensure the user still exists (after DB reset sessions can remain stale)
    const user = await db.user.findUnique({ where: { id: session.user.id } })
    if (!user) {
      return NextResponse.json(
        { error: 'Session is stale after reset. Please sign out/in again.' },
        { status: 401 }
      )
    }

    const data = await request.formData()
    const file: File | null = data.get('file') as unknown as File

    if (!file) {
      return NextResponse.json({ error: 'No file uploaded' }, { status: 400 })
    }

    // Extract metadata if provided
    const provenance = data.get('provenance') as string | null
    const imagingMethod = data.get('imagingMethod') as string | null
    const scriptType = data.get('scriptType') as string | null
    const metadataJson = data.get('metadata') as string | null

    let metadata: any = null
    if (metadataJson) {
      try {
        metadata = JSON.parse(metadataJson)
      } catch {
        // Invalid JSON, ignore
      }
    }

    const bytes = await file.arrayBuffer()
    const buffer = Buffer.from(bytes)

    // Create uploads directory if it doesn't exist
    const uploadsDir = join(process.cwd(), 'uploads')
    try {
      await mkdir(uploadsDir, { recursive: true })
    } catch (error) {
      // Directory already exists
    }

    // Generate unique filename
    const timestamp = Date.now()
    const filename = `${timestamp}-${file.name}`
    const filepath = join(uploadsDir, filename)

    // Save file
    await writeFile(filepath, buffer)

    // Save to database with authenticated user ID and enhanced metadata
    // Build data object dynamically to handle schema changes gracefully
    const uploadData: any = {
      userId: session.user.id,
      originalName: file.name,
      filePath: filepath,
      status: 'PENDING'
    }

    // Add new fields only if they exist in the schema (for backward compatibility)
    // These fields were added in the Rune-X rebrand update
    if (provenance !== null) {
      uploadData.provenance = provenance
    }
    if (imagingMethod !== null) {
      uploadData.imagingMethod = imagingMethod
    }
    if (scriptType !== null) {
      uploadData.scriptType = scriptType
    }
    if (metadata) {
      uploadData.metadata = JSON.stringify(metadata)
    }

    const upload = await db.upload.create({
      data: uploadData
    })

    return NextResponse.json({ 
      success: true, 
      uploadId: upload.id,
      filename: filename
    })

  } catch (error: any) {
    console.error('Upload error:', error)
    
    // Provide more detailed error information
    let errorMessage = 'Failed to upload file'
    let errorDetails = error.message || String(error)
    
    // Check for common database errors
    if (error.message?.includes('Unknown column') || error.message?.includes('no such column')) {
      errorMessage = 'Database schema mismatch. Please run: npm run db:push'
      errorDetails = 'The database schema needs to be updated. Run "npm run db:push" to sync the schema.'
    } else if (error.message?.includes('SQLITE_ERROR')) {
      errorMessage = 'Database error'
      errorDetails = error.message
    }
    
    return NextResponse.json(
      { 
        error: errorMessage,
        details: errorDetails,
        stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
      },
      { status: 500 }
    )
  }
}