import { SECTION_LABELS, sectionPath } from './paths.js'
import { withVersion } from './writes.js'
import { recordSource } from './normalize.js'
import { REASON_SPEC, draftFromSettings, validateDraft, patchFromDraft } from './fieldKit.js'

export function choices(...values) {
  return values.map((val) => {
    const str = String(val)
    if (/^[a-zA-Z_]+$/.test(str)) {
      const lowerWithSpaces = str.toLowerCase().replace(/_/g, ' ')
      const label = lowerWithSpaces.charAt(0).toUpperCase() + lowerWithSpaces.slice(1)
      return { value: val, label }
    }
    return { value: val, label: str }
  })
}

export const TASKS = 'business_assistant customer_support marketing summarization recommendations'.split(' ')
export const CONTEXTS =
  'profile facts metrics issues relationships graph approved_policies knowledge goals'.split(' ')
export const ACTIONS =
  'CREATE_SUPPORT_DRAFT PROPOSE_COURIER_CHANGE PROPOSE_CAMPAIGN_CHANGE CREATE_TASK'.split(' ')
export const KNOWLEDGE_TYPES = 'PROFILE POLICY PRODUCT SUPPORT BRAND INTERNAL GOALS DECISIONS'.split(' ')
export const SOURCE_TYPES = 'MANUAL UPLOAD WEBSITE INTEGRATION'.split(' ')

const s = (path, label, type, extra = {}) => ({ path, label, type, ...extra })

export const SECTION_SPECS = {
  profile: [
    s('name', 'Business name', 'text', { required: true, maxLength: 255 }),
    s('description', 'Description', 'textarea', { maxLength: 2000 }),
    s('industry', 'Industry', 'text', { maxLength: 100 }),
    s('contact.email', 'Contact email', 'text', {
      maxLength: 254,
      regex: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
      regexMessage: 'Enter a valid email address.',
    }),
    s('contact.phone', 'Contact phone', 'text', { maxLength: 50 }),
    s('contact.website', 'Website', 'text', {
      maxLength: 200,
      regex: /^https?:\/\/\S+$/i,
      regexMessage: 'Website must start with http:// or https://.',
    }),
    s('location.country', 'Country code', 'text', {
      regex: /^[A-Z]{2}$/,
      regexMessage: 'Use a two-letter upper-case country code.',
      omitWhenBlank: true,
    }),
    s('location.city', 'City', 'text', { maxLength: 150 }),
    s('location.address', 'Address', 'text', { maxLength: 500 }),
    s('operating_regions', 'Operating regions', 'list', { maxItems: 50, itemMaxLength: 255 }),
    s('channels', 'Sales channels', 'multi', {
      options: choices('WEBSITE', 'SOCIAL_COMMERCE', 'MARKETPLACE', 'PHYSICAL', 'DIRECT'),
      maxItems: 5,
    }),
  ],
  general: [
    s('currency', 'Currency code', 'text', {
      required: true,
      regex: /^[A-Z]{3}$/,
      regexMessage: 'Use a three-letter upper-case currency code.',
    }),
    s('timezone', 'Time zone', 'text', {
      required: true,
      maxLength: 100,
      hint: 'An IANA name such as Asia/Dhaka.',
    }),
    s('locale', 'Locale', 'text', {
      regex: /^[a-z]{2,3}(?:-[A-Z]{2})?$/,
      regexMessage: 'Use a form like en or en-US.',
      omitWhenBlank: true,
    }),
    s('language', 'Language', 'text', {
      regex: /^[a-z]{2,3}(?:-[A-Z]{2})?$/,
      regexMessage: 'Use a form like en or en-US.',
      omitWhenBlank: true,
    }),
    s('date_format', 'Date format', 'select', {
      required: true,
      options: choices('YYYY-MM-DD', 'DD/MM/YYYY', 'MM/DD/YYYY'),
    }),
    s('time_format', 'Time format', 'select', {
      required: true,
      options: choices('12H', '24H'),
    }),
    s('decimal_places', 'Decimal places', 'int', { required: true, min: 0, max: 6 }),
    s('decimal_separator', 'Decimal separator', 'select', {
      required: true,
      options: [
        { value: '.', label: 'Dot (.)' },
        { value: ',', label: 'Comma (,)' },
      ],
    }),
    s('thousands_separator', 'Thousands separator', 'select', {
      allowEmpty: true,
      options: [
        { value: '.', label: 'Dot (.)' },
        { value: ',', label: 'Comma (,)' },
        { value: ' ', label: 'Space' },
        { value: '', label: 'None' },
      ],
    }),
    s('currency_display', 'Currency display', 'select', {
      required: true,
      options: choices('CODE', 'SYMBOL'),
    }),
    s('reporting_period', 'Reporting period', 'select', {
      required: true,
      options: [
        { value: 'DAY', label: 'Day' },
        { value: 'WEEK', label: 'Week' },
        { value: 'MONTH', label: 'Month' },
        { value: 'ROLLING_7D', label: 'Rolling 7 days' },
        { value: 'ROLLING_30D', label: 'Rolling 30 days' },
      ],
    }),
    s('week_start', 'Week starts on', 'select', {
      required: true,
      options: [
        { value: 0, label: 'Monday' },
        { value: 1, label: 'Tuesday' },
        { value: 2, label: 'Wednesday' },
        { value: 3, label: 'Thursday' },
        { value: 4, label: 'Friday' },
        { value: 5, label: 'Saturday' },
        { value: 6, label: 'Sunday' },
      ],
    }),
    s('operational_defaults.order_status', 'Default order status', 'select', {
      options: choices('PENDING', 'CONFIRMED'),
    }),
    s('operational_defaults.conversation_priority', 'Default conversation priority', 'select', {
      options: choices('LOW', 'NORMAL', 'HIGH'),
    }),
    s('operational_defaults.delivery_region', 'Default delivery region', 'text', {
      maxLength: 100,
      omitWhenBlank: true,
    }),
    s('features.calling', 'Feature: calling', 'bool'),
    s('features.marketing', 'Feature: marketing', 'bool'),
    s('features.website', 'Feature: website', 'bool'),
    s('features.support', 'Feature: support', 'bool'),
    s('features.delivery', 'Feature: delivery', 'bool'),
    s('features.graph', 'Feature: graph', 'bool'),
    s('features.ai_recommendations', 'Feature: ai recommendations', 'bool'),
  ],
  ai: [
    s('enabled', 'AI assistant enabled', 'bool'),
    s('provider', 'AI provider', 'text', {
      required: true,
      maxLength: 50,
      hint: 'Must be registered on this server. The server rejects other values.',
    }),
    ...TASKS.map((t) =>
      s(`models.${t}`, `Model: ${choices(t)[0].label}`, 'text', {
        maxLength: 150,
        omitWhenBlank: true,
        hint: 'Blank keeps the saved value.',
      }),
    ),
    ...TASKS.map((t) => s(`features.${t}`, `Feature: ${choices(t)[0].label}`, 'bool')),
    s('features.suggested_replies', 'Feature: Suggested replies', 'bool'),
    s('context_categories', 'Context the AI may use', 'multi', {
      options: choices(...CONTEXTS),
      maxItems: 10,
    }),
    s('response.detail', 'Answer detail', 'select', {
      required: true,
      options: choices('BRIEF', 'NORMAL', 'DETAILED'),
    }),
    s('response.tone', 'Answer tone', 'select', {
      required: true,
      options: choices('PROFESSIONAL', 'FRIENDLY', 'FORMAL'),
    }),
    s('response.language', 'Answer language', 'text', { maxLength: 30, omitWhenBlank: true }),
    s('confidence_threshold', 'Confidence threshold', 'decimal', {
      required: true,
      min: 0,
      max: 1,
      places: 4,
      hint: 'Between 0 and 1. The platform sets a minimum; the server rejects lower values.',
    }),
    s('escalation.topics', 'Always escalate these topics', 'list', {
      maxItems: 50,
      itemMaxLength: 255,
    }),
    s('allowed_actions', 'Actions the AI may propose', 'multi', {
      options: choices(...ACTIONS),
      maxItems: 4,
    }),
    s('execution.disabled_actions', 'Actions switched off', 'multi', {
      options: choices(...ACTIONS),
      maxItems: 4,
    }),
    s('parameters.temperature', 'Temperature', 'decimal', {
      required: true,
      min: 0,
      max: 2,
      places: 2,
    }),
    s('parameters.max_output_tokens', 'Maximum output tokens', 'int', {
      required: true,
      min: 1,
      max: 8192,
    }),
  ],
  knowledge: [
    s('knowledge_types', 'Knowledge categories', 'multi', {
      options: choices(...KNOWLEDGE_TYPES),
      maxItems: 8,
    }),
    s('ingestion.allowed_types', 'Allowed source types', 'multi', {
      options: choices(...SOURCE_TYPES),
      maxItems: 4,
    }),
    s('ingestion.max_document_bytes', 'Maximum document size (bytes)', 'int', {
      required: true,
      min: 1024,
      max: 52428800,
    }),
    s('chunk_size', 'Chunk size', 'int', { required: true, min: 100, max: 8000 }),
    s('chunk_overlap', 'Chunk overlap', 'int', { required: true, min: 0, max: 2000 }),
    s('embedding_model', 'Embedding model', 'text', {
      required: true,
      maxLength: 150,
      hint: 'Must be registered on this server.',
    }),
    s('vector.enabled', 'Vector search enabled', 'bool'),
    s('vector.limit', 'Vector results', 'int', { required: true, min: 1, max: 100 }),
    s('vector.minimum_similarity', 'Vector minimum similarity', 'decimal', {
      required: true,
      min: 0,
      max: 1,
      places: 4,
    }),
    s('keyword.enabled', 'Keyword search enabled', 'bool'),
    s('keyword.limit', 'Keyword results', 'int', { required: true, min: 1, max: 100 }),
    s('hybrid.enabled', 'Hybrid search enabled', 'bool'),
    s('hybrid.vector_weight', 'Hybrid vector weight', 'decimal', {
      required: true,
      min: 0,
      max: 1,
      places: 4,
    }),
    s('hybrid.keyword_weight', 'Hybrid keyword weight', 'decimal', {
      required: true,
      min: 0,
      max: 1,
      places: 4,
    }),
    s('retrieval_limit', 'Results per question', 'int', { required: true, min: 1, max: 100 }),
    s('include_archived_for_history', 'Include archived sources for historical questions', 'bool'),
  ],
}

export function validTimeZone(value) {
  if (!value || typeof value !== 'string') return false
  try {
    new Intl.DateTimeFormat('en', { timeZone: value })
    return true
  } catch {
    return false
  }
}

export function crossChecks(section, draft) {
  const errs = {}
  if (section === 'general') {
    const tz = draft.timezone
    if (tz !== undefined && tz !== null && tz.trim() !== '') {
      if (!validTimeZone(tz.trim())) {
        errs.timezone = 'Use a valid IANA time zone.'
      }
    }
    const decSep = draft.decimal_separator
    const thouSep = draft.thousands_separator
    if (decSep !== undefined && decSep !== '' && decSep === thouSep) {
      errs.thousands_separator = 'Decimal and thousands separators must differ.'
    }
  } else if (section === 'knowledge') {
    const sizeStr = draft.chunk_size
    const overStr = draft.chunk_overlap
    if (
      sizeStr !== undefined &&
      overStr !== undefined &&
      /^-?\d+$/.test(String(sizeStr).trim()) &&
      /^-?\d+$/.test(String(overStr).trim())
    ) {
      const size = Number(sizeStr)
      const over = Number(overStr)
      if (over >= size) {
        errs.chunk_overlap = 'Chunk overlap must be smaller than chunk size.'
      }
    }
    if (draft['hybrid.enabled']) {
      const vw = Number(draft['hybrid.vector_weight'])
      const kw = Number(draft['hybrid.keyword_weight'])
      if (!isNaN(vw) && !isNaN(kw)) {
        const sum = Math.round(vw * 10000) + Math.round(kw * 10000)
        if (sum !== 10000) {
          errs['hybrid.keyword_weight'] = 'Hybrid weights must add up to 1.'
        }
      }
      if (!draft['vector.enabled'] || !draft['keyword.enabled']) {
        errs['hybrid.enabled'] = 'Hybrid search needs vector and keyword search switched on.'
      }
    }
  }
  return errs
}

export function buildSectionSave(section, record, draft) {
  const specs = [...SECTION_SPECS[section], REASON_SPEC]
  const errors = {
    ...validateDraft(specs, draft),
    ...crossChecks(section, draft),
  }

  if (!record || record.version === null || record.version === undefined) {
    errors._form = 'The current version is unknown. Reload before saving.'
  }

  const patch = patchFromDraft(specs, recordSource(record), draft)
  const changedKeys = Object.keys(patch).filter((k) => k !== 'reason')
  const changed = changedKeys.length > 0

  let body = null
  if (Object.keys(errors).length === 0 && changed) {
    body = withVersion(record, patch)
  }

  return { errors, changed, body }
}

const SECTION_NOTES = {
  profile: ['Currency and time zone are shared with General settings and are edited there.'],
  general: ['Changing the currency or time zone changes the setting used across the whole workspace.'],
  ai: [
    'Platform rules cannot be switched off here: low-confidence answers are always escalated and every external action needs human approval.',
    'Per-workflow overrides are kept as saved and are not editable here.',
  ],
  knowledge: ['Per-workflow knowledge scopes are kept as saved and are not editable here.'],
}

export const SECTION_RESOURCES = {
  profile: makeSectionResource('profile'),
  general: makeSectionResource('general'),
  ai: makeSectionResource('ai'),
  knowledge: makeSectionResource('knowledge'),
}

function makeSectionResource(section) {
  const specs = [...SECTION_SPECS[section], REASON_SPEC]
  return {
    id: section,
    title: SECTION_LABELS[section],
    singular: 'settings',
    updateMethod: 'PUT',
    keyField: false,
    notes: SECTION_NOTES[section] || [],
    createPath: null,
    itemPath: (businessId) => sectionPath(businessId, section),
    nameOf: () => SECTION_LABELS[section],
    draftFor: (record) => draftFromSettings(specs, recordSource(record)),
    specsFor: () => specs,
    lockedPaths: () => [],
    build: ({ record, draft }) => buildSectionSave(section, record, draft),
  }
}
