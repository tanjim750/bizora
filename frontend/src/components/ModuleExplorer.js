import Link from 'next/link'
import { FieldGrid, StatusBadge } from './DataTable'
import { businessPath, MODULE_VIEWS, SECTIONS } from '@/lib/catalog'
import { fieldValue, label, recordTitle, statusText } from '@/lib/format'

export default function ModuleExplorer({ businessId, section, view, data, recordId, query }) {
  const module = MODULE_VIEWS[section]
  const base = businessPath(businessId, section)
  const rows = Array.isArray(data) ? data : data?.results
  const detailEnabled = module.details.includes(view)
  const queryValues = new URLSearchParams(
    Object.entries(query).filter(
      ([key, value]) => !['view', 'record'].includes(key) && typeof value === 'string' && value,
    ),
  )
  const previous = data?.previous ? new URL(data.previous).searchParams.get('page') : null
  const next = data?.next ? new URL(data.next).searchParams.get('page') : null
  const pageHref = (page) => {
    const params = new URLSearchParams(queryValues)
    params.set('view', view)
    params.set('page', page)
    return `${base}?${params}`
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="page-context">{label(view.replaceAll('/', ' '))}</p>
          <h1>{SECTIONS.find((item) => item.key === section).label}</h1>
          <p>Business scoped records and evidence from the {label(module.prefix)} service.</p>
        </div>
        <StatusBadge text={recordId ? `Record #${recordId}` : 'Recorded evidence'} />
      </div>
      <nav className="module-nav" aria-label={`${label(section)} views`}>
        {module.views.map((item) => (
          <Link
            key={item}
            className={`button ${item === view ? 'button-primary' : 'button-secondary'}`}
            href={`${base}?view=${encodeURIComponent(item)}`}
          >
            {label(item.replaceAll('/', ' '))}
          </Link>
        ))}
      </nav>
      {recordId && (
        <p>
          <Link href={`${base}?view=${encodeURIComponent(view)}`}>← Back to {label(view)}</Link>
        </p>
      )}
      <section className="surface">
        {rows ? (
          <>
            <div className="section-header">
              <h2>Records</h2>
              <span className="count-chip">{data?.count ?? rows.length}</span>
            </div>
            {rows.length ? (
              rows.map((row, index) => (
                <details className="disclosure" key={row.id ?? row.key ?? index}>
                  <summary>
                    {recordTitle(row)} · <StatusBadge text={statusText(row)} />
                  </summary>
                  <div className="disclosure-body">
                    <FieldGrid data={row} />
                    {detailEnabled && Number.isSafeInteger(Number(row.id)) && Number(row.id) > 0 && (
                      <Link
                        className="button button-secondary"
                        href={`${base}?view=${encodeURIComponent(view)}&record=${row.id}`}
                      >
                        Open full evidence
                      </Link>
                    )}
                  </div>
                </details>
              ))
            ) : (
              <p className="empty-state">No records in this view.</p>
            )}
          </>
        ) : (
          <FieldGrid data={data && typeof data === 'object' ? data : { result: fieldValue(data) }} />
        )}
        {(previous || next) && (
          <nav className="pagination" aria-label="Pages">
            {previous && (
              <Link className="button button-secondary" href={pageHref(previous)}>
                Previous
              </Link>
            )}
            {next && (
              <Link className="button button-secondary" href={pageHref(next)}>
                Next
              </Link>
            )}
          </nav>
        )}
      </section>
    </>
  )
}
