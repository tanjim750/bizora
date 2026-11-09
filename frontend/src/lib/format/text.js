/**
 * Formats a fraction (e.g. 0.17) as a percentage string (e.g. "17.0%").
 */
export function percent(fraction, decimals = 1) {
  if (fraction === 'UNAVAILABLE') return 'UNAVAILABLE'
  if (fraction === null || fraction === undefined || fraction === '') return '—'

  const num = typeof fraction === 'number' ? fraction : parseFloat(String(fraction))
  if (Number.isNaN(num)) return '—'

  return `${(num * 100).toFixed(decimals)}%`
}

/**
 * Converts snake_case or kebab-case to Title Case (replaces underscores/dashes with spaces and capitalizes every word).
 * Kept for full backward compatibility with catalog and format.
 */
export function label(value) {
  return String(value ?? '—')
    .replaceAll('_', ' ')
    .replaceAll('-', ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

/**
 * Converts snake_case or SCREAMING_SNAKE to Sentence case.
 * Example: "MERGE_CANDIDATE" -> "Merge candidate"
 */
export function enumLabel(value) {
  if (value === null || value === undefined || value === '') return '—'
  const str = String(value).replaceAll('_', ' ').replaceAll('-', ' ').trim()

  if (!str) return '—'
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

/**
 * Fallback for missing values: returns "—" unless explicitly "UNAVAILABLE".
 */
export function missing(value) {
  if (value === 'UNAVAILABLE') return 'UNAVAILABLE'
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}

/**
 * Strips customer untrusted data tags (<untrusted_customer_data>...</untrusted_customer_data>).
 * Renders customer content as safe plain text.
 */
export function stripUntrusted(text) {
  if (!text) return ''
  return String(text).replaceAll('<untrusted_customer_data>', '').replaceAll('</untrusted_customer_data>', '')
}

/**
 * Formats a generic field value for display.
 */
export function fieldValue(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

/**
 * Derives a human-readable title for a record.
 */
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
