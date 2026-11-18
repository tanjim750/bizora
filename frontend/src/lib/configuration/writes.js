import { MANAGER_ROLES } from '../catalog.js'

export const STALE_MESSAGE = 'Someone else changed this configuration. Reload to continue.'

export function canEditConfiguration(role) {
  if (typeof role !== 'string') return false
  return MANAGER_ROLES.has(role.toUpperCase())
}

export function expectedVersion(record) {
  if (
    record &&
    typeof record.version === 'number' &&
    Number.isInteger(record.version) &&
    record.version >= 0
  ) {
    return record.version
  }
  throw new Error('The current version is unknown. Reload before saving.')
}

export function withVersion(record, body = {}) {
  if (body && Object.prototype.hasOwnProperty.call(body, 'version')) {
    throw new Error('The body must not contain version')
  }
  return { version: expectedVersion(record), ...body }
}

export function flattenFieldErrors(raw) {
  const out = {}
  if (!raw || typeof raw !== 'object') {
    return out
  }

  function walk(val, path) {
    if (!val) return

    if (Array.isArray(val)) {
      if (val.length === 0) return
      const isStringArray = val.every((x) => typeof x === 'string')
      if (isStringArray) {
        const key = path.length > 0 ? path.join('.') : '_form'
        out[key] = val.join(' ')
      } else {
        val.forEach((item, idx) => {
          walk(item, [...path, String(idx)])
        })
      }
      return
    }

    if (typeof val === 'object') {
      for (const [k, v] of Object.entries(val)) {
        if (path.length === 0 && (k === 'detail' || k === 'code')) {
          continue
        }
        if (k === 'non_field_errors') {
          const msg = Array.isArray(v) ? v.join(' ') : String(v)
          if (msg) {
            const key = path.length > 0 ? path.join('.') : '_form'
            out[key] = msg
          }
          continue
        }
        if (k === 'unknown') {
          if (Array.isArray(v) && v.length > 0) {
            const names = v.join(', ')
            const key = path.length > 0 ? path.join('.') : '_form'
            out[key] = `Not an editable setting: ${names}.`
          }
          continue
        }
        walk(v, [...path, k])
      }
    }
  }

  walk(raw, [])
  return out
}

export function classifyWriteError(err, context = 'update') {
  const status = Number(err?.status) || 0
  const detail =
    typeof err?.detail === 'string' && err.detail.trim().length > 0 ? err.detail : 'The request failed.'

  if (status === 409) {
    if (context === 'create') {
      return {
        kind: 'duplicate',
        stale: false,
        message: 'A record with this key already exists. Choose another key.',
        fieldErrors: {},
      }
    }
    if (context === 'reprocess') {
      return {
        kind: 'idempotency',
        stale: false,
        message: detail,
        fieldErrors: {},
      }
    }
    return {
      kind: 'stale',
      stale: true,
      message: STALE_MESSAGE,
      fieldErrors: {},
    }
  }

  if (status === 403) {
    return {
      kind: 'forbidden',
      stale: false,
      message: 'Only owners and managers can change configuration.',
      fieldErrors: {},
    }
  }

  if (status === 404) {
    return {
      kind: 'not_found',
      stale: false,
      message: 'This item no longer exists. Reload to continue.',
      fieldErrors: {},
    }
  }

  if (status === 400) {
    return {
      kind: 'validation',
      stale: false,
      message: detail,
      fieldErrors: flattenFieldErrors(err?.raw),
    }
  }

  if (status === 0 || status === 408) {
    return {
      kind: 'network',
      stale: false,
      message: detail,
      fieldErrors: {},
    }
  }

  return {
    kind: 'server',
    stale: false,
    message: detail,
    fieldErrors: {},
  }
}
