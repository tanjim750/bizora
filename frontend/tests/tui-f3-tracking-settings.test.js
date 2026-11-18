import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { settingsPatchBody } from '../src/lib/tracking/api.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const ROOT = path.resolve(__dirname, '..')

test('TrackingIntegration.js implements manager settings editor (TUI-F3)', () => {
  const componentPath = path.join(ROOT, 'src/components/TrackingIntegration.js')
  const content = fs.readFileSync(componentPath, 'utf8')

  // Required imports
  assert.match(
    content,
    /import\s+[\s\S]*?\bsettingsPatchBody\b[\s\S]*?\bsettingsPath\b[\s\S]*?\bALLOWED_EVENTS\b[\s\S]*?from\s+['"]@\/lib\/tracking\/api['"]/,
  )
  assert.match(content, /import\s+[\s\S]*?\bMANAGER_ROLES\b[\s\S]*?from\s+['"]@\/lib\/catalog['"]/)

  // Required texts
  assert.ok(content.includes('Edit settings'), 'Expected "Edit settings" button text')
  assert.ok(content.includes('Tracking settings'), 'Expected "Tracking settings" dialog title text')
  assert.ok(
    content.includes('Personal identifiers are never sent'),
    'Expected "Personal identifiers are never sent" privacy guarantee text',
  )
  assert.ok(content.includes("method: 'PATCH'"), "Expected method: 'PATCH' in clientApi call")
  assert.ok(content.includes('Leave all unchecked'), 'Expected "Leave all unchecked" helper text for events')

  // Zero raw hex colors
  const hexMatches = content.match(/#(?:[0-9a-fA-F]{3}){1,2}\b/g) || []
  assert.equal(
    hexMatches.length,
    0,
    `Found raw hex colors in TrackingIntegration.js: ${hexMatches.join(', ')}`,
  )

  // No window.confirm
  assert.doesNotMatch(content, /\bwindow\.confirm\b/, 'Must not use window.confirm')
})

test('settingsPatchBody drops forbidden keys like send_pii and is_mock (TUI-F3)', () => {
  const connection = {
    id: 5,
    provider: 'meta',
    settings: {
      enabled: false,
      test_mode: false,
      events: [],
      test_event_code: null,
      measurement_id: null,
      api_version: null,
      send_pii: false,
    },
  }

  const draft = {
    enabled: true,
    send_pii: true,
    is_mock: false,
  }

  const body = settingsPatchBody(connection, draft)
  assert.deepEqual(body, { enabled: true })
  assert.equal(body.send_pii, undefined)
  assert.equal(body.is_mock, undefined)
})
