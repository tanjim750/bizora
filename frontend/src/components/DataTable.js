import Link from 'next/link'
import { detailPath, RESOURCES } from '@/lib/catalog'
import { fieldValue, label, recordTitle, statusText, statusTone } from '@/lib/format'
import { StatusChip } from './ui/StatusChip'
import { DataTable as UiDataTable } from './ui/DataTable'

const HIDDEN_FIELDS = new Set(['source_metadata', 'config', 'recording_url'])

export function StatusBadge({ text, status }) {
  const s = text || status
  return <StatusChip status={s} />
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

export function DataTable({
  rows = [],
  businessId,
  resource,
  emptyMessage = 'No records found.',
  columns,
  ...props
}) {
  return (
    <UiDataTable
      rows={rows}
      businessId={businessId}
      resource={resource}
      columns={columns}
      emptyTitle={emptyMessage}
      {...props}
    />
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
