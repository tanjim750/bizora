import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  controlSpecs,
  KEY_MESSAGE,
  scopeSummary,
  buildResourceSave,
} from '../src/lib/configuration/resources.js'
import {
  RULE_CATEGORIES,
  OPERATORS,
  parseScalar,
  parseCondition,
  parseConditions,
  formatConditions,
  RULE_FIELD_SPECS,
  ruleSpecs,
  buildRuleSave,
  RULES_RESOURCE,
} from '../src/lib/configuration/rules.js'
import {
  POLICY_CATEGORIES,
  PARAMETER_SPECS,
  policySpecs,
  buildPolicySave,
  POLICIES_RESOURCE,
} from '../src/lib/configuration/policies.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const ROOT = path.resolve(__dirname, '..')

test('resources lib: controlSpecs, scopeSummary, buildResourceSave (CFG-F3)', () => {
  const specsDefault = controlSpecs('DRAFT')
  assert.equal(specsDefault.length, 3)
  const statusSpec = specsDefault.find((s) => s.path === 'status')
  assert.deepEqual(
    statusSpec.options.map((o) => o.value),
    ['DRAFT', 'ACTIVE', 'DISABLED', 'ARCHIVED'],
  )

  const specsSuperseded = controlSpecs('SUPERSEDED')
  assert.deepEqual(
    specsSuperseded.find((s) => s.path === 'status').options.map((o) => o.value),
    ['DRAFT', 'ACTIVE', 'DISABLED', 'ARCHIVED', 'SUPERSEDED'],
  )

  assert.equal(scopeSummary(null), 'Everywhere')
  assert.equal(scopeSummary({}), 'Everywhere')
  assert.equal(
    scopeSummary({ region: 'Gazipur', courier: 'Courier X' }),
    'courier: Courier X, region: Gazipur',
  )

  // buildResourceSave invalid key on create
  const invalidKeyRes = buildResourceSave({
    specs: specsDefault,
    record: null,
    draft: { status: 'DRAFT' },
    key: 'Bad Key',
    creating: true,
  })
  assert.equal(invalidKeyRes.errors.key, KEY_MESSAGE)
  assert.equal(invalidKeyRes.body, null)

  // buildResourceSave missing version on update
  const unkVersionRes = buildResourceSave({
    specs: specsDefault,
    record: { version: null, settings: {} },
    draft: { status: 'ACTIVE' },
    key: 'valid_key',
    creating: false,
  })
  assert.equal(unkVersionRes.errors._form, 'The current version is unknown. Reload before saving.')
  assert.equal(unkVersionRes.body, null)

  // buildResourceSave reason-only is not changed
  const reasonOnlyRes = buildResourceSave({
    specs: specsDefault,
    record: { version: 1, status: 'DRAFT', settings: {} },
    draft: { status: 'DRAFT', reason: 'just reason' },
    creating: false,
  })
  assert.equal(reasonOnlyRes.changed, false)
  assert.equal(reasonOnlyRes.body, null)
})

test('rules lib: parsing, formatting, specs, buildRuleSave (CFG-F3)', () => {
  assert.equal(parseScalar('  5  '), 5)
  assert.equal(parseScalar('  -3.14 '), -3.14)
  assert.equal(parseScalar('true'), true)
  assert.equal(parseScalar('false'), false)
  assert.equal(parseScalar('DELIVERED'), 'DELIVERED')

  // parseCondition
  assert.deepEqual(parseCondition('delivery_failure_rate gt 15'), {
    field: 'delivery_failure_rate',
    operator: 'gt',
    value: '15',
  })
  assert.deepEqual(parseCondition('status eq DELIVERED'), {
    field: 'status',
    operator: 'eq',
    value: 'DELIVERED',
  })
  assert.deepEqual(parseCondition('region in Dhaka, Gazipur'), {
    field: 'region',
    operator: 'in',
    value: ['Dhaka', 'Gazipur'],
  })

  assert.throws(() => parseCondition('bad_line'), /Write field, operator and value/)
  assert.throws(() => parseCondition('9field eq 1'), /Field names use letters, digits and underscores/)
  assert.throws(
    () => parseCondition('field invalid_op 1'),
    /Operator must be one of gt, gte, lt, lte, eq, ne, in, not_in/,
  )
  assert.throws(() => parseCondition('field gt not_a_num'), /Use a number with at most 6 decimals/)
  assert.throws(() => parseCondition('field in , , '), /Use 1 to 50 values separated by commas/)

  // parseConditions
  assert.deepEqual(parseConditions('   \n\n  '), {
    conditions: [],
    error: 'Add at least one condition.',
  })
  const parsedMultiple = parseConditions('\n  delivery_failure_rate gt 15\n\n  region in Dhaka, Gazipur\n')
  assert.equal(parsedMultiple.error, null)
  assert.equal(parsedMultiple.conditions.length, 2)

  // formatConditions
  const formatted = formatConditions({
    all: [{ field: 'delivery_failure_rate', operator: 'gt', value: '15' }],
  })
  assert.deepEqual(formatted, {
    mode: 'all',
    text: 'delivery_failure_rate gt 15',
  })

  // RULE_FIELD_SPECS paths
  const rulePaths = RULE_FIELD_SPECS.map((s) => s.path)
  assert.deepEqual(rulePaths, [
    'category',
    'description',
    'outcome.type',
    'outcome.code',
    'outcome.severity',
    'sample_metric',
    'min_samples',
    'window_days',
  ])

  // Verified buildRuleSave example on create
  const ruleDraft = {
    category: 'DELIVERY',
    'outcome.type': 'ALERT',
    'outcome.code': 'HIGH_FAILURE',
    'outcome.severity': 'HIGH',
    status: 'DRAFT',
    conditions_mode: 'all',
    conditions: 'delivery_failure_rate gt 15',
  }
  const createRuleRes = buildRuleSave({
    record: null,
    creating: true,
    key: 'my_rule',
    draft: ruleDraft,
  })
  assert.deepEqual(createRuleRes.errors, {})
  assert.deepEqual(createRuleRes.body, {
    key: 'my_rule',
    category: 'DELIVERY',
    outcome: { type: 'ALERT', code: 'HIGH_FAILURE', severity: 'HIGH' },
    status: 'DRAFT',
    conditions: {
      all: [{ field: 'delivery_failure_rate', operator: 'gt', value: '15' }],
    },
  })

  // Edit saved rule: conditions unchanged
  const savedRule = {
    version: 1,
    status: 'ACTIVE',
    key: 'my_rule',
    settings: {
      category: 'DELIVERY',
      outcome: { type: 'ALERT', code: 'HIGH_FAILURE', severity: 'HIGH' },
      conditions: {
        all: [{ field: 'delivery_failure_rate', operator: 'gt', value: '15' }],
      },
    },
  }
  const editRuleDraft = {
    ...RULES_RESOURCE.draftFor(savedRule),
    status: 'DISABLED',
    window_days: '45',
  }
  const editRuleRes = buildRuleSave({
    record: savedRule,
    creating: false,
    key: 'my_rule',
    draft: editRuleDraft,
  })
  assert.deepEqual(editRuleRes.errors, {})
  assert.deepEqual(editRuleRes.body, {
    version: 1,
    status: 'DISABLED',
    window_days: 45,
  })
  assert.equal(editRuleRes.body.conditions, undefined)

  // Resource definition checks
  assert.equal(RULES_RESOURCE.itemPath(7, { key: 'r1' }), 'businesses/7/configuration/rules/r1/')
  assert.equal(RULES_RESOURCE.createPath(7), 'businesses/7/configuration/rules/')
  assert.equal(
    RULES_RESOURCE.listPath(7, { page: 2, pageSize: 25 }),
    'businesses/7/configuration/rules/?page=2&page_size=25',
  )
  assert.deepEqual(RULES_RESOURCE.lockedPaths({ creating: false }), ['conditions_mode'])
})

test('policies lib: specs, buildPolicySave, verified examples (CFG-F3)', () => {
  // policySpecs: non-active drops required and minItems
  const draftActive = { category: 'RETURN', status: 'ACTIVE' }
  const activeSpecs = policySpecs(null, draftActive)
  const activeProc = activeSpecs.find((s) => s.path === 'parameters.procedure')
  assert.equal(activeProc.required, true)
  const activeTerms = activeSpecs.find((s) => s.path === 'terms')
  assert.equal(activeTerms.required, true)

  const draftNonActive = { category: 'RETURN', status: 'DRAFT' }
  const nonActiveSpecs = policySpecs(null, draftNonActive)
  const nonActiveProc = nonActiveSpecs.find((s) => s.path === 'parameters.procedure')
  assert.equal(nonActiveProc.required, false)
  const nonActiveTerms = nonActiveSpecs.find((s) => s.path === 'terms')
  assert.equal(nonActiveTerms.required, false)

  // Verified buildPolicySave create returns expected body
  const pDraft = {
    ...draftFromSettings(policySpecs(null, { category: 'RETURN', status: 'ACTIVE' }), { status: 'ACTIVE' }),
    category: 'RETURN',
    title: 'Returns',
    terms: 'Unused products may be returned.',
    ai_available: true,
    'parameters.window_days': '7',
    'parameters.eligibility': 'UNUSED',
    'parameters.procedure': 'Contact support',
    status: 'ACTIVE',
  }
  const createPolicyRes = buildPolicySave({
    record: null,
    creating: true,
    key: 'returns',
    draft: pDraft,
  })
  assert.deepEqual(createPolicyRes.errors, {})
  assert.deepEqual(createPolicyRes.body, {
    key: 'returns',
    terms: 'Unused products may be returned.',
    parameters: {
      window_days: 7,
      eligibility: ['UNUSED'],
      procedure: 'Contact support',
    },
    category: 'RETURN',
    title: 'Returns',
    ai_available: true,
    status: 'ACTIVE',
  })

  // DRAFT with empty parameters.procedure is valid
  const draftPolicyRes = buildPolicySave({
    record: null,
    creating: true,
    key: 'returns',
    draft: { ...pDraft, status: 'DRAFT', 'parameters.procedure': '' },
  })
  assert.deepEqual(draftPolicyRes.errors, {})

  // ACTIVE with empty parameters.procedure returns error
  const activeMissingProcRes = buildPolicySave({
    record: null,
    creating: true,
    key: 'returns',
    draft: { ...pDraft, status: 'ACTIVE', 'parameters.procedure': '' },
  })
  assert.equal(activeMissingProcRes.errors['parameters.procedure'], 'Procedure is required.')

  // Resource definition checks
  assert.deepEqual(POLICIES_RESOURCE.lockedPaths({ creating: false }), ['category'])
})

test('source text: ConfigResourceManager, ConfigRulesPolicies, Admin.js (CFG-F3)', () => {
  const componentFiles = ['ConfigResourceManager.js', 'ConfigRulesPolicies.js']

  for (const file of componentFiles) {
    const fullPath = path.join(ROOT, 'src/components', file)
    assert.ok(fs.existsSync(fullPath), `${file} must exist`)
    const content = fs.readFileSync(fullPath, 'utf8')
    assert.match(content, /^'use client'/, `${file} must start with 'use client'`)
    assert.doesNotMatch(content, /\bwindow\.confirm\b/, `${file} must not use window.confirm`)
    assert.doesNotMatch(content, /<Banner\b[^>]*\btone=/, `${file} must not use tone= on Banner`)
    assert.doesNotMatch(content, /<Dialog\b[^>]*\sopen=\{/, `${file} must not use open= on Dialog`)

    const hex = content.match(/#(?:[0-9a-fA-F]{3}){1,2}\b/g) || []
    assert.equal(hex.length, 0, `Found raw hex in ${file}: ${hex.join(', ')}`)
  }

  const managerContent = fs.readFileSync(path.join(ROOT, 'src/components/ConfigResourceManager.js'), 'utf8')
  assert.match(managerContent, /aria-live="polite"/)
  assert.ok(
    managerContent.includes('You can view this configuration. Only owners and managers can change it.'),
  )
  assert.ok(managerContent.includes('Could not open the record'))
  assert.match(managerContent, /router\.refresh\(\)/)
  assert.ok(managerContent.includes('isOpen'))
  assert.match(managerContent, /\bConfigRecordForm\b/)

  const adminContent = fs.readFileSync(path.join(ROOT, 'src/components/Admin.js'), 'utf8')
  assert.match(adminContent, /\bConfigRulesPolicies\b/)
  assert.ok(adminContent.includes('Rules & policies'))
})

// Helper needed by test
import { draftFromSettings } from '../src/lib/configuration/fieldKit.js'
