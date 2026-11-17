import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

test('support workspace enforces token styles, zero raw hex, and honest wording', () => {
  const supportFile = path.resolve('src/components/Support.js')
  const content = fs.readFileSync(supportFile, 'utf8')

  // Zero raw hex color values outside comments
  const codeWithoutComments = content.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '')
  const hexMatches = codeWithoutComments.match(/#[0-9a-fA-F]{3,8}\b/g)
  assert.equal(hexMatches, null, `Found raw hex color in Support.js: ${hexMatches}`)

  // Verifies all three tabs are supported
  assert.ok(content.includes("activeTab === 'inbox'"), 'Inbox tab missing')
  assert.ok(content.includes("activeTab === 'queue'"), 'Queue tab missing')
  assert.ok(content.includes("activeTab === 'calls'"), 'Calls tab missing')

  // Verifies honest wording per 00-project-law.md and contracts
  assert.ok(content.includes('Saved — not sent'), 'Honest saved-not-sent wording missing')
  assert.ok(content.includes('Prepared — not executed'), 'Honest prepared-not-executed wording missing')
  assert.ok(content.includes('UnavailableState'), 'Calm unavailable state missing')
  assert.ok(
    content.includes('The customer is not notified automatically'),
    'Handover notification disclaimer missing',
  )
})

test('support operations match D11, D12, and D17 contracts', () => {
  const supportFile = path.resolve('src/components/Support.js')
  const content = fs.readFileSync(supportFile, 'utf8')

  // D11 Assign
  assert.ok(content.includes('conversations/${activeConversation.id}/assign'), 'Assign endpoint missing')
  assert.ok(content.includes('assignee_type'), 'D11 assignee_type field missing')

  // D12 Handover
  assert.ok(content.includes('conversations/${activeConversation.id}/handover'), 'Handover endpoint missing')
  assert.ok(content.includes('handoverTarget'), 'D12 handover target missing')

  // D17 Priority
  assert.ok(content.includes('conversations/${activeConversation.id}/priority'), 'Priority endpoint missing')

  // D23 Schedule callback
  assert.ok(content.includes('callbacks/${selectedCall.id}/schedule'), 'Callback schedule endpoint missing')
})
