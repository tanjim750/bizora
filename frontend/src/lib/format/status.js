import { enumLabel } from './text.js'

/**
 * Maps an exact status code or normalized string to a visual semantic tone:
 * 'success' | 'warning' | 'danger' | 'info' | 'ai' | 'unavailable' | 'not-mounted' | 'neutral'
 */
const EXACT_STATUS_TONES = {
  // Not mounted / Unavailable
  'NOT MOUNTED': 'not-mounted',
  NOT_MOUNTED: 'not-mounted',
  UNAVAILABLE: 'unavailable',
  'NOT CONNECTED': 'unavailable',
  NOT_CONNECTED: 'unavailable',

  // AI
  SUGGESTED: 'ai',
  'AI SUGGESTION': 'ai',
  AI_SUGGESTION: 'ai',
  REVIEWING: 'ai',

  // Danger
  FAILED: 'danger',
  BLOCKED: 'danger',
  REJECTED: 'danger',
  CANCELLED: 'danger',
  CANCELED: 'danger',
  ERROR: 'danger',
  MISSED: 'danger',
  RETURNED: 'danger',

  // Warning
  PENDING: 'warning',
  OPEN: 'warning',
  REVIEW: 'warning',
  PARTIAL: 'warning',
  DRAFT: 'warning',
  BUSY: 'warning',
  PROCESSING: 'warning',
  WAITING: 'warning',

  // Success
  PAID: 'success',
  HEALTHY: 'success',
  RESOLVED: 'success',
  APPROVED: 'success',
  DELIVERED: 'success',
  COMPLETED: 'success',
  ACTIVE: 'success',
  SENT: 'success',
  REFUNDED: 'success',
  CLOSED: 'success',

  // Neutral (Explicitly includes INACTIVE, UNLINKED)
  INACTIVE: 'neutral',
  UNLINKED: 'neutral',
  RECORDED: 'neutral',
  UNKNOWN: 'neutral',
}

export function statusTone(status) {
  if (!status) return 'neutral'
  const normalized = String(status).trim().toUpperCase()

  if (EXACT_STATUS_TONES[normalized]) {
    return EXACT_STATUS_TONES[normalized]
  }

  // Handle phrases
  if (normalized.includes('NOT MOUNTED')) return 'not-mounted'
  if (normalized.includes('UNAVAILABLE') || normalized.includes('NOT CONNECTED')) return 'unavailable'
  if (normalized.includes('AI ') || normalized.startsWith('AI_')) return 'ai'
  if (normalized.startsWith('INACTIVE')) return 'neutral'

  return 'neutral'
}

/**
 * Derives a human-readable status text honoring Bizora honesty rules.
 */
export function statusText(record) {
  const status = record?.delivery_status || record?.status || record?.decision
  if (status === 'PENDING' && record?.direction === 'OUTGOING') return 'Pending — not delivered'
  if (record?.is_ai_generated && status === 'SUGGESTED') return 'AI suggestion'
  return status ? enumLabel(status) : 'Recorded'
}
