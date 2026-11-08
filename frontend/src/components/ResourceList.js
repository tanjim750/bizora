import Link from 'next/link'
import { DataTable } from './DataTable'
import { resourcePath, RESOURCES } from '@/lib/catalog'
import { label } from '@/lib/format'

const FILTERS = {
  customers: ['q', 'contact', 'contact_type', 'tag', 'status'],
  products: ['q', 'sku', 'category', 'status'],
  orders: ['q', 'customer', 'status'],
  payments: ['customer', 'order', 'payment_method', 'status'],
  conversations: ['q', 'channel', 'priority', 'status'],
  'support-queue': ['channel', 'priority', 'assigned', 'status'],
  campaigns: ['q', 'platform', 'status'],
  visitors: [],
  shipments: ['q', 'customer', 'order', 'provider', 'status'],
  calls: ['customer', 'order', 'direction', 'status'],
  callbacks: ['status'],
  conflicts: ['status'],
  'merge-candidates': ['status'],
  'financial-timeline': ['customer', 'order'],
}

export default function ResourceList({
  title,
  description,
  businessId,
  resource,
  data,
  query = {},
  path,
  children,
}) {
  const rows = Array.isArray(data) ? data : data?.results || []
  const count = Array.isArray(data) ? data.length : (data?.count ?? rows.length)
  const filters = FILTERS[resource] || []
  const previous = data?.previous ? new URL(data.previous).search : null
  const next = data?.next ? new URL(data.next).search : null
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="page-context">Business operations</p>
          <h1>{title}</h1>
          <p>{description || 'Authorized, stored records for this business.'}</p>
        </div>
        <span className="count-chip">{count} records</span>
      </div>
      {filters.length > 0 && (
        <form className="filter-panel" action={path}>
          <div className="filter-grid">
            {filters.map((filter) => (
              <div key={filter}>
                <label htmlFor={`filter-${filter}`}>{label(filter)}</label>
                {filter === 'assigned' ? (
                  <select id={`filter-${filter}`} name={filter} defaultValue={query[filter] || ''}>
                    <option value="">All</option>
                    <option value="me">Assigned to me</option>
                    <option value="unassigned">Unassigned</option>
                    <option value="team">My teams</option>
                  </select>
                ) : (
                  <input
                    id={`filter-${filter}`}
                    name={filter}
                    type={filter === 'q' ? 'search' : 'text'}
                    defaultValue={query[filter] || ''}
                  />
                )}
              </div>
            ))}
            <div className="filter-buttons">
              <button className="button button-primary">Apply filters</button>
              <Link className="button button-secondary" href={path}>
                Clear
              </Link>
            </div>
          </div>
        </form>
      )}
      <section className="surface">
        <div className="section-header">
          <div>
            <h2>Records</h2>
            <p>
              {count} stored record{count === 1 ? '' : 's'}
            </p>
          </div>
        </div>
        <DataTable
          rows={rows}
          businessId={businessId}
          resource={resource}
          emptyMessage={Object.keys(query).length ? 'No records match these filters.' : 'No records yet.'}
        />
        {(previous || next) && (
          <nav className="pagination" aria-label="Pages">
            {previous && (
              <Link className="button button-secondary" href={`${path}${previous}`}>
                Previous
              </Link>
            )}
            {next && (
              <Link className="button button-secondary" href={`${path}${next}`}>
                Next
              </Link>
            )}
          </nav>
        )}
      </section>
      {children}
    </>
  )
}

export function MoreResources({ businessId }) {
  return (
    <details className="surface disclosure">
      <summary>All canonical resource lists</summary>
      <div className="resource-links">
        {RESOURCES.map((resource) => (
          <Link key={resource} href={resourcePath(businessId, resource)}>
            {label(resource)}
          </Link>
        ))}
      </div>
    </details>
  )
}
