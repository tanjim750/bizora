export function assessmentPayload(values) {
  const name = String(values.name || '').trim()
  const sku = String(values.sku || '').trim()
  const connectionId = String(values.connectionId || '').trim()
  const externalProductId = String(values.externalProductId || '').trim()
  if (!name || !sku) throw new Error('Name and SKU are required.')
  if (Boolean(connectionId) !== Boolean(externalProductId))
    throw new Error('Provide both the connection ID and external product ID for source assessment.')
  if (connectionId && !/^[1-9]\d*$/.test(connectionId))
    throw new Error('Connection ID must be a positive integer.')
  return {
    data: {
      name,
      sku,
      ...(externalProductId ? { external_reference: { external_product_id: externalProductId } } : {}),
    },
    ...(connectionId ? { connection_id: Number(connectionId) } : {}),
  }
}

export function reviewedMapping(assessment, selectedId, reason, payload) {
  const id = Number(selectedId)
  if (
    assessment?.decision !== 'REVIEW' ||
    !assessment.candidate_ids?.includes(id) ||
    !payload?.connection_id ||
    !payload.data?.external_reference?.external_product_id
  )
    throw new Error('Assess a source product and select one of its reviewed candidates first.')
  if (!String(reason || '').trim()) throw new Error('Record the evidence for this source mapping.')
  return {
    connection_id: payload.connection_id,
    data: {
      product: id,
      external_product_id: payload.data.external_reference.external_product_id,
      source_metadata: { review_reason: String(reason).trim(), review_source: 'frontend_assessment' },
    },
  }
}
