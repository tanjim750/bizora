import { choices } from './sections.js'
import { resourcesPath, resourcePath } from './paths.js'
import { recordSource } from './normalize.js'
import { draftFromSettings } from './fieldKit.js'
import { controlSpecs, scopeSummary, buildResourceSave } from './resources.js'

export const RULE_CATEGORIES =
  'ORDERS CUSTOMERS DELIVERY MARKETING SUPPORT PAYMENTS INTELLIGENCE WEBSITE'.split(' ')

export const OPERATORS = 'gt gte lt lte eq ne in not_in'.split(' ')

export function parseScalar(token) {
  const t = String(token).trim()
  if (t === 'true') return true
  if (t === 'false') return false
  if (/^-?\d+(\.\d+)?$/.test(t)) {
    return Number(t)
  }
  return t
}

export function parseCondition(line) {
  const match = String(line).match(/^\s*(\S+)\s+(\S+)\s+(.+?)\s*$/)
  if (!match) {
    throw new Error('Write field, operator and value, for example: delivery_failure_rate gt 15')
  }
  const [, field, op, rest] = match

  if (!/^[a-zA-Z][a-zA-Z0-9_]{0,99}$/.test(field)) {
    throw new Error('Field names use letters, digits and underscores and start with a letter.')
  }

  if (!OPERATORS.includes(op)) {
    throw new Error('Operator must be one of gt, gte, lt, lte, eq, ne, in, not_in.')
  }

  if (['gt', 'gte', 'lt', 'lte'].includes(op)) {
    const trimmedVal = rest.trim()
    if (!/^-?\d+(\.\d{1,6})?$/.test(trimmedVal) || Math.abs(Number(trimmedVal)) >= 1e18) {
      throw new Error('Use a number with at most 6 decimals.')
    }
    return { field, operator: op, value: trimmedVal }
  }

  if (['eq', 'ne'].includes(op)) {
    return { field, operator: op, value: parseScalar(rest) }
  }

  // in, not_in
  const items = rest
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .map(parseScalar)
  if (items.length < 1 || items.length > 50) {
    throw new Error('Use 1 to 50 values separated by commas.')
  }
  return { field, operator: op, value: items }
}

export function parseConditions(text) {
  const lines = String(text ?? '').split('\n')
  const conditions = []
  const errs = []

  lines.forEach((line, idx) => {
    const trimmed = line.trim()
    if (!trimmed) return
    try {
      const cond = parseCondition(trimmed)
      conditions.push(cond)
    } catch (err) {
      errs.push(`Line ${idx + 1}: ${err.message}`)
    }
  })

  if (conditions.length === 0 && errs.length === 0) {
    errs.push('Add at least one condition.')
  } else if (conditions.length > 30) {
    errs.push('Use at most 30 conditions.')
  }

  return {
    conditions,
    error: errs.length > 0 ? errs.join(' ') : null,
  }
}

export function formatConditions(conditions) {
  if (!conditions || typeof conditions !== 'object') {
    return { mode: 'all', text: '' }
  }

  const mode = Array.isArray(conditions.any) && conditions.any.length > 0 ? 'any' : 'all'
  const list = Array.isArray(conditions[mode]) ? conditions[mode] : []

  const text = list
    .map((c) => {
      let valStr = ''
      if (Array.isArray(c.value)) {
        valStr = c.value.join(', ')
      } else {
        valStr = String(c.value)
      }
      return `${c.field} ${c.operator} ${valStr}`
    })
    .join('\n')

  return { mode, text }
}

export const RULE_FIELD_SPECS = [
  {
    path: 'category',
    label: 'Category',
    type: 'select',
    required: true,
    options: choices(...RULE_CATEGORIES),
  },
  {
    path: 'description',
    label: 'Description',
    type: 'textarea',
    maxLength: 2000,
  },
  {
    path: 'outcome.type',
    label: 'When it matches',
    type: 'select',
    required: true,
    options: choices('CLASSIFY', 'ALERT', 'REQUIRE_APPROVAL'),
  },
  {
    path: 'outcome.code',
    label: 'Outcome code',
    type: 'text',
    required: true,
    regex: /^[A-Z][A-Z0-9_]{0,99}$/,
    regexMessage: 'Use UPPER_CASE letters, digits and underscores.',
  },
  {
    path: 'outcome.severity',
    label: 'Severity',
    type: 'select',
    required: true,
    options: choices('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'),
  },
  {
    path: 'sample_metric',
    label: 'Sample metric',
    type: 'text',
    regex: /^[a-zA-Z][a-zA-Z0-9_]{0,99}$/,
    omitWhenBlank: true,
  },
  {
    path: 'min_samples',
    label: 'Minimum samples',
    type: 'int',
    min: 1,
    max: 1000000000,
    omitWhenBlank: true,
  },
  {
    path: 'window_days',
    label: 'Window (days)',
    type: 'int',
    min: 1,
    max: 366,
    omitWhenBlank: true,
  },
]

const VIRTUAL_SPECS = [
  {
    path: 'conditions_mode',
    label: 'Match',
    type: 'select',
    required: true,
    options: [
      { value: 'all', label: 'All conditions must match' },
      { value: 'any', label: 'Any condition may match' },
    ],
  },
  {
    path: 'conditions',
    label: 'Conditions',
    type: 'textarea',
    required: true,
    hint: 'One per line: field operator value. Operators: gt, gte, lt, lte, eq, ne, in, not_in. Use commas for in and not_in.',
  },
]

export function ruleSpecs(record) {
  return [...VIRTUAL_SPECS, ...RULE_FIELD_SPECS, ...controlSpecs(record?.status)]
}

export function buildRuleSave({ record, draft, key, creating }) {
  const allSpecs = ruleSpecs(record)
  const dataSpecs = allSpecs.filter((s) => s.path !== 'conditions_mode' && s.path !== 'conditions')
  const parsed = parseConditions(draft?.conditions)

  const extraErrors = {}
  if (parsed.error) {
    extraErrors.conditions = parsed.error
  }

  if (
    draft?.min_samples !== '' &&
    draft?.min_samples !== undefined &&
    (!draft?.sample_metric || draft.sample_metric === '') &&
    !record?.settings?.sample_metric
  ) {
    extraErrors.min_samples = 'A minimum sample needs a sample metric.'
  }

  const condObj = { [draft?.conditions_mode || 'all']: parsed.conditions }
  let extraBody = {}
  if (creating || JSON.stringify(condObj) !== JSON.stringify(record?.settings?.conditions)) {
    extraBody = { conditions: condObj }
  }

  return buildResourceSave({
    specs: dataSpecs,
    record,
    draft,
    key,
    creating,
    extraErrors,
    extraBody,
  })
}

export const RULES_RESOURCE = {
  id: 'rules',
  title: 'Rules',
  singular: 'rule',
  updateMethod: 'PATCH',
  keyField: true,
  notes: [
    'Only Active rules are used by other parts of Bizora. Draft, Disabled and Archived rules are kept but ignored.',
    'Rules are never deleted; set the status to Archived instead.',
  ],
  listPath: (id, opts) => resourcesPath(id, 'rules', opts),
  itemPath: (id, record) => resourcePath(id, 'rules', record.key),
  createPath: (id) => resourcesPath(id, 'rules'),
  nameOf: (record) => `"${record.key}"`,
  columns: [
    { key: 'key', label: 'Key', mono: true, text: (r) => r.key },
    { key: 'category', label: 'Category', text: (r) => r.settings?.category || '—' },
    { key: 'status', label: 'Status', chip: true, text: (r) => r.status },
    {
      key: 'priority',
      label: 'Priority',
      align: 'right',
      text: (r) => String(r.priority ?? 0),
    },
    {
      key: 'scope',
      label: 'Applies to',
      text: (r) => scopeSummary(r.settings?.scope),
    },
  ],
  draftFor: (record) => {
    const dataSpecs = ruleSpecs(record).filter((s) => s.path !== 'conditions_mode' && s.path !== 'conditions')
    const base = draftFromSettings(dataSpecs, recordSource(record || { status: 'DRAFT' }))
    const { mode, text } = formatConditions(record?.settings?.conditions)
    return { ...base, conditions_mode: mode, conditions: text }
  },
  specsFor: ({ record }) => ruleSpecs(record),
  lockedPaths: ({ creating }) => (creating ? [] : ['conditions_mode']),
  build: buildRuleSave,
}
