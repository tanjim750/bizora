import { getSession } from '@/lib/serverApi'
import { evaluateDocsAccess, isDocsAdmin } from '@/lib/docs/config'
import { loadDocsConfig, saveDocsConfig } from '@/lib/docs/store'

export const dynamic = 'force-dynamic'

export async function GET() {
  const session = await getSession()
  const config = loadDocsConfig()
  const access = evaluateDocsAccess(config, session)

  return Response.json(
    {
      config,
      access,
      serverTime: new Date().toISOString(),
    },
    { headers: { 'cache-control': 'no-store' } },
  )
}

export async function POST(request) {
  const session = await getSession()
  const isAdmin = isDocsAdmin(session)

  // Security check: Must be authenticated administrative user or running in development
  const isDev = process.env.NODE_ENV !== 'production'
  if (!isAdmin && !isDev) {
    return Response.json(
      { detail: 'Forbidden. Modifying documentation visibility requires administrative privileges.' },
      { status: 403, headers: { 'cache-control': 'no-store' } },
    )
  }

  try {
    const body = await request.json()
    const allowedKeys = [
      'enabled',
      'overrideMode',
      'startDate',
      'endDate',
      'timezone',
      'title',
      'tagline',
      'teamName',
      'contactEmail',
    ]

    const updates = {}
    for (const key of allowedKeys) {
      if (body[key] !== undefined) {
        updates[key] = body[key]
      }
    }

    if (body.overrideMode && !['SCHEDULE', 'ALWAYS_PUBLIC', 'FORCE_OFFLINE'].includes(body.overrideMode)) {
      return Response.json({ detail: 'Invalid overrideMode.' }, { status: 400 })
    }

    const updatedConfig = saveDocsConfig(updates)
    const access = evaluateDocsAccess(updatedConfig, session)

    return Response.json(
      {
        ok: true,
        config: updatedConfig,
        access,
        updatedAt: updatedConfig.updatedAt,
      },
      { headers: { 'cache-control': 'no-store' } },
    )
  } catch (err) {
    return Response.json({ detail: err.message || 'Invalid request payload.' }, { status: 400 })
  }
}
