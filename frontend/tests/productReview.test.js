import test from 'node:test'
import assert from 'node:assert/strict'
import { assessmentPayload, reviewedMapping } from '../src/lib/productReview.js'

test('source assessment requires a complete scoped source identity', () => {
  assert.deepEqual(assessmentPayload({ name: ' Tea ', sku: ' T1 ' }), {
    data: { name: 'Tea', sku: 'T1' },
  })
  assert.deepEqual(
    assessmentPayload({ name: 'Tea', sku: 'T1', connectionId: '4', externalProductId: 'remote-1' }),
    {
      connection_id: 4,
      data: { name: 'Tea', sku: 'T1', external_reference: { external_product_id: 'remote-1' } },
    },
  )
  assert.throws(() => assessmentPayload({ name: 'Tea', sku: 'T1', connectionId: '4' }))
  assert.throws(() =>
    assessmentPayload({ name: 'Tea', sku: 'T1', connectionId: '0', externalProductId: 'x' }),
  )
})

test('reviewed mapping accepts only a returned candidate with evidence', () => {
  const payload = assessmentPayload({
    name: 'Tea',
    sku: 'T1',
    connectionId: '4',
    externalProductId: 'remote-1',
  })
  const assessment = { decision: 'REVIEW', candidate_ids: [7, 9] }
  assert.deepEqual(reviewedMapping(assessment, '9', ' Same manufacturer ', payload), {
    connection_id: 4,
    data: {
      product: 9,
      external_product_id: 'remote-1',
      source_metadata: { review_reason: 'Same manufacturer', review_source: 'frontend_assessment' },
    },
  })
  assert.throws(() => reviewedMapping(assessment, '8', 'Evidence', payload))
  assert.throws(() => reviewedMapping(assessment, '7', ' ', payload))
  assert.throws(() => reviewedMapping({ decision: 'REUSE', candidate_ids: [7] }, '7', 'Evidence', payload))
})
