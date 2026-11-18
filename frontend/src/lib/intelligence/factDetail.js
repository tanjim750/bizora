import { businessApiPath } from '../catalog.js'
import { confidencePercent } from './facts.js'

export const EVIDENCE_MAX_ENTRIES = 50
export const EVIDENCE_MAX_TEXT = 500
export const SENSITIVE_KEY = /token|secret|password|authorization|api.?key|cookie|credential/i

export function parseFactId(value) {
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

export function isFactIdOpenable(value) {
  return parseFactId(value) !== null
}

export function factDetailPath(businessId, factId) {
  const parsed = parseFactId(factId)
  if (!parsed) {
    throw new Error('Invalid fact ID')
  }
  return businessApiPath(businessId, `intelligence/facts/${parsed}/`)
}

export function evidenceEntries(
  evidence,
  { maxEntries = EVIDENCE_MAX_ENTRIES, maxText = EVIDENCE_MAX_TEXT } = {},
) {
  if (!evidence || typeof evidence !== 'object' || Array.isArray(evidence)) {
    return []
  }

  const entries = []
  const rawPairs = Object.entries(evidence).slice(0, maxEntries)

  for (const [rawKey, val] of rawPairs) {
    const key = String(rawKey).slice(0, 100)
    const masked = SENSITIVE_KEY.test(key)

    let text = ''
    if (masked) {
      text = '[hidden]'
    } else if (typeof val === 'string') {
      text = val
    } else if (typeof val === 'number' || typeof val === 'boolean') {
      text = String(val)
    } else if (val === null || val === undefined) {
      text = '—'
    } else {
      try {
        text = JSON.stringify(val, (subK, subVal) => {
          if (subK && SENSITIVE_KEY.test(subK)) {
            return '[hidden]'
          }
          return subVal
        })
      } catch {
        text = '[unreadable]'
      }
    }

    if (text.length > maxText) {
      text = text.slice(0, maxText) + '…'
    }

    entries.push({ key, text, masked })
  }

  return entries
}

export function normalizeFactDetail(data) {
  if (!data || typeof data !== 'object') {
    return null
  }
  const parsedId = parseFactId(data.id)
  if (parsedId === null) {
    return null
  }

  const businessId = Number.isInteger(data.business_id) ? data.business_id : null
  const factType = typeof data.fact_type === 'string' ? data.fact_type : null
  const statement = typeof data.statement === 'string' ? data.statement : ''
  const value = data.value !== null && data.value !== undefined ? String(data.value) : null
  const valueUnit = typeof data.value_unit === 'string' ? data.value_unit : null
  const confidencePercentVal = confidencePercent(data.confidence)
  const status = typeof data.status === 'string' ? data.status : null
  const ruleKey = typeof data.rule_key === 'string' ? data.rule_key : null
  const validFrom = typeof data.valid_from === 'string' ? data.valid_from : null
  const validTo = typeof data.valid_to === 'string' ? data.valid_to : null
  const detectedAt = typeof data.detected_at === 'string' ? data.detected_at : null

  const isEvidenceObj = data.evidence && typeof data.evidence === 'object' && !Array.isArray(data.evidence)
  const entries = evidenceEntries(data.evidence)
  const total = isEvidenceObj ? Object.keys(data.evidence).length : 0

  return {
    id: data.id,
    businessId,
    factType,
    statement,
    value,
    valueUnit,
    confidencePercent: confidencePercentVal,
    status,
    ruleKey,
    validFrom,
    validTo,
    detectedAt,
    evidence: { entries, total },
  }
}

export function factErrorMessage(error) {
  if (error?.status === 403) {
    return 'You do not have access to this business.'
  }
  if (error?.status === 404) {
    return 'This fact was not found. It may belong to another business or may have been removed.'
  }
  if (typeof error?.detail === 'string' && error.detail.trim()) {
    return error.detail
  }
  if (typeof error?.message === 'string' && error.message.trim()) {
    return error.message
  }
  return 'The fact could not be loaded.'
}
