/**
 * Structured API Error keeping status, code, detail, and field-level error mappings.
 */
export class ApiError extends Error {
  constructor({
    status = 500,
    code = 'ERROR',
    detail = 'Request failed',
    fieldErrors = {},
    raw = null,
  } = {}) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.detail = detail
    this.fieldErrors = fieldErrors
    this.raw = raw
  }
}

/**
 * Normalizes all backend error shapes into a predictable structure:
 * 1. { code, detail }
 * 2. { detail }
 * 3. { error } or { message }
 * 4. DRF field dict: { field: ["error"] }
 * 5. DRF bare list: ["error1", "error2"]
 * 6. Query filter error: { query: "..." } or { unknown: [...] }
 * 7. Non-JSON or HTML 500 response
 */
export function normalizeError(data, status = 500) {
  let code = 'ERROR'
  let detail = ''
  const fieldErrors = {}

  if (status === 404) code = 'NOT_FOUND'
  else if (status === 403) code = 'FORBIDDEN'
  else if (status === 401) code = 'UNAUTHENTICATED'
  else if (status === 409) code = 'STALE_STATE'
  else if (status === 400) code = 'VALIDATION_ERROR'

  if (!data || typeof data !== 'object') {
    if (typeof data === 'string' && data.length > 0 && !data.trim().startsWith('<')) {
      detail = data
    } else {
      detail = `Request failed (${status})`
    }
    return { status, code, detail, fieldErrors, raw: data }
  }

  // Bare list error: ["Error 1", "Error 2"]
  if (Array.isArray(data)) {
    detail = data.map((item) => (typeof item === 'object' ? JSON.stringify(item) : String(item))).join(' ')
    return { status, code, detail, fieldErrors, raw: data }
  }

  // Extract explicit code
  if (typeof data.code === 'string') {
    code = data.code
  }

  // Extract message / detail
  if (typeof data.detail === 'string') {
    detail = data.detail
  } else if (typeof data.error === 'string') {
    detail = data.error
  } else if (typeof data.message === 'string') {
    detail = data.message
  }

  // Extract field-level errors
  const reservedKeys = new Set(['detail', 'code', 'error', 'message', 'status'])
  for (const [key, value] of Object.entries(data)) {
    if (reservedKeys.has(key)) continue

    if (Array.isArray(value)) {
      fieldErrors[key] = value.map(String).join(' ')
    } else if (value && typeof value === 'object') {
      fieldErrors[key] = JSON.stringify(value)
    } else if (value !== null && value !== undefined) {
      fieldErrors[key] = String(value)
    }
  }

  // If no main detail string, derive from the first field error
  if (!detail) {
    const fieldEntries = Object.entries(fieldErrors)
    if (fieldEntries.length > 0) {
      const [firstKey, firstVal] = fieldEntries[0]
      detail = `${firstKey}: ${firstVal}`
    } else {
      detail = `Request failed (${status})`
    }
  }

  return { status, code, detail, fieldErrors, raw: data }
}

/**
 * Backward compatibility helper for legacy code expecting errorMessage(data, status).
 */
export function errorMessage(data, status) {
  const normalized = normalizeError(data, status)
  return normalized.detail
}
