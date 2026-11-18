import test from 'node:test'
import assert from 'node:assert/strict'
import {
  CONFIG_SECTIONS,
  RESOURCE_KINDS,
  RECORD_STATES,
  SECTION_LABELS,
  KEY_PATTERN,
  listQuery,
  effectivePath,
  changesPath,
  sectionPath,
  sectionHistoryPath,
  resourcesPath,
  resourcePath,
  resourceHistoryPath,
  connectionsPath,
  connectionPath,
  connectionHistoryPath,
  sourcesPath,
  sourcePath,
  sourceHistoryPath,
  providersPath,
  reprocessingPath,
  monitoringPath,
  monitoringHistoryPath,
  freshnessPath,
  freshnessHistoryPath,
} from '../src/lib/configuration/paths.js'
import {
  STALE_MESSAGE,
  canEditConfiguration,
  expectedVersion,
  withVersion,
  flattenFieldErrors,
  classifyWriteError,
} from '../src/lib/configuration/writes.js'
import {
  actorLabel,
  normalizePage,
  normalizeRecord,
  recordSource,
} from '../src/lib/configuration/normalize.js'
import {
  REASON_SPEC,
  getPath,
  setPath,
  parseListText,
  draftFromSettings,
  validateDraft,
  patchFromDraft,
  fieldError,
  rebaseDraft,
} from '../src/lib/configuration/fieldKit.js'

test('paths: constants and query builder (CFG-F1)', () => {
  assert.deepEqual(CONFIG_SECTIONS, ['profile', 'general', 'ai', 'knowledge'])
  assert.deepEqual(RESOURCE_KINDS, ['rules', 'policies'])
  assert.deepEqual(RECORD_STATES, ['DRAFT', 'ACTIVE', 'DISABLED', 'SUPERSEDED', 'ARCHIVED'])
  assert.deepEqual(SECTION_LABELS, {
    profile: 'Business profile',
    general: 'General settings',
    ai: 'AI assistant',
    knowledge: 'Knowledge retrieval',
  })
  assert.ok(KEY_PATTERN.test('returns'))
  assert.ok(KEY_PATTERN.test('high_delivery_failure'))
  assert.equal(KEY_PATTERN.test('Bad Key'), false)

  assert.equal(listQuery(), '')
  assert.equal(listQuery({ page: 1, pageSize: 50, status: 'ACTIVE' }), '?page=1&page_size=50&status=ACTIVE')
  assert.equal(listQuery({ page: 2 }), '?page=2')
  assert.equal(listQuery({ pageSize: 25 }), '?page_size=25')
  assert.equal(listQuery({ status: 'DRAFT' }), '?status=DRAFT')

  assert.throws(() => listQuery({ page: 0 }), /page must be an integer >= 1/)
  assert.throws(() => listQuery({ page: -1 }), /page must be an integer >= 1/)
  assert.throws(() => listQuery({ pageSize: 0 }), /pageSize must be an integer from 1 to 100/)
  assert.throws(() => listQuery({ pageSize: 101 }), /pageSize must be an integer from 1 to 100/)
  assert.throws(() => listQuery({ status: 'X' }), /Unsupported status: X/)
})

test('paths: path builders with examples and validations (CFG-F1)', () => {
  assert.equal(effectivePath(7), 'businesses/7/configuration/effective/')
  assert.equal(changesPath(7, { page: 2 }), 'businesses/7/configuration/changes/?page=2')
  assert.equal(sectionPath(7, 'profile'), 'businesses/7/configuration/profile/')
  assert.equal(
    sectionHistoryPath(7, 'ai', { page: 2, pageSize: 25 }),
    'businesses/7/configuration/ai/history/?page=2&page_size=25',
  )
  assert.equal(
    resourcesPath(7, 'rules', { status: 'ACTIVE', page: 1, pageSize: 50 }),
    'businesses/7/configuration/rules/?page=1&page_size=50&status=ACTIVE',
  )
  assert.equal(resourcePath(7, 'policies', 'returns'), 'businesses/7/configuration/policies/returns/')
  assert.equal(
    resourceHistoryPath(7, 'rules', 'high_delivery_failure', { page: 1 }),
    'businesses/7/configuration/rules/high_delivery_failure/history/?page=1',
  )
  assert.equal(connectionsPath(7, { pageSize: 10 }), 'businesses/7/configuration/connections/?page_size=10')
  assert.equal(connectionPath(7, 5), 'businesses/7/configuration/connections/5/')
  assert.equal(connectionHistoryPath(7, 5), 'businesses/7/configuration/connections/5/history/')
  assert.equal(sourcesPath(7), 'businesses/7/configuration/sources/')
  assert.equal(sourcePath(7, 9), 'businesses/7/configuration/sources/9/')
  assert.equal(sourceHistoryPath(7, 9, { page: 3 }), 'businesses/7/configuration/sources/9/history/?page=3')
  assert.equal(providersPath(7), 'businesses/7/configuration/providers/')
  assert.equal(reprocessingPath(7), 'businesses/7/configuration/reprocessing/')
  assert.equal(monitoringPath(7), 'businesses/7/configuration/monitoring/')
  assert.equal(monitoringHistoryPath(7), 'businesses/7/configuration/monitoring/history/')
  assert.equal(freshnessPath(7), 'businesses/7/configuration/freshness/')
  assert.equal(
    freshnessHistoryPath(7, 3, { pageSize: 100 }),
    'businesses/7/configuration/freshness/3/history/?page_size=100',
  )

  // Throwing cases
  assert.throws(() => effectivePath('x'), /Invalid business ID/)
  assert.throws(() => sectionPath(7, 'unknown'), /Unknown configuration section: unknown/)
  assert.throws(() => resourcesPath(7, 'unknown'), /Unknown resource kind: unknown/)
  assert.throws(() => resourcePath(7, 'policies', 'Bad Key'), /Invalid configuration key/)
  assert.throws(() => connectionPath(7, 0), /Invalid connection id/)
  assert.throws(() => connectionPath(7, '5x'), /Invalid connection id/)
  assert.throws(() => sourcePath(7, -1), /Invalid source id/)
  assert.throws(() => freshnessHistoryPath(7, 'bad'), /Invalid policy id/)
})

test('writes: versioning, role, and STALE_MESSAGE (CFG-F1)', () => {
  assert.equal(STALE_MESSAGE, 'Someone else changed this configuration. Reload to continue.')

  assert.equal(canEditConfiguration('manager'), true)
  assert.equal(canEditConfiguration('OWNER'), true)
  assert.equal(canEditConfiguration('MANAGER'), true)
  assert.equal(canEditConfiguration('VIEWER'), false)
  assert.equal(canEditConfiguration('OPERATOR'), false)
  assert.equal(canEditConfiguration(undefined), false)
  assert.equal(canEditConfiguration(null), false)

  assert.equal(expectedVersion({ version: 5 }), 5)
  assert.equal(expectedVersion({ version: 0 }), 0)
  assert.throws(() => expectedVersion({ version: null }), /The current version is unknown/)
  assert.throws(() => expectedVersion({ version: '3' }), /The current version is unknown/)
  assert.throws(() => expectedVersion({ version: -1 }), /The current version is unknown/)
  assert.throws(() => expectedVersion({}), /The current version is unknown/)

  assert.deepEqual(withVersion({ version: 0 }, { name: 'x' }), { version: 0, name: 'x' })
  assert.deepEqual(withVersion({ version: 2 }), { version: 2 })
  assert.throws(() => withVersion({ version: 1 }, { version: 2 }), /The body must not contain version/)
})

test('writes: flattenFieldErrors (CFG-F1)', () => {
  assert.deepEqual(flattenFieldErrors({ contact: { email: ['Enter a valid email address.'] } }), {
    'contact.email': 'Enter a valid email address.',
  })
  assert.deepEqual(flattenFieldErrors({ unknown: ['zzz'] }), {
    _form: 'Not an editable setting: zzz.',
  })
  assert.deepEqual(flattenFieldErrors({ features: { unknown: ['grant'] } }), {
    features: 'Not an editable setting: grant.',
  })
  assert.deepEqual(
    flattenFieldErrors({ non_field_errors: ['Decimal and thousands separators must differ.'] }),
    { _form: 'Decimal and thousands separators must differ.' },
  )
  assert.deepEqual(
    flattenFieldErrors({
      conditions: {
        all: [
          { non_field_errors: ['Numeric value exceeds the supported decimal range.'] },
          { field: ['This value does not match the required pattern.'] },
        ],
      },
      outcome: { code: ['This value does not match the required pattern.'] },
    }),
    {
      'conditions.all.0': 'Numeric value exceeds the supported decimal range.',
      'conditions.all.1.field': 'This value does not match the required pattern.',
      'outcome.code': 'This value does not match the required pattern.',
    },
  )
  assert.deepEqual(flattenFieldErrors({ knowledge_types: { 0: ['"X" is not a valid choice.'] } }), {
    'knowledge_types.0': '"X" is not a valid choice.',
  })
  assert.deepEqual(flattenFieldErrors(['Version must be a nonnegative integer.']), {
    _form: 'Version must be a nonnegative integer.',
  })
  assert.deepEqual(flattenFieldErrors({ detail: 'x' }), {})
  assert.deepEqual(flattenFieldErrors(null), {})
  assert.deepEqual(flattenFieldErrors('bad'), {})
})

test('writes: classifyWriteError (CFG-F1)', () => {
  // 409 contexts
  assert.deepEqual(classifyWriteError({ status: 409 }, 'create'), {
    kind: 'duplicate',
    stale: false,
    message: 'A record with this key already exists. Choose another key.',
    fieldErrors: {},
  })
  assert.deepEqual(classifyWriteError({ status: 409, detail: 'Reprocess active' }, 'reprocess'), {
    kind: 'idempotency',
    stale: false,
    message: 'Reprocess active',
    fieldErrors: {},
  })
  assert.deepEqual(classifyWriteError({ status: 409 }, 'update'), {
    kind: 'stale',
    stale: true,
    message: STALE_MESSAGE,
    fieldErrors: {},
  })

  // 403
  assert.deepEqual(classifyWriteError({ status: 403 }), {
    kind: 'forbidden',
    stale: false,
    message: 'Only owners and managers can change configuration.',
    fieldErrors: {},
  })

  // 404
  assert.deepEqual(classifyWriteError({ status: 404 }), {
    kind: 'not_found',
    stale: false,
    message: 'This item no longer exists. Reload to continue.',
    fieldErrors: {},
  })

  // 400 validation with raw
  const validationRes = classifyWriteError({
    status: 400,
    detail: 'Invalid input',
    raw: { contact: { email: ['Bad email'] } },
  })
  assert.equal(validationRes.kind, 'validation')
  assert.equal(validationRes.message, 'Invalid input')
  assert.deepEqual(validationRes.fieldErrors, { 'contact.email': 'Bad email' })

  // 0, 408 network
  assert.equal(classifyWriteError({ status: 0, detail: 'Offline' }).kind, 'network')
  assert.equal(classifyWriteError({ status: 408, detail: 'Timeout' }).kind, 'network')

  // 503 server & undefined
  assert.equal(classifyWriteError({ status: 503, detail: 'Down' }).kind, 'server')
  assert.equal(classifyWriteError(undefined).kind, 'network')
  assert.equal(classifyWriteError(undefined).message, 'The request failed.')
})

test('normalize: actorLabel, normalizePage, normalizeRecord, recordSource (CFG-F1)', () => {
  assert.equal(actorLabel(12), 'User #12')
  assert.equal(actorLabel(null), 'System or unknown user')
  assert.equal(actorLabel(0), 'System or unknown user')
  assert.equal(actorLabel(-5), 'System or unknown user')

  // normalizePage
  const pageData = {
    count: 1,
    next: 'http://next',
    previous: null,
    results: [{ id: 1 }, null, 'junk'],
  }
  const normPage = normalizePage(pageData, (r) => ({ ...r, ok: true }))
  assert.deepEqual(normPage, {
    count: 1,
    next: 'http://next',
    previous: null,
    results: [{ id: 1, ok: true }],
  })

  assert.deepEqual(normalizePage(null), {
    count: 0,
    next: null,
    previous: null,
    results: [],
  })

  assert.equal(normalizePage({ total_count: 5, results: [] }).count, 5)

  // normalizeRecord
  const fullRec = {
    id: 1,
    kind: 'RULE',
    key: 'rule_1',
    version: 2,
    status: 'ACTIVE',
    priority: 10,
    valid_from: '2026-01-01',
    valid_to: null,
    settings: { threshold: 10 },
    updated_at: '2026-11-10T00:00:00Z',
    updated_by_id: 3,
  }
  assert.deepEqual(normalizeRecord(fullRec), fullRec)

  // Never-saved section
  const neverSaved = {
    kind: 'GENERAL',
    key: 'default',
    version: 0,
    status: 'ACTIVE',
    settings: {},
    updated_at: null,
    updated_by_id: null,
  }
  const normNeverSaved = normalizeRecord(neverSaved)
  assert.equal(normNeverSaved.version, 0)
  assert.equal(normNeverSaved.id, null)

  // Junk input & string version
  assert.equal(normalizeRecord(null).version, null)
  assert.equal(normalizeRecord({ version: '3', key: 5, settings: [] }).version, null)
  assert.equal(normalizeRecord({ version: '3', key: 5, settings: [] }).key, '5')
  assert.deepEqual(normalizeRecord({ version: '3', key: 5, settings: [] }).settings, {})

  // recordSource
  assert.deepEqual(recordSource({ version: 1, status: 'DRAFT', priority: 4, settings: { a: { b: 1 } } }), {
    a: { b: 1 },
    status: 'DRAFT',
    priority: 4,
  })
})

test('fieldKit: generic form engine verified examples (CFG-F1)', () => {
  assert.equal(REASON_SPEC.path, 'reason')
  assert.equal(REASON_SPEC.maxLength, 500)

  // getPath and setPath
  const orig = { a: { b: 1, c: 2 } }
  const updated = setPath(orig, 'a.d.e', 5)
  assert.deepEqual(updated, { a: { b: 1, c: 2, d: { e: 5 } } })
  assert.deepEqual(orig, { a: { b: 1, c: 2 } }) // immutable!
  assert.equal(getPath(updated, 'a.d.e'), 5)
  assert.equal(getPath(updated, 'a.z.none'), undefined)

  // parseListText
  assert.deepEqual(parseListText(' a, b\n\nc ,'), ['a', 'b', 'c'])

  const specs = [
    { path: 'name', label: 'Business name', type: 'text', required: true, maxLength: 255 },
    { path: 'description', label: 'Description', type: 'textarea', maxLength: 2000 },
    { path: 'contact.email', label: 'Contact email', type: 'text', maxLength: 254 },
    { path: 'location.country', label: 'Country', type: 'text', regex: /^[A-Z]{2}$/, omitWhenBlank: true },
    { path: 'operating_regions', label: 'Regions', type: 'list', maxItems: 50, itemMaxLength: 255 },
    {
      path: 'channels',
      label: 'Channels',
      type: 'multi',
      options: [
        { value: 'WEBSITE', label: 'Website' },
        { value: 'DIRECT', label: 'Direct' },
      ],
      maxItems: 5,
    },
    { path: 'decimal_places', label: 'Decimal places', type: 'int', min: 0, max: 6 },
    {
      path: 'week_start',
      label: 'Week start',
      type: 'select',
      options: [
        { value: 0, label: 'Monday' },
        { value: 6, label: 'Sunday' },
      ],
    },
    {
      path: 'thousands_separator',
      label: 'Thousands separator',
      type: 'select',
      allowEmpty: true,
      options: [
        { value: ',', label: 'Comma' },
        { value: '', label: 'None' },
      ],
    },
    {
      path: 'confidence_threshold',
      label: 'Confidence',
      type: 'decimal',
      min: 0,
      max: 1,
      places: 4,
      required: true,
    },
    { path: 'features.calling', label: 'Calling', type: 'bool' },
  ]

  const source = {
    name: 'Shop',
    description: '',
    contact: {},
    location: {},
    operating_regions: ['Dhaka'],
    channels: ['WEBSITE'],
    decimal_places: 2,
    week_start: 0,
    thousands_separator: ',',
    confidence_threshold: '0.7000',
    features: {},
  }

  // 1. draftFromSettings
  const draft = draftFromSettings(specs, source)
  assert.deepEqual(draft, {
    name: 'Shop',
    description: '',
    'contact.email': '',
    'location.country': '',
    operating_regions: 'Dhaka',
    channels: ['WEBSITE'],
    decimal_places: '2',
    week_start: '0',
    thousands_separator: ',',
    confidence_threshold: '0.7000',
    'features.calling': false,
  })

  // 2. patchFromDraft with unchanged draft is {}
  assert.deepEqual(patchFromDraft(specs, source, draft), {})

  // 3. patchFromDraft with changed draft
  const changedDraft = {
    ...draft,
    name: ' New ',
    'contact.email': 'a@b.co',
    'location.country': '',
    operating_regions: 'Dhaka\nGazipur,',
    channels: ['DIRECT', 'WEBSITE'],
    decimal_places: '3',
    week_start: '6',
    thousands_separator: '',
    confidence_threshold: '0.70',
    'features.calling': true,
  }
  const patch = patchFromDraft(specs, source, changedDraft)
  assert.deepEqual(patch, {
    name: 'New',
    contact: { email: 'a@b.co' },
    operating_regions: ['Dhaka', 'Gazipur'],
    channels: ['DIRECT', 'WEBSITE'],
    decimal_places: 3,
    week_start: 6,
    thousands_separator: '',
    features: { calling: true },
  })

  // 4. Same set other order gives {}
  const otherOrderDraft = {
    ...draft,
    channels: ['WEBSITE', 'DIRECT'],
  }
  assert.deepEqual(patchFromDraft(specs, { ...source, channels: ['DIRECT', 'WEBSITE'] }, otherOrderDraft), {})

  // 5. Clearing allow-blank field
  assert.deepEqual(patchFromDraft(specs, { ...source, description: 'old' }, { ...draft, description: '' }), {
    description: '',
  })

  // 6. sendAll: true
  const sendAllDraft = draftFromSettings(specs, {
    name: 'N',
    decimal_places: 2,
    confidence_threshold: '0.8',
    thousands_separator: '',
  })
  assert.deepEqual(patchFromDraft(specs, {}, sendAllDraft, { sendAll: true }), {
    name: 'N',
    decimal_places: 2,
    confidence_threshold: '0.8',
    features: { calling: false },
  })

  // 7. validateDraft
  const invalidDraft = {
    ...changedDraft,
    name: '',
    'location.country': 'bd',
    decimal_places: '9',
    confidence_threshold: '0.12345',
    channels: ['X'],
    'contact.email': 'a'.repeat(300),
    week_start: '3',
    operating_regions: 'a'.repeat(256),
  }
  const errors = validateDraft(specs, invalidDraft)
  assert.deepEqual(errors, {
    name: 'Business name is required.',
    'contact.email': 'Contact email must be at most 254 characters.',
    'location.country': 'Country is not in the expected format.',
    operating_regions: 'Regions: each item must be at most 255 characters.',
    channels: 'Channels has an unsupported choice.',
    decimal_places: 'Decimal places must be between 0 and 6.',
    week_start: 'Week start has an unsupported value.',
    confidence_threshold: 'Confidence allows at most 4 decimal places.',
  })

  // Single validations
  assert.equal(
    validateDraft(specs, { ...draft, decimal_places: '1.5' }).decimal_places,
    'Decimal places must be a whole number.',
  )
  assert.equal(
    validateDraft(specs, { ...draft, confidence_threshold: 'abc' }).confidence_threshold,
    'Confidence must be a number.',
  )
  assert.equal(
    validateDraft(specs, { ...draft, confidence_threshold: '' }).confidence_threshold,
    'Confidence is required.',
  )
  assert.equal(
    validateDraft(specs, { ...draft, confidence_threshold: '1.5' }).confidence_threshold,
    'Confidence must be between 0 and 1.',
  )
  assert.deepEqual(validateDraft(specs, draft), {})

  // 8. rebaseDraft
  const rebased = rebaseDraft(
    specs.slice(0, 3),
    source,
    { ...source, name: 'Server' },
    { ...draftFromSettings(specs, source), 'contact.email': 'mine@x.co' },
  )
  assert.deepEqual(rebased, {
    name: 'Server',
    description: '',
    'contact.email': 'mine@x.co',
  })

  // 9. fieldError
  assert.equal(
    fieldError({ 'conditions.all.0.field': 'bad', 'conditions.all.1.value': 'worse' }, 'conditions.all'),
    'bad worse',
  )
  assert.equal(fieldError({ window_days: 'bad' }, 'parameters.window_days'), 'bad')
  assert.equal(fieldError({}, 'unknown'), undefined)
})
