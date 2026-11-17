import React from 'react'
import { notFound, redirect } from 'next/navigation'
import { PageHeader } from '@/components/ui/PageHeader'
import { getSession } from '@/lib/serverApi'
import { businessApiPath } from '@/lib/catalog'
import { serverApi } from '@/lib/serverApi'
import { FACTS_PATH, ISSUES_PATH } from '@/lib/intelligence/facts'
import Intelligence from '@/components/Intelligence'

export const dynamic = 'force-dynamic'

export const metadata = {
  title: 'Intelligence',
  description: 'Grounded business facts, entity relationships graph, metrics catalog, and data pipeline.',
}

export default async function IntelligenceWorkspacePage({ params, searchParams }) {
  const { businessId, tab: tabSegments } = await params
  const query = await searchParams
  const session = await getSession()
  if (!session.authenticated) redirect(`/login?next=/business/${businessId}/intelligence`)

  const business = session.businesses.find((item) => String(item.id) === businessId)
  if (!business) notFound()

  const currentTab = (tabSegments && tabSegments[0]) || query?.tab || 'facts'

  const loadErrors = {}

  // Pre-fetch real facts and issues from Business Intelligence
  const factsRes = await serverApi(FACTS_PATH(businessId, { limit: 50 })).catch((err) => {
    loadErrors.facts = err?.detail || err?.message || 'Failed to load facts.'
    return { data: { total_count: 0, results: [] } }
  })

  const issuesRes = await serverApi(ISSUES_PATH(businessId, { limit: 50 })).catch((err) => {
    loadErrors.issues = err?.detail || err?.message || 'Failed to load issues.'
    return { data: { total_count: 0, results: [] } }
  })

  return (
    <div className="workspace-page stack-lg">
      <PageHeader
        breadcrumbs={[
          { label: 'Workspaces', href: '/workspace' },
          { label: business.name, href: `/business/${businessId}/overview` },
          { label: 'Intelligence' },
        ]}
        title="Business Intelligence & Graph"
        description="Authoritative facts, entity graph topology, real-time issue detection, and analytical pipelines."
        badge="Deterministic Brain"
      />

      <Intelligence
        business={business}
        businessId={businessId}
        activeTab={currentTab}
        factsData={factsRes.data}
        issuesData={issuesRes.data}
        loadErrors={loadErrors}
      />
    </div>
  )
}
