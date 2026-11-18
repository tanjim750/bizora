import { choices } from './sections.js'
import { resourcesPath, resourcePath } from './paths.js'
import { recordSource } from './normalize.js'
import { draftFromSettings } from './fieldKit.js'
import { controlSpecs, scopeSummary, buildResourceSave } from './resources.js'

export const POLICY_CATEGORIES = 'DELIVERY RETURN REFUND CANCELLATION SUPPORT PRODUCT'.split(' ')

export const PARAMETER_SPECS = {
  DELIVERY: [
    {
      path: 'parameters.coverage_regions',
      label: 'Coverage regions',
      type: 'list',
      minItems: 1,
      required: true,
      maxItems: 50,
      itemMaxLength: 255,
    },
    {
      path: 'parameters.estimated_days',
      label: 'Estimated delivery days',
      type: 'int',
      min: 0,
      max: 366,
      required: true,
    },
    {
      path: 'parameters.charge',
      label: 'Delivery charge',
      type: 'decimal',
      min: 0,
      places: 2,
      omitWhenBlank: true,
    },
    {
      path: 'parameters.preferred_couriers',
      label: 'Preferred couriers',
      type: 'list',
      maxItems: 50,
      itemMaxLength: 255,
    },
    {
      path: 'parameters.cod_enabled',
      label: 'Cash on delivery available',
      type: 'bool',
    },
    {
      path: 'parameters.cod_limit',
      label: 'Cash on delivery limit',
      type: 'decimal',
      min: 0,
      places: 2,
      omitWhenBlank: true,
    },
    {
      path: 'parameters.failure_instructions',
      label: 'If delivery fails',
      type: 'textarea',
      maxLength: 2000,
      omitWhenBlank: true,
    },
  ],
  RETURN: [
    {
      path: 'parameters.window_days',
      label: 'Return window (days)',
      type: 'int',
      min: 0,
      max: 366,
      required: true,
    },
    {
      path: 'parameters.eligibility',
      label: 'Eligible when',
      type: 'list',
      minItems: 1,
      required: true,
      maxItems: 50,
      itemMaxLength: 255,
    },
    {
      path: 'parameters.exclusions',
      label: 'Exclusions',
      type: 'list',
      maxItems: 50,
      itemMaxLength: 255,
    },
    {
      path: 'parameters.procedure',
      label: 'Procedure',
      type: 'textarea',
      maxLength: 2000,
      required: true,
    },
  ],
  REFUND: [
    {
      path: 'parameters.window_days',
      label: 'Refund window (days)',
      type: 'int',
      min: 0,
      max: 366,
      required: true,
    },
    {
      path: 'parameters.methods',
      label: 'Refund methods',
      type: 'list',
      minItems: 1,
      required: true,
      maxItems: 50,
      itemMaxLength: 255,
    },
    {
      path: 'parameters.approval_required',
      label: 'Manager approval required',
      type: 'bool',
    },
    {
      path: 'parameters.eligibility',
      label: 'Eligible when',
      type: 'list',
      minItems: 1,
      required: true,
      maxItems: 50,
      itemMaxLength: 255,
    },
    {
      path: 'parameters.procedure',
      label: 'Procedure',
      type: 'textarea',
      maxLength: 2000,
      required: true,
    },
  ],
  CANCELLATION: [
    {
      path: 'parameters.allowed_statuses',
      label: 'Order statuses that can be cancelled',
      type: 'list',
      minItems: 1,
      required: true,
      maxItems: 50,
      itemMaxLength: 255,
    },
    {
      path: 'parameters.cutoff_hours',
      label: 'Cancellation cutoff (hours)',
      type: 'int',
      min: 0,
      max: 8760,
      required: true,
    },
    {
      path: 'parameters.procedure',
      label: 'Procedure',
      type: 'textarea',
      maxLength: 2000,
      required: true,
    },
  ],
  SUPPORT: [
    {
      path: 'parameters.response_time_seconds',
      label: 'Response time (seconds)',
      type: 'int',
      min: 1,
      max: 2592000,
      required: true,
    },
    {
      path: 'parameters.escalation_conditions',
      label: 'Escalate when',
      type: 'list',
      minItems: 1,
      required: true,
      maxItems: 50,
      itemMaxLength: 255,
    },
    {
      path: 'parameters.instructions',
      label: 'Instructions',
      type: 'textarea',
      maxLength: 2000,
      required: true,
    },
  ],
  PRODUCT: [
    {
      path: 'parameters.constraints',
      label: 'Constraints',
      type: 'list',
      minItems: 1,
      required: true,
      maxItems: 50,
      itemMaxLength: 255,
    },
    {
      path: 'parameters.instructions',
      label: 'Instructions',
      type: 'textarea',
      maxLength: 2000,
      required: true,
    },
  ],
}

export function policySpecs(record, draft) {
  const category = draft?.category || record?.settings?.category || ''
  const active = (draft ? draft.status : record?.status) === 'ACTIVE'
  const rawParams = PARAMETER_SPECS[category] || []

  const params = rawParams.map((s) => {
    if (!active) {
      return {
        ...s,
        required: false,
        minItems: s.minItems ? 0 : s.minItems,
      }
    }
    return s
  })

  return [
    {
      path: 'category',
      label: 'Category',
      type: 'select',
      required: true,
      options: choices(...POLICY_CATEGORIES),
    },
    {
      path: 'title',
      label: 'Title',
      type: 'text',
      required: true,
      maxLength: 255,
    },
    {
      path: 'terms',
      label: 'Terms',
      type: 'textarea',
      maxLength: 8000,
      required: active,
    },
    {
      path: 'ai_available',
      label: 'Available to the AI assistant',
      type: 'bool',
      hint: 'When off, the AI assistant does not use this policy.',
    },
    ...params,
    ...controlSpecs(record?.status),
  ]
}

export function buildPolicySave({ record, draft, key, creating }) {
  return buildResourceSave({
    specs: policySpecs(record, draft),
    record,
    draft,
    key,
    creating,
    createDefaults: { terms: '', parameters: {} },
  })
}

export const POLICIES_RESOURCE = {
  id: 'policies',
  title: 'Policies',
  singular: 'policy',
  updateMethod: 'PATCH',
  keyField: true,
  notes: [
    'Only Active policies are used by other parts of Bizora. Draft, Disabled and Archived policies are kept but ignored.',
    'Policies are never deleted; set the status to Archived instead.',
  ],
  listPath: (id, opts) => resourcesPath(id, 'policies', opts),
  itemPath: (id, record) => resourcePath(id, 'policies', record.key),
  createPath: (id) => resourcesPath(id, 'policies'),
  nameOf: (record) => `"${record.key}"`,
  columns: [
    { key: 'key', label: 'Key', mono: true, text: (r) => r.key },
    {
      key: 'policy',
      label: 'Policy',
      text: (r) => `${r.settings?.category || '—'} · ${r.settings?.title || '—'}`,
    },
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
  draftFor: (record) =>
    draftFromSettings(policySpecs(record, null), recordSource(record || { status: 'DRAFT' })),
  specsFor: ({ record, draft }) => policySpecs(record, draft),
  lockedPaths: ({ creating }) => (creating ? [] : ['category']),
  build: buildPolicySave,
}
