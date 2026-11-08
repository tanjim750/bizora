export function label(value) {
  return String(value ?? '—')
    .replaceAll('_', ' ')
    .replaceAll('-', ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

export function statusText(record) {
  const status = record?.delivery_status || record?.status || record?.decision
  if (status === 'PENDING' && record?.direction === 'OUTGOING') return 'Pending — not delivered'
  if (record?.is_ai_generated && status === 'SUGGESTED') return 'AI suggestion'
  return status ? label(status) : 'Recorded'
}

export function statusTone(status) {
  const value = String(status || '').toUpperCase()
  if (/NOT MOUNTED/.test(value)) return 'not-mounted'
  if (/UNAVAILABLE/.test(value)) return 'unavailable'
  if (/SUGGEST|AI /.test(value)) return 'ai'
  if (/FAILED|BLOCKED|REJECTED|CANCELLED|ERROR/.test(value)) return 'danger'
  if (/PENDING|OPEN|REVIEW|PARTIAL|DRAFT/.test(value)) return 'warning'
  if (/PAID|HEALTHY|RESOLVED|APPROVED|DELIVERED|COMPLETED|ACTIVE/.test(value)) return 'success'
  return 'neutral'
}

export function recordTitle(record) {
  for (const key of [
    'display_name',
    'name',
    'subject',
    'order_number',
    'tracking_code',
    'title',
    'event_type',
    'action',
  ]) {
    if (record?.[key]) return String(record[key])
  }
  return `Record #${record?.id ?? '—'}`
}

export function fieldValue(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}
