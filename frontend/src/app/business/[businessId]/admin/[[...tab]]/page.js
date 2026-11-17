import React from 'react'
import { notFound, redirect } from 'next/navigation'
import { getSession, serverApi } from '@/lib/serverApi'
import { MANAGER_ROLES, businessApiPath } from '@/lib/catalog'
import Admin from '@/components/Admin'

export const dynamic = 'force-dynamic'

export const metadata = {
  title: 'Administration',
  description:
    'Entity identity resolution rules, platform integrations, business policies, and simulation controls.',
}

export default async function AdminWorkspacePage({ params, searchParams }) {
  const { businessId, tab: tabSegments } = await params
  const query = await searchParams
  const session = await getSession()
  if (!session.authenticated) redirect(`/login?next=/business/${businessId}/admin`)

  const business = session.businesses.find((item) => String(item.id) === businessId)
  if (!business) notFound()

  // Guard: Admin workspace requires manager or owner role
  if (!MANAGER_ROLES.has(business.role)) {
    notFound()
  }

  const currentTab = (tabSegments && tabSegments[0]) || query?.tab || 'identity'

  // Prefetch data in parallel
  const [
    canonicalResult,
    externalResult,
    linksResult,
    conflictsResult,
    mergeCandidatesResult,
    historyResult,
    observabilitySummaryResult,
    connectionsResult,
    configResult,
  ] = await Promise.all([
    serverApi(businessApiPath(businessId, 'identity/canonical/?page_size=50')),
    serverApi(businessApiPath(businessId, 'identity/external/?page_size=50')),
    serverApi(businessApiPath(businessId, 'identity/links/?page_size=50')),
    serverApi(businessApiPath(businessId, 'identity/conflicts/?page_size=50')),
    serverApi(businessApiPath(businessId, 'identity/merge-candidates/?page_size=50')),
    serverApi(businessApiPath(businessId, 'identity/history/?page_size=50')),
    serverApi(businessApiPath(businessId, 'observability/summary/')),
    serverApi(businessApiPath(businessId, 'observability/connections/?page_size=50')),
    serverApi(businessApiPath(businessId, 'configuration/effective/')),
  ])

  return (
    <Admin
      businessId={businessId}
      business={business}
      currentTab={currentTab}
      initialCanonical={canonicalResult?.data?.results || []}
      initialExternal={externalResult?.data?.results || []}
      initialLinks={linksResult?.data?.results || []}
      initialConflicts={conflictsResult?.data?.results || []}
      initialMergeCandidates={mergeCandidatesResult?.data?.results || []}
      initialHistory={historyResult?.data?.results || []}
      initialObservabilitySummary={observabilitySummaryResult?.data || null}
      initialConnections={connectionsResult?.data?.results || []}
      initialConfiguration={configResult?.data || null}
    />
  )
}
