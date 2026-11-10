import React from 'react'
import { notFound, redirect } from 'next/navigation'
import { PageHeader } from '@/components/ui/PageHeader'
import { Tabs } from '@/components/ui/Tabs'
import { Banner } from '@/components/ui/Banner'
import { UnavailableState } from '@/components/ui/UnavailableState'
import { getSession } from '@/lib/serverApi'
import { AssistantWorkspace } from '@/components/AdvisoryTools'
import { ActionReview } from '@/components/ReviewForms'
import { businessApiPath } from '@/lib/catalog'
import { serverApi } from '@/lib/serverApi'

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

  const aiTabs = [
    { key: 'assistant', label: 'AI Assistant', href: `/business/${businessId}/ai/assistant` },
    { key: 'actions', label: 'Action Proposals', href: `/business/${businessId}/ai/actions` },
    { key: 'audit', label: 'Audit Trail', href: `/business/${businessId}/ai/audit` },
  ]

  // Recommendations and actions
  const [recommendationsResult, actionsResult] = await Promise.all([
    serverApi(businessApiPath(businessId, 'ai/recommendations/')),
    serverApi(businessApiPath(businessId, 'ai/actions/')),
  ])

  return (
    <div className="workspace-page">
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

      <Tabs tabs={aiTabs} activeKey={currentTab} className="workspace-tabs" />

      <div className="workspace-tab-content">
        {currentTab === 'assistant' && (
          <div className="ai-assistant-tab">
            <Banner variant="info" style={{ marginBottom: 'var(--space-4)' }}>
              Answers are advisory and synthesized from recorded business facts and customer evidence.
            </Banner>
            <AssistantWorkspace
              business={business}
              recommendations={recommendationsResult.data}
              hideHeading={true}
            />
          </div>
        )}

        {currentTab === 'actions' && (
          <div className="ai-actions-tab">
            <Banner variant="warning" style={{ marginBottom: 'var(--space-4)' }}>
              <strong>Execution is simulated.</strong> Action approvals record an audit entry but do not
              trigger automated external mutation.
            </Banner>
            <ActionReview business={business} actions={actionsResult.data} hideHeading={true} />
          </div>
        )}

        {currentTab === 'audit' && (
          <UnavailableState
            title="Autonomous Action Execution Audit"
            owner="AI Intelligence"
            reason="Direct read endpoint for AI execution history is not exposed on this backend."
          />
        )}
      </div>
    </div>
  )
}
