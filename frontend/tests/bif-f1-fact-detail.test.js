import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

import {
  EVIDENCE_MAX_ENTRIES,
  EVIDENCE_MAX_TEXT,
  SENSITIVE_KEY,
  parseFactId,
  isFactIdOpenable,
  factDetailPath,
  evidenceEntries,
  normalizeFactDetail,
  factErrorMessage,
} from '../src/lib/intelligence/factDetail.js'

test('parseFactId and isFactIdOpenable validate IDs correctly (BIF-F1)', () => {
  assert.equal(parseFactId(7), '7')
  assert.equal(parseFactId('12'), '12')
  assert.equal(parseFactId(' 9 '), '9')
  assert.equal(parseFactId('007'), '7')
  assert.equal(parseFactId('9223372036854775807'), '9223372036854775807')

  const invalid = ['f-101', '', 0, -1, 1.5, '1.5', '0x10', null, undefined, true, NaN, '9223372036854775808']
  for (const v of invalid) {
    assert.equal(parseFactId(v), null)
  }

  assert.equal(isFactIdOpenable('f-101'), false)
  assert.equal(isFactIdOpenable(7), true)
})

test('factDetailPath constructs valid paths and validates (BIF-F1)', () => {
  assert.equal(factDetailPath(1, 7), 'businesses/1/intelligence/facts/7/')
  assert.equal(factDetailPath(1, '12'), 'businesses/1/intelligence/facts/12/')
  assert.ok(!factDetailPath(1, 7).includes('?'))

  assert.throws(() => factDetailPath(1, 'f-101'), /Invalid fact ID/)
  assert.throws(() => factDetailPath(1, 0), /Invalid fact ID/)
  assert.throws(() => factDetailPath(0, 7), /Invalid business ID/)
})

test('SENSITIVE_KEY regex matches security sensitive names (BIF-F1)', () => {
  const sensitive = [
    'Authorization',
    'x_cookie',
    'apikey',
    'api-key',
    'db_password',
    'credentials',
    'refresh_token',
  ]
  for (const s of sensitive) {
    assert.ok(SENSITIVE_KEY.test(s), `Expected ${s} to be sensitive`)
  }

  const safe = ['status', 'source']
  for (const s of safe) {
    assert.ok(!SENSITIVE_KEY.test(s), `Expected ${s} to be safe`)
  }
})

test('evidenceEntries masks, stringifies, and truncates safely (BIF-F1)', () => {
  const input = {
    delivery_rate: 0.12,
    source: 'Courier log',
    ok: true,
    none: null,
    nested: { api_key: 'abc', fine: 1 },
    db_password: 'p',
    list: [1, 2],
  }

  const expected = [
    { key: 'delivery_rate', text: '0.12', masked: false },
    { key: 'source', text: 'Courier log', masked: false },
    { key: 'ok', text: 'true', masked: false },
    { key: 'none', text: '—', masked: false },
    { key: 'nested', text: '{"api_key":"[hidden]","fine":1}', masked: false },
    { key: 'db_password', text: '[hidden]', masked: true },
    { key: 'list', text: '[1,2]', masked: false },
  ]

  assert.deepEqual(evidenceEntries(input), expected)

  // 60 keys cut to 50
  const manyKeys = {}
  for (let i = 0; i < 60; i++) manyKeys[`k_${i}`] = 'val'
  assert.equal(evidenceEntries(manyKeys).length, 50)

  // 600-character string cut to 500 + '…' = 501 chars
  const longStr = 'a'.repeat(600)
  const entriesWithLong = evidenceEntries({ big: longStr })
  assert.equal(entriesWithLong[0].text.length, 501)
  assert.ok(entriesWithLong[0].text.endsWith('…'))

  // Invalid inputs give []
  for (const inv of [[], null, 'x', 5, undefined]) {
    assert.deepEqual(evidenceEntries(inv), [])
  }

  // Circular reference does not throw
  const circular = {}
  circular.self = circular
  const circEntries = evidenceEntries({ circ: circular })
  assert.equal(circEntries[0].text, '[unreadable]')
})

test('normalizeFactDetail handles complete example and junk (BIF-F1)', () => {
  const sample = {
    id: 7,
    business_id: 1,
    fact_type: 'DELIVERY_FAILURE_RATE',
    statement: 'Delivery failure rate reached 12%',
    value: '0.120000',
    value_unit: 'RATIO',
    confidence: '1.0000',
    status: 'VERIFIED',
    rule_key: 'rule.delivery',
    valid_from: null,
    valid_to: '2026-12-01T00:00:00+00:00',
    detected_at: '2026-11-17T09:00:00+00:00',
    evidence: { source: 'Courier log' },
  }

  const expected = {
    id: 7,
    businessId: 1,
    factType: 'DELIVERY_FAILURE_RATE',
    statement: 'Delivery failure rate reached 12%',
    value: '0.120000',
    valueUnit: 'RATIO',
    confidencePercent: 100,
    status: 'VERIFIED',
    ruleKey: 'rule.delivery',
    validFrom: null,
    validTo: '2026-12-01T00:00:00+00:00',
    detectedAt: '2026-11-17T09:00:00+00:00',
    evidence: { entries: [{ key: 'source', text: 'Courier log', masked: false }], total: 1 },
  }

  assert.deepEqual(normalizeFactDetail(sample), expected)

  // Minimal fact
  assert.deepEqual(normalizeFactDetail({ id: 3 }), {
    id: 3,
    businessId: null,
    factType: null,
    statement: '',
    value: null,
    valueUnit: null,
    confidencePercent: null,
    status: null,
    ruleKey: null,
    validFrom: null,
    validTo: null,
    detectedAt: null,
    evidence: { entries: [], total: 0 },
  })

  // Junk inputs
  for (const j of [null, {}, { id: 'x' }, { id: 'f-1' }]) {
    assert.equal(normalizeFactDetail(j), null)
  }
})

test('factErrorMessage maps errors correctly (BIF-F1)', () => {
  assert.equal(factErrorMessage({ status: 403 }), 'You do not have access to this business.')
  assert.equal(
    factErrorMessage({ status: 404 }),
    'This fact was not found. It may belong to another business or may have been removed.',
  )
  assert.equal(factErrorMessage({ status: 400, detail: 'Bad' }), 'Bad')
  assert.equal(factErrorMessage(new Error('boom')), 'boom')
  assert.equal(factErrorMessage(null), 'The fact could not be loaded.')
})

test('source checks: factDetail.js, FactDetailDrawer.js, and Intelligence.js (BIF-F1)', () => {
  const libFile = path.resolve('src/lib/intelligence/factDetail.js')
  const compFile = path.resolve('src/components/FactDetailDrawer.js')
  const intelFile = path.resolve('src/components/Intelligence.js')

  const libCode = fs.readFileSync(libFile, 'utf8')
  assert.ok(!libCode.includes('@/'))
  assert.ok(!libCode.includes('window'))
  assert.ok(!libCode.includes('fetch'))

  const importStatements = libCode.match(/import\s+[\s\S]*?from\s+['"][^'"]+['"]/g) || []
  assert.equal(importStatements.length, 2, 'Must have exactly two import statements')
  assert.ok(libCode.includes("from '../catalog.js'"))
  assert.ok(libCode.includes("from './facts.js'"))

  assert.ok(fs.existsSync(compFile), 'FactDetailDrawer.js must exist')
  const compCode = fs.readFileSync(compFile, 'utf8')
  assert.ok(compCode.startsWith("'use client'"))
  assert.ok(compCode.includes("from '@/lib/intelligence/factDetail'"))
  assert.ok(compCode.includes("from '@/lib/clientApi'"))
  assert.ok(compCode.includes("from '@/components/ui'"))

  assert.ok(compCode.includes('isOpen='))
  assert.ok(!/\bopen=\{/.test(compCode))

  const requiredCodeTokens = ['factDetailPath(', 'normalizeFactDetail(', 'useCallback']
  for (const tok of requiredCodeTokens) {
    assert.ok(compCode.includes(tok), `Must contain ${tok}`)
  }

  const requiredPhrases = [
    'Fact detail',
    'Statement',
    'Stored evidence',
    'No evidence notes are stored for this fact.',
    'No validity window is stored for this fact.',
    'The fact could not be opened',
    'Loading fact details...',
    'Try again',
    'This view is read only.',
    'aria-live="polite"',
  ]
  for (const phrase of requiredPhrases) {
    assert.ok(compCode.includes(phrase), `Must contain phrase "${phrase}"`)
  }

  const strippedCode = compCode.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '')
  assert.ok(!strippedCode.includes('JSON.stringify'))
  assert.ok(!strippedCode.includes('dangerouslySetInnerHTML'))
  assert.ok(!strippedCode.includes('localStorage'))
  assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(strippedCode))
  assert.ok(!/<Banner[^>]*\btone=/.test(strippedCode))

  const forbiddenClasses = ['text-caption', 'text-muted', 'text-secondary', 'stack-xs', 'stack-md']
  for (const cls of forbiddenClasses) {
    const classRegex = new RegExp(`className=["'][^"']*\\b${cls}\\b[^"']*["']`)
    assert.ok(!classRegex.test(strippedCode), `Must not contain forbidden class ${cls}`)
  }

  const intelCode = fs.readFileSync(intelFile, 'utf8')
  assert.ok(intelCode.includes('FactDetailDrawer'))
  assert.ok(intelCode.includes('isFactIdOpenable'))
  assert.ok(intelCode.includes('setFactDetailId'))
  assert.ok(intelCode.includes('Open details for fact'))
  assert.ok(intelCode.includes('Acknowledge'))
  assert.ok(intelCode.includes('@/lib/intelligence/facts'))
  assert.ok(intelCode.includes("activeTab === 'facts'"))
  assert.ok(intelCode.includes('handleOpenEvidence'))
})
