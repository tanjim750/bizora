import React from 'react'
import { notFound, redirect } from 'next/navigation'
import { getSession, serverApi } from '@/lib/serverApi'
import { businessApiPath } from '@/lib/catalog'
import Growth from '@/components/Growth'

export const dynamic = 'force-dynamic'

export const metadata = {
  title: 'Growth & Marketing',
  description:
    'Omnichannel marketing campaign telemetry, ad spend attribution, and website visitor sessions.',
}

export default async function GrowthWorkspacePage({ params, searchParams }) {
  const { businessId, tab: tabSegments } = await params
  const query = await searchParams
  const session = await getSession()
  if (!session.authenticated) redirect(`/login?next=/business/${businessId}/growth`)

  const business = session.businesses.find((item) => String(item.id) === businessId)
  if (!business) notFound()

  const currentTab = (tabSegments && tabSegments[0]) || query?.tab || 'campaigns'

  // Prefetch campaigns and website-performance in parallel
  const [campaignsResult, websiteResult] = await Promise.all([
    serverApi(businessApiPath(businessId, 'campaigns/?page_size=50')),
    serverApi(businessApiPath(businessId, 'website-performance/')),
  ])

  return (
    <Growth
      businessId={businessId}
      business={business}
      currentTab={currentTab}
      initialCampaigns={campaignsResult?.data?.results || []}
      initialWebsite={websiteResult?.data || null}
      query={query}
    />
  )
}
