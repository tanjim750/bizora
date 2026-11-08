import { notFound, redirect } from 'next/navigation'
import AppShell from '@/components/AppShell'
import Overview from '@/components/Overview'
import ResourceList, { MoreResources } from '@/components/ResourceList'
import { DataSections, StatusBadge } from '@/components/DataTable'
import { ActionReview, IdentityReview } from '@/components/ReviewForms'
import IdentityTools from '@/components/IdentityTools'
import IdentityEvidence from '@/components/IdentityEvidence'
import ContractTools from '@/components/ContractTools'
import ProductAssessment from '@/components/ProductAssessment'
import { AssistantWorkspace } from '@/components/AdvisoryTools'
import { businessApiPath, businessPath, MANAGER_ROLES, SECTIONS, WRITER_ROLES } from '@/lib/catalog'
import { getSession, serverApi } from '@/lib/serverApi'

export const dynamic = 'force-dynamic'

export default async function SectionPage({ params, searchParams }) {
  const { businessId, section: sectionKey } = await params
  const query = await searchParams
  const session = await getSession()
  if (!session.authenticated) redirect('/login')
  const business = session.businesses.find((item) => String(item.id) === businessId)
  if (!business) notFound()
  const section = SECTIONS.find((item) => item.key === sectionKey)
  if (!section || (section.manager && !MANAGER_ROLES.has(business.role))) notFound()
  const queryString = new URLSearchParams(
    Object.entries(query).filter(([, value]) => typeof value === 'string' && value),
  ).toString()
  const suffix = section.resource ? `${section.resource}/` : section.endpoint
  const path = suffix ? businessApiPath(businessId, suffix) : null
  const [result, extra, identityLists] = await Promise.all([
    path
      ? serverApi(`${path}${queryString ? `?${queryString}` : ''}`)
      : Promise.resolve({ ok: true, data: null }),
    sectionKey === 'overview'
      ? serverApi(businessApiPath(businessId, 'support-queue/?page_size=1'))
      : sectionKey === 'assistant'
        ? serverApi(businessApiPath(businessId, 'issues/'))
        : sectionKey === 'identity'
          ? serverApi(businessApiPath(businessId, 'identity/merge-candidates/?page_size=25'))
          : Promise.resolve(null),
    sectionKey === 'identity'
      ? Promise.all(
          ['canonical', 'external', 'links', 'history'].map((name) =>
            serverApi(businessApiPath(businessId, `identity/${name}/?page_size=25`)),
          ),
        )
      : Promise.resolve(null),
  ])
  if (result.status === 401) redirect('/login')
  let content
  if (!result.ok) {
    content = (
      <div className="page-heading">
        <div>
          <h1>{section.label}</h1>
          <div className="alert alert-danger" role="alert">
            {result.status === 403
              ? 'Access denied for this business.'
              : result.data?.detail || 'This view is unavailable.'}
          </div>
        </div>
      </div>
    )
  } else if (sectionKey === 'overview') {
    content = (
      <Overview business={business} data={result.data} queueCount={extra?.ok ? extra.data?.count : null} />
    )
  } else if (sectionKey === 'assistant') {
    content = (
      <AssistantWorkspace
        business={business}
        recommendations={result.data}
        issues={extra?.ok ? extra.data : []}
      />
    )
  } else if (sectionKey === 'actions') {
    content = <ActionReview business={business} actions={result.data} />
  } else if (sectionKey === 'contracts') {
    content = <ContractTools business={business} />
  } else if (sectionKey === 'identity') {
    content = (
      <>
        <IdentityReview
          business={business}
          conflicts={result.data}
          candidates={extra?.ok ? extra.data : null}
        />
        <IdentityTools businessId={businessId} />
        <IdentityEvidence lists={identityLists || []} />
      </>
    )
  } else if (sectionKey === 'website-performance') {
    content = (
      <>
        <div className="page-heading">
          <div>
            <p className="page-context">Website evidence</p>
            <h1>Website evidence</h1>
            <p>Observed records and explicit availability of analytical projections.</p>
          </div>
          <StatusBadge text="Partial" />
        </div>
        <DataSections data={result.data} businessId={businessId} />
      </>
    )
  } else {
    content = (
      <>
        <ResourceList
          title={section.label}
          businessId={businessId}
          resource={section.resource || (sectionKey === 'finance' ? 'financial-timeline' : 'support-queue')}
          data={result.data}
          query={query}
          path={businessPath(businessId, sectionKey)}
          description={
            sectionKey === 'queue' ? 'Open and pending conversations, ordered by priority.' : undefined
          }
        />
        {sectionKey === 'products' && WRITER_ROLES.has(business.role) && (
          <ProductAssessment businessId={businessId} role={business.role} />
        )}
        <MoreResources businessId={businessId} />
      </>
    )
  }
  return (
    <AppShell session={session} business={business}>
      {content}
    </AppShell>
  )
}
