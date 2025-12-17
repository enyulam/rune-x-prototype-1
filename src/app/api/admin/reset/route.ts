import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'
import { getSession } from '@/lib/get-session'

// POST /api/admin/reset - wipes the entire database (use with caution)
export async function POST(_req: NextRequest) {
  try {
    const session = await getSession()
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Delete in FK-safe order
    await db.translation.deleteMany({})
    await db.glyphMatch.deleteMany({})
    await db.upload.deleteMany({})
    await db.glyph.deleteMany({})
    await db.ancientScript.deleteMany({})
    await db.session?.deleteMany?.({})
    await db.account?.deleteMany?.({})
    await db.verificationToken?.deleteMany?.({})
    await db.user.deleteMany({})

    return NextResponse.json({ success: true, message: 'Database wiped successfully' })
  } catch (error: any) {
    console.error('Admin reset error:', error)
    return NextResponse.json(
      { error: 'Failed to wipe database', details: error.message },
      { status: 500 }
    )
  }
}

