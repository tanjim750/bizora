import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

import {
  PAYLOAD_PREVIEW_MAX_CHARS,
  PAYLOAD_NOTICES,
  canViewPayloads,
  parsePayloadId,
  payloadDiagnosticPath,
  normalizePayloadDiagnostic,
  personalDataHints,
  describePayload,
  markerSummary,
  payloadErrorMessage,
} from '../src/lib/observability/payloads.js'

test('canViewPayloads allows only exact OWNER and MANAGER (OBS-F1)', () => {
  assert.equal(canViewPayloads('OWNER'), true)
  assert.equal(canViewPayloads('MANAGER'), true)
  assert.equal(canViewPayloads('OPERATOR'), false)
  assert.equal(canViewPayloads('VIEWER'), false)
  assert.equal(canViewPayloads('owner'), false)
  assert.equal(canViewPayloads(' OWNER'), false)
  assert.equal(canViewPayloads(''), false)
  assert.equal(canViewPayloads(null), false)
  assert.equal(canViewPayloads(undefined), false)
  assert.equal(canViewPayloads(5), false)
})

test('parsePayloadId and payloadDiagnosticPath validate correctly (OBS-F1)', () => {
  assert.equal(parsePayloadId(12), '12')
  assert.equal(parsePayloadId(' 7 '), '7')
  assert.equal(parsePayloadId('007'), '7')
  assert.equal(parsePayloadId('9223372036854775807'), '9223372036854775807')

  const invalid = ['p-1', '', 0, -1, 1.5, '0x10', null, undefined, true, NaN, '9223372036854775808']
  for (const inv of invalid) {
    assert.equal(parsePayloadId(inv), null)
  }

  assert.equal(payloadDiagnosticPath(1, 12), 'businesses/1/observability/payloads/12/')
  assert.ok(!payloadDiagnosticPath(1, 12).includes('?'))

  assert.throws(() => payloadDiagnosticPath(1, 'p-1'), /Invalid payload ID/)
  assert.throws(() => payloadDiagnosticPath(1, 0), /Invalid payload ID/)
  assert.throws(() => payloadDiagnosticPath(0, 12), /Invalid business ID/)
})

test('normalizePayloadDiagnostic maps fields and discards extra properties (OBS-F1)', () => {
  const full = {
    id: 12,
    connection_id: 5,
    digest: 'a'.repeat(64),
    received_at: '2026-11-17T09:00:00Z',
    source_at: null,
    signature_verified: true,
    diagnostic_payload: { id: 'p-1', name: 'Coffee', api_key: '[REDACTED]' },
    extra: 'IGNORED',
  }

  const expected = {
    id: 12,
    connectionId: 5,
    digest: 'a'.repeat(64),
    receivedAt: '2026-11-17T09:00:00Z',
    sourceAt: null,
    signatureVerified: true,
    body: { id: 'p-1', name: 'Coffee', api_key: '[REDACTED]' },
  }

  assert.deepEqual(normalizePayloadDiagnostic(full), expected)

  // signature_verified must be boolean true
  assert.equal(normalizePayloadDiagnostic({ id: 1, signature_verified: 'true' }).signatureVerified, false)

  assert.deepEqual(normalizePayloadDiagnostic({ id: 3 }), {
    id: 3,
    connectionId: null,
    digest: null,
    receivedAt: null,
    sourceAt: null,
    signatureVerified: false,
    body: null,
  })

  for (const j of [null, {}, { id: 'x' }]) {
    assert.equal(normalizePayloadDiagnostic(j), null)
  }
})

test('personalDataHints detects emails and phone numbers (OBS-F1)', () => {
  assert.deepEqual(personalDataHints('{"email": "rina@example.com"}'), ['an email address'])
  assert.deepEqual(personalDataHints('+8801712345678'), ['a phone number'])
  assert.deepEqual(personalDataHints('01712345678'), ['a phone number'])
  assert.deepEqual(personalDataHints('Call +8801712345678 or write to test@example.com'), [
    'an email address',
    'a phone number',
  ])
  assert.deepEqual(personalDataHints('{"id":"p-1","name":"Coffee"}'), [])
  assert.deepEqual(personalDataHints('order 12345678901'), [])
  assert.deepEqual(personalDataHints(null), [])
  assert.deepEqual(personalDataHints(5), [])
})

test('describePayload computes markers, preview, and checks entire body for hints (OBS-F1)', () => {
  const val = { id: 'p-1', api_key: '[REDACTED]', note: 'x' }
  const desc = describePayload(val)
  assert.equal(desc.text, JSON.stringify(val, null, 2))
  assert.equal(desc.previewTruncated, false)
  assert.deepEqual(desc.markers, { redacted: 1, cutOff: 0, unsupported: 0 })
  assert.deepEqual(desc.hints, [])

  const bigVal = { big: 'x'.repeat(25000) }
  const bigDesc = describePayload(bigVal)
  assert.equal(bigDesc.text.length, 20000)
  assert.equal(bigDesc.previewTruncated, true)
  assert.ok(bigDesc.totalChars > 25000)

  const cut10 = describePayload({ a: '1234567890abcdef' }, { maxChars: 10 })
  assert.equal(cut10.text.length, 10)

  const arrVal = ['[TRUNCATED]', '[UNSUPPORTED]', '[UNSUPPORTED]', 'Bearer [REDACTED]']
  const arrDesc = describePayload(arrVal)
  assert.deepEqual(arrDesc.markers, { redacted: 1, cutOff: 1, unsupported: 2 })

  // Email placed AFTER 20000 chars is still in hints
  const deepEmail = { pad: 'y'.repeat(22000), contact: 'late@example.com' }
  const deepDesc = describePayload(deepEmail)
  assert.ok(!deepDesc.text.includes('late@example.com'))
  assert.deepEqual(deepDesc.hints, ['an email address'])

  assert.deepEqual(describePayload(undefined), {
    text: '',
    previewTruncated: false,
    totalChars: 0,
    markers: { redacted: 0, cutOff: 0, unsupported: 0 },
    hints: [],
  })

  const circular = {}
  circular.self = circular
  assert.deepEqual(describePayload(circular), {
    text: '',
    previewTruncated: false,
    totalChars: 0,
    markers: { redacted: 0, cutOff: 0, unsupported: 0 },
    hints: [],
  })
})

test('markerSummary produces honest summary sentences (OBS-F1)', () => {
  assert.equal(markerSummary({ redacted: 0, cutOff: 0, unsupported: 0 }), '')
  assert.equal(
    markerSummary({ redacted: 1, cutOff: 0, unsupported: 0 }),
    'The server replaced 1 value with [REDACTED].',
  )
  assert.equal(
    markerSummary({ redacted: 2, cutOff: 0, unsupported: 1 }),
    'The server replaced 2 values with [REDACTED] and 1 value with [UNSUPPORTED].',
  )
  assert.equal(
    markerSummary({ redacted: 2, cutOff: 3, unsupported: 1 }),
    'The server replaced 2 values with [REDACTED], 3 values with [TRUNCATED] and 1 value with [UNSUPPORTED].',
  )
})

test('PAYLOAD_NOTICES and payloadErrorMessage contracts (OBS-F1)', () => {
  assert.equal(
    PAYLOAD_NOTICES.personalData,
    'This is a diagnostic copy of what a provider sent. The server hides values it recognises as credentials (keys such as token, secret, password, authorization, API key, cookie or credential) and shortens very long content. It does not remove personal data: names, email addresses, phone numbers and addresses can still appear.',
  )
  assert.equal(
    PAYLOAD_NOTICES.audit,
    'Opening this view is recorded in the audit log together with your user.',
  )
  assert.equal(
    PAYLOAD_NOTICES.handling,
    'Do not copy this into chats, tickets or documents. This screen has no copy, download or save option and clears the content when you close it.',
  )

  assert.equal(payloadErrorMessage({ status: 403 }), 'Only owners and managers can open diagnostic payloads.')
  assert.equal(payloadErrorMessage({ status: 404 }), 'This payload was not found for this business.')
  assert.equal(payloadErrorMessage({ status: 400 }), 'The server did not accept the request.')
  assert.equal(payloadErrorMessage({ status: 400, detail: 'No query' }), 'No query')
  assert.equal(payloadErrorMessage({ status: 500, detail: 'Server broke' }), 'Server broke')
  assert.equal(payloadErrorMessage(new Error('boom')), 'boom')
  assert.equal(payloadErrorMessage(null), 'The payload could not be loaded.')
})

test('source checks: payloads.js and PayloadDiagnosticDrawer.js (OBS-F1)', () => {
  const libFile = path.resolve('src/lib/observability/payloads.js')
  const compFile = path.resolve('src/components/PayloadDiagnosticDrawer.js')

  const libCode = fs.readFileSync(libFile, 'utf8')
  assert.ok(!libCode.includes('@/'))
  assert.ok(!libCode.includes('window'))
  assert.ok(!libCode.includes('fetch'))
  assert.ok(!libCode.includes('localStorage'))
  assert.ok(!libCode.includes('sessionStorage'))
  assert.ok(!libCode.includes('console.'))

  const importLines = libCode.split('\n').filter((line) => line.trim().startsWith('import '))
  assert.equal(importLines.length, 1, 'payloads.js must have exactly one import line')
  assert.ok(libCode.includes("import { businessApiPath, MANAGER_ROLES } from '../catalog.js'"))

  assert.ok(fs.existsSync(compFile), 'PayloadDiagnosticDrawer.js must exist')
  const compCode = fs.readFileSync(compFile, 'utf8')
  assert.ok(compCode.startsWith("'use client'"))
  assert.ok(compCode.includes("from '@/lib/observability/payloads'"))
  assert.ok(compCode.includes("from '@/lib/clientApi'"))
  assert.ok(compCode.includes("from '@/components/ui'"))

  assert.ok(compCode.includes('isOpen='))
  assert.ok(!/\bopen=\{/.test(compCode))

  const requiredCodeTokens = [
    'canViewPayloads(',
    'payloadDiagnosticPath(',
    'normalizePayloadDiagnostic(',
    'describePayload(',
    'markerSummary(',
    'PAYLOAD_NOTICES',
    'useCallback',
  ]
  for (const tok of requiredCodeTokens) {
    assert.ok(compCode.includes(tok), `Must contain ${tok}`)
  }

  const requiredPhrases = [
    'Diagnostic payload',
    'Sensitive content',
    'Show payload content',
    'Hide payload content',
    'The payload could not be opened',
    'Loading diagnostic payload...',
    'Try again',
    'Only owners and managers can open diagnostic payloads.',
    'Handle it as personal data',
    'aria-live="polite"',
  ]
  for (const phrase of requiredPhrases) {
    assert.ok(compCode.includes(phrase), `Must contain phrase "${phrase}"`)
  }

  // Exactly one clientApi( call
  const clientApiMatches = compCode.match(/clientApi\(/g) || []
  assert.equal(clientApiMatches.length, 1, 'Must have exactly one clientApi( call')

  // canViewPayloads comes before clientApi in source
  const canViewIdx = compCode.indexOf('canViewPayloads(')
  const clientApiIdx = compCode.indexOf('clientApi(')
  assert.ok(canViewIdx < clientApiIdx, 'canViewPayloads must precede clientApi')

  // Gated <pre>
  assert.ok(
    compCode.includes('revealed &&') || compCode.includes('revealed ?'),
    '<pre> must be gated by revealed',
  )

  // Forbidden patterns in the entire file
  const forbiddenPatterns = [
    'localStorage',
    'sessionStorage',
    'indexedDB',
    'clipboard',
    'CopyableCode',
    'console.',
    'createObjectURL',
    'Blob',
    'download',
    'document.cookie',
    'postMessage',
    'window.open',
    'window.print',
    'useRouter',
    'dangerouslySetInnerHTML',
    'JSON.stringify',
    'setInterval',
    'setTimeout',
    'onMouseEnter',
    'onMouseOver',
    'onFocus',
    'prefetch',
  ]
  for (const pat of forbiddenPatterns) {
    assert.ok(!compCode.includes(pat), `Must not contain forbidden pattern ${pat}`)
  }

  const strippedCode = compCode.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '')
  assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(strippedCode))
  assert.ok(!/<Banner[^>]*\btone=/.test(strippedCode))

  const forbiddenClasses = ['text-caption', 'text-muted', 'text-secondary', 'stack-xs', 'stack-md']
  for (const cls of forbiddenClasses) {
    const classRegex = new RegExp(`className=["'][^"']*\\b${cls}\\b[^"']*["']`)
    assert.ok(!classRegex.test(strippedCode), `Must not contain forbidden class ${cls}`)
  }
})
