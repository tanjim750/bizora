import test from 'node:test'
import assert from 'node:assert/strict'
import { businessApiPath, businessPath, detailPath } from '../src/lib/catalog.js'
import { label, statusText, statusTone } from '../src/lib/format.js'
import { errorMessage } from '../src/lib/clientApi.js'

test('business paths stay scoped and reject invalid identifiers', () => {
  assert.equal(businessApiPath(4, 'orders/'), 'businesses/4/orders/')
  assert.equal(businessPath(4, 'orders'), '/business/4/orders')
  assert.equal(detailPath(4, 'orders', 9), '/business/4/records/orders/9')
  assert.throws(() => businessApiPath('bad', 'orders/'))
})

test('statuses distinguish pending provider work and unmounted services', () => {
  assert.equal(statusText({ direction: 'OUTGOING', delivery_status: 'PENDING' }), 'Pending — not delivered')
  assert.equal(statusTone('Not mounted'), 'not-mounted')
  assert.equal(statusTone('Unavailable'), 'unavailable')
  assert.equal(statusTone('AI suggestion'), 'ai')
  assert.equal(label('merge_candidates'), 'Merge Candidates')
})

test('validation errors keep the field and a readable message', () => {
  assert.equal(
    errorMessage({ amount: ['Must be greater than zero.'] }, 400),
    'amount: Must be greater than zero.',
  )
  assert.equal(errorMessage({ detail: 'Access denied.' }, 403), 'Access denied.')
})
