import { businessApiPath } from '../catalog.js'

export const CONFIG_SECTIONS = ['profile', 'general', 'ai', 'knowledge']
export const RESOURCE_KINDS = ['rules', 'policies']
export const RECORD_STATES = ['DRAFT', 'ACTIVE', 'DISABLED', 'SUPERSEDED', 'ARCHIVED']

export const SECTION_LABELS = {
  profile: 'Business profile',
  general: 'General settings',
  ai: 'AI assistant',
  knowledge: 'Knowledge retrieval',
}

export const KEY_PATTERN = /^[a-z][a-z0-9_-]{0,99}$/

function validatePositiveId(id, name) {
  const isNum = typeof id === 'number' && Number.isSafeInteger(id) && id > 0
  const isStr = typeof id === 'string' && /^\d+$/.test(id) && Number(id) > 0
  if (!isNum && !isStr) {
    throw new Error(`Invalid ${name} id`)
  }
}

export function listQuery({ page, pageSize, status } = {}) {
  const parts = []

  if (page !== undefined && page !== null) {
    if (!Number.isInteger(page) || page < 1) {
      throw new Error('page must be an integer >= 1')
    }
    parts.push(`page=${page}`)
  }

  if (pageSize !== undefined && pageSize !== null) {
    if (!Number.isInteger(pageSize) || pageSize < 1 || pageSize > 100) {
      throw new Error('pageSize must be an integer from 1 to 100')
    }
    parts.push(`page_size=${pageSize}`)
  }

  if (status !== undefined && status !== null) {
    if (!RECORD_STATES.includes(status)) {
      throw new Error(`Unsupported status: ${status}`)
    }
    parts.push(`status=${status}`)
  }

  return parts.length > 0 ? `?${parts.join('&')}` : ''
}

export function effectivePath(businessId) {
  return businessApiPath(businessId, 'configuration/effective/')
}

export function changesPath(businessId, opts) {
  return `${businessApiPath(businessId, 'configuration/changes/')}${listQuery(opts)}`
}

export function sectionPath(businessId, section) {
  if (!CONFIG_SECTIONS.includes(section)) {
    throw new Error(`Unknown configuration section: ${section}`)
  }
  return businessApiPath(businessId, `configuration/${section}/`)
}

export function sectionHistoryPath(businessId, section, opts) {
  if (!CONFIG_SECTIONS.includes(section)) {
    throw new Error(`Unknown configuration section: ${section}`)
  }
  return `${businessApiPath(businessId, `configuration/${section}/history/`)}${listQuery(opts)}`
}

export function resourcesPath(businessId, kind, opts) {
  if (!RESOURCE_KINDS.includes(kind)) {
    throw new Error(`Unknown resource kind: ${kind}`)
  }
  return `${businessApiPath(businessId, `configuration/${kind}/`)}${listQuery(opts)}`
}

export function resourcePath(businessId, kind, key) {
  if (!RESOURCE_KINDS.includes(kind)) {
    throw new Error(`Unknown resource kind: ${kind}`)
  }
  if (!KEY_PATTERN.test(key)) {
    throw new Error('Invalid configuration key')
  }
  return businessApiPath(businessId, `configuration/${kind}/${key}/`)
}

export function resourceHistoryPath(businessId, kind, key, opts) {
  if (!RESOURCE_KINDS.includes(kind)) {
    throw new Error(`Unknown resource kind: ${kind}`)
  }
  if (!KEY_PATTERN.test(key)) {
    throw new Error('Invalid configuration key')
  }
  return `${businessApiPath(businessId, `configuration/${kind}/${key}/history/`)}${listQuery(opts)}`
}

export function connectionsPath(businessId, opts) {
  return `${businessApiPath(businessId, 'configuration/connections/')}${listQuery(opts)}`
}

export function connectionPath(businessId, id) {
  validatePositiveId(id, 'connection')
  return businessApiPath(businessId, `configuration/connections/${id}/`)
}

export function connectionHistoryPath(businessId, id, opts) {
  validatePositiveId(id, 'connection')
  return `${businessApiPath(businessId, `configuration/connections/${id}/history/`)}${listQuery(opts)}`
}

export function sourcesPath(businessId, opts) {
  return `${businessApiPath(businessId, 'configuration/sources/')}${listQuery(opts)}`
}

export function sourcePath(businessId, id) {
  validatePositiveId(id, 'source')
  return businessApiPath(businessId, `configuration/sources/${id}/`)
}

export function sourceHistoryPath(businessId, id, opts) {
  validatePositiveId(id, 'source')
  return `${businessApiPath(businessId, `configuration/sources/${id}/history/`)}${listQuery(opts)}`
}

export function providersPath(businessId, opts) {
  return `${businessApiPath(businessId, 'configuration/providers/')}${listQuery(opts)}`
}

export function reprocessingPath(businessId, opts) {
  return `${businessApiPath(businessId, 'configuration/reprocessing/')}${listQuery(opts)}`
}

export function monitoringPath(businessId) {
  return businessApiPath(businessId, 'configuration/monitoring/')
}

export function monitoringHistoryPath(businessId, opts) {
  return `${businessApiPath(businessId, 'configuration/monitoring/history/')}${listQuery(opts)}`
}

export function freshnessPath(businessId, opts) {
  return `${businessApiPath(businessId, 'configuration/freshness/')}${listQuery(opts)}`
}

export function freshnessHistoryPath(businessId, id, opts) {
  validatePositiveId(id, 'policy')
  return `${businessApiPath(businessId, `configuration/freshness/${id}/history/`)}${listQuery(opts)}`
}
