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
  title: 'Customers',
  description: 'Unified customer profiles, identity resolution, orders, and interaction timeline.',
}

export default async function CustomersWorkspacePage({ params, searchParams }) {
  const { businessId, tab: tabSegments } = await params
  const query = await searchParams
  const session = await getSession()
  if (!session.authenticated) redirect(`/login?next=/business/${businessId}/customers`)

  const business = session.businesses.find((item) => String(item.id) === businessId)
  if (!business) notFound()

  const currentTab = (tabSegments && tabSegments[0]) || query?.tab || 'list'

  const customerTabs = [
    { key: 'list', label: 'All Customers', href: `/business/${businessId}/customers/list` },
    { key: '360', label: 'Customer 360', href: `/business/${businessId}/customers/360` },
  ]

  // Fetch customers list
  const listResult = await serverApi(businessApiPath(businessId, `customers/?page_size=25`))

  return (
    <div className="workspace-page">
      <PageHeader
        breadcrumbs={[
          { label: 'Workspaces', href: '/workspace' },
          { label: business.name, href: `/business/${businessId}/overview` },
          { label: 'Customers' },
        ]}
        title="Customer Directory & 360"
        description="Unified customer identities, lifetime purchase history, linked touchpoints, and activity stream."
        badge="Identity & Touchpoints"
      />

      <Tabs tabs={customerTabs} activeKey={currentTab} className="workspace-tabs" />

      <div className="workspace-tab-content">
        <ResourceList
          title="Customers"
          businessId={businessId}
          resource="customers"
          data={listResult.data}
          query={query}
          path={`/business/${businessId}/customers/${currentTab}`}
          hideHeading={true}
        >
          {WRITER_ROLES.has(business.role) && <CreateRecord businessId={businessId} resource="customers" />}
        </ResourceList>
      </div>
    </div>
  )
}
