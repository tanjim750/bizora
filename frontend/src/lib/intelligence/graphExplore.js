import { businessApiPath } from '../catalog.js'
import { confidencePercent } from './facts.js'
import { graphErrorKind } from './graph.js'

export const GRAPH_ENTITY_TYPES = Object.freeze([
  'CUSTOMER',
  'PRODUCT',
  'PRODUCT_VARIANT',
  'ORDER',
  'PAYMENT',
  'SHIPMENT',
  'CAMPAIGN',
  'CAMPAIGN_CONVERSION',
  'WEBSITE_VISITOR',
  'WEBSITE_SESSION',
  'WEBSITE_EVENT',
  'CONVERSATION',
  'MESSAGE',
  'CALL',
])

export const GRAPH_RELATIONSHIP_TYPES = Object.freeze([
  'PLACED_ORDER',
  'CONTAINS_PRODUCT',
  'CONTAINS_VARIANT',
  'HAS_PAYMENT',
  'HAS_SHIPMENT',
  'HAS_CONVERSATION',
  'HAS_MESSAGE',
  'HAS_CALL',
  'HAS_VISITOR',
  'HAS_SESSION',
  'HAS_EVENT',
  'HAS_WEBSITE_EVENT',
  'REFERENCES_PRODUCT',
  'REFERENCES_ORDER',
  'HAS_REPORTED_CONVERSION',
  'REPORTED_CUSTOMER',
  'REPORTED_ORDER',
  'REPORTED_SESSION',
])

export const GRAPH_DIRECTIONS = Object.freeze(['BIDIRECTIONAL', 'OUTBOUND', 'INBOUND'])

export const GRAPH_DIRECTION_LABELS = Object.freeze({
  BIDIRECTIONAL: 'Either direction',
  OUTBOUND: 'Start to end only',
  INBOUND: 'End to start only',
})

export const PATH_MAX_HOPS = 5
export const PATH_RESULT_LIMIT = 10
export const GRAPH_ID_MAX = '9223372036854775807'

export function parseGraphEntityId(value, label = 'Entity ID') {
  const errMsg = `${label} must be a whole number between 1 and 9223372036854775807.`
  if (value === null || value === undefined || typeof value === 'boolean') {
    throw new Error(errMsg)
  }
  let str = ''
  if (typeof value === 'number') {
    if (!Number.isSafeInteger(value)) {
      throw new Error(errMsg)
    }
    str = String(value)
  } else if (typeof value === 'string') {
    str = value.trim()
  } else {
    throw new Error(errMsg)
  }

  if (!/^\d+$/.test(str)) {
    throw new Error(errMsg)
  }

  try {
    const b = BigInt(str)
    if (b < 1n || b > 9223372036854775807n) {
      throw new Error(errMsg)
    }
    return b.toString()
  } catch (err) {
    if (err.message === errMsg) throw err
    throw new Error(errMsg)
  }
}

export function graphFilterParams({ minConfidence, relationshipTypes } = {}) {
  const fragments = []

  if (minConfidence !== undefined && minConfidence !== null && String(minConfidence).trim() !== '') {
    const trimmed = String(minConfidence).trim()
    const num = Number(trimmed)
    if (!Number.isFinite(num) || num < 0 || num > 1) {
      throw new Error('Minimum confidence must be a number between 0 and 1.')
    }
    fragments.push(`min_confidence=${String(num)}`)
  }

  if (relationshipTypes !== undefined && relationshipTypes !== null) {
    if (!Array.isArray(relationshipTypes)) {
      throw new Error('Relationship types must be a list.')
    }
    const deduped = []
    for (const item of relationshipTypes) {
      const normalized = String(item).trim().toUpperCase()
      if (!GRAPH_RELATIONSHIP_TYPES.includes(normalized)) {
        throw new Error(`Unknown relationship type: ${item}`)
      }
      if (!deduped.includes(normalized)) {
        deduped.push(normalized)
      }
    }
    if (deduped.length > 0) {
      fragments.push(`relationship_types=${deduped.join(',')}`)
    }
  }

  return fragments
}

export function pathSearchPath(businessId, options = {}) {
  const base = businessApiPath(businessId, 'graph/paths/')
  const {
    startType,
    startId,
    endType,
    endId,
    direction = 'BIDIRECTIONAL',
    maxDepth = 3,
    explain = false,
    minConfidence,
    relationshipTypes,
  } = options

  if (!GRAPH_ENTITY_TYPES.includes(startType)) {
    throw new Error(`Invalid start entity type: ${startType}`)
  }
  if (!GRAPH_ENTITY_TYPES.includes(endType)) {
    throw new Error(`Invalid end entity type: ${endType}`)
  }

  const parsedStartId = parseGraphEntityId(startId, 'Start ID')
  const parsedEndId = parseGraphEntityId(endId, 'End ID')

  if (!GRAPH_DIRECTIONS.includes(direction)) {
    throw new Error(`Invalid direction: ${direction}`)
  }

  if (
    typeof maxDepth !== 'number' ||
    !Number.isInteger(maxDepth) ||
    maxDepth < 1 ||
    maxDepth > PATH_MAX_HOPS
  ) {
    throw new Error('Maximum hops must be a whole number between 1 and 5.')
  }

  if (typeof explain !== 'boolean') {
    throw new Error('explain must be true or false.')
  }

  const fragments = [
    `start_entity_type=${startType}`,
    `start_entity_id=${parsedStartId}`,
    `end_entity_type=${endType}`,
    `end_entity_id=${parsedEndId}`,
    `direction=${direction}`,
    `max_depth=${maxDepth}`,
  ]

  if (explain === true) {
    fragments.push('explain=true')
  }

  const extra = graphFilterParams({ minConfidence, relationshipTypes })
  fragments.push(...extra)

  return `${base}?${fragments.join('&')}`
}

export function graphNodeLabel(node) {
  if (!node || typeof node !== 'object') {
    return 'Unknown entity'
  }
  if (typeof node.label === 'string' && node.label.trim()) {
    return node.label.trim()
  }
  if (node.entity_type && node.entity_id !== null && node.entity_id !== undefined) {
    return `${node.entity_type} #${node.entity_id}`
  }
  return 'Unknown entity'
}

export function normalizePathSearch(data) {
  if (!data || typeof data !== 'object' || !Array.isArray(data.paths)) {
    return { pathsFound: 0, mayHaveMore: false, paths: [] }
  }

  const normalizedPaths = []
  for (const p of data.paths) {
    if (!p || typeof p !== 'object') continue

    const hasExplanation = Array.isArray(p.explanation) && p.explanation.length > 0
    const steps = []

    if (hasExplanation) {
      for (const item of p.explanation) {
        if (!item || typeof item !== 'object' || !item.node || typeof item.node !== 'object') {
          continue
        }
        const n = item.node
        const node = {
          id: n.id,
          type: n.entity_type,
          entityId: n.entity_id,
          label: graphNodeLabel(n),
        }

        let edge = null
        if (item.edge && typeof item.edge === 'object') {
          const e = item.edge
          const ev = e.evidence && typeof e.evidence === 'object' ? e.evidence : {}
          edge = {
            id: e.id,
            relationshipType: e.relationship_type,
            confidencePercent: confidencePercent(e.confidence),
            ruleKey: ev.rule_key ?? null,
            source: ev.relationship_source ?? null,
            validFrom: ev.valid_from ?? null,
            validTo: ev.valid_to ?? null,
          }
        }

        const facts = Array.isArray(n.facts)
          ? n.facts
              .filter((f) => f && typeof f === 'object')
              .map((f) => ({
                id: f.fact_id,
                factType: f.fact_type,
                statement: f.statement,
                status: f.status,
              }))
          : []

        const issues = Array.isArray(n.issues)
          ? n.issues
              .filter((iss) => iss && typeof iss === 'object')
              .map((iss) => ({
                id: iss.issue_id,
                issueType: iss.issue_type,
                title: iss.title,
                severity: iss.severity,
                status: iss.status,
              }))
          : []

        steps.push({ node, edge, facts, issues })
      }
    } else {
      const nodes = Array.isArray(p.nodes) ? p.nodes : []
      const edges = Array.isArray(p.edges) ? p.edges : []
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i]
        const node = {
          id: n?.id,
          type: n?.entity_type,
          entityId: n?.entity_id,
          label: graphNodeLabel(n),
        }

        let edge = null
        if (i < edges.length && edges[i] && typeof edges[i] === 'object') {
          const e = edges[i]
          edge = {
            id: e.id,
            relationshipType: e.relationship_type,
            confidencePercent: null,
            ruleKey: null,
            source: null,
            validFrom: null,
            validTo: null,
          }
        }

        steps.push({ node, edge, facts: [], issues: [] })
      }
    }

    const length = Number.isInteger(p.length) ? p.length : Math.max(0, steps.length - 1)
    normalizedPaths.push({
      length,
      explained: hasExplanation,
      steps,
    })
  }

  const pathsFound = Number.isInteger(data.paths_found) ? data.paths_found : normalizedPaths.length
  const mayHaveMore = normalizedPaths.length >= PATH_RESULT_LIMIT

  return { pathsFound, mayHaveMore, paths: normalizedPaths }
}

export function graphErrorMessage(error, { notFound } = {}) {
  if (error?.status === 403) {
    return 'You do not have access to this business graph.'
  }
  const kind = graphErrorKind(error)
  if (kind === 'not_built') {
    return 'The business graph has not been built yet. An owner or manager can rebuild it from the Data Pipeline tab.'
  }
  if (kind === 'not_found') {
    if (typeof notFound === 'string' && notFound.trim()) {
      return notFound
    }
    return 'Nothing was found in the graph for that request. If the record is new, rebuild the graph first.'
  }
  if (kind === 'invalid') {
    if (typeof error?.detail === 'string' && error.detail.trim()) {
      return error.detail
    }
    return 'The request was not accepted by the server.'
  }
  if (typeof error?.detail === 'string' && error.detail.trim()) {
    return error.detail
  }
  if (typeof error?.message === 'string' && error.message.trim()) {
    return error.message
  }
  return 'The graph request failed. Try again.'
}
