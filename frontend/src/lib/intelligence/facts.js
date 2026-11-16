import { businessApiPath } from '../catalog.js'
import { normalizeList } from './metrics.js'

const ALLOWED_FACT_STATUSES = new Set(['CANDIDATE', 'VERIFIED', 'INVALIDATED', 'EXPIRED'])
const ALLOWED_ISSUE_STATUSES = new Set(['OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'DISMISSED'])
const ALLOWED_PATCH_STATUSES = new Set(['ACKNOWLEDGED', 'RESOLVED', 'DISMISSED'])
const MAX_BIGINT = 9223372036854775807n

export function FACTS_PATH(businessId, { limit = 50, offset = 0, status } = {}) {
  if (status !== undefined && status !== null && !ALLOWED_FACT_STATUSES.has(status)) {
    throw new Error(`Invalid fact status: ${status}`)
  }
  const base = businessApiPath(businessId, 'intelligence/facts/')
  let query = `?limit=${limit}&offset=${offset}`
  if (status) query += `&status=${encodeURIComponent(status)}`
  return `${base}${query}`
}

export function ISSUES_PATH(businessId, { limit = 50, offset = 0, status, severity } = {}) {
  if (status !== undefined && status !== null && !ALLOWED_ISSUE_STATUSES.has(status)) {
    throw new Error(`Invalid issue status: ${status}`)
  }
  const base = businessApiPath(businessId, 'intelligence/issues/')
  let query = `?limit=${limit}&offset=${offset}`
  if (status) query += `&status=${encodeURIComponent(status)}`
  if (severity) query += `&severity=${encodeURIComponent(severity)}`
  return `${base}${query}`
}

export function issuePatchPath(businessId, issueId) {
  let idBig
  try {
    idBig = BigInt(issueId)
  } catch {
    throw new Error('Invalid issue ID')
  }
  if (idBig <= 0n || idBig > MAX_BIGINT) {
    throw new Error('Invalid issue ID')
  }
  return businessApiPath(businessId, `intelligence/issues/${issueId}/`)
}

export function issuePatchBody(status, notes) {
  if (!status || !ALLOWED_PATCH_STATUSES.has(status)) {
    throw new Error(`Invalid issue patch status: ${status}. Must be one of ACKNOWLEDGED, RESOLVED, DISMISSED`)
  }
  const trimmed = typeof notes === 'string' ? notes.trim() : ''
  if (trimmed) {
    return { status, notes: trimmed }
  }
  return { status }
}

export function confidencePercent(value) {
  if (value === null || value === undefined || value === '') return null
  const num = Number(value)
  if (!Number.isFinite(num) || num < 0 || num > 1) return null
  return Math.round(num * 100)
}

export { normalizeList }
