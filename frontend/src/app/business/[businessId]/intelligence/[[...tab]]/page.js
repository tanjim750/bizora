import React from 'react'
import { notFound, redirect } from 'next/navigation'
import { PageHeader } from '@/components/ui/PageHeader'
import { getSession } from '@/lib/serverApi'
import { businessApiPath } from '@/lib/catalog'
import { serverApi } from '@/lib/serverApi'
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

  // Pre-fetch real open issues from E12
  const issuesRes = await serverApi(businessApiPath(businessId, 'issues/?page_size=50')).catch(() => ({
    data: { count: 0, results: [] },
  }))

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
        issuesData={issuesRes.data}
      />
    </div>
  )
}
