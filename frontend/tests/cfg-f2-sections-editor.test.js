import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  choices,
  TASKS,
  CONTEXTS,
  ACTIONS,
  KNOWLEDGE_TYPES,
  SOURCE_TYPES,
  SECTION_SPECS,
  validTimeZone,
  crossChecks,
  buildSectionSave,
  SECTION_RESOURCES,
} from '../src/lib/configuration/sections.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const ROOT = path.resolve(__dirname, '..')

test('sections lib: choices, constants, and specs definitions (CFG-F2)', () => {
  assert.deepEqual(choices('SOCIAL_COMMERCE', 'approved_policies', '12H', '.'), [
    { value: 'SOCIAL_COMMERCE', label: 'Social commerce' },
    { value: 'approved_policies', label: 'Approved policies' },
    { value: '12H', label: '12H' },
    { value: '.', label: '.' },
  ])

  assert.deepEqual(TASKS, [
    'business_assistant',
    'customer_support',
    'marketing',
    'summarization',
    'recommendations',
  ])
  assert.deepEqual(CONTEXTS, [
    'profile',
    'facts',
    'metrics',
    'issues',
    'relationships',
    'graph',
    'approved_policies',
    'knowledge',
    'goals',
  ])
  assert.deepEqual(ACTIONS, [
    'CREATE_SUPPORT_DRAFT',
    'PROPOSE_COURIER_CHANGE',
    'PROPOSE_CAMPAIGN_CHANGE',
    'CREATE_TASK',
  ])
  assert.deepEqual(KNOWLEDGE_TYPES, [
    'PROFILE',
    'POLICY',
    'PRODUCT',
    'SUPPORT',
    'BRAND',
    'INTERNAL',
    'GOALS',
    'DECISIONS',
  ])
  assert.deepEqual(SOURCE_TYPES, ['MANUAL', 'UPLOAD', 'WEBSITE', 'INTEGRATION'])

  assert.equal(SECTION_SPECS.profile.length, 11)
  assert.equal(SECTION_SPECS.general.length, 22)
  assert.equal(SECTION_SPECS.ai.length, 23)
  assert.equal(SECTION_SPECS.knowledge.length, 16)

  // Verify key required fields
  const nameSpec = SECTION_SPECS.profile.find((s) => s.path === 'name')
  assert.ok(nameSpec && nameSpec.required === true)

  const currSpec = SECTION_SPECS.general.find((s) => s.path === 'currency')
  assert.ok(currSpec && currSpec.required === true)

  const confSpec = SECTION_SPECS.ai.find((s) => s.path === 'confidence_threshold')
  assert.ok(confSpec && confSpec.required === true)

  // Verify banned paths are absent in all specs
  const bannedPaths = [
    'guardrails',
    'metadata',
    'workflows',
    'workflow_scopes',
    'execution.approval_required',
    'escalation.on_low_confidence',
  ]
  for (const [sec, specs] of Object.entries(SECTION_SPECS)) {
    for (const spec of specs) {
      assert.ok(!bannedPaths.includes(spec.path), `${sec} must not contain banned path ${spec.path}`)
    }
  }

  // TimeZone check
  assert.equal(validTimeZone('Asia/Dhaka'), true)
  assert.equal(validTimeZone('UTC'), true)
  assert.equal(validTimeZone('Mars/Base'), false)
  assert.equal(validTimeZone(''), false)
})

test('sections lib: verified examples and save builders (CFG-F2)', () => {
  // general example
  const R = {
    version: 0,
    status: 'ACTIVE',
    settings: {
      currency: 'BDT',
      timezone: 'Asia/Dhaka',
      locale: 'en',
      language: 'en',
      date_format: 'YYYY-MM-DD',
      time_format: '24H',
      decimal_places: 2,
      decimal_separator: '.',
      thousands_separator: ',',
      currency_display: 'CODE',
      reporting_period: 'DAY',
      week_start: 0,
      operational_defaults: {},
      features: {},
      metadata: {},
    },
  }
  const D = SECTION_RESOURCES.general.draftFor(R)
  assert.equal(Object.keys(D).length, 23)

  assert.deepEqual(buildSectionSave('general', R, D), { errors: {}, changed: false, body: null })
  assert.deepEqual(buildSectionSave('general', R, { ...D, reason: 'only a reason' }), {
    errors: {},
    changed: false,
    body: null,
  })

  const changedGen = {
    ...D,
    week_start: '6',
    'features.calling': true,
    reason: 'weekend start',
  }
  assert.deepEqual(buildSectionSave('general', R, changedGen), {
    errors: {},
    changed: true,
    body: {
      version: 0,
      week_start: 6,
      features: { calling: true },
      reason: 'weekend start',
    },
  })

  assert.deepEqual(buildSectionSave('general', R, { ...D, thousands_separator: '' }), {
    errors: {},
    changed: true,
    body: { version: 0, thousands_separator: '' },
  })

  // Cross checks errors on general
  assert.deepEqual(buildSectionSave('general', R, { ...D, decimal_separator: ',', timezone: 'Mars/Base' }), {
    errors: {
      timezone: 'Use a valid IANA time zone.',
      thousands_separator: 'Decimal and thousands separators must differ.',
    },
    changed: true,
    body: null,
  })

  // Validation error and stale/version error
  assert.deepEqual(buildSectionSave('general', R, { ...D, decimal_places: '' }), {
    errors: { decimal_places: 'Decimal places is required.' },
    changed: false,
    body: null,
  })

  assert.deepEqual(buildSectionSave('general', { ...R, version: null }, { ...D, week_start: '1' }), {
    errors: { _form: 'The current version is unknown. Reload before saving.' },
    changed: true,
    body: null,
  })

  // knowledge example
  const K = {
    version: 3,
    status: 'ACTIVE',
    settings: {
      knowledge_types: ['POLICY'],
      ingestion: { allowed_types: ['MANUAL'], max_document_bytes: 1000000 },
      chunk_size: 500,
      chunk_overlap: 50,
      embedding_model: 'mock-embedding',
      vector: { enabled: true, limit: 8, minimum_similarity: '0.7000' },
      keyword: { enabled: true, limit: 8 },
      hybrid: { enabled: true, vector_weight: '0.6000', keyword_weight: '0.4000' },
      retrieval_limit: 10,
      workflow_scopes: {},
      include_archived_for_history: false,
    },
  }
  const DK = SECTION_RESOURCES.knowledge.draftFor(K)
  assert.equal(buildSectionSave('knowledge', K, DK).changed, false)

  assert.deepEqual(
    buildSectionSave('knowledge', K, {
      ...DK,
      chunk_size: '700',
      'hybrid.vector_weight': '0.7',
      'hybrid.keyword_weight': '0.3',
    }),
    {
      errors: {},
      changed: true,
      body: {
        version: 3,
        chunk_size: 700,
        hybrid: { vector_weight: '0.7', keyword_weight: '0.3' },
      },
    },
  )

  assert.deepEqual(
    buildSectionSave('knowledge', K, {
      ...DK,
      chunk_size: '500',
      chunk_overlap: '600',
      'hybrid.vector_weight': '0.8',
      'hybrid.keyword_weight': '0.4',
    }),
    {
      errors: {
        chunk_overlap: 'Chunk overlap must be smaller than chunk size.',
        'hybrid.keyword_weight': 'Hybrid weights must add up to 1.',
      },
      changed: true,
      body: null,
    },
  )

  assert.deepEqual(
    buildSectionSave('knowledge', K, {
      ...DK,
      'vector.enabled': false,
    }),
    {
      errors: {
        'hybrid.enabled': 'Hybrid search needs vector and keyword search switched on.',
      },
      changed: true,
      body: null,
    },
  )

  // profile example
  const P = {
    version: 2,
    status: 'ACTIVE',
    settings: {
      name: 'Shop',
      description: '',
      industry: '',
      contact: {},
      location: {},
      operating_regions: [],
      channels: [],
      currency: 'BDT',
      timezone: 'Asia/Dhaka',
      metadata: {},
    },
  }
  const DP = SECTION_RESOURCES.profile.draftFor(P)
  assert.deepEqual(
    buildSectionSave('profile', P, {
      ...DP,
      name: 'Renamed',
      'contact.email': 'help@example.com',
      operating_regions: 'Dhaka\nGazipur',
      channels: ['DIRECT'],
      'location.country': 'BD',
    }),
    {
      errors: {},
      changed: true,
      body: {
        version: 2,
        name: 'Renamed',
        contact: { email: 'help@example.com' },
        location: { country: 'BD' },
        operating_regions: ['Dhaka', 'Gazipur'],
        channels: ['DIRECT'],
      },
    },
  )

  assert.deepEqual(
    buildSectionSave('profile', P, {
      ...DP,
      'contact.email': 'bad',
    }),
    {
      errors: {
        'contact.email': 'Enter a valid email address.',
      },
      changed: true,
      body: null,
    },
  )

  // ai example
  const A = {
    version: 1,
    status: 'ACTIVE',
    settings: {
      enabled: false,
      provider: 'mock',
      models: {},
      features: { business_assistant: false },
      context_categories: ['profile', 'facts', 'approved_policies'],
      response: { language: 'en', detail: 'NORMAL', tone: 'PROFESSIONAL' },
      confidence_threshold: '0.7',
      escalation: { on_low_confidence: true, topics: [] },
      allowed_actions: [],
      execution: { approval_required: true, disabled_actions: [] },
      parameters: { temperature: '0.2', max_output_tokens: 1000 },
      workflows: {},
      guardrails: { evidence_required: true },
    },
  }
  const DA = SECTION_RESOURCES.ai.draftFor(A)
  assert.equal(Object.keys(DA).length, 24)
  assert.deepEqual(
    buildSectionSave('ai', A, {
      ...DA,
      enabled: true,
      'models.business_assistant': 'mock-business',
      'features.business_assistant': true,
      confidence_threshold: '0.8',
      'escalation.topics': 'refund',
      allowed_actions: ['CREATE_TASK'],
    }),
    {
      errors: {},
      changed: true,
      body: {
        version: 1,
        enabled: true,
        models: { business_assistant: 'mock-business' },
        features: { business_assistant: true },
        confidence_threshold: '0.8',
        escalation: { topics: ['refund'] },
        allowed_actions: ['CREATE_TASK'],
      },
    },
  )

  // Resource definition contract properties
  assert.equal(SECTION_RESOURCES.general.updateMethod, 'PUT')
  assert.equal(SECTION_RESOURCES.general.createPath, null)
  assert.equal(SECTION_RESOURCES.general.itemPath(7), 'businesses/7/configuration/general/')
})

test('source text: components existence, contracts, and styling rules (CFG-F2)', () => {
  const componentFiles = [
    'ConfigFields.js',
    'ConfigRecordForm.js',
    'ConfigSectionsEditor.js',
    'ConfigViewNav.js',
  ]

  for (const file of componentFiles) {
    const fullPath = path.join(ROOT, 'src/components', file)
    assert.ok(fs.existsSync(fullPath), `${file} must exist`)
    const content = fs.readFileSync(fullPath, 'utf8')
    assert.match(content, /^'use client'/, `${file} must start with 'use client'`)

    // No window.confirm
    assert.doesNotMatch(content, /\bwindow\.confirm\b/, `${file} must not use window.confirm`)

    // No tone= on Banner
    assert.doesNotMatch(content, /<Banner\b[^>]*\btone=/, `${file} must not use tone= on Banner`)

    // No open= on Dialog
    assert.doesNotMatch(content, /<Dialog\b[^>]*\sopen=\{/, `${file} must not use open= on Dialog`)

    // No raw hex
    const hex = content.match(/#(?:[0-9a-fA-F]{3}){1,2}\b/g) || []
    assert.equal(hex.length, 0, `Found raw hex in ${file}: ${hex.join(', ')}`)
  }

  // ConfigFields checks
  const fieldsContent = fs.readFileSync(path.join(ROOT, 'src/components/ConfigFields.js'), 'utf8')
  assert.match(fieldsContent, /from\s+['"]@\/components\/ui['"]/)
  assert.match(fieldsContent, /from\s+['"]@\/lib\/configuration\/fieldKit['"]/)
  assert.match(fieldsContent, /role="alert"/)
  assert.match(fieldsContent, /<fieldset/)

  // ConfigRecordForm checks
  const formContent = fs.readFileSync(path.join(ROOT, 'src/components/ConfigRecordForm.js'), 'utf8')
  assert.ok(formContent.includes('Reload and keep my edits'))
  assert.ok(formContent.includes('Could not save'))
  assert.ok(formContent.includes('Save changes'))
  assert.match(formContent, /resource\.updateMethod/)
  assert.match(formContent, /\bclassifyWriteError\b/)
  assert.match(formContent, /\brebaseDraft\b/)

  // ConfigSectionsEditor checks
  const editorContent = fs.readFileSync(path.join(ROOT, 'src/components/ConfigSectionsEditor.js'), 'utf8')
  assert.match(editorContent, /aria-live="polite"/)
  assert.ok(editorContent.includes('Save or discard your changes before switching sections.'))
  assert.ok(editorContent.includes('You can view these settings. Only owners and managers can change them.'))
  assert.match(editorContent, /router\.refresh\(\)/)
  assert.match(editorContent, /\bsectionPath\b/)

  // Admin.js checks
  const adminContent = fs.readFileSync(path.join(ROOT, 'src/components/Admin.js'), 'utf8')
  assert.match(adminContent, /\bConfigSectionsEditor\b/)
  assert.match(adminContent, /\bConfigViewNav\b/)
  assert.match(adminContent, /\bCONFIG_VIEWS\b/)
  assert.match(adminContent, /configView === ['"]effective['"]/)
  assert.ok(adminContent.includes('Preview 409 Concurrency Banner'))
  assert.ok(adminContent.includes('Someone else changed this configuration. Reload to continue.'))
  assert.doesNotMatch(adminContent, /\bVersion: v1\b/)
})
