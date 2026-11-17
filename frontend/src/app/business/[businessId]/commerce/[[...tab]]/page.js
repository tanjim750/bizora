import React from 'react'
import { notFound, redirect } from 'next/navigation'
import { PageHeader } from '@/components/ui/PageHeader'
import { Tabs } from '@/components/ui/Tabs'
import { getSession } from '@/lib/serverApi'
import { businessApiPath } from '@/lib/catalog'
import { serverApi } from '@/lib/serverApi'
import Commerce from '@/components/Commerce'

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
    { key: 'orders', label: 'Orders', href: `/business/${businessId}/commerce` },
    { key: 'payments', label: 'Payments & Refunds', href: `/business/${businessId}/commerce/payments` },
    { key: 'deliveries', label: 'Deliveries', href: `/business/${businessId}/commerce/deliveries` },
    { key: 'products', label: 'Products & Variants', href: `/business/${businessId}/commerce/products` },
  ]

  // Fetch data across commerce domains
  const [ordersResult, paymentsResult, timelineResult, shipmentsResult, productsResult] = await Promise.all([
    serverApi(businessApiPath(businessId, 'orders/?page_size=25')),
    serverApi(businessApiPath(businessId, 'payments/?page_size=25')),
    serverApi(businessApiPath(businessId, 'financial-timeline/?page_size=25')),
    serverApi(businessApiPath(businessId, 'shipments/?page_size=25')),
    serverApi(businessApiPath(businessId, 'products/?page_size=25')),
  ])

  // Handle server-side prefetching for open record drawer if specified in ?open=res:id
  let initialActiveRecord = null
  if (query?.open && typeof query.open === 'string' && query.open.includes(':')) {
    const [openResource, openId] = query.open.split(':')
    const detailRes = await serverApi(businessApiPath(businessId, `${openResource}/${openId}/`))
    if (detailRes.ok && detailRes.data) {
      initialActiveRecord = { resource: openResource, ...detailRes.data }
    }
  }

  return (
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
        <Commerce
          business={business}
          businessId={businessId}
          activeTab={currentTab}
          ordersData={ordersResult.data}
          paymentsData={paymentsResult.data}
          timelineData={timelineResult.data}
          shipmentsData={shipmentsResult.data}
          productsData={productsResult.data}
          initialActiveRecord={initialActiveRecord}
        />
      </div>
    </div>
  )
}
