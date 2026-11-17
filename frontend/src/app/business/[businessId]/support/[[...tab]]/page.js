import React from 'react'
import { notFound, redirect } from 'next/navigation'
import { PageHeader } from '@/components/ui/PageHeader'
import { getSession } from '@/lib/serverApi'
import { businessApiPath } from '@/lib/catalog'
import { serverApi } from '@/lib/serverApi'
import Support from '@/components/Support'

export const dynamic = 'force-dynamic'

export const metadata = {
  title: 'Support',
  description: 'Omnichannel customer messaging, SLA priority queue, and recorded callback logging.',
}

export default async function SupportWorkspacePage({ params, searchParams }) {
  const { businessId, tab: tabSegments } = await params
  const query = await searchParams
  const session = await getSession()
  if (!session.authenticated) redirect(`/login?next=/business/${businessId}/support`)

  const business = session.businesses.find((item) => String(item.id) === businessId)
  if (!business) notFound()

  const currentTab = (tabSegments && tabSegments[0]) || query?.tab || 'inbox'

  // Pre-fetch conversations, support queue, and calls in parallel
  const [conversationsRes, queueRes, callsRes] = await Promise.all([
    serverApi(businessApiPath(businessId, 'conversations/?page_size=50&ordering=-started_at')).catch(() => ({
      data: { count: 0, results: [] },
    })),
    serverApi(businessApiPath(businessId, 'support-queue/?page_size=50')).catch(() => ({
      data: { count: 0, results: [] },
    })),
    serverApi(businessApiPath(businessId, 'calls/?page_size=50&ordering=-started_at')).catch(() => ({
      data: { count: 0, results: [] },
    })),
  ])

  return (
    <div className="workspace-page stack-lg">
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

      <Support
        business={business}
        businessId={businessId}
        activeTab={currentTab}
        conversationsData={conversationsRes.data}
        queueData={queueRes.data}
        callsData={callsRes.data}
      />
    </div>
  )
}
