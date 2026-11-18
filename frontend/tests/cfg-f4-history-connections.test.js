import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  CHANGE_KIND_LABELS,
  kindLabel,
  normalizeChange,
  itemLabel,
  normalizeRevision,
  subjectFromChange,
  historyPathFor,
  flattenSettings,
  diffSettings,
  formatDiffValue,
  withDiffs,
} from '../src/lib/configuration/history.js'
import {
  normalizeProvider,
  requiredScope,
  connectionSpecs,
  validateConnection,
  CONNECTIONS_RESOURCE,
} from '../src/lib/configuration/integrations.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const ROOT = path.resolve(__dirname, '..')

test('history lib: kindLabel, normalize, itemLabel, subject, historyPathFor (CFG-F4)', () => {
  assert.equal(kindLabel('PROFILE'), 'Business profile')
  assert.equal(kindLabel('CUSTOM_SECTION'), 'CUSTOM_SECTION')
  assert.equal(kindLabel(''), 'Unknown')
  assert.equal(kindLabel(null), 'Unknown')

  // normalizeChange
  const ch = normalizeChange({
    id: '12',
    section: 'PROFILE',
    key: 'default',
    version: '3',
    actor_id: 1,
    created_at: '2026-11-10T12:00:00Z',
    delivery_state: 'DELIVERED',
  })
  assert.deepEqual(ch, {
    id: 12,
    section: 'PROFILE',
    key: 'default',
    version: 3,
    actor_id: 1,
    created_at: '2026-11-10T12:00:00Z',
    delivery_state: 'DELIVERED',
  })

  // normalizeChange junk
  assert.deepEqual(normalizeChange(null), {
    id: null,
    section: null,
    key: null,
    version: 0,
    actor_id: null,
    created_at: null,
    delivery_state: null,
  })

  // itemLabel
  assert.equal(itemLabel({ key: 'default' }), '—')
  assert.equal(itemLabel({ key: '' }), '—')
  assert.equal(itemLabel({ section: 'INTEGRATION', key: '5' }), 'Connection #5')
  assert.equal(itemLabel({ section: 'SOURCE', key: 'web_kb' }), 'Source #web_kb')
  assert.equal(itemLabel({ section: 'FRESHNESS', key: 'hourly' }), 'Policy #hourly')
  assert.equal(itemLabel({ section: 'RULE', key: 'delivery_rule' }), 'delivery_rule')

  // normalizeRevision
  const rev = normalizeRevision({
    id: 9,
    key: 'my_rule',
    kind: 'RULE',
    version: 2,
    status: 'ACTIVE',
    valid_from: '2026-01-01',
    valid_to: null,
    settings: { a: 1 },
    actor_id: 5,
    reason: 'update',
    created_at: '2026-11-10T12:00:00Z',
  })
  assert.equal(rev.id, 9)
  assert.equal(rev.status, 'ACTIVE')

  // monitoring revision: status and id null
  const monRev = normalizeRevision({
    version: 1,
    settings: { ping: true },
    actor_id: 2,
    created_at: '2026-11-10T12:00:00Z',
  })
  assert.equal(monRev.id, null)
  assert.equal(monRev.status, null)

  // subjectFromChange
  assert.deepEqual(subjectFromChange({ section: 'MONITORING' }), {
    kind: 'monitoring',
    key: null,
  })
  assert.deepEqual(subjectFromChange({ section: 'PROFILE' }), {
    kind: 'section',
    key: 'profile',
  })
  assert.deepEqual(subjectFromChange({ section: 'RULE', key: 'r1' }), {
    kind: 'rules',
    key: 'r1',
  })
  assert.deepEqual(subjectFromChange({ section: 'POLICY', key: 'p1' }), {
    kind: 'policies',
    key: 'p1',
  })
  assert.deepEqual(subjectFromChange({ section: 'INTEGRATION', key: '5' }), {
    kind: 'connections',
    key: '5',
  })
  assert.deepEqual(subjectFromChange({ section: 'SOURCE', key: 's1' }), {
    kind: 'sources',
    key: 's1',
  })
  assert.deepEqual(subjectFromChange({ section: 'FRESHNESS', key: 'f1' }), {
    kind: 'freshness',
    key: 'f1',
  })
  assert.equal(subjectFromChange({ section: 'UNKNOWN' }), null)

  // historyPathFor
  assert.equal(
    historyPathFor(7, { kind: 'section', key: 'ai' }, { pageSize: 100 }),
    'businesses/7/configuration/ai/history/?page_size=100',
  )
  assert.equal(
    historyPathFor(7, { kind: 'monitoring', key: null }),
    'businesses/7/configuration/monitoring/history/',
  )
  assert.equal(
    historyPathFor(7, { kind: 'rules', key: 'r1' }),
    'businesses/7/configuration/rules/r1/history/',
  )
  assert.equal(
    historyPathFor(7, { kind: 'policies', key: 'p1' }),
    'businesses/7/configuration/policies/p1/history/',
  )
  assert.equal(
    historyPathFor(7, { kind: 'connections', key: '2' }),
    'businesses/7/configuration/connections/2/history/',
  )
  assert.equal(
    historyPathFor(7, { kind: 'sources', key: 3 }),
    'businesses/7/configuration/sources/3/history/',
  )
  assert.equal(
    historyPathFor(7, { kind: 'freshness', key: 4 }),
    'businesses/7/configuration/freshness/4/history/',
  )
  assert.throws(() => historyPathFor(7, { kind: 'unknown_kind' }), /Unknown history subject: unknown_kind/)
})

test('history lib: diffSettings, formatDiffValue, withDiffs (CFG-F4)', () => {
  // Verified diffSettings example from spec
  const before = { a: 1, b: { c: ['x'], d: true }, gone: 1 }
  const after = { a: 1, b: { c: ['x', 'y'], d: true }, added: 'n' }
  const diffs = diffSettings(before, after)
  assert.deepEqual(diffs, [
    { path: 'added', after: 'n', change: 'added' },
    { path: 'b.c', before: ['x'], after: ['x', 'y'], change: 'changed' },
    { path: 'gone', before: 1, change: 'removed' },
  ])

  // formatDiffValue
  assert.equal(formatDiffValue(undefined), '—')
  assert.equal(formatDiffValue(null), '—')
  assert.equal(formatDiffValue(''), '—')
  assert.equal(formatDiffValue(true), 'Yes')
  assert.equal(formatDiffValue(false), 'No')
  assert.equal(formatDiffValue([]), '(empty list)')
  assert.equal(formatDiffValue(['a', 'b']), 'a, b')
  const longText = 'x'.repeat(100)
  assert.equal(formatDiffValue(longText), 'x'.repeat(77) + '...')

  // withDiffs
  const revs = [
    { version: 3, settings: { a: 2 } },
    { version: 2, settings: { a: 1 } },
    { version: 1, settings: { a: 0 } },
  ]
  const withD = withDiffs(revs)
  assert.equal(withD[0].note, null)
  assert.deepEqual(withD[0].diff, [{ path: 'a', before: 1, after: 2, change: 'changed' }])
  assert.equal(withD[2].note, 'First saved version')
  assert.deepEqual(withD[2].diff, [{ path: 'a', after: 0, change: 'added' }])

  // Last on page note when version > 1
  const pageRevs = [
    { version: 3, settings: { a: 2 } },
    { version: 2, settings: { a: 1 } },
  ]
  const withPageD = withDiffs(pageRevs)
  assert.equal(withPageD[1].diff, null)
  assert.equal(withPageD[1].note, 'The earlier version is on the next page.')
})

test('integrations lib: normalizeProvider, requiredScope, specs, validation, examples (CFG-F4)', () => {
  const prov = normalizeProvider({
    id: 2,
    key: 'shopify',
    name: 'Shopify',
    category: 'COMMERCE',
    capabilities: {
      entities: ['PRODUCT', 'ORDER'],
      scopes: ['READ_PRODUCTS', 'READ_ORDERS'],
    },
    mock_supported: true,
  })
  assert.deepEqual(prov, {
    id: 2,
    key: 'shopify',
    name: 'Shopify',
    category: 'COMMERCE',
    entities: ['PRODUCT', 'ORDER'],
    scopes: ['READ_PRODUCTS', 'READ_ORDERS'],
    mock_supported: true,
  })

  // requiredScope
  assert.equal(requiredScope('PRODUCT', 'COMMERCE'), 'READ_PRODUCTS')
  assert.equal(requiredScope('ORDER', 'COMMERCE'), 'READ_ORDERS')
  assert.equal(requiredScope('CUSTOMER', 'COMMUNICATION'), 'READ_CONVERSATIONS')
  assert.equal(requiredScope('CUSTOMER', 'SUPPORT'), 'READ_CONVERSATIONS')
  assert.equal(requiredScope('CUSTOMER', 'MESSAGING'), 'READ_CONVERSATIONS')
  assert.equal(requiredScope('CUSTOMER', 'COMMERCE'), 'READ_CUSTOMERS')

  // connectionSpecs paths
  const specs = connectionSpecs(null, prov)
  const paths = specs.map((s) => s.path)
  assert.deepEqual(paths, [
    'name',
    'enabled',
    'entities',
    'scopes',
    'sync.mode',
    'sync.interval_seconds',
    'reason',
  ])

  // Verified example from spec
  const record = {
    id: 5,
    version: 1,
    status: 'ACTIVE',
    settings: {
      connection_id: 5,
      provider_id: 2,
      name: 'Store',
      enabled: true,
      is_mock: true,
      entities: ['PRODUCT', 'ORDER'],
      scopes: ['READ_PRODUCTS', 'READ_ORDERS'],
      sync: { mode: 'MANUAL', interval_seconds: 900 },
      webhooks: { enabled: false, events: [], endpoint: '' },
      provider_settings: {},
      credentials: { configured: false, fields: [] },
      mock: { connection_outcome: 'SUCCESS', product_name_field: 'name' },
    },
  }
  const context = { providers: [prov] }
  const draft = CONNECTIONS_RESOURCE.draftFor(record, context)

  // Unchanged draft
  const unchangedRes = CONNECTIONS_RESOURCE.build({
    record,
    draft,
    creating: false,
    context,
  })
  assert.equal(unchangedRes.changed, false)

  // Changed draft
  const changedDraft = {
    ...draft,
    name: 'Renamed',
    enabled: false,
    'sync.interval_seconds': '300',
  }
  const changedRes = CONNECTIONS_RESOURCE.build({
    record,
    draft: changedDraft,
    creating: false,
    context,
  })
  assert.deepEqual(changedRes.errors, {})
  assert.deepEqual(changedRes.body, {
    version: 1,
    name: 'Renamed',
    enabled: false,
    sync: { interval_seconds: 300 },
  })

  // Deselect READ_ORDERS while ORDER stays selected
  const missingScopeDraft = {
    ...draft,
    scopes: ['READ_PRODUCTS'],
  }
  const missingScopeRes = CONNECTIONS_RESOURCE.build({
    record,
    draft: missingScopeDraft,
    creating: false,
    context,
  })
  assert.equal(missingScopeRes.errors.entities, 'ORDER needs the READ_ORDERS scope.')

  // sync.interval_seconds out of bounds
  const badIntervalDraft = {
    ...draft,
    'sync.interval_seconds': '10',
  }
  const badIntervalRes = CONNECTIONS_RESOURCE.build({
    record,
    draft: badIntervalDraft,
    creating: false,
    context,
  })
  assert.ok(badIntervalRes.errors['sync.interval_seconds'].includes('between 60 and 2592000'))

  // Live connection without credentials error
  const liveUnconfiguredRecord = {
    ...record,
    settings: {
      ...record.settings,
      is_mock: false,
      credentials: { configured: false },
    },
  }
  const liveUnconfiguredRes = CONNECTIONS_RESOURCE.build({
    record: liveUnconfiguredRecord,
    draft: { ...draft, enabled: true },
    creating: false,
    context,
  })
  assert.equal(
    liveUnconfiguredRes.errors.enabled,
    'Live connections need credential references configured on the server.',
  )

  // Resource definition contract properties
  assert.equal(CONNECTIONS_RESOURCE.itemPath(7, { id: 5 }), 'businesses/7/configuration/connections/5/')
  assert.equal(CONNECTIONS_RESOURCE.createPath, null)
  assert.equal(
    CONNECTIONS_RESOURCE.listPath(7, { page: 1, pageSize: 25 }),
    'businesses/7/configuration/connections/?page=1&page_size=25',
  )
})

test('source text: ConfigHistory, ConfigConnections, Admin.js (CFG-F4)', () => {
  const componentFiles = ['ConfigHistory.js', 'ConfigConnections.js']

  for (const file of componentFiles) {
    const fullPath = path.join(ROOT, 'src/components', file)
    assert.ok(fs.existsSync(fullPath), `${file} must exist`)
    const content = fs.readFileSync(fullPath, 'utf8')
    assert.match(content, /^'use client'/, `${file} must start with 'use client'`)
    assert.doesNotMatch(content, /\bwindow\.confirm\b/, `${file} must not use window.confirm`)
    assert.doesNotMatch(content, /<Banner\b[^>]*\btone=/, `${file} must not use tone= on Banner`)
    assert.doesNotMatch(content, /<Dialog\b[^>]*\sopen=\{/, `${file} must not use open= on Dialog`)

    const hex = content.match(/#(?:[0-9a-fA-F]{3}){1,2}\b/g) || []
    assert.equal(hex.length, 0, `Found raw hex in ${file}: ${hex.join(', ')}`)
  }

  const histContent = fs.readFileSync(path.join(ROOT, 'src/components/ConfigHistory.js'), 'utf8')
  assert.match(histContent, /aria-live="polite"/)
  assert.ok(histContent.includes('Versions cannot be restored from here'))
  assert.ok(histContent.includes('No saved versions yet'))
  assert.ok(histContent.includes('View versions'))
  assert.match(histContent, /\bDrawer\b/)
  assert.ok(histContent.includes('isOpen'))
  assert.doesNotMatch(histContent, /\bmethod:\s*['"]POST['"]/)
  assert.doesNotMatch(histContent, /\bmethod:\s*['"]PUT['"]/)
  assert.doesNotMatch(histContent, /\bmethod:\s*['"]PATCH['"]/)
  assert.doesNotMatch(histContent, /\bJSON\.stringify\b/)

  const connContent = fs.readFileSync(path.join(ROOT, 'src/components/ConfigConnections.js'), 'utf8')
  assert.ok(connContent.includes('Open Integrations & Sync for health, syncs and connection tests'))
  assert.match(connContent, /\bConfigResourceManager\b/)

  const adminContent = fs.readFileSync(path.join(ROOT, 'src/components/Admin.js'), 'utf8')
  assert.match(adminContent, /\bConfigHistory\b/)
  assert.match(adminContent, /\bConfigConnections\b/)
  assert.ok(adminContent.includes('Change history'))
})
