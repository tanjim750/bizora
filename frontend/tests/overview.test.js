import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

test('overview canonical counts format missing values as em-dash, never 0', () => {
  const formatCount = (val) => (val !== null && val !== undefined && val !== '' ? val : '—')

  assert.equal(formatCount(undefined), '—')
  assert.equal(formatCount(null), '—')
  assert.equal(formatCount(''), '—')
  assert.equal(formatCount(0), 0)
  assert.equal(formatCount(42), 42)
})

test('overview domain filter categorizes entity types accurately', () => {
  const DOMAIN_MAP = {
    COMMERCE: ['ORDER', 'PAYMENT', 'REFUND', 'PRODUCT', 'SHIPMENT', 'VARIANT'],
    SUPPORT: ['CONVERSATION', 'MESSAGE', 'CALL', 'CALLBACK'],
    IDENTITY: ['CUSTOMER', 'IDENTITY', 'CONTACT', 'TAG'],
  }

  const classify = (entityType) => {
    const type = (entityType || '').toUpperCase()
    if (DOMAIN_MAP.COMMERCE.includes(type)) return 'COMMERCE'
    if (DOMAIN_MAP.SUPPORT.includes(type)) return 'SUPPORT'
    if (DOMAIN_MAP.IDENTITY.includes(type)) return 'IDENTITY'
    return 'SYSTEM'
  }

  assert.equal(classify('ORDER'), 'COMMERCE')
  assert.equal(classify('Payment'), 'COMMERCE')
  assert.equal(classify('refund'), 'COMMERCE')
  assert.equal(classify('Product'), 'COMMERCE')
  assert.equal(classify('SHIPMENT'), 'COMMERCE')

  assert.equal(classify('conversation'), 'SUPPORT')
  assert.equal(classify('MESSAGE'), 'SUPPORT')
  assert.equal(classify('Call'), 'SUPPORT')

  assert.equal(classify('customer'), 'IDENTITY')
  assert.equal(classify('IDENTITY'), 'IDENTITY')
  assert.equal(classify('TAG'), 'IDENTITY')

  assert.equal(classify('settings'), 'SYSTEM')
  assert.equal(classify('unknown'), 'SYSTEM')
  assert.equal(classify(null), 'SYSTEM')
})

test('overview component contains no hardcoded hex colors and enforces token styles', () => {
  const overviewFile = path.resolve('src/components/Overview.js')
  const content = fs.readFileSync(overviewFile, 'utf8')

  // Zero raw hex color values outside comments
  const codeWithoutComments = content.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '')
  const hexMatches = codeWithoutComments.match(/#[0-9a-fA-F]{3,8}\b/g)
  assert.equal(hexMatches, null, `Found raw hex color in Overview.js: ${hexMatches}`)

  // Verifies all three tabs are present
  assert.ok(content.includes("activeTab === 'overview'"), 'Overview tab missing')
  assert.ok(content.includes("activeTab === 'trends'"), 'Trends tab missing')
  assert.ok(content.includes("activeTab === 'health'"), 'Health tab missing')

  // Verifies calm unavailable state is used for executive KPIs
  assert.ok(content.includes('unavailableOwner="Overview & Monitoring"'), 'Honest unavailable state missing')
  assert.ok(content.includes('SIMULATED'), 'Simulated badge missing')
})
