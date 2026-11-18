import { businessApiPath } from '../catalog.js'
import { canViewPayloads } from './payloads.js'

export const RECORD_KINDS = Object.freeze(['failed-records', 'webhooks'])
export const FAILED_RECORD_STATUSES = Object.freeze(['OPEN', 'REVIEWING', 'RETRYING', 'RESOLVED', 'IGNORED'])
export const WEBHOOK_STATUSES = Object.freeze(['RECEIVED', 'ROUTING', 'PROCESSED', 'FAILED', 'REJECTED'])
export const RECORD_PAGE_SIZE = 25
export const MESSAGE_PREVIEW_CHARS = 160

export function recordListPath(businessId, kind, { page = 1, pageSize = RECORD_PAGE_SIZE, status } = {}) {
  if (!RECORD_KINDS.includes(kind)) {
    throw new Error(`Unsupported record list: ${kind}`)
  }
  if (typeof page !== 'number' || !Number.isInteger(page) || page < 1) {
    throw new Error('page must be a whole number of at least 1.')
  }
  if (typeof pageSize !== 'number' || !Number.isInteger(pageSize) || pageSize < 1 || pageSize > 100) {
    throw new Error('pageSize must be a whole number between 1 and 100.')
  }

  const hasStatus = typeof status === 'string' && status.trim() !== ''
  if (hasStatus) {
    const allowed = kind === 'failed-records' ? FAILED_RECORD_STATUSES : WEBHOOK_STATUSES
    if (!allowed.includes(status)) {
      throw new Error(`Unsupported status: ${status}`)
    }
  }

  const query = `page=${page}&page_size=${pageSize}${hasStatus ? `&status=${status}` : ''}`
  return businessApiPath(businessId, `observability/${kind}/?${query}`)
}

export function shortenText(value, max = MESSAGE_PREVIEW_CHARS) {
  if (typeof value !== 'string') return ''
  const trimmed = value.replace(/\s+/g, ' ').trim()
  if (trimmed.length > max) {
    return trimmed.slice(0, max) + '…'
  }
  return trimmed
}

export function normalizeRecordPage(data, kind) {
  if (!RECORD_KINDS.includes(kind)) {
    throw new Error(`Unsupported record list: ${kind}`)
  }
  if (!data || typeof data !== 'object' || !Array.isArray(data.results)) {
    return { total: 0, rows: [] }
  }

  const validItems = data.results.filter(
    (item) => item && typeof item.id === 'number' && Number.isInteger(item.id) && item.id > 0,
  )

  const rows = validItems.map((item) => {
    const payloadId =
      typeof item.payload_id === 'number' && Number.isInteger(item.payload_id) && item.payload_id > 0
        ? item.payload_id
        : null

    if (kind === 'failed-records') {
      return {
        id: item.id,
        entityType: typeof item.entity_type === 'string' ? item.entity_type : null,
        externalId: typeof item.external_id === 'string' ? item.external_id : null,
        stage: typeof item.stage === 'string' ? item.stage : null,
        code: typeof item.code === 'string' ? item.code : null,
        message: shortenText(item.message),
        status: typeof item.status === 'string' ? item.status : null,
        payloadId,
        lastSeenAt: typeof item.last_seen_at === 'string' ? item.last_seen_at : null,
      }
    }

    return {
      id: item.id,
      eventId: typeof item.event_id === 'string' ? item.event_id : null,
      eventType: typeof item.event_type === 'string' ? item.event_type : null,
      entityType: typeof item.entity_type === 'string' ? item.entity_type : null,
      validation: typeof item.validation === 'string' ? item.validation : null,
      status: typeof item.status === 'string' ? item.status : null,
      payloadId,
      receivedAt: typeof item.received_at === 'string' ? item.received_at : null,
      deliveryCount:
        typeof item.delivery_count === 'number' && Number.isInteger(item.delivery_count)
          ? item.delivery_count
          : null,
    }
  })

  const total = typeof data.count === 'number' && Number.isInteger(data.count) ? data.count : rows.length

  return { total, rows }
}

export function canOpenPayload(row, role) {
  if (!canViewPayloads(role)) return false
  if (!row || typeof row !== 'object') return false
  return typeof row.payloadId === 'number' && Number.isInteger(row.payloadId) && row.payloadId > 0
}

export function recordListError(error) {
  if (!error) return 'The list could not be loaded.'
  if (error.status === 403) return 'You do not have access to this business.'
  if (error.status === 400) {
    if (typeof error.detail === 'string' && error.detail.trim() !== '') {
      return error.detail
    }
    return 'The server did not accept the request.'
  }
  if (typeof error.detail === 'string' && error.detail.trim() !== '') {
    return error.detail
  }
  if (typeof error.message === 'string' && error.message.trim() !== '') {
    return error.message
  }
  return 'The list could not be loaded.'
}
