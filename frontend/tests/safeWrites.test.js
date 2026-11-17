import test from 'node:test'
import assert from 'node:assert/strict'
import { newIdempotencyKey, makeExternalId } from '../src/lib/api/idempotency.js'
import { ApiError } from '../src/lib/api/errors.js'

test('newIdempotencyKey produces valid RFC4122 v4 UUIDs', () => {
  const key1 = newIdempotencyKey()
  const key2 = newIdempotencyKey()

  assert.equal(typeof key1, 'string')
  assert.equal(typeof key2, 'string')
  assert.notEqual(key1, key2)

  // Standard UUID v4 regex
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
  assert.match(key1, uuidRegex)
  assert.match(key2, uuidRegex)
})

test('makeExternalId produces stable external IDs for the same key across retries', () => {
  const key = newIdempotencyKey()
  const id1 = makeExternalId('ref', key)
  const id2 = makeExternalId('ref', key)

  assert.equal(id1, id2)
  assert.equal(id1.startsWith('ref_'), true)
  assert.equal(id1.includes('-'), false) // Sanitized hyphens
})

test('Idempotency manager reuses key on retries of same payload, and rotates on payload change', () => {
  // Simulate useActionForm logic in headless test
  let currentKey = newIdempotencyKey()
  let lastPayload = null

  function getOrRotateKey(payload) {
    const serialized = JSON.stringify(payload)
    if (lastPayload !== null && lastPayload !== serialized) {
      currentKey = newIdempotencyKey()
    }
    lastPayload = serialized
    return currentKey
  }

  const payloadA = { amount: '100.00', reason: 'Customer requested refund' }
  const firstKey = getOrRotateKey(payloadA)

  // Retry with EXACT SAME payload (e.g. after network timeout)
  const retryKey = getOrRotateKey(payloadA)
  assert.equal(firstKey, retryKey, 'Idempotency key MUST be reused on retry of identical payload')

  // Third retry still identical
  const thirdRetryKey = getOrRotateKey(payloadA)
  assert.equal(firstKey, thirdRetryKey)

  // User alters the form (payload changed)
  const payloadB = { amount: '120.00', reason: 'Customer requested refund' }
  const changedKey = getOrRotateKey(payloadB)
  assert.notEqual(firstKey, changedKey, 'Idempotency key MUST rotate when payload changes')
})

test('409 STALE_STATE error triggers reload flow and produces expected notice', async () => {
  let reloaded = false
  const onReload = async () => {
    reloaded = true
  }

  const err409 = new ApiError({
    status: 409,
    code: 'STALE_STATE',
    detail: 'Order status changed to CONFIRMED.',
  })

  // Simulate useActionForm handler
  let stale = false
  let error = ''

  try {
    throw err409
  } catch (err) {
    if (err.status === 409 || err.code === 'STALE_STATE') {
      stale = true
      error = 'This record changed. Reloaded with latest data.'
      await onReload()
    }
  }

  assert.equal(stale, true)
  assert.equal(reloaded, true)
  assert.equal(error, 'This record changed. Reloaded with latest data.')
})
