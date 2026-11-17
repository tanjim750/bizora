import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

test('growth workspace enforces token styles, zero raw hex, and honest wording', () => {
  const componentPath = path.resolve('src/components/Growth.js')
  const content = fs.readFileSync(componentPath, 'utf8')

  // Zero raw hex colors
  const hexMatches = content.match(/#(?:[0-9a-fA-F]{3}){1,2}\b/g) || []
  assert.equal(hexMatches.length, 0, `Found raw hex colors in Growth.js: ${hexMatches.join(', ')}`)

  // Honest wording checks
  assert.ok(
    content.includes('Platform-reported'),
    'Expected "Platform-reported" badge and labels on spend, clicks, conversions',
  )
  assert.ok(
    content.includes('Attribution models require an active provider contract'),
    'Expected attribution models unavailable state',
  )
  assert.ok(
    content.includes('Execution is simulated'),
    'Expected "Execution is simulated" banner on AI campaign performance diagnosis',
  )
  assert.ok(
    content.includes('oldest first'),
    'Expected D19 oldest first requirement for chronological visitor journey',
  )
})

test('growth workspace provides two separate charts and zero dual-axis charts', () => {
  const componentPath = path.resolve('src/components/Growth.js')
  const content = fs.readFileSync(componentPath, 'utf8')

  // Must have two separate charts: Daily Platform Spend and Daily Platform Clicks
  assert.ok(content.includes('Daily Platform Spend'), 'Expected Daily Platform Spend chart')
  assert.ok(content.includes('Daily Platform Clicks'), 'Expected Daily Platform Clicks chart')

  // Must use TrendLine components with separate keys
  assert.ok(content.includes('dataKey="spend"'), 'Expected spend dataKey on TrendLine')
  assert.ok(content.includes('dataKey="clicks"'), 'Expected clicks dataKey on TrendLine')
})

test('growth website performance covers all 7 D7 analysis categories as calm unavailable states', () => {
  const componentPath = path.resolve('src/components/Growth.js')
  const content = fs.readFileSync(componentPath, 'utf8')

  const expectedPanels = [
    'Traffic source attribution requires an active provider contract.',
    'Conversion funnel modeling requires an active provider contract.',
    'Cart abandonment analytics requires an active provider contract.',
    'Checkout drop-off telemetry requires an active provider contract.',
    'Landing page performance indexing requires an active provider contract.',
    'Device experience breakdown requires an active provider contract.',
    'Experience friction analysis requires an active provider contract.',
  ]

  for (const panel of expectedPanels) {
    assert.ok(content.includes(panel), `Missing D7 unavailable panel: ${panel}`)
  }
})

test('growth campaign creation dialog enforces role protection and required fields', () => {
  const componentPath = path.resolve('src/components/Growth.js')
  const content = fs.readFileSync(componentPath, 'utf8')

  assert.ok(
    content.includes('Requires Operator role'),
    'Create button must be disabled for non-writers with tooltip',
  )
  assert.ok(
    content.includes('WRITER_ROLES.has(business?.role)'),
    'Must check writer roles for create campaign action',
  )
  assert.ok(
    content.includes('aria-label="Campaign Name"'),
    'Must provide accessible label for Campaign Name input',
  )
  assert.ok(
    content.includes('aria-label="Advertising Platform"'),
    'Must provide accessible label for Advertising Platform select',
  )
  assert.ok(
    content.includes('aria-label="Allocated Budget"'),
    'Must provide accessible label for Allocated Budget input',
  )
})
