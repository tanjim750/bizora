import test from 'node:test'
import assert from 'node:assert/strict'
import { ApiError, normalizeError, errorMessage } from '../src/lib/api/errors.js'
import { isSafeRelativePath } from '../src/lib/api/client.js'

test('ApiError keeps status, code, detail, and fieldErrors map', () => {
  const err = new ApiError({
    status: 400,
    code: 'VALIDATION_ERROR',
    detail: 'Field amount is required.',
    fieldErrors: { amount: 'Field is required.' },
    raw: { amount: ['Field is required.'] },
  })

  assert.equal(err instanceof Error, true)
  assert.equal(err instanceof ApiError, true)
  assert.equal(err.name, 'ApiError')
  assert.equal(err.status, 400)
  assert.equal(err.code, 'VALIDATION_ERROR')
  assert.equal(err.detail, 'Field amount is required.')
  assert.deepEqual(err.fieldErrors, { amount: 'Field is required.' })
})

test('normalizeError parses all 7 backend error shapes correctly', () => {
  // Shape 1: Standard code and detail
  const shape1 = normalizeError({ code: 'NOT_FOUND', detail: 'Order #42 not found.' }, 404)
  assert.equal(shape1.code, 'NOT_FOUND')
  assert.equal(shape1.detail, 'Order #42 not found.')
  assert.equal(shape1.status, 404)

  // Shape 2: DRF detail only
  const shape2 = normalizeError({ detail: 'Authentication credentials were not provided.' }, 403)
  assert.equal(shape2.code, 'FORBIDDEN')
  assert.equal(shape2.detail, 'Authentication credentials were not provided.')

  // Shape 3: error or message key
  const shape3 = normalizeError({ error: 'Service temporarily unavailable.' }, 503)
  assert.equal(shape3.detail, 'Service temporarily unavailable.')

  // Shape 4: DRF field errors dictionary
  const shape4 = normalizeError(
    {
      amount: ['Must be greater than zero.'],
      reason: ['This field is required.'],
    },
    400,
  )
  assert.equal(shape4.code, 'VALIDATION_ERROR')
  assert.equal(shape4.fieldErrors.amount, 'Must be greater than zero.')
  assert.equal(shape4.fieldErrors.reason, 'This field is required.')
  assert.equal(shape4.detail, 'amount: Must be greater than zero.')

  // Shape 5: DRF bare list (Must NOT format as "0: message")
  const shape5 = normalizeError(['Item is required.', 'Minimum 1 item.'], 400)
  assert.equal(shape5.detail, 'Item is required. Minimum 1 item.')
  assert.equal(shape5.detail.includes('0:'), false)

  // Shape 6: Query filter error
  const shape6 = normalizeError({ query: "Unknown query parameter 'platform'." }, 400)
  assert.equal(shape6.fieldErrors.query, "Unknown query parameter 'platform'.")
  assert.equal(shape6.detail, "query: Unknown query parameter 'platform'.")

  // Shape 7: HTML / Non-JSON 500 string (including leading whitespace)
  const shape7 = normalizeError('<!DOCTYPE html><html><body>500 Internal Error</body></html>', 500)
  assert.equal(shape7.detail, 'Request failed (500)')
  const shape7Whitespace = normalizeError(
    '\n  \t<!DOCTYPE html><html><body>500 Internal Error</body></html>',
    500,
  )
  assert.equal(shape7Whitespace.detail, 'Request failed (500)')
})

test('errorMessage backward compatibility shim produces expected strings', () => {
  assert.equal(
    errorMessage({ amount: ['Must be greater than zero.'] }, 400),
    'amount: Must be greater than zero.',
  )
  assert.equal(errorMessage({ detail: 'Access denied.' }, 403), 'Access denied.')
})

test('isSafeRelativePath strictly allows only same-site relative paths', () => {
  assert.equal(isSafeRelativePath('/workspace'), true)
  assert.equal(isSafeRelativePath('/business/1/overview?tab=orders'), true)

  // Prevent open redirect vectors
  assert.equal(isSafeRelativePath('//attacker.com'), false)
  assert.equal(isSafeRelativePath('/\\attacker.com'), false)
  assert.equal(isSafeRelativePath('/foo\\bar'), false)
  assert.equal(isSafeRelativePath('/ \nattacker.com'), false)
  assert.equal(isSafeRelativePath('https://attacker.com'), false)
  assert.equal(isSafeRelativePath('http://attacker.com/workspace'), false)
  assert.equal(isSafeRelativePath('javascript:alert(1)'), false)
  assert.equal(isSafeRelativePath(''), false)
  assert.equal(isSafeRelativePath(null), false)
})
