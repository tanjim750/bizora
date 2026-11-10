import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8')

test('QuickSearchDialog registers complete workspace and multi-tenant routes', () => {
  const quickSearchSource = read('../src/components/shell/QuickSearchDialog.js')

  // Core 7 workspace entries
  assert.match(quickSearchSource, /id:\s*'ws-overview'/)
  assert.match(quickSearchSource, /id:\s*'ws-customers'/)
  assert.match(quickSearchSource, /id:\s*'ws-commerce'/)
  assert.match(quickSearchSource, /id:\s*'ws-support'/)
  assert.match(quickSearchSource, /id:\s*'ws-growth'/)
  assert.match(quickSearchSource, /id:\s*'ws-intelligence'/)
  assert.match(quickSearchSource, /id:\s*'ws-ai'/)

  // Switch Workspace & UI Kit shortcuts
  assert.match(quickSearchSource, /id:\s*'ws-switch'/)
  assert.match(quickSearchSource, /href:\s*'\/workspace'/)
  assert.match(quickSearchSource, /id:\s*'ws-uikit'/)
  assert.match(quickSearchSource, /href:\s*`\/business\/\$\{bId\}\/ui-kit`/)
})

test('QuickSearchDialog registers administration, resource, and action items', () => {
  const quickSearchSource = read('../src/components/shell/QuickSearchDialog.js')

  // Admin modules
  assert.match(quickSearchSource, /id:\s*'ws-identity'/)
  assert.match(quickSearchSource, /id:\s*'ws-integrations'/)
  assert.match(quickSearchSource, /id:\s*'ws-config'/)

  // Resources
  assert.match(quickSearchSource, /id:\s*'res-orders'/)
  assert.match(quickSearchSource, /id:\s*'res-payments'/)
  assert.match(quickSearchSource, /id:\s*'res-products'/)
  assert.match(quickSearchSource, /id:\s*'res-shipments'/)
  assert.match(quickSearchSource, /id:\s*'res-calls'/)

  // Actions
  assert.match(quickSearchSource, /id:\s*'act-theme'/)
})

test('QuickSearchDialog supports keyboard navigation and accessible dialog attributes', () => {
  const quickSearchSource = read('../src/components/shell/QuickSearchDialog.js')

  // Accessible dialog wrap
  assert.match(quickSearchSource, /<Dialog/)
  assert.match(quickSearchSource, /isOpen=\{isOpen\}/)
  assert.match(quickSearchSource, /onClose=\{onClose\}/)

  // Keyboard navigation logic
  assert.match(quickSearchSource, /e\.key === 'ArrowDown'/)
  assert.match(quickSearchSource, /e\.key === 'ArrowUp'/)
  assert.match(quickSearchSource, /e\.key === 'Enter'/)
})
