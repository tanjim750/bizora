import { businessApiPath, MANAGER_ROLES } from '../catalog.js'

export const PAYLOAD_PREVIEW_MAX_CHARS = 20000

export const PAYLOAD_NOTICES = Object.freeze({
  personalData:
    'This is a diagnostic copy of what a provider sent. The server hides values it recognises as credentials (keys such as token, secret, password, authorization, API key, cookie or credential) and shortens very long content. It does not remove personal data: names, email addresses, phone numbers and addresses can still appear.',
  audit: 'Opening this view is recorded in the audit log together with your user.',
  handling:
    'Do not copy this into chats, tickets or documents. This screen has no copy, download or save option and clears the content when you close it.',
})

export function canViewPayloads(role) {
  return typeof role === 'string' && MANAGER_ROLES.has(role)
}

export function parsePayloadId(value) {
  if (value === null || value === undefined || typeof value === 'boolean') {
    return null
  }
  let str = ''
  if (typeof value === 'number') {
    if (!Number.isSafeInteger(value)) {
      return null
    }
    str = String(value)
  } else if (typeof value === 'string') {
    str = value.trim()
  } else {
    return null
  }

  if (!/^\d+$/.test(str)) {
    return null
  }

  try {
    const b = BigInt(str)
    if (b < 1n || b > 9223372036854775807n) {
      return null
    }
    return b.toString()
  } catch {
    return null
  }
}

export function payloadDiagnosticPath(businessId, payloadId) {
  const parsed = parsePayloadId(payloadId)
  if (!parsed) {
    throw new Error('Invalid payload ID')
  }
  return businessApiPath(businessId, `observability/payloads/${parsed}/`)
}

export function normalizePayloadDiagnostic(data) {
  if (!data || typeof data !== 'object') {
    return null
  }
  const parsedId = parsePayloadId(data.id)
  if (parsedId === null) {
    return null
  }

  const connectionId = Number.isInteger(data.connection_id) ? data.connection_id : null
  const digest = typeof data.digest === 'string' ? data.digest : null
  const receivedAt = typeof data.received_at === 'string' ? data.received_at : null
  const sourceAt = typeof data.source_at === 'string' ? data.source_at : null
  const signatureVerified = data.signature_verified === true
  const body = data.diagnostic_payload !== undefined ? data.diagnostic_payload : null

  return {
    id: data.id,
    connectionId,
    digest,
    receivedAt,
    sourceAt,
    signatureVerified,
    body,
  }
}

export function personalDataHints(text) {
  if (typeof text !== 'string') {
    return []
  }
  const hints = []
  if (/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/.test(text)) {
    hints.push('an email address')
  }
  if (/\+\d{8,15}\b|\b01[3-9]\d{8}\b/.test(text)) {
    hints.push('a phone number')
  }
  return hints
}

export function describePayload(value, { maxChars = PAYLOAD_PREVIEW_MAX_CHARS } = {}) {
  let full = ''
  try {
    const s = JSON.stringify(value, null, 2)
    full = s !== undefined ? s : ''
  } catch {
    full = ''
  }

  const text = full.slice(0, maxChars)
  const previewTruncated = full.length > maxChars
  const totalChars = full.length

  const countMatches = (str, pattern) => (str.match(new RegExp(pattern, 'g')) || []).length
  const markers = {
    redacted: countMatches(full, '\\[REDACTED\\]'),
    cutOff: countMatches(full, '\\[TRUNCATED\\]'),
    unsupported: countMatches(full, '\\[UNSUPPORTED\\]'),
  }
  const hints = personalDataHints(full)

  return { text, previewTruncated, totalChars, markers, hints }
}

export function markerSummary(markers) {
  if (!markers || typeof markers !== 'object') {
    return ''
  }
  const { redacted = 0, cutOff = 0, unsupported = 0 } = markers
  if (redacted === 0 && cutOff === 0 && unsupported === 0) {
    return ''
  }

  const parts = []
  if (redacted > 0) {
    parts.push(`${redacted} ${redacted === 1 ? 'value' : 'values'} with [REDACTED]`)
  }
  if (cutOff > 0) {
    parts.push(`${cutOff} ${cutOff === 1 ? 'value' : 'values'} with [TRUNCATED]`)
  }
  if (unsupported > 0) {
    parts.push(`${unsupported} ${unsupported === 1 ? 'value' : 'values'} with [UNSUPPORTED]`)
  }

  let joined = ''
  if (parts.length === 1) {
    joined = parts[0]
  } else if (parts.length === 2) {
    joined = `${parts[0]} and ${parts[1]}`
  } else if (parts.length === 3) {
    joined = `${parts[0]}, ${parts[1]} and ${parts[2]}`
  }

  return `The server replaced ${joined}.`
}

export function payloadErrorMessage(error) {
  if (error?.status === 403) {
    return 'Only owners and managers can open diagnostic payloads.'
  }
  if (error?.status === 404) {
    return 'This payload was not found for this business.'
  }
  if (error?.status === 400) {
    return typeof error?.detail === 'string' && error.detail.trim()
      ? error.detail
      : 'The server did not accept the request.'
  }
  if (typeof error?.detail === 'string' && error.detail.trim()) {
    return error.detail
  }
  if (typeof error?.message === 'string' && error.message.trim()) {
    return error.message
  }
  return 'The payload could not be loaded.'
}
