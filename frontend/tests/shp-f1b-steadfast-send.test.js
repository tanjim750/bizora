import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const ROOT = path.resolve(__dirname, '..')

test('source text: SteadfastSendOrder.js and Commerce.js (SHP-F1b)', () => {
  const compPath = path.join(ROOT, 'src/components/SteadfastSendOrder.js')
  assert.ok(fs.existsSync(compPath), 'SteadfastSendOrder.js must exist')
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
    'canManageSteadfast',
    'providersPath',
    'connectionsPath',
    'createShipmentPath',
    'steadfastProviderId',
    'normalizeConnections',
    'connectionAvailability',
    'findSteadfastShipment',
    'prefillShipmentForm',
    'validateShipmentForm',
    'confirmedAbsentBody',
    'describeCreateError',
    'normalizeCreateResult',
    'invoiceFor',
    "method: 'POST'",
  ]
  for (const n of reqNames) {
    assert.ok(compContent.includes(n), `SteadfastSendOrder.js must include "${n}"`)
  }

  // Required exact texts
  const reqTexts = [
    'Courier (Steadfast)',
    'Only owners and managers can send orders to Steadfast.',
    'Send to Steadfast',
    'Review shipment',
    'This books a real parcel with the courier',
    'Steadfast is not connected for sending',
    'Looking for the Steadfast connection',
    'Steadfast may already have this parcel',
    'I checked the Steadfast portal',
    'Send again',
    'Send this parcel to Steadfast now?',
    'This order had already been sent to Steadfast. No new parcel was created.',
    'aria-live="polite"',
  ]
  for (const t of reqTexts) {
    assert.ok(compContent.includes(t), `SteadfastSendOrder.js must include "${t}"`)
  }

  // Banned patterns
  assert.doesNotMatch(compContent, /\bwindow\.confirm\b/)
  assert.doesNotMatch(compContent, /\bIdempotency-Key\b/i)
  assert.doesNotMatch(compContent, /\bapi_key\b/i)
  assert.doesNotMatch(compContent, /\bsecret_key\b/i)
  assert.doesNotMatch(compContent, /<Banner\b[^>]*\btone=/)
  assert.doesNotMatch(compContent, /simulated/i)
  assert.doesNotMatch(compContent, /prepared/i)

  const hex = compContent.match(/#(?:[0-9a-fA-F]{3}){1,2}\b/g) || []
  assert.equal(hex.length, 0, 'No raw hex')
  const px = compContent.match(/\b\d+px\b/g) || []
  assert.equal(px.length, 0, 'No px units')

  // Commerce.js checks
  const commercePath = path.join(ROOT, 'src/components/Commerce.js')
  const commerceContent = fs.readFileSync(commercePath, 'utf8')
  assert.match(commerceContent, /import\s+SteadfastSendOrder\s+from\s+['"]\.\/SteadfastSendOrder['"]/)
  assert.match(commerceContent, /<SteadfastSendOrder/)
  assert.ok(commerceContent.includes('role={business?.role}'))
  assert.ok(commerceContent.includes('shipments={activeRecord?.shipments?.results}'))
})
