import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { operationBody, describeAttempt, operationErrorText } from '../src/lib/observability/operations.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const ROOT = path.resolve(__dirname, '..')

test('operationBody validates key length and produces correct payload (ADM-F1)', () => {
  assert.deepEqual(operationBody('abc'), { idempotency_key: 'abc' })
  assert.deepEqual(operationBody('k'.repeat(200)), { idempotency_key: 'k'.repeat(200) })

  assert.throws(() => operationBody(''), /idempotency/i)
  assert.throws(() => operationBody(null), /idempotency/i)
  assert.throws(() => operationBody(undefined), /idempotency/i)
  assert.throws(() => operationBody(123), /idempotency/i)
  assert.throws(() => operationBody('k'.repeat(201)), /idempotency/i)
})

test('describeAttempt returns exact tone and text for connection_test and sync_retry (ADM-F1)', () => {
  // connection_test
  assert.deepEqual(describeAttempt('connection_test', { status: 'SUCCEEDED' }), {
    tone: 'success',
    text: 'Connection test succeeded.',
  })
  assert.deepEqual(describeAttempt('connection_test', { status: 'FAILED' }), {
    tone: 'danger',
    text: 'Connection test failed.',
  })
  assert.deepEqual(describeAttempt('connection_test', { status: 'UNSUPPORTED' }), {
    tone: 'warning',
    text: 'This action is not supported for this connection.',
  })
  assert.deepEqual(describeAttempt('connection_test', { status: 'RUNNING' }), {
    tone: 'warning',
    text: 'The action is still running.',
  })

  // sync_retry
  assert.deepEqual(describeAttempt('sync_retry', { status: 'SUCCEEDED' }), {
    tone: 'success',
    text: 'Sync retry succeeded.',
  })
  assert.deepEqual(describeAttempt('sync_retry', { status: 'FAILED' }), {
    tone: 'danger',
    text: 'Sync retry failed.',
  })
  assert.deepEqual(describeAttempt('sync_retry', { status: 'UNSUPPORTED' }), {
    tone: 'warning',
    text: 'This action is not supported for this connection.',
  })
  assert.deepEqual(describeAttempt('sync_retry', { status: 'RUNNING' }), {
    tone: 'warning',
    text: 'The action is still running.',
  })

  // fallbacks
  const fallback = {
    tone: 'warning',
    text: 'The server answered without a clear result.',
  }
  assert.deepEqual(describeAttempt('connection_test', null), fallback)
  assert.deepEqual(describeAttempt('connection_test', {}), fallback)
  assert.deepEqual(describeAttempt('connection_test', { status: 'WEIRD' }), fallback)
  assert.deepEqual(describeAttempt('unknown_kind', { status: 'SUCCEEDED' }), fallback)
  assert.deepEqual(describeAttempt('sync_retry', { status: 'OTHER' }), fallback)
})

test('operationErrorText formats ApiErrors correctly (ADM-F1)', () => {
  assert.equal(operationErrorText({ status: 409 }), 'This action is not supported for this connection.')
  assert.equal(operationErrorText({ status: 403 }), 'Only owners and managers can run this action.')
  assert.equal(operationErrorText({ status: 0 }), 'The server could not be reached. Try again in a moment.')
  assert.equal(operationErrorText({ status: 408 }), 'The server could not be reached. Try again in a moment.')
  assert.equal(
    operationErrorText({ status: 400, detail: 'Retry backoff has not elapsed.' }),
    'Retry backoff has not elapsed.',
  )
  assert.equal(operationErrorText({ status: 400 }), 'The action could not be started.')
  assert.equal(operationErrorText(null), 'The action could not be started.')
  assert.equal(operationErrorText({}), 'The action could not be started.')
})

test('Admin.js source code uses idempotency key and operations lib (ADM-F1)', () => {
  const adminSource = fs.readFileSync(path.join(ROOT, 'src/components/Admin.js'), 'utf8')

  const occurrences = (adminSource.match(/operationBody\(newIdempotencyKey\(\)\)/g) || []).length
  assert.ok(
    occurrences >= 2,
    `Admin.js should contain operationBody(newIdempotencyKey()) at least twice, found ${occurrences}`,
  )

  assert.match(adminSource, /\bdescribeAttempt\b/)
  assert.match(adminSource, /\boperationErrorText\b/)

  assert.doesNotMatch(adminSource, /'Attempt recorded — Succeeded' : 'Attempt recorded — Succeeded'/)

  // Verify handlers don't have body: {}
  const testConnHandlerMatch = adminSource.match(/const handleTestConnection[\s\S]*?\/\/ Handle Sync Retry/)
  assert.ok(testConnHandlerMatch, 'handleTestConnection block found')
  assert.doesNotMatch(testConnHandlerMatch[0], /body:\s*\{\}/)

  const retrySyncHandlerMatch = adminSource.match(/const handleRetrySync[\s\S]*?const effectiveSections/)
  assert.ok(retrySyncHandlerMatch, 'handleRetrySync block found')
  assert.doesNotMatch(retrySyncHandlerMatch[0], /body:\s*\{\}/)
})
