import { businessApiPath } from '../catalog.js'

const ALLOWED_PERIOD_TYPES = new Set(['CUSTOM', 'DAY', 'HOUR', 'MONTH', 'WEEK'])

export function metricsPath(businessId, { limit = 100, offset = 0 } = {}) {
  if (!Number.isInteger(limit) || limit < 1 || limit > 200) {
    throw new Error('limit must be an integer between 1 and 200')
  }
  if (!Number.isInteger(offset) || offset < 0) {
    throw new Error('offset must be an integer >= 0')
  }
  const base = businessApiPath(businessId, 'intelligence/metrics/')
  return `${base}?limit=${limit}&offset=${offset}`
}

export function snapshotsPath(businessId, metricKey, { periodType, limit = 50, offset = 0 } = {}) {
  if (!metricKey || typeof metricKey !== 'string' || !/^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)*$/.test(metricKey)) {
    throw new Error('Invalid metric key')
  }
  if (!Number.isInteger(limit) || limit < 1 || limit > 200) {
    throw new Error('limit must be an integer between 1 and 200')
  }
  if (!Number.isInteger(offset) || offset < 0) {
    throw new Error('offset must be an integer >= 0')
  }
  if (periodType !== undefined && periodType !== null && !ALLOWED_PERIOD_TYPES.has(periodType)) {
    throw new Error(
      `Invalid period type: ${periodType}. Must be one of ${Array.from(ALLOWED_PERIOD_TYPES).join(', ')}`,
    )
  }

  const base = businessApiPath(businessId, `intelligence/metrics/${metricKey}/snapshots/`)
  let query = `?limit=${limit}&offset=${offset}`
  if (periodType) {
    query += `&period_type=${encodeURIComponent(periodType)}`
  }
  return `${base}${query}`
}

export function normalizeList(data) {
  if (!data || typeof data !== 'object' || !Array.isArray(data.results)) {
    return { total: 0, limit: 0, offset: 0, results: [] }
  }
  const total =
    typeof data.total_count === 'number'
      ? data.total_count
      : typeof data.count === 'number'
        ? data.count
        : data.results.length

  const limit = typeof data.limit === 'number' ? data.limit : 0
  const offset = typeof data.offset === 'number' ? data.offset : 0

  return {
    total,
    limit,
    offset,
    results: data.results,
  }
}
