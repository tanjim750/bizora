import React from 'react'
import { notFound, redirect } from 'next/navigation'
import AppShell from '@/components/AppShell'
import { PageHeader } from '@/components/ui/PageHeader'
import { Tabs } from '@/components/ui/Tabs'
import { getSession } from '@/lib/serverApi'
import { businessApiPath } from '@/lib/catalog'
import { serverApi } from '@/lib/serverApi'
import ResourceList from '@/components/ResourceList'
import CreateRecord from '@/components/CreateRecord'
import { WRITER_ROLES } from '@/lib/catalog'

export const dynamic = 'force-dynamic'

export const metadata = {
  title: 'Growth',
  description: 'Marketing campaigns, ad performance, visitor traffic, and web telemetry.',
}

export default async function GrowthWorkspacePage({ params, searchParams }) {
  const { businessId, tab: tabSegments } = await params
  const query = await searchParams
  const session = await getSession()
  if (!session.authenticated) redirect(`/login?next=/business/${businessId}/growth`)

  const business = session.businesses.find((item) => String(item.id) === businessId)
  if (!business) notFound()

  const currentTab = (tabSegments && tabSegments[0]) || query?.tab || 'campaigns'

  const growthTabs = [
    { key: 'campaigns', label: 'Campaigns & Ads', href: `/business/${businessId}/growth/campaigns` },
    { key: 'website', label: 'Website & Visitors', href: `/business/${businessId}/growth/website` },
  ]

  const tabResourceMap = {
    campaigns: 'campaigns',
    website: 'visitors',
  }

  const primaryResource = tabResourceMap[currentTab] || 'campaigns'

  // Fetch list data
  const listResult = await serverApi(businessApiPath(businessId, `${primaryResource}/?page_size=25`))

  return (
    <AppShell session={session} business={business}>
      <div className="workspace-page">
        <PageHeader
          breadcrumbs={[
            { label: 'Workspaces', href: '/workspace' },
            { label: business.name, href: `/business/${businessId}/overview` },
            { label: 'Growth' },
          ]}
          title="Growth & Marketing"
          description="Omnichannel marketing campaign telemetry, ad spend attribution, and website visitor sessions."
          badge="Platform-reported"
        />

        <Tabs tabs={growthTabs} activeKey={currentTab} className="workspace-tabs" />

        <div className="workspace-tab-content">
          <ResourceList
            title={growthTabs.find((t) => t.key === currentTab)?.label || 'Growth'}
            businessId={businessId}
            resource={primaryResource}
            data={listResult.data}
            query={query}
            path={`/business/${businessId}/growth/${currentTab}`}
            hideHeading={true}
          >
            {WRITER_ROLES.has(business.role) && (
              <CreateRecord businessId={businessId} resource={primaryResource} />
            )}
          </ResourceList>
        </div>
      </div>
    </AppShell>
  )
}
