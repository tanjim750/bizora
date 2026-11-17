import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

test('ai studio workspace enforces token styles, zero raw hex, and honest wording', () => {
  const aiFile = path.resolve('src/components/AiStudio.js')
  const content = fs.readFileSync(aiFile, 'utf8')

  // Zero raw hex color values outside comments
  const codeWithoutComments = content.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '')
  const hexMatches = codeWithoutComments.match(/#[0-9a-fA-F]{3,8}\b/g)
  assert.equal(hexMatches, null, `Found raw hex color in AiStudio.js: ${hexMatches}`)

  // Verifies all three tabs are supported
  assert.ok(content.includes("activeTab === 'assistant'"), 'Assistant tab missing')
  assert.ok(content.includes("activeTab === 'actions'"), 'Actions tab missing')
  assert.ok(content.includes("activeTab === 'audit'"), 'Audit tab missing')

  // Verifies honest wording per 00-project-law.md and contracts
  assert.ok(content.includes('Execution is simulated.'), 'Honest simulated execution wording missing')
  assert.ok(content.includes('Answers are advisory and synthesized'), 'Advisory disclaimer missing')
  assert.ok(content.includes('UnavailableState'), 'Calm unavailable state missing')
})

test('ai studio review note validation and endpoint contracts match E1 and E16', () => {
  const aiFile = path.resolve('src/components/AiStudio.js')
  const content = fs.readFileSync(aiFile, 'utf8')

  // E1 Assistant query endpoint
  assert.ok(content.includes('businesses/${businessId}/ai/assistant/query'), 'E1 query endpoint missing')

  // E16 Action review endpoints
  assert.ok(content.includes('actions/${actionId}/approve'), 'E16 approve endpoint missing')
  assert.ok(content.includes('actions/${actionId}/reject'), 'E16 reject endpoint missing')

  // Review note length rule: 3 to 1000 chars
  assert.ok(content.includes('reviewNote.length < 3'), 'Min note length rule missing')
  assert.ok(content.includes('reviewNote.length > 1000'), 'Max note length rule missing')
})
