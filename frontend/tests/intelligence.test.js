import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

test('intelligence workspace enforces token styles, zero raw hex, and honest wording', () => {
  const file = path.resolve('src/components/Intelligence.js')
  const content = fs.readFileSync(file, 'utf8')

  // Zero raw hex color values outside comments
  const codeWithoutComments = content.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '')
  const hexMatches = codeWithoutComments.match(/#[0-9a-fA-F]{3,8}\b/g)
  assert.equal(hexMatches, null, `Found raw hex color in Intelligence.js: ${hexMatches}`)

  // Verifies all four tabs are supported
  assert.ok(content.includes("activeTab === 'facts'"), 'Facts tab missing')
  assert.ok(content.includes("activeTab === 'graph'"), 'Graph tab missing')
  assert.ok(content.includes("activeTab === 'metrics'"), 'Metrics tab missing')
  assert.ok(content.includes("activeTab === 'pipeline'"), 'Pipeline tab missing')

  // Verifies honest states and unmounted service ownership
  assert.ok(content.includes('UnavailableState'), 'Calm unavailable state missing')
  assert.ok(content.includes('Business Intelligence'), 'Business Intelligence owner missing')
  assert.ok(content.includes('Business Graph'), 'Business Graph owner missing')
  assert.ok(content.includes('Run data pipeline'), 'Run data pipeline action missing')
})

test('intelligence graph legend differentiates by shape and icon, not color alone', () => {
  const file = path.resolve('src/components/Intelligence.js')
  const content = fs.readFileSync(file, 'utf8')

  // Shape indicators in legend
  assert.ok(content.includes('circle'), 'Circle symbol missing')
  assert.ok(content.includes('diamond'), 'Diamond symbol missing')
  assert.ok(content.includes('square'), 'Square symbol missing')
  assert.ok(content.includes('hexagon'), 'Hexagon symbol missing')

  // Icons used alongside shapes
  assert.ok(content.includes('User'), 'User icon missing')
  assert.ok(content.includes('ShoppingBag'), 'ShoppingBag icon missing')
  assert.ok(content.includes('Package'), 'Package icon missing')
  assert.ok(content.includes('Shield'), 'Shield icon missing')

  // One-hop graph context endpoint
  assert.ok(
    content.includes('graph-context/${graphKind}/${graphEntityId.trim()}'),
    'D22 graph-context endpoint missing',
  )

  // Sample data toggle
  assert.ok(content.includes('Sample data (SIMULATED)'), 'Sample data switch missing')
})
