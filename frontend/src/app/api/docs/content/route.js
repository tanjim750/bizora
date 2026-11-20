import { getSession } from '@/lib/serverApi'
import { isDocsAdmin } from '@/lib/docs/config'
import { loadDocsContent, saveDocsContent } from '@/lib/docs/store'
import { TEAM_MEMBERS, YC_PITCH_SECTIONS, TECHNICAL_SECTIONS } from '@/lib/docs/content'

export const dynamic = 'force-dynamic'

export async function GET() {
  const content = loadDocsContent()
  return Response.json(content, {
    headers: { 'cache-control': 'no-store' },
  })
}

export async function POST(request) {
  const session = await getSession()
  const isAdmin = isDocsAdmin(session)
  const isDev = process.env.NODE_ENV !== 'production'

  if (!isAdmin && !isDev) {
    return Response.json(
      { detail: 'Forbidden. Modifying documentation content requires administrative privileges.' },
      { status: 403, headers: { 'cache-control': 'no-store' } },
    )
  }

  try {
    const body = await request.json()

    // Reset to defaults if requested
    if (body.action === 'RESET_TO_DEFAULTS') {
      const resetContent = saveDocsContent({
        teamMembers: TEAM_MEMBERS,
        pitchSections: YC_PITCH_SECTIONS,
        technicalSections: TECHNICAL_SECTIONS,
      })
      return Response.json({ ok: true, content: resetContent })
    }

    const updates = {}
    if (Array.isArray(body.teamMembers)) updates.teamMembers = body.teamMembers
    if (Array.isArray(body.pitchSections)) updates.pitchSections = body.pitchSections
    if (Array.isArray(body.technicalSections)) updates.technicalSections = body.technicalSections

    const saved = saveDocsContent(updates)
    return Response.json({ ok: true, content: saved })
  } catch (err) {
    return Response.json({ detail: err.message || 'Invalid payload.' }, { status: 400 })
  }
}
