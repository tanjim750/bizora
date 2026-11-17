import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

test('admin workspace enforces token styles, zero raw hex, and honest wording', () => {
  const componentPath = path.resolve('src/components/Admin.js')
  const content = fs.readFileSync(componentPath, 'utf8')

  // Zero raw hex colors
  const hexMatches = content.match(/#(?:[0-9a-fA-F]{3}){1,2}\b/g) || []
  assert.equal(hexMatches.length, 0, `Found raw hex colors in Admin.js: ${hexMatches.join(', ')}`)

  // Honest wording checks
  assert.ok(
    content.includes('Blocked by design.'),
    'Expected "Blocked by design." permanently disabled merge wording per D24 spec',
  )
  assert.ok(
    content.includes('Attempt recorded — Succeeded'),
    'Expected "Attempt recorded — Succeeded" operation wording',
  )
  assert.ok(
    content.includes('Attempt recorded — Failed'),
    'Expected "Attempt recorded — Failed" operation wording',
  )
  assert.ok(
    content.includes('Someone else changed this configuration. Reload to continue.'),
    'Expected 409 stale concurrency banner wording',
  )
  assert.ok(content.includes('Memory & Knowledge Base'), 'Expected Knowledge Base unavailable state title')
  assert.ok(
    content.includes('Prototype Simulation & Sandbox'),
    'Expected Simulation sandbox unavailable state title',
  )
})

test('admin identity review actions match D14 and D24 contracts', () => {
  const componentPath = path.resolve('src/components/Admin.js')
  const content = fs.readFileSync(componentPath, 'utf8')

  // D14 conflict review choices
  assert.ok(content.includes('value="REVIEWING"'), 'Conflict review must offer REVIEWING choice')
  assert.ok(content.includes('value="RESOLVED"'), 'Conflict review must offer RESOLVED choice')
  assert.ok(content.includes('value="IGNORED"'), 'Conflict review must offer IGNORED choice')

  // D14 merge review choices
  assert.ok(content.includes('value="APPROVED"'), 'Merge review must offer APPROVED choice')
  assert.ok(content.includes('value="REJECTED"'), 'Merge review must offer REJECTED choice')

  // D24 merge dry run
  assert.ok(content.includes('dry-run'), 'Admin must include D24 dry-run plan trigger')
  assert.ok(
    content.includes('BI_GRAPH_AI_MERGE_CONTRACT'),
    'Admin plan must cite BI_GRAPH_AI_MERGE_CONTRACT reason',
  )
})

test('admin workspace enforces accessible labels on form controls', () => {
  const componentPath = path.resolve('src/components/Admin.js')
  const content = fs.readFileSync(componentPath, 'utf8')

  assert.ok(content.includes('aria-label="Resolution Action"'), 'Conflict review select must have aria-label')
  assert.ok(
    content.includes('aria-label="Resolution Reason"'),
    'Conflict review textarea must have aria-label',
  )
  assert.ok(content.includes('aria-label="Review Decision"'), 'Merge review select must have aria-label')
  assert.ok(
    content.includes('aria-label="Manager Decision Reason"'),
    'Merge review textarea must have aria-label',
  )
})
