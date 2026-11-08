import { notFound, redirect } from 'next/navigation'
import AppShell from '@/components/AppShell'
import ResourceList from '@/components/ResourceList'
import CreateRecord from '@/components/CreateRecord'
import { RESOURCES, WRITER_ROLES, businessApiPath, resourcePath } from '@/lib/catalog'
import { label } from '@/lib/format'
import { getSession, serverApi } from '@/lib/serverApi'

export const dynamic = 'force-dynamic'

export default async function CanonicalResourcePage({ params, searchParams }) {
  const { businessId, resource } = await params
  const query = await searchParams
  const session = await getSession()
  if (!session.authenticated) redirect('/login')
  const business = session.businesses.find((item) => String(item.id) === businessId)
  if (!business || !RESOURCES.includes(resource)) notFound()
  const queryString = new URLSearchParams(
    Object.entries(query).filter(([, value]) => typeof value === 'string' && value),
  ).toString()
  const result = await serverApi(
    businessApiPath(businessId, `${resource}/${queryString ? `?${queryString}` : ''}`),
  )
  return (
    <AppShell session={session} business={business}>
      {result.ok ? (
        <ResourceList
          title={label(resource)}
          businessId={businessId}
          resource={resource}
          data={result.data}
          query={query}
          path={resourcePath(businessId, resource)}
        >
          {WRITER_ROLES.has(business.role) && <CreateRecord businessId={businessId} resource={resource} />}
        </ResourceList>
      ) : (
        <div className="alert alert-danger" role="alert">
          {result.data?.detail || 'Unable to load records.'}
        </div>
      )}
    </AppShell>
  )
}
