import { businessApiPath } from '../catalog.js'

export const ENTITY_KINDS = {
  customer: 'CUSTOMER',
  order: 'ORDER',
  product: 'PRODUCT',
  conversation: 'CONVERSATION',
  shipment: 'SHIPMENT',
}

export const REBUILD_BODY = { clean: false }

const ALLOWED_DIRECTIONS = new Set(['OUTBOUND', 'INBOUND', 'BIDIRECTIONAL'])
const MAX_BIGINT = 9223372036854775807n

export function traversalPath(
  businessId,
  kind,
  entityId,
  { direction = 'BIDIRECTIONAL', maxDepth = 2, maxNodes = 100 } = {},
) {
  if (!kind || !Object.prototype.hasOwnProperty.call(ENTITY_KINDS, kind)) {
    throw new Error(`Invalid entity kind: ${kind}`)
  }
  let idBig
  try {
    idBig = BigInt(entityId)
  } catch {
    throw new Error('Invalid entity ID')
  }
  if (idBig <= 0n || idBig > MAX_BIGINT) {
    throw new Error('Invalid entity ID')
  }
  if (!ALLOWED_DIRECTIONS.has(direction)) {
    throw new Error(`Invalid direction: ${direction}`)
  }
  if (!Number.isInteger(maxDepth) || maxDepth < 0 || maxDepth > 5) {
    throw new Error('maxDepth must be an integer between 0 and 5')
  }
  if (!Number.isInteger(maxNodes) || maxNodes < 1 || maxNodes > 1000) {
    throw new Error('maxNodes must be an integer between 1 and 1000')
  }

  const base = businessApiPath(businessId, 'graph/traversal/')
  const type = ENTITY_KINDS[kind]
  return `${base}?root_entity_type=${encodeURIComponent(type)}&root_entity_id=${entityId}&direction=${encodeURIComponent(direction)}&max_depth=${maxDepth}&max_nodes=${maxNodes}`
}

export function buildGraphView(data) {
  const nodes = Array.isArray(data?.nodes) ? data.nodes : []
  const rawEdges = Array.isArray(data?.edges) ? data.edges : []
  const truncated = Boolean(data?.truncated)

  const nodeMap = new Map()
  for (const n of nodes) {
    nodeMap.set(n.id, n)
  }

  const edges = []
  let hiddenEdges = 0

  for (const edge of rawEdges) {
    const sourceNode = nodeMap.get(edge.source_node_id)
    const targetNode = nodeMap.get(edge.target_node_id)
    if (!sourceNode || !targetNode) {
      hiddenEdges += 1
      continue
    }
    const sourceLabel = sourceNode.label || `${sourceNode.entity_type} #${sourceNode.entity_id}`
    const targetLabel = targetNode.label || `${targetNode.entity_type} #${targetNode.entity_id}`
    edges.push({
      ...edge,
      sourceLabel,
      targetLabel,
    })
  }

  return {
    nodes,
    edges,
    truncated,
    hiddenEdges,
  }
}

export function graphErrorKind(error) {
  if (error?.code === 'GRAPH_NOT_BUILT' || (error?.status === 409 && error?.code === 'GRAPH_NOT_BUILT')) {
    return 'not_built'
  }
  if (error?.status === 404) {
    return 'not_found'
  }
  if (error?.status === 400) {
    return 'invalid'
  }
  return 'other'
}
