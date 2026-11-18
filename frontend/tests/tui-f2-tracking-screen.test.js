import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const ROOT = path.resolve(__dirname, '..')

test('TrackingIntegration.js exists and adheres to contracts and privacy rules (TUI-F2)', () => {
  const componentPath = path.join(ROOT, 'src/components/TrackingIntegration.js')
  assert.ok(fs.existsSync(componentPath), 'TrackingIntegration.js component must exist')

  const content = fs.readFileSync(componentPath, 'utf8')

  // Required imports
  assert.match(content, /from\s+['"]@\/lib\/tracking\/api['"]/)
  assert.match(content, /from\s+['"]@\/lib\/clientApi['"]/)
  assert.match(content, /from\s+['"]@\/components\/ui['"]/)

  // Required honest wording and privacy texts
  assert.ok(content.includes('Prepared, not sent'), 'Expected "Prepared, not sent" status text')
  assert.ok(
    content.includes('No tracking connection yet'),
    'Expected "No tracking connection yet" empty state title',
  )
  assert.ok(
    content.includes('No tracking events recorded yet'),
    'Expected "No tracking events recorded yet" empty state text',
  )
  assert.ok(
    content.includes('Personal identifiers are never sent'),
    'Expected "Personal identifiers are never sent" privacy guarantee text',
  )

  // Zero raw hex colors
  const hexMatches = content.match(/#(?:[0-9a-fA-F]{3}){1,2}\b/g) || []
  assert.equal(
    hexMatches.length,
    0,
    `Found raw hex colors in TrackingIntegration.js: ${hexMatches.join(', ')}`,
  )

  // Banned secret and payload words
  const bannedWords = ['payload', 'access_token', 'api_secret', 'endpoint_url']
  for (const word of bannedWords) {
    const wordRegex = new RegExp(`\\b${word}\\b`, 'i')
    assert.doesNotMatch(content, wordRegex, `TrackingIntegration.js must not contain banned word "${word}"`)
  }
})

test('Admin.js mounts TrackingIntegration under Integrations & Sync tab (TUI-F2)', () => {
  const adminSource = fs.readFileSync(path.join(ROOT, 'src/components/Admin.js'), 'utf8')

  assert.match(adminSource, /import\s+TrackingIntegration\s+from\s+['"]\.\/TrackingIntegration['"]/)
  assert.match(adminSource, /integrationsSubTab === ['"]tracking['"]/)
  assert.match(adminSource, />\s*Tracking\s*</)
})
