import { businessApiPath } from '../catalog.js'
import { enumLabel } from '../format/index.js'
import { cleanText, cleanCount, cleanId } from './api.js'

export const DOCUMENTS_PAGE_LIMIT = 25
export const DOCUMENT_STATUS_ORDER = Object.freeze([
  'READY',
  'PUBLISHED',
  'PENDING',
  'FAILED',
  'SUPERSEDED',
  'ARCHIVED',
])

export function documentsPath(businessId, { source, status, limit = 25, offset = 0 } = {}) {
  if (typeof limit !== 'number' || !Number.isInteger(limit) || limit < 1 || limit > 100) {
    throw new Error('limit must be an integer between 1 and 100')
  }
  if (typeof offset !== 'number' || !Number.isInteger(offset) || offset < 0) {
    throw new Error('offset must be a non-negative integer')
  }

  let sourceParam = ''
  const hasSource = source !== undefined && source !== null && source !== ''
  if (hasSource) {
    let parsedSource = null
    if (typeof source === 'number' && Number.isInteger(source) && source > 0) {
      parsedSource = source
    } else if (typeof source === 'string' && /^\d+$/.test(source.trim())) {
      const n = Number(source.trim())
      if (Number.isInteger(n) && n > 0) parsedSource = n
    }
    if (parsedSource === null) {
      throw new Error('source must be a positive integer')
    }
    sourceParam = `&source=${parsedSource}`
  }

  let statusParam = ''
  const hasStatus = typeof status === 'string' && status.trim() !== ''
  if (hasStatus) {
    if (!/^[A-Z_]{1,30}$/.test(status)) {
      throw new Error('status must match ^[A-Z_]{1,30}$')
    }
    statusParam = `&status=${status}`
  }

  const query = `limit=${limit}&offset=${offset}${sourceParam}${statusParam}`
  return businessApiPath(businessId, `knowledge/documents/?${query}`)
}

export function documentStatusLabel(status) {
  if (typeof status !== 'string' || status.length === 0) return 'Unknown'
  if (status === 'READY') return 'Ready'
  if (status === 'PUBLISHED') return 'Published'
  if (status === 'PENDING') return 'Waiting to be processed'
  if (status === 'FAILED') return 'Processing failed'
  if (status === 'SUPERSEDED') return 'Replaced by a newer version'
  if (status === 'ARCHIVED') return 'Archived'
  return enumLabel(status)
}

export function documentStatusTone(status) {
  if (status === 'READY' || status === 'PUBLISHED') return 'success'
  if (status === 'PENDING') return 'warning'
  if (status === 'FAILED') return 'danger'
  return 'neutral'
}

export function searchabilityNote(doc) {
  if (!doc || typeof doc !== 'object') return 'Not searchable'
  if (doc.searchable === true) return 'Searchable'
  if (typeof doc.source_status === 'string' && doc.source_status !== '' && doc.source_status !== 'ACTIVE') {
    return 'Not searchable: its source is not active'
  }
  if (doc.status !== 'READY' && doc.status !== 'PUBLISHED') {
    return 'Not searchable: the document is not ready'
  }
  if (doc.chunk_count === 0) {
    return 'Not searchable: it has no text chunks yet'
  }
  return 'Not searchable'
}

export function normalizeDocuments(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return { businessId: null, total: 0, limit: 0, offset: 0, results: [] }
  }

  const rawBusinessId =
    typeof data.business_id === 'number'
      ? data.business_id
      : typeof data.businessId === 'number'
        ? data.businessId
        : null
  const businessId = cleanId(rawBusinessId)

  const limit = typeof data.limit === 'number' ? data.limit : 0
  const offset = typeof data.offset === 'number' ? data.offset : 0

  const results = []
  if (Array.isArray(data.results)) {
    for (const item of data.results) {
      const id = cleanId(item?.id)
      if (id !== null) {
        results.push({
          id,
          source_id: cleanId(item.source_id),
          source_name: cleanText(item.source_name),
          source_status: cleanText(item.source_status),
          title: cleanText(item.title),
          document_type: cleanText(item.document_type),
          mime_type: cleanText(item.mime_type),
          version: cleanCount(item.version),
          status: cleanText(item.status),
          searchable: item.searchable === true,
          is_duplicate: item.is_duplicate === true,
          chunk_count: cleanCount(item.chunk_count),
          preview: cleanText(item.preview),
          ingested_at: cleanText(item.ingested_at),
          processed_at: cleanText(item.processed_at),
          created_at: cleanText(item.created_at),
          updated_at: cleanText(item.updated_at),
        })
      }
    }
  }

  const total =
    typeof data.total_count === 'number'
      ? data.total_count
      : typeof data.total === 'number'
        ? data.total
        : results.length

  return {
    businessId,
    total,
    limit,
    offset,
    results,
  }
}

export function pageForOffset(offset, limit) {
  if (typeof offset !== 'number' || !Number.isFinite(offset) || offset < 0) return 1
  if (typeof limit !== 'number' || !Number.isInteger(limit) || limit <= 0) return 1
  return Math.floor(offset / limit) + 1
}

export function offsetForPage(page, limit) {
  if (typeof page !== 'number' || !Number.isFinite(page) || page < 1) page = 1
  if (typeof limit !== 'number' || !Number.isInteger(limit) || limit <= 0) return 0
  return (Math.max(1, Math.floor(page)) - 1) * limit
}
