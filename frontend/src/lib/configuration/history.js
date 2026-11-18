import {
  sectionHistoryPath,
  resourceHistoryPath,
  connectionHistoryPath,
  sourceHistoryPath,
  freshnessHistoryPath,
  monitoringHistoryPath,
} from './paths.js'

export const CHANGE_KIND_LABELS = {
  PROFILE: 'Business profile',
  GENERAL: 'General settings',
  AI: 'AI assistant',
  KNOWLEDGE: 'Knowledge retrieval',
  RULE: 'Rule',
  POLICY: 'Policy',
  INTEGRATION: 'Connection',
  SOURCE: 'Knowledge source',
  FRESHNESS: 'Freshness policy',
  MONITORING: 'Monitoring settings',
}

export function kindLabel(kind) {
  if (kind && CHANGE_KIND_LABELS[kind]) {
    return CHANGE_KIND_LABELS[kind]
  }
  if (typeof kind === 'string' && kind.trim().length > 0) {
    return kind
  }
  return 'Unknown'
}

export function normalizeChange(row) {
  if (!row || typeof row !== 'object') {
    return {
      id: null,
      section: null,
      key: null,
      version: 0,
      actor_id: null,
      created_at: null,
      delivery_state: null,
    }
  }

  const idNum = row.id != null ? Number(row.id) : null
  const verNum = row.version != null ? Number(row.version) : 0
  const actorNum = row.actor_id != null ? Number(row.actor_id) : null

  return {
    id: isNaN(idNum) ? null : idNum,
    section: row.section != null ? String(row.section) : null,
    key: row.key != null ? String(row.key) : null,
    version: isNaN(verNum) || verNum < 0 ? 0 : verNum,
    actor_id: isNaN(actorNum) ? null : actorNum,
    created_at: row.created_at != null ? String(row.created_at) : null,
    delivery_state: row.delivery_state != null ? String(row.delivery_state) : null,
  }
}

export function itemLabel(change) {
  if (!change?.key || change.key === 'default') {
    return '—'
  }
  if (change.section === 'INTEGRATION') {
    return `Connection #${change.key}`
  }
  if (change.section === 'SOURCE') {
    return `Source #${change.key}`
  }
  if (change.section === 'FRESHNESS') {
    return `Policy #${change.key}`
  }
  return change.key
}

export function normalizeRevision(row) {
  if (!row || typeof row !== 'object') {
    return {
      id: null,
      key: null,
      kind: null,
      version: 0,
      status: null,
      valid_from: null,
      valid_to: null,
      settings: {},
      actor_id: null,
      reason: '',
      created_at: null,
    }
  }

  const idNum = row.id != null ? Number(row.id) : null
  const verNum = row.version != null ? Number(row.version) : 0
  const actorNum = row.actor_id != null ? Number(row.actor_id) : null

  return {
    id: isNaN(idNum) ? null : idNum,
    key: row.key != null ? String(row.key) : null,
    kind: row.kind != null ? String(row.kind) : null,
    version: isNaN(verNum) ? 0 : verNum,
    status: row.status != null ? String(row.status) : null,
    valid_from: row.valid_from != null ? String(row.valid_from) : null,
    valid_to: row.valid_to != null ? String(row.valid_to) : null,
    settings:
      row.settings && typeof row.settings === 'object' && !Array.isArray(row.settings) ? row.settings : {},
    actor_id: isNaN(actorNum) ? null : actorNum,
    reason: row.reason != null ? String(row.reason) : '',
    created_at: row.created_at != null ? String(row.created_at) : null,
  }
}

export function subjectFromChange(change) {
  if (!change?.section) return null
  const sec = String(change.section).toUpperCase()

  if (sec === 'MONITORING') {
    return { kind: 'monitoring', key: null }
  }
  if (['PROFILE', 'GENERAL', 'AI', 'KNOWLEDGE'].includes(sec)) {
    return { kind: 'section', key: sec.toLowerCase() }
  }
  if (sec === 'RULE') {
    return { kind: 'rules', key: change.key }
  }
  if (sec === 'POLICY') {
    return { kind: 'policies', key: change.key }
  }
  if (sec === 'INTEGRATION') {
    return { kind: 'connections', key: change.key }
  }
  if (sec === 'SOURCE') {
    return { kind: 'sources', key: change.key }
  }
  if (sec === 'FRESHNESS') {
    return { kind: 'freshness', key: change.key }
  }
  return null
}

export function historyPathFor(businessId, subject, opts) {
  if (!subject || !subject.kind) {
    throw new Error('Unknown history subject: ' + subject?.kind)
  }

  switch (subject.kind) {
    case 'section':
      return sectionHistoryPath(businessId, subject.key, opts)
    case 'monitoring':
      return monitoringHistoryPath(businessId, opts)
    case 'rules':
      return resourceHistoryPath(businessId, 'rules', subject.key, opts)
    case 'policies':
      return resourceHistoryPath(businessId, 'policies', subject.key, opts)
    case 'connections':
      return connectionHistoryPath(businessId, subject.key, opts)
    case 'sources':
      return sourceHistoryPath(businessId, subject.key, opts)
    case 'freshness':
      return freshnessHistoryPath(businessId, subject.key, opts)
    default:
      throw new Error('Unknown history subject: ' + subject.kind)
  }
}

export function flattenSettings(obj, prefix = '') {
  const result = {}
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) {
    return result
  }

  for (const [key, val] of Object.entries(obj)) {
    const fullPath = prefix ? `${prefix}.${key}` : key
    if (val && typeof val === 'object' && !Array.isArray(val)) {
      Object.assign(result, flattenSettings(val, fullPath))
    } else {
      result[fullPath] = val
    }
  }

  return result
}

export function diffSettings(before, after) {
  const flatBefore = flattenSettings(before)
  const flatAfter = flattenSettings(after)

  const allKeys = Array.from(new Set([...Object.keys(flatBefore), ...Object.keys(flatAfter)])).sort()
  const diffs = []

  for (const key of allKeys) {
    const hasBefore = Object.prototype.hasOwnProperty.call(flatBefore, key)
    const hasAfter = Object.prototype.hasOwnProperty.call(flatAfter, key)

    if (hasBefore && !hasAfter) {
      diffs.push({
        path: key,
        before: flatBefore[key],
        change: 'removed',
      })
    } else if (!hasBefore && hasAfter) {
      diffs.push({
        path: key,
        after: flatAfter[key],
        change: 'added',
      })
    } else {
      const bVal = flatBefore[key]
      const aVal = flatAfter[key]
      if (JSON.stringify(bVal) !== JSON.stringify(aVal)) {
        diffs.push({
          path: key,
          before: bVal,
          after: aVal,
          change: 'changed',
        })
      }
    }
  }

  return diffs
}

export function formatDiffValue(value) {
  if (value === undefined || value === null || value === '') {
    return '—'
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No'
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return '(empty list)'
    return value.join(', ')
  }
  const str = String(value)
  if (str.length > 80) {
    return str.slice(0, 77) + '...'
  }
  return str
}

export function withDiffs(revisions) {
  if (!Array.isArray(revisions)) return []

  return revisions.map((rev, idx) => {
    const ver = rev.version ?? 0
    if (ver <= 1) {
      return {
        ...rev,
        diff: diffSettings({}, rev.settings),
        note: 'First saved version',
      }
    }

    const nextOlder = revisions[idx + 1]
    if (nextOlder) {
      return {
        ...rev,
        diff: diffSettings(nextOlder.settings, rev.settings),
        note: null,
      }
    }

    return {
      ...rev,
      diff: null,
      note: 'The earlier version is on the next page.',
    }
  })
}
