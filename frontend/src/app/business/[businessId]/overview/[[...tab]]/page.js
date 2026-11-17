import React from 'react'
import { notFound, redirect } from 'next/navigation'
import { PageHeader } from '@/components/ui/PageHeader'
import { Tabs } from '@/components/ui/Tabs'
import { getSession } from '@/lib/serverApi'
import Overview from '@/components/Overview'
import { businessApiPath } from '@/lib/catalog'
import { serverApi } from '@/lib/serverApi'

export const dynamic = 'force-dynamic'

export const metadata = {
  title: 'Overview',
  description: 'Executive KPIs, performance metrics, and operational health.',
}

export default async function OverviewWorkspacePage({ params, searchParams }) {
  const { businessId, tab: tabSegments } = await params
  const query = await searchParams
  const session = await getSession()
  if (!session.authenticated) redirect(`/login?next=/business/${businessId}/overview`)

  const business = session.businesses.find((item) => String(item.id) === businessId)
  if (!business) notFound()

  const currentTab = (tabSegments && tabSegments[0]) || query?.tab || 'overview'

  const overviewTabs = [
    { key: 'overview', label: 'Overview', href: `/business/${businessId}/overview` },
    { key: 'trends', label: 'Trends', href: `/business/${businessId}/overview/trends` },
    { key: 'health', label: 'Health', href: `/business/${businessId}/overview/health` },
  ]

  // Fetch overview data, queue count, and open issues from backend
  const [overviewResult, queueResult, issuesResult] = await Promise.all([
    serverApi(businessApiPath(businessId, 'overview/')),
    serverApi(businessApiPath(businessId, 'support-queue/?page_size=1')),
    serverApi(businessApiPath(businessId, 'issues/')),
  ])

  return (
    <div className="workspace-page">
      <PageHeader
        breadcrumbs={[
          { label: 'Workspaces', href: '/workspace' },
          { label: business.name, href: `/business/${businessId}/overview` },
          { label: 'Overview' },
        ]}
        title="Executive Overview"
        description="High-level operational metrics, performance trends, and live business monitoring."
        badge={`${business.currency} · ${business.timezone || 'Asia/Dhaka'}`}
      />

      <Tabs tabs={overviewTabs} activeKey={currentTab} className="workspace-tabs" />

      <div className="workspace-tab-content">
        <Overview
          business={business}
          data={overviewResult.data}
          queueCount={queueResult.data?.count}
          issues={issuesResult.ok && Array.isArray(issuesResult.data) ? issuesResult.data : []}
          businessId={businessId}
          activeTab={currentTab}
          hideHeading={true}
        />
      </div>
    </div>
  )
}
