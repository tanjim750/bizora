import { businessApiPath } from '../catalog.js'
import { enumLabel } from '../format/text.js'
import {
  GRAPH_ENTITY_TYPES,
  GRAPH_RELATIONSHIP_TYPES,
  parseGraphEntityId,
  graphFilterParams,
  graphNodeLabel,
} from './graphExplore.js'
import { buildGraphView } from './graph.js'
import { confidencePercent } from './facts.js'

export const QUERY_LIMIT_DEFAULT = 100
export const QUERY_LIMIT_MAX = 1000
export const QUERY_ROW_CAP = 200

export function graphQueryPath(businessId, options = {}) {
  const base = businessApiPath(businessId, 'graph/query/')
  const { entityType, entityId, relationshipType, limit = QUERY_LIMIT_DEFAULT, minConfidence } = options

  const hasType = entityType !== undefined && entityType !== null && String(entityType).trim() !== ''
  const hasId = entityId !== undefined && entityId !== null && String(entityId).trim() !== ''

  if ((hasType && !hasId) || (!hasType && hasId)) {
    throw new Error('Choose an entity type and an entity ID together, or leave both empty.')
  }

  const fragments = []

  if (hasType && hasId) {
    if (!GRAPH_ENTITY_TYPES.includes(entityType)) {
      throw new Error(`Invalid entity type: ${entityType}`)
    }
    const parsedId = parseGraphEntityId(entityId, 'Entity ID')
    fragments.push(`entity_type=${entityType}`)
    fragments.push(`entity_id=${parsedId}`)
  }

  if (relationshipType !== undefined && relationshipType !== null && String(relationshipType).trim() !== '') {
    if (!GRAPH_RELATIONSHIP_TYPES.includes(relationshipType)) {
      throw new Error(`Invalid relationship type: ${relationshipType}`)
    }
    fragments.push(`relationship_type=${relationshipType}`)
  }

  if (typeof limit !== 'number' || !Number.isInteger(limit) || limit < 1 || limit > QUERY_LIMIT_MAX) {
    throw new Error('Limit must be a whole number between 1 and 1000.')
  }
  fragments.push(`limit=${limit}`)

  const extra = graphFilterParams({ minConfidence })
  fragments.push(...extra)

  return `${base}?${fragments.join('&')}`
}

export function describeGraphQuery(options = {}) {
  const { entityType, entityId, relationshipType, limit = QUERY_LIMIT_DEFAULT, minConfidence } = options
  const effLimit = limit ?? QUERY_LIMIT_DEFAULT

  const hasType = entityType !== undefined && entityType !== null && String(entityType).trim() !== ''
  const hasId = entityId !== undefined && entityId !== null && String(entityId).trim() !== ''

  if (hasType && hasId) {
    let desc = `Everything within 2 hops of ${enumLabel(entityType)} ${entityId}, in both directions, up to ${effLimit} nodes`
    if (relationshipType && String(relationshipType).trim()) {
      desc += `, following only ${relationshipType} relationships`
    }
    if (minConfidence !== undefined && minConfidence !== null && String(minConfidence).trim() !== '') {
      desc += `, ignoring relationships below ${String(minConfidence).trim()} confidence`
    }
    desc += '.'
    return desc
  }

  let desc = `Up to ${effLimit} relationships`
  if (relationshipType && String(relationshipType).trim()) {
    desc += ` of type ${relationshipType}`
  }
  desc += ` in this business, with the entities they connect`
  if (minConfidence !== undefined && minConfidence !== null && String(minConfidence).trim() !== '') {
    desc += `, ignoring relationships below ${String(minConfidence).trim()} confidence`
  }
  desc += '.'
  return desc
}

export function normalizeGraphQuery(data) {
  if (!data || typeof data !== 'object') {
    return {
      nodes: [],
      edges: [],
      truncated: false,
      hiddenEdges: 0,
      nodeCount: 0,
      edgeCount: 0,
      depthReached: null,
      rootNodeId: null,
    }
  }

  const view = buildGraphView(data)
  const nodes = view.nodes.map((node) => ({
    id: node.id,
    entityType: node.entity_type,
    entityId: node.entity_id,
    label: graphNodeLabel(node),
  }))

  const edges = view.edges.map((e) => ({
    id: e.id,
    relationshipType: e.relationship_type || 'Unknown',
    sourceLabel: e.sourceLabel,
    targetLabel: e.targetLabel,
    confidencePercent: confidencePercent(e.confidence),
  }))

  const truncated = view.truncated === true
  const hiddenEdges = typeof view.hiddenEdges === 'number' ? view.hiddenEdges : 0
  const nodeCount = Number.isInteger(data.node_count) ? data.node_count : nodes.length
  const edgeCount = Number.isInteger(data.edge_count) ? data.edge_count : edges.length
  const depthReached = Number.isInteger(data.depth_reached) ? data.depth_reached : null
  const rootNodeId = Number.isInteger(data.root_node_id) && data.root_node_id > 0 ? data.root_node_id : null

  return {
    nodes,
    edges,
    truncated,
    hiddenEdges,
    nodeCount,
    edgeCount,
    depthReached,
    rootNodeId,
  }
}
