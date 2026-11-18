import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const ROOT = path.resolve(__dirname, '..')

test('source text: SteadfastRefreshShipment.js and Commerce.js (SHP-F2)', () => {
  const compPath = path.join(ROOT, 'src/components/SteadfastRefreshShipment.js')
  assert.ok(fs.existsSync(compPath), 'SteadfastRefreshShipment.js must exist')
  const compContent = fs.readFileSync(compPath, 'utf8')
  assert.match(compContent, /^'use client'/)
  assert.match(compContent, /from\s+['"]@\/lib\/shipping\/steadfast['"]/)
  assert.match(compContent, /from\s+['"]@\/lib\/clientApi['"]/)
  assert.match(compContent, /from\s+['"]@\/components\/ui['"]/)

  // Verify all imported ui components exist in ui/index.js
  const uiIndexContent = fs.readFileSync(path.join(ROOT, 'src/components/ui/index.js'), 'utf8')
  const uiImportsMatch = compContent.match(/import\s+\{([^}]+)\}\s+from\s+['"]@\/components\/ui['"]/)
  assert.ok(uiImportsMatch, 'Must import named members from @/components/ui')
  const importedUiNames = uiImportsMatch[1].split(',').map((s) => s.trim())
  for (const name of importedUiNames) {
    assert.ok(uiIndexContent.includes(name), `UI kit index must export ${name}`)
  }

  // Required function/path names
  const reqNames = [
    'isSteadfastShipment',
    'canManageSteadfast',
    'canRefreshShipment',
    'refreshShipmentPath',
    'normalizeRefreshResult',
    'describeRefresh',
    'describeRefreshError',
    "method: 'POST'",
    'aria-live="polite"',
  ]
  for (const n of reqNames) {
    assert.ok(compContent.includes(n), `SteadfastRefreshShipment.js must include "${n}"`)
  }

  // Required exact texts
  const reqTexts = [
    'Courier status (Steadfast)',
    'Status in Bizora',
    'Check status with Steadfast',
    'Only owners and managers can check courier status.',
    'This only reads from Steadfast.',
    'Last checked',
  ]
  for (const t of reqTexts) {
    assert.ok(compContent.includes(t), `SteadfastRefreshShipment.js must include "${t}"`)
  }

  // Banned patterns
  assert.doesNotMatch(compContent, /\bwindow\.confirm\b/)
  assert.doesNotMatch(compContent, /\bIdempotency-Key\b/i)
  assert.doesNotMatch(compContent, /courier says/i)
  assert.doesNotMatch(compContent, /Steadfast says/i)
  assert.doesNotMatch(compContent, /Steadfast reports/i)
  assert.doesNotMatch(compContent, /<Banner\b[^>]*\btone=/)

  const hex = compContent.match(/#(?:[0-9a-fA-F]{3}){1,2}\b/g) || []
  assert.equal(hex.length, 0, 'No raw hex')
  const px = compContent.match(/\b\d+px\b/g) || []
  assert.equal(px.length, 0, 'No px units')

  // Commerce.js checks
  const commercePath = path.join(ROOT, 'src/components/Commerce.js')
  const commerceContent = fs.readFileSync(commercePath, 'utf8')
  assert.match(
    commerceContent,
    /import\s+SteadfastRefreshShipment\s+from\s+['"]\.\/SteadfastRefreshShipment['"]/,
  )
  assert.match(commerceContent, /<SteadfastRefreshShipment/)
  assert.ok(commerceContent.includes('shipment={currentRecord}'))
  assert.ok(commerceContent.includes('row.tracking_code'))
  assert.ok(commerceContent.includes('currentRecord.tracking_code'))
  assert.ok(commerceContent.includes('Prepared — not executed'))
  assert.ok(commerceContent.includes('Prepare Carrier Dispatch Sync'))
  assert.doesNotMatch(commerceContent, /\btracking_number\b/)
})
