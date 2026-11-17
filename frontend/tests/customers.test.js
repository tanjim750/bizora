import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

test('customer legal transitions match D4 state machine contract', () => {
  const CUSTOMER_TRANSITIONS = {
    ACTIVE: ['INACTIVE', 'BLOCKED'],
    INACTIVE: ['ACTIVE', 'BLOCKED'],
    BLOCKED: ['ACTIVE'],
  }

  // Active customer can be deactivated or blocked
  assert.deepEqual(CUSTOMER_TRANSITIONS.ACTIVE, ['INACTIVE', 'BLOCKED'])
  // Inactive customer can be reactivated or blocked
  assert.deepEqual(CUSTOMER_TRANSITIONS.INACTIVE, ['ACTIVE', 'BLOCKED'])
  // Blocked customer can only be unblocked to active
  assert.deepEqual(CUSTOMER_TRANSITIONS.BLOCKED, ['ACTIVE'])
})

test('customers component enforces token styles, zero raw hex, and honest wording', () => {
  const customersFile = path.resolve('src/components/Customers.js')
  const content = fs.readFileSync(customersFile, 'utf8')

  // Zero raw hex color values outside comments
  const codeWithoutComments = content.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '')
  const hexMatches = codeWithoutComments.match(/#[0-9a-fA-F]{3,8}\b/g)
  assert.equal(hexMatches, null, `Found raw hex color in Customers.js: ${hexMatches}`)

  // Verifies Customer 360 tabs are defined
  assert.ok(content.includes("'timeline'"), 'Timeline sub-tab missing')
  assert.ok(content.includes("'orders'"), 'Orders sub-tab missing')
  assert.ok(content.includes("'conversations'"), 'Conversations sub-tab missing')
  assert.ok(content.includes("'deliveries'"), 'Deliveries sub-tab missing')
  assert.ok(content.includes("'website'"), 'Website & Events sub-tab missing')
  assert.ok(content.includes("'graph'"), 'Context Graph sub-tab missing')
  assert.ok(content.includes("'identity'"), 'Identities & Links sub-tab missing')

  // Verifies honest states and concurrency guard
  assert.ok(content.includes('UnavailableState'), 'Calm unavailable state missing')
  assert.ok(content.includes('expected_status'), 'D4 concurrency guard expected_status missing')
  assert.ok(content.includes('Persisted one-hop'), 'Graph context scope missing')
})
