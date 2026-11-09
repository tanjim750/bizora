import React from 'react'
import { notFound, redirect } from 'next/navigation'
import AppShell from '@/components/AppShell'
import { PageHeader } from '@/components/ui/PageHeader'
import { Tabs } from '@/components/ui/Tabs'
import { UnavailableState } from '@/components/ui/UnavailableState'
import { getSession } from '@/lib/serverApi'
import { MANAGER_ROLES, businessApiPath } from '@/lib/catalog'
import { serverApi } from '@/lib/serverApi'
import { IdentityReview } from '@/components/ReviewForms'
import IdentityTools from '@/components/IdentityTools'
import IdentityEvidence from '@/components/IdentityEvidence'
import ModuleExplorer from '@/components/ModuleExplorer'

export const dynamic = 'force-dynamic'

export const metadata = {
  title: 'Administration',
  description:
    'Identity resolution rules, platform integrations, business policies, and simulation controls.',
}

export default async function AdminWorkspacePage({ params, searchParams }) {
  const { businessId, tab: tabSegments } = await params
  const query = await searchParams
  const session = await getSession()
  if (!session.authenticated) redirect(`/login?next=/business/${businessId}/admin`)

  const business = session.businesses.find((item) => String(item.id) === businessId)
  if (!business) notFound()

  // Guard: Admin workspace requires manager or owner role
  if (!MANAGER_ROLES.has(business.role)) {
    notFound()
  }

  const currentTab = (tabSegments && tabSegments[0]) || query?.tab || 'identity'

  const adminTabs = [
    { key: 'identity', label: 'Identity Resolution', href: `/business/${businessId}/admin/identity` },
    { key: 'integrations', label: 'Integrations & Sync', href: `/business/${businessId}/admin/integrations` },
    {
      key: 'configuration',
      label: 'Configuration & Policies',
      href: `/business/${businessId}/admin/configuration`,
    },
    { key: 'knowledge', label: 'Knowledge Base', href: `/business/${businessId}/admin/knowledge` },
    { key: 'simulation', label: 'Simulation & Sandbox', href: `/business/${businessId}/admin/simulation` },
  ]

  // Data fetching for identity / observability / config
  const [identityConflictsResult, identityEvidenceResult] = await Promise.all([
    serverApi(businessApiPath(businessId, 'identity/conflicts/?page_size=25')),
    serverApi(businessApiPath(businessId, 'identity/merge-candidates/?page_size=25')),
  ])

  return (
    <AppShell session={session} business={business}>
      <div className="workspace-page">
        <PageHeader
          breadcrumbs={[
            { label: 'Workspaces', href: '/workspace' },
            { label: business.name, href: `/business/${businessId}/overview` },
            { label: 'Admin' },
          ]}
          title="Administration & Controls"
          description="Entity identity resolution, integration sync status, business governance rules, and system configuration."
          badge="Restricted · Manager Access"
        />

        <Tabs tabs={adminTabs} activeKey={currentTab} className="workspace-tabs" />

        <div className="workspace-tab-content">
          {currentTab === 'identity' && (
            <div className="admin-identity-tab">
              <IdentityTools businessId={businessId} />
              <IdentityReview
                business={business}
                conflicts={identityConflictsResult.data}
                hideHeading={true}
              />
              <IdentityEvidence lists={[]} />
            </div>
          )}

          {currentTab === 'integrations' && (
            <div className="admin-integrations-tab">
              <ModuleExplorer
                title="Integrations & Observability"
                section="observability"
                businessId={businessId}
                view={query.view || 'summary'}
                data={{}}
                query={query}
                hideHeading={true}
              />
            </div>
          )}

          {currentTab === 'configuration' && (
            <div className="admin-configuration-tab">
              <ModuleExplorer
                title="Business Configuration"
                section="configuration"
                businessId={businessId}
                view={query.view || 'effective'}
                data={{}}
                query={query}
                hideHeading={true}
              />
            </div>
          )}

          {currentTab === 'knowledge' && (
            <UnavailableState
              title="Memory & Knowledge Base"
              owner="Memory Knowledge"
              reason="Vector knowledge repository and business semantic memory are unmounted in this environment."
            />
          )}

          {currentTab === 'simulation' && (
            <UnavailableState
              title="Prototype Simulation & Sandbox"
              owner="Prototype Simulation"
              reason="What-if simulation engine and scenario sandbox are unmounted in this environment."
            />
          )}
        </div>
      </div>
    </AppShell>
  )
}
