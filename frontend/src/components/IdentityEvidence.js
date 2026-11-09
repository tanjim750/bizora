import { FieldGrid, StatusBadge } from './DataTable'
import { fieldValue, statusText } from '@/lib/format'

const NAMES = ['Canonical identities', 'External identities', 'Identity links', 'Identity history']

export default function IdentityEvidence({ lists = [] }) {
  const safeLists = Array.isArray(lists) ? lists : []
  return (
    <div className="section-stack">
      {safeLists.map((item, index) => (
        <section className="surface" key={NAMES[index]}>
          <div className="section-header">
            <div>
              <h2>{NAMES[index]}</h2>
              <p>Business-scoped evidence; expand a record to inspect its identifiers and history.</p>
            </div>
            <span className="count-chip">{item.ok ? (item.data?.count ?? 0) : 'Unavailable'}</span>
          </div>
          {!item.ok ? (
            <p className="form-error" role="alert">
              {item.data?.detail || 'Identity evidence is unavailable.'}
            </p>
          ) : item.data?.results?.length ? (
            <div className="card-stack">
              {item.data.results.map((row) => (
                <details className="disclosure" key={row.id}>
                  <summary>
                    Record #{row.id} ·{' '}
                    {fieldValue(row.entity_type || row.identity_type || row.action || row.status)}
                    {' · '}
                    <StatusBadge text={statusText(row)} />
                  </summary>
                  <div className="disclosure-body">
                    <FieldGrid data={row} />
                  </div>
                </details>
              ))}
            </div>
          ) : (
            <p className="empty-state">No evidence records in this collection.</p>
          )}
          {item.ok && item.data?.next && (
            <p className="helptext">
              Showing the first {item.data.results.length} records. More evidence exists in the API.
            </p>
          )}
        </section>
      ))}
    </div>
  )
}
