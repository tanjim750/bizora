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
  title: 'Commerce',
  description: 'Orders fulfillment, payments and refund ledger, delivery dispatches, and catalog.',
}

export default async function CommerceWorkspacePage({ params, searchParams }) {
  const { businessId, tab: tabSegments } = await params
  const query = await searchParams
  const session = await getSession()
  if (!session.authenticated) redirect(`/login?next=/business/${businessId}/commerce`)

  const business = session.businesses.find((item) => String(item.id) === businessId)
  if (!business) notFound()

  const currentTab = (tabSegments && tabSegments[0]) || query?.tab || 'orders'

  const commerceTabs = [
    { key: 'orders', label: 'Orders', href: `/business/${businessId}/commerce/orders` },
    { key: 'payments', label: 'Payments & Refunds', href: `/business/${businessId}/commerce/payments` },
    { key: 'deliveries', label: 'Deliveries', href: `/business/${businessId}/commerce/deliveries` },
    { key: 'products', label: 'Products & Variants', href: `/business/${businessId}/commerce/products` },
  ]

  // Map tab to underlying primary resource
  const tabResourceMap = {
    orders: 'orders',
    payments: 'payments',
    deliveries: 'shipments',
    products: 'products',
  }

  const primaryResource = tabResourceMap[currentTab] || 'orders'

  // Fetch list data for the active tab's primary resource
  const listResult = await serverApi(businessApiPath(businessId, `${primaryResource}/?page_size=25`))

  return (
    <AppShell session={session} business={business}>
      <div className="workspace-page">
        <PageHeader
          breadcrumbs={[
            { label: 'Workspaces', href: '/workspace' },
            { label: business.name, href: `/business/${businessId}/overview` },
            { label: 'Commerce' },
          ]}
          title="Commerce Operations"
          description="Order lifecycle fulfillment, payment settlement, refund tracking, and SKU inventory management."
          badge={`Commerce · ${business.currency}`}
        />

        <Tabs tabs={commerceTabs} activeKey={currentTab} className="workspace-tabs" />

        <div className="workspace-tab-content">
          <ResourceList
            title={commerceTabs.find((t) => t.key === currentTab)?.label || 'Commerce'}
            businessId={businessId}
            resource={primaryResource}
            data={listResult.data}
            query={query}
            path={`/business/${businessId}/commerce/${currentTab}`}
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
