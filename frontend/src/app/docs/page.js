import React from 'react'
import { getSession } from '@/lib/serverApi'
import { evaluateDocsAccess } from '@/lib/docs/config'
import { loadDocsConfig, loadDocsContent } from '@/lib/docs/store'
import { getLiveSystemStats, LIVE_FEATURE_MATRIX } from '@/lib/docs/liveStats'
import { DocsPortal } from '@/components/docs/DocsPortal'
import { DocsAccessRestricted } from '@/components/docs/DocsAccessRestricted'

export const dynamic = 'force-dynamic'

export const metadata = {
  title: 'Live Documentation & YC Pitch Deck',
  description:
    'Comprehensive YC-style pitch deck, deep technical whitepaper, and real-time application state telemetry for Bizora.',
  openGraph: {
    title: 'Bizora — Live Documentation & YC Pitch Deck',
    description:
      'Autonomous Enterprise Business Brain for Emerging Market Commerce. Unifying Customer Identity, Steadfast Logistics, and Dialyra Voice Telephony with Deterministic AI Guardrails.',
  },
}

export default async function DocsPage({ searchParams }) {
  const query = await searchParams
  const session = await getSession()
  const config = loadDocsConfig()
  const access = evaluateDocsAccess(config, session)

  // Admin preview query flag: allow admins to simulate restricted public view
  const forceSimulatePublic = query?.preview === 'public'
  const isAccessBlocked = !access.granted || (forceSimulatePublic && !access.publicGranted)

  if (isAccessBlocked) {
    return <DocsAccessRestricted access={access} config={config} />
  }

  const content = loadDocsContent()
  const liveStats = await getLiveSystemStats()

  return (
    <DocsPortal
      initialConfig={config}
      initialContent={content}
      initialLiveStats={liveStats}
      initialFeatureMatrix={LIVE_FEATURE_MATRIX}
      access={access}
      session={session}
    />
  )
}
