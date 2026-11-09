import Link from 'next/link'
import { detailPath, RESOURCES } from '@/lib/catalog'
import { fieldValue, label, recordTitle, statusText, statusTone } from '@/lib/format'

const HIDDEN_FIELDS = new Set(['source_metadata', 'config', 'recording_url'])

export function StatusBadge({ text }) {
  return <span className={`badge badge-${statusTone(text)}`}>{text}</span>
}

export function FieldGrid({ data }) {
  return (
    <dl className="field-grid">
      {Object.entries(data || {})
        .filter(([key]) => !HIDDEN_FIELDS.has(key))
        .map(([key, value]) => (
          <div key={key}>
            <dt>{label(key)}</dt>
            <dd>
              {typeof value === 'object' && value !== null ? (
                <pre>{fieldValue(value)}</pre>
              ) : (
                fieldValue(value)
              )}
            </dd>
          </div>
        ))}
    </dl>
  )
}

export function DataTable({ rows = [], businessId, resource, emptyMessage = 'No records found.' }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col">Record</th>
            <th scope="col">State</th>
            <th scope="col">Reference</th>
            <th scope="col">Action</th>
          </tr>
        </thead>
        <tbody>
          {(() => {
            const seen = new Set()
            return rows.map((row, index) => {
              const target =
                resource === 'financial-timeline'
                  ? { PAYMENT: 'payments', REFUND: 'refunds' }[row.entity_kind]
                  : resource
              const linkable = RESOURCES.includes(target) && row.id
              const prefix = target || row.entity_kind || resource || 'row'
              const idPart = row.id !== undefined && row.id !== null ? row.id : `idx-${index}`
              let rowKey = `${prefix}-${idPart}`
              if (seen.has(rowKey)) {
                rowKey = `${rowKey}-${index}`
              }
              seen.add(rowKey)
              return (
                <tr key={rowKey}>
                  <td>
                    <strong>{recordTitle(row)}</strong>
                    <small>
                      {row.customer_id
                        ? `Customer #${row.customer_id}`
                        : row.business_id
                          ? `Business #${row.business_id}`
                          : 'Stored record'}
                    </small>
                  </td>
                  <td>
                    <StatusBadge text={statusText(row)} />
                  </td>
                  <td className="tabular">#{row.id ?? '—'}</td>
                  <td>
                    {linkable ? (
                      <Link className="row-link" href={detailPath(businessId, target, row.id)}>
                        Open record
                      </Link>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                </tr>
              )
            })
          })()}
          {rows.length === 0 && (
            <tr>
              <td colSpan="4">
                <div className="empty-state">
                  <strong>{emptyMessage}</strong>
                  <p>New authorized records will appear here.</p>
                </div>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

export function DataSections({ data, businessId }) {
  return (
    <div className="section-stack">
      {Object.entries(data || {})
        .filter(([key]) => key !== 'record' && key !== 'business')
        .map(([key, value]) => {
          if (value && Array.isArray(value.results))
            return (
              <section key={key} className="surface">
                <div className="section-header">
                  <div>
                    <h2>{label(key)}</h2>
                    <p>
                      {value.count ?? value.results.length} stored records
                      {value.truncated ? ' · first 50 shown' : ''}
                    </p>
                  </div>
                </div>
                <DataTable rows={value.results} businessId={businessId} resource={key.replaceAll('_', '-')} />
              </section>
            )
          if (value && typeof value === 'object' && value.status === 'UNAVAILABLE')
            return (
              <section key={key} className="surface">
                <div className="section-header">
                  <h2>{label(key)}</h2>
                  <StatusBadge text="Unavailable" />
                </div>
                <p className="muted">{value.reason || value.detail || 'This service is unavailable.'}</p>
              </section>
            )
          return (
            <details key={key} className="surface disclosure">
              <summary>{label(key)}</summary>
              <div className="disclosure-body">
                {typeof value === 'object' && value !== null ? (
                  <FieldGrid data={value} />
                ) : (
                  <p>{fieldValue(value)}</p>
                )}
              </div>
            </details>
          )
        })}
    </div>
  )
}
