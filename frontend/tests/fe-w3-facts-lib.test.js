import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import {
  FACTS_PATH,
  ISSUES_PATH,
  issuePatchPath,
  issuePatchBody,
  confidencePercent,
  normalizeList,
} from '../src/lib/intelligence/facts.js'

test('FACTS_PATH returns correct path with default limit/offset and valid status', () => {
  assert.equal(FACTS_PATH(1), 'businesses/1/intelligence/facts/?limit=50&offset=0')
  assert.equal(
    FACTS_PATH(1, { limit: 20, offset: 5, status: 'VERIFIED' }),
    'businesses/1/intelligence/facts/?limit=20&offset=5&status=VERIFIED',
  )
})

test('FACTS_PATH throws on invalid status', () => {
  assert.throws(() => FACTS_PATH(1, { status: 'UNKNOWN' }), /status/i)
  assert.throws(() => FACTS_PATH(1, { status: 'OPEN' }), /status/i)
})

test('ISSUES_PATH returns correct path with status and URL-encoded severity', () => {
  assert.equal(ISSUES_PATH(1), 'businesses/1/intelligence/issues/?limit=50&offset=0')
  assert.equal(
    ISSUES_PATH(1, { status: 'OPEN', severity: 'CRITICAL/HIGH' }),
    'businesses/1/intelligence/issues/?limit=50&offset=0&status=OPEN&severity=CRITICAL%2FHIGH',
  )
})

test('ISSUES_PATH throws on invalid status', () => {
  assert.throws(() => ISSUES_PATH(1, { status: 'VERIFIED' }), /status/i)
  assert.throws(() => ISSUES_PATH(1, { status: 'INVALID' }), /status/i)
})

test('issuePatchPath validates issueId range', () => {
  assert.equal(issuePatchPath(1, 42), 'businesses/1/intelligence/issues/42/')
  assert.equal(
    issuePatchPath(1, '9223372036854775807'),
    'businesses/1/intelligence/issues/9223372036854775807/',
  )

  assert.throws(() => issuePatchPath(1, 0), /issue id/i)
  assert.throws(() => issuePatchPath(1, -5), /issue id/i)
  assert.throws(() => issuePatchPath(1, '9223372036854775808'), /issue id/i)
  assert.throws(() => issuePatchPath(1, 'abc'), /issue id/i)
})

test('issuePatchBody handles allowed statuses and notes', () => {
  assert.deepEqual(issuePatchBody('ACKNOWLEDGED'), { status: 'ACKNOWLEDGED' })
  assert.deepEqual(issuePatchBody('RESOLVED', '  Fixed by courier  '), {
    status: 'RESOLVED',
    notes: 'Fixed by courier',
  })
  assert.deepEqual(issuePatchBody('DISMISSED', '   '), { status: 'DISMISSED' })
  assert.deepEqual(issuePatchBody('DISMISSED', null), { status: 'DISMISSED' })

  // Reopening or invalid statuses throw
  assert.throws(() => issuePatchBody('OPEN'), /status/i)
  assert.throws(() => issuePatchBody('FOO'), /status/i)
  assert.throws(() => issuePatchBody(undefined), /status/i)
})

test('confidencePercent converts 0..1 values to 0..100 whole percents', () => {
  assert.equal(confidencePercent('0.9500'), 95)
  assert.equal(confidencePercent(0.5), 50)
  assert.equal(confidencePercent(1), 100)
  assert.equal(confidencePercent(0), 0)
  assert.equal(confidencePercent('abc'), null)
  assert.equal(confidencePercent(2), null)
  assert.equal(confidencePercent(-1), null)
  assert.equal(confidencePercent(null), null)
  assert.equal(confidencePercent(undefined), null)
})

test('normalizeList is exported and functional in facts.js', () => {
  assert.deepEqual(normalizeList({ count: 2, results: [1, 2] }), {
    total: 2,
    limit: 0,
    offset: 0,
    results: [1, 2],
  })
})

test('page.js no longer contains issues/?page_size=50', () => {
  const filePath = path.join(process.cwd(), 'src/app/business/[businessId]/intelligence/[[...tab]]/page.js')
  const content = fs.readFileSync(filePath, 'utf8')
  assert.ok(!content.includes('issues/?page_size=50'), 'page.js must no longer prefetch issues/?page_size=50')
})

test('Intelligence.js imports from @/lib/intelligence/facts and contains Acknowledge', () => {
  const filePath = path.join(process.cwd(), 'src/components/Intelligence.js')
  const content = fs.readFileSync(filePath, 'utf8')
  assert.ok(
    content.includes('@/lib/intelligence/facts'),
    'Intelligence.js must import from @/lib/intelligence/facts',
  )
  assert.ok(content.includes('Acknowledge'), 'Intelligence.js must contain action "Acknowledge"')
})
