import React from 'react'
import { notFound, redirect } from 'next/navigation'
import { PageHeader } from '@/components/ui/PageHeader'
import { Tabs } from '@/components/ui/Tabs'
import { getSession } from '@/lib/serverApi'
import { businessApiPath } from '@/lib/catalog'
import { serverApi } from '@/lib/serverApi'
import Customers from '@/components/Customers'

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
    { key: 'list', label: 'All Customers', href: `/business/${businessId}/customers` },
    { key: '360', label: 'Customer 360', href: `/business/${businessId}/customers/360` },
  ]

  // Determine if a specific customer is requested via query or 360 tab
  let targetCustomerId = null
  if (query?.open && typeof query.open === 'string' && query.open.startsWith('customers:')) {
    targetCustomerId = query.open.split(':')[1]
  } else if (query?.id) {
    targetCustomerId = query.id
  } else if (currentTab === '360') {
    // Default to first customer if on 360 tab
    targetCustomerId = '1'
  }

  // Fetch customers list, issues, and optionally customer 360 pre-fetch
  const fetches = [
    serverApi(businessApiPath(businessId, 'customers/?page_size=25')),
    serverApi(businessApiPath(businessId, 'issues/')),
  ]

  if (targetCustomerId) {
    fetches.push(serverApi(businessApiPath(businessId, `customers/${targetCustomerId}/360/`)))
    fetches.push(serverApi(businessApiPath(businessId, `graph-context/customer/${targetCustomerId}/`)))
  }

  const [listResult, issuesResult, initial360Res, initialGraphRes] = await Promise.all(fetches)

  const initialCustomer360 = initial360Res?.ok && initial360Res?.data ? initial360Res.data : null
  const initialGraphContext = initialGraphRes?.ok && initialGraphRes?.data ? initialGraphRes.data : null

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
        <Customers
          business={business}
          businessId={businessId}
          activeTab={currentTab}
          customersData={listResult.data}
          initialCustomer360={initialCustomer360}
          initialGraphContext={initialGraphContext}
          issues={issuesResult.ok && Array.isArray(issuesResult.data) ? issuesResult.data : []}
        />
      </div>
    </div>
  )
}
