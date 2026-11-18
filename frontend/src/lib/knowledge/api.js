import { businessApiPath } from '../catalog.js'
import { enumLabel } from '../format/index.js'

export const SOURCES_PAGE_LIMIT = 100

export function knowledgeBase(businessId) {
  return businessApiPath(businessId, 'knowledge/')
}

export function sourcesPath(businessId, { status, limit = 25, offset = 0 } = {}) {
  if (typeof limit !== 'number' || !Number.isInteger(limit) || limit < 1 || limit > 100) {
    throw new Error('limit must be an integer between 1 and 100')
  }
  if (typeof offset !== 'number' || !Number.isInteger(offset) || offset < 0) {
    throw new Error('offset must be a non-negative integer')
  }

  const hasStatus = typeof status === 'string' && status.trim() !== ''
  if (hasStatus && !/^[A-Z_]{1,30}$/.test(status)) {
    throw new Error('status must match ^[A-Z_]{1,30}$')
  }

  const query = `limit=${limit}&offset=${offset}${hasStatus ? `&status=${status}` : ''}`
  return businessApiPath(businessId, `knowledge/sources/?${query}`)
}

export function cleanText(value) {
  return typeof value === 'string' && value.length > 0 ? value : null
}

export function cleanCount(value) {
  return typeof value === 'number' && Number.isInteger(value) && value >= 0 ? value : null
}

export function cleanId(value) {
  return typeof value === 'number' && Number.isInteger(value) && value > 0 ? value : null
}

export function sourceStatusLabel(status) {
  if (typeof status !== 'string' || status.length === 0) return 'Unknown'
  if (status === 'ACTIVE') return 'Active'
  if (status === 'DRAFT') return 'Draft (not approved)'
  if (status === 'DISABLED') return 'Disabled'
  if (status === 'SUPERSEDED') return 'Superseded'
  if (status === 'ARCHIVED') return 'Archived'
  return enumLabel(status)
}

export function sourceStatusTone(status) {
  if (status === 'ACTIVE') return 'success'
  if (status === 'DRAFT') return 'warning'
  return 'neutral'
}

export function normalizeSources(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return { businessId: null, total: 0, limit: 0, offset: 0, totals: null, results: [] }
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

  let totals = null
  if (data.totals && typeof data.totals === 'object' && !Array.isArray(data.totals)) {
    totals = {
      sources: cleanCount(data.totals.sources),
      documents: cleanCount(data.totals.documents),
      ready_documents: cleanCount(data.totals.ready_documents),
      chunks: cleanCount(data.totals.chunks),
    }
  }

  const results = []
  if (Array.isArray(data.results)) {
    for (const item of data.results) {
      const id = cleanId(item?.id)
      if (id !== null) {
        results.push({
          id,
          name: cleanText(item.name),
          source_type: cleanText(item.source_type),
          knowledge_type: cleanText(item.knowledge_type),
          status: cleanText(item.status),
          document_count: cleanCount(item.document_count),
          ready_document_count: cleanCount(item.ready_document_count),
          chunk_count: cleanCount(item.chunk_count),
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
    totals,
    results,
  }
}

export function knowledgeErrorReason(err) {
  if (!err || typeof err !== 'object') {
    return 'The knowledge base could not be loaded.'
  }
  if (err.status === 403) {
    return "You do not have access to this business's knowledge base."
  }
  if (err.status === 404) {
    return 'The knowledge service is not available on this server.'
  }
  if (err.status === 0 || err.status === 408) {
    return 'The server could not be reached. Try again in a moment.'
  }
  if (typeof err.status === 'number' && err.status >= 500) {
    return 'The server could not read the knowledge base. Try again later.'
  }
  if (typeof err.detail === 'string' && err.detail.trim() !== '') {
    return err.detail
  }
  return 'The knowledge base could not be loaded.'
}
