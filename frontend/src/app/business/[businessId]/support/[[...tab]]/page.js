import React from 'react'
import { notFound, redirect } from 'next/navigation'
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
  title: 'Support',
  description: 'Customer communications, urgent queue resolution, and phone call logging.',
}

export default async function SupportWorkspacePage({ params, searchParams }) {
  const { businessId, tab: tabSegments } = await params
  const query = await searchParams
  const session = await getSession()
  if (!session.authenticated) redirect(`/login?next=/business/${businessId}/support`)

  const business = session.businesses.find((item) => String(item.id) === businessId)
  if (!business) notFound()

  const currentTab = (tabSegments && tabSegments[0]) || query?.tab || 'inbox'

  const supportTabs = [
    { key: 'inbox', label: 'Unified Inbox', href: `/business/${businessId}/support/inbox` },
    { key: 'queue', label: 'Support Queue', href: `/business/${businessId}/support/queue` },
    { key: 'calls', label: 'Calls & Logs', href: `/business/${businessId}/support/calls` },
  ]

  const tabResourceMap = {
    inbox: 'conversations',
    queue: 'conversations',
    calls: 'calls',
  }

  const primaryResource = tabResourceMap[currentTab] || 'conversations'

  // Fetch list data
  const endpoint = currentTab === 'queue' ? 'support-queue/?page_size=25' : `${primaryResource}/?page_size=25`
  const listResult = await serverApi(businessApiPath(businessId, endpoint))

  return (
    <div className="workspace-page">
      <PageHeader
        breadcrumbs={[
          { label: 'Workspaces', href: '/workspace' },
          { label: business.name, href: `/business/${businessId}/overview` },
          { label: 'Support' },
        ]}
        title="Customer Support"
        description="Omnichannel customer messaging, SLA priority queue, and recorded callback logging."
        badge="Saved — not sent"
      />

      <Tabs tabs={supportTabs} activeKey={currentTab} className="workspace-tabs" />

      <div className="workspace-tab-content">
        <ResourceList
          title={supportTabs.find((t) => t.key === currentTab)?.label || 'Support'}
          businessId={businessId}
          resource={primaryResource}
          data={listResult.data}
          query={query}
          path={`/business/${businessId}/support/${currentTab}`}
          hideHeading={true}
        >
          {WRITER_ROLES.has(business.role) && (
            <CreateRecord businessId={businessId} resource={primaryResource} />
          )}
        </ResourceList>
      </div>
    </div>
  )
}
