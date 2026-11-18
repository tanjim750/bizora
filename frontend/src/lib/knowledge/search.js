import { businessApiPath } from '../catalog.js'
import { enumLabel } from '../format/index.js'
import { knowledgeErrorReason, cleanText, cleanCount, cleanId } from './api.js'

export const SEARCH_MIN_CHARS = 2
export const SEARCH_MAX_CHARS = 200
export const SEARCH_MAX_WORDS = 10
export const SEARCH_DEFAULT_LIMIT = 10
export const SEARCH_MAX_LIMIT = 20
export const SCORE_HELP =
  'Keyword relevance for this search only. A higher score is a better keyword match. It is not a percentage and cannot be compared between searches.'

export function validateSearchQuery(q) {
  if (typeof q !== 'string') {
    return { ok: false, message: 'Type at least 2 characters to search.' }
  }
  const trimmed = q.trim()
  if (trimmed.length < SEARCH_MIN_CHARS) {
    return { ok: false, message: 'Type at least 2 characters to search.' }
  }
  if (trimmed.length > SEARCH_MAX_CHARS) {
    return { ok: false, message: 'Use at most 200 characters.' }
  }
  const words = trimmed.split(/\s+/).filter(Boolean)
  if (words.length > SEARCH_MAX_WORDS) {
    return { ok: false, message: 'Use at most 10 words.' }
  }

  for (let i = 0; i < trimmed.length; i++) {
    const code = trimmed.charCodeAt(i)
    if (code < 32 && code !== 9 && code !== 10) {
      return { ok: false, message: 'Remove special control characters.' }
    }
  }

  return { ok: true, query: trimmed }
}

export function searchPath(businessId, q, { limit = SEARCH_DEFAULT_LIMIT } = {}) {
  const validated = validateSearchQuery(q)
  if (!validated.ok) {
    throw new Error(validated.message)
  }
  if (typeof limit !== 'number' || !Number.isInteger(limit) || limit < 1 || limit > SEARCH_MAX_LIMIT) {
    throw new Error('limit must be an integer between 1 and 20')
  }

  const query = `q=${encodeURIComponent(validated.query)}&limit=${limit}`
  return businessApiPath(businessId, `knowledge/search/?${query}`)
}

export function normalizeSearch(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return {
      businessId: null,
      query: '',
      mode: 'KEYWORD',
      semanticAvailable: false,
      limit: 0,
      resultCount: 0,
      results: [],
    }
  }

  const rawBusinessId =
    typeof data.business_id === 'number'
      ? data.business_id
      : typeof data.businessId === 'number'
        ? data.businessId
        : null
  const businessId = cleanId(rawBusinessId)

  const query = typeof data.query === 'string' ? data.query : ''
  const mode = typeof data.mode === 'string' && data.mode.length > 0 ? data.mode : 'KEYWORD'
  const semanticAvailable = data.semantic_available === true
  const limit = typeof data.limit === 'number' ? data.limit : 0

  const results = []
  if (Array.isArray(data.results)) {
    for (const item of data.results) {
      const chunk_id = cleanId(item?.chunk_id)
      if (chunk_id !== null) {
        results.push({
          chunk_id,
          chunk_index: cleanCount(item.chunk_index),
          document_id: cleanId(item.document_id),
          document_title: cleanText(item.document_title),
          document_type: cleanText(item.document_type),
          version: cleanCount(item.version),
          source_id: cleanId(item.source_id),
          source_name: cleanText(item.source_name),
          section: cleanText(item.section),
          score: typeof item.score === 'number' && Number.isFinite(item.score) ? item.score : null,
          snippet: typeof item.snippet === 'string' ? item.snippet : '',
        })
      }
    }
  }

  const resultCount =
    typeof data.result_count === 'number'
      ? data.result_count
      : typeof data.resultCount === 'number'
        ? data.resultCount
        : results.length

  return {
    businessId,
    query,
    mode,
    semanticAvailable,
    limit,
    resultCount,
    results,
  }
}

export function scoreLabel(score) {
  if (typeof score !== 'number' || !Number.isFinite(score)) {
    return 'No score'
  }
  return `Score ${score.toFixed(2)}`
}

export function searchModeNotice({ mode, semanticAvailable } = {}) {
  if (mode === 'KEYWORD' || !mode || semanticAvailable !== true) {
    return 'Keyword search: results contain the words you typed. Semantic (meaning-based) search is not available in this version.'
  }
  return `Search mode: ${enumLabel(mode)}.`
}

export function resultCountText(resultCount, limit) {
  if (resultCount === 0) {
    return 'No matches'
  }
  if (limit > 0 && resultCount >= limit) {
    return `Showing the best ${resultCount} ${resultCount === 1 ? 'match' : 'matches'}. There may be more.`
  }
  if (resultCount === 1) {
    return '1 match'
  }
  return `${resultCount} matches`
}

export function searchErrorReason(err) {
  if (
    err &&
    err.status === 400 &&
    err.raw &&
    typeof err.raw.fields?.q === 'string' &&
    err.raw.fields.q.trim() !== ''
  ) {
    return err.raw.fields.q
  }
  return knowledgeErrorReason(err)
}
