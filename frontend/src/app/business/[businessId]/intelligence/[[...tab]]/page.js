import React from 'react'
import { notFound, redirect } from 'next/navigation'
import { PageHeader } from '@/components/ui/PageHeader'
import { Tabs } from '@/components/ui/Tabs'
import { UnavailableState } from '@/components/ui/UnavailableState'
import { getSession } from '@/lib/serverApi'
import { businessApiPath } from '@/lib/catalog'
import { serverApi } from '@/lib/serverApi'

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

  const intelligenceTabs = [
    { key: 'facts', label: 'Facts & Issues', href: `/business/${businessId}/intelligence/facts` },
    { key: 'graph', label: 'Entity Graph', href: `/business/${businessId}/intelligence/graph` },
    { key: 'metrics', label: 'Metrics & Analysis', href: `/business/${businessId}/intelligence/metrics` },
    { key: 'pipeline', label: 'Data Pipeline', href: `/business/${businessId}/intelligence/pipeline` },
  ]

  // E12 / issues
  const issuesResult = await serverApi(businessApiPath(businessId, 'issues/'))

  return (
    <div className="workspace-page">
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

      <Tabs tabs={intelligenceTabs} activeKey={currentTab} className="workspace-tabs" />

      <div className="workspace-tab-content">
        {currentTab === 'facts' && (
          <div className="facts-tab-container">
            {issuesResult.data?.results?.length ? (
              <p>Issues detected</p>
            ) : (
              <UnavailableState
                title="Business Intelligence facts service"
                owner="Business Intelligence"
                reason="The Business Intelligence fact derivation engine has not generated snapshots for this period."
              />
            )}
          </div>
        )}

        {currentTab === 'graph' && (
          <UnavailableState
            title="Full Graph Traversal & Topology"
            owner="Business Graph"
            reason="Multi-hop graph traversal and topology views are unavailable in this environment."
          />
        )}

        {currentTab === 'metrics' && (
          <UnavailableState
            title="Metrics & Multi-dimensional Analysis"
            owner="Business Intelligence"
            reason="Analytical metrics registry and snapshot store are unmounted."
          />
        )}

        {currentTab === 'pipeline' && (
          <UnavailableState
            title="Automated Data Pipeline"
            owner="Platform Operations"
            reason="Pipeline orchestration and continuous ingestion runners are offline."
          />
        )}
      </div>
    </div>
  )
}
