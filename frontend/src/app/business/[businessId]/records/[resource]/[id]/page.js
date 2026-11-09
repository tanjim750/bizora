import Link from 'next/link'
import { notFound, redirect } from 'next/navigation'
import AppShell from '@/components/AppShell'
import { DataSections, FieldGrid, StatusBadge } from '@/components/DataTable'
import { RecordCommands } from '@/components/RecordCommands'
import { RecordAdvisoryTools } from '@/components/AdvisoryTools'
import { businessApiPath, resourcePath, RESOURCES } from '@/lib/catalog'
import { label, recordTitle, statusText } from '@/lib/format'
import { getSession, serverApi } from '@/lib/serverApi'

export const dynamic = 'force-dynamic'

export default async function RecordPage({ params }) {
  const { businessId, resource, id } = await params
  const session = await getSession()
  if (!session.authenticated) redirect('/login')
  const business = session.businesses.find((item) => String(item.id) === businessId)
  if (!business || !RESOURCES.includes(resource) || !/^\d+$/.test(id)) notFound()
  const suffix = resource === 'customers' ? `customers/${id}/360/` : `${resource}/${id}/`
  const extras = []
  if (['customers', 'products', 'orders'].includes(resource))
    extras.push(['graph_context', `graph-context/${resource.slice(0, -1)}/${id}/`])
  if (resource === 'customers') extras.push(['retargeting_context', `customers/${id}/retargeting-context/`])
  if (resource === 'conversations') extras.push(['support_context', `conversations/${id}/context/`])
  if (resource === 'visitors') extras.push(['visitor_journey', `visitors/${id}/journey/`])
  const [result, ...extraResults] = await Promise.all([
    serverApi(businessApiPath(businessId, suffix)),
    ...extras.map(([, path]) => serverApi(businessApiPath(businessId, path))),
  ])
  if (result.status === 404) notFound()
  const data = { ...(result.data || {}) }
  extras.forEach(([key], index) => {
    if (extraResults[index]?.ok) data[key] = extraResults[index].data
  })
  const record = data.record || data.customer || {}
  return (
    <AppShell session={session} business={business}>
      {result.ok ? (
        <>
          <div className="page-heading">
            <div>
              <p className="page-context">
                <Link href={resourcePath(businessId, resource)}>{label(resource)}</Link> / #{id}
              </p>
              <h1>{recordTitle(record)}</h1>
              <p>Canonical record and related evidence for {business.name}.</p>
            </div>
            <StatusBadge text={statusText(record)} />
          </div>
          {resource === 'messages' &&
            record.direction === 'OUTGOING' &&
            record.delivery_status === 'PENDING' && (
              <div className="alert alert-warning">
                <strong>Pending — not delivered.</strong> This message is stored internally; no provider
                delivery is confirmed.
              </div>
            )}
          <section className="surface">
            <div className="section-header">
              <div>
                <h2>Stored fields</h2>
                <p>
                  Business #{business.id} · {business.timezone}
                </p>
              </div>
            </div>
            <FieldGrid data={record} />
          </section>
          <RecordCommands business={business} resource={resource} record={record} />
          <RecordAdvisoryTools business={business} resource={resource} record={record} />
          <DataSections data={data} businessId={businessId} />
        </>
      ) : (
        <div className="alert alert-danger" role="alert">
          {data.detail || 'Unable to load record.'}
        </div>
      )}
    </AppShell>
  )
}
