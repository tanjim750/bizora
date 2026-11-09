const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/**
 * Parses an ISO date string and returns a Date object.
 */
function toDate(iso) {
  if (!iso || iso === 'UNAVAILABLE') return null
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? null : d
}

/**
 * Formats a date string into "DD MMM YYYY, HH:MM" in the specified timezone.
 * Hydration-safe across server and client.
 */
export function dateTime(iso, timezone = 'Asia/Dhaka') {
  if (iso === 'UNAVAILABLE') return 'UNAVAILABLE'
  const d = toDate(iso)
  if (!d) return '—'

  try {
    const formatter = new Intl.DateTimeFormat('en-GB', {
      timeZone: timezone,
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })

    const parts = formatter.formatToParts(d)
    const get = (type) => parts.find((p) => p.type === type)?.value || ''
    const day = get('day')
    const month = get('month')
    const year = get('year')
    const hour = get('hour')
    const minute = get('minute')

    return `${day} ${month} ${year}, ${hour}:${minute}`
  } catch {
    // Fallback if timezone is invalid
    const day = String(d.getDate()).padStart(2, '0')
    const month = MONTHS[d.getMonth()]
    const year = d.getFullYear()
    const hour = String(d.getHours()).padStart(2, '0')
    const minute = String(d.getMinutes()).padStart(2, '0')
    return `${day} ${month} ${year}, ${hour}:${minute}`
  }
}

/**
 * Formats a date string into "DD MMM YYYY".
 */
export function date(iso, timezone = 'Asia/Dhaka') {
  if (iso === 'UNAVAILABLE') return 'UNAVAILABLE'
  const d = toDate(iso)
  if (!d) return '—'

  try {
    const formatter = new Intl.DateTimeFormat('en-GB', {
      timeZone: timezone,
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
    const parts = formatter.formatToParts(d)
    const get = (type) => parts.find((p) => p.type === type)?.value || ''
    return `${get('day')} ${get('month')} ${get('year')}`
  } catch {
    const day = String(d.getDate()).padStart(2, '0')
    const month = MONTHS[d.getMonth()]
    const year = d.getFullYear()
    return `${day} ${month} ${year}`
  }
}

/**
 * Formats a duration in seconds into human-readable string (e.g. "2d 4h", "45m 12s").
 */
export function duration(seconds) {
  if (seconds === null || seconds === undefined || seconds === '' || seconds === 'UNAVAILABLE') {
    return '—'
  }
  const s = Math.round(Number(seconds))
  if (Number.isNaN(s) || s < 0) return '—'
  if (s === 0) return '0s'

  const days = Math.floor(s / 86400)
  const hours = Math.floor((s % 86400) / 3600)
  const minutes = Math.floor((s % 3600) / 60)
  const remSec = s % 60

  if (days > 0) {
    return hours > 0 ? `${days}d ${hours}h` : `${days}d`
  }
  if (hours > 0) {
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
  }
  if (minutes > 0) {
    return remSec > 0 ? `${minutes}m ${remSec}s` : `${minutes}m`
  }
  return `${remSec}s`
}

/**
 * Relative time from now (e.g. "5m ago", "just now").
 */
export function relativeTime(iso, now = new Date()) {
  const d = toDate(iso)
  if (!d) return '—'

  const diffSec = Math.floor((now.getTime() - d.getTime()) / 1000)
  if (diffSec < 30) return 'just now'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
  if (diffSec < 2592000) return `${Math.floor(diffSec / 86400)}d ago`
  return date(iso)
}
