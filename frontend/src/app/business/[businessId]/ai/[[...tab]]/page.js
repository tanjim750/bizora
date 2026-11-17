import React from 'react'
import { notFound, redirect } from 'next/navigation'
import { PageHeader } from '@/components/ui/PageHeader'
import { getSession } from '@/lib/serverApi'
import { businessApiPath } from '@/lib/catalog'
import { serverApi } from '@/lib/serverApi'
import AiStudio from '@/components/AiStudio'

export const dynamic = 'force-dynamic'

export const metadata = {
  title: 'AI Studio',
  description: 'Grounded business assistant, advisory action proposals, and review execution logs.',
}

export default async function AiWorkspacePage({ params, searchParams }) {
  const { businessId, tab: tabSegments } = await params
  const query = await searchParams
  const session = await getSession()
  if (!session.authenticated) redirect(`/login?next=/business/${businessId}/ai`)

  const business = session.businesses.find((item) => String(item.id) === businessId)
  if (!business) notFound()

  const currentTab = (tabSegments && tabSegments[0]) || query?.tab || 'assistant'

  // Pre-fetch recommendations and actions in parallel
  const [recommendationsRes, actionsRes] = await Promise.all([
    serverApi(businessApiPath(businessId, 'ai/recommendations/')).catch(() => ({
      data: [],
    })),
    serverApi(businessApiPath(businessId, 'ai/actions/')).catch(() => ({
      data: [],
    })),
  ])

  return (
    <div className="workspace-page stack-lg">
      <PageHeader
        breadcrumbs={[
          { label: 'Workspaces', href: '/workspace' },
          { label: business.name, href: `/business/${businessId}/overview` },
          { label: 'AI Studio' },
        ]}
        title="AI Studio & Operational Advisory"
        description="Grounded advisory queries, recommended workflow improvements, and human-in-the-loop approval."
        badge="Execution is simulated"
      />

      <AiStudio
        business={business}
        businessId={businessId}
        activeTab={currentTab}
        recommendations={recommendationsRes.data}
        actions={actionsRes.data}
      />
    </div>
  )
}
