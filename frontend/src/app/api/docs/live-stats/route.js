import { getLiveSystemStats, LIVE_FEATURE_MATRIX } from '@/lib/docs/liveStats'

export const dynamic = 'force-dynamic'

export async function GET() {
  const stats = await getLiveSystemStats()
  return Response.json(
    {
      stats,
      featureMatrix: LIVE_FEATURE_MATRIX,
      syncedAt: new Date().toISOString(),
    },
    {
      headers: { 'cache-control': 'no-store' },
    },
  )
}
