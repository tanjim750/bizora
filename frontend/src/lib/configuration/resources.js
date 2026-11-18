import { choices } from './sections.js'
import { KEY_PATTERN } from './paths.js'
import { withVersion } from './writes.js'
import { recordSource } from './normalize.js'
import { REASON_SPEC, validateDraft, patchFromDraft } from './fieldKit.js'

export function controlSpecs(currentStatus) {
  const statusValues = ['DRAFT', 'ACTIVE', 'DISABLED', 'ARCHIVED']
  if (currentStatus === 'SUPERSEDED') {
    statusValues.push('SUPERSEDED')
  }

  return [
    {
      path: 'status',
      label: 'Status',
      type: 'select',
      required: true,
      options: choices(...statusValues),
    },
    {
      path: 'priority',
      label: 'Priority',
      type: 'int',
      min: 0,
      max: 10000,
      omitWhenBlank: true,
      hint: 'Higher numbers win. 0 to 10000.',
    },
    REASON_SPEC,
  ]
}

export const KEY_MESSAGE = 'Use lowercase letters, digits, "_" or "-", starting with a letter (at most 100).'

export function scopeSummary(scope) {
  if (!scope || typeof scope !== 'object' || Object.keys(scope).length === 0) {
    return 'Everywhere'
  }
  return Object.keys(scope)
    .sort()
    .map((k) => `${k}: ${scope[k]}`)
    .join(', ')
}

export function buildResourceSave({
  specs,
  record,
  draft,
  key,
  creating,
  extraErrors = {},
  extraBody = {},
  createDefaults = {},
}) {
  const errors = { ...validateDraft(specs, draft), ...extraErrors }

  if (creating && (!key || !KEY_PATTERN.test(key))) {
    errors.key = KEY_MESSAGE
  }

  if (!creating && (!record || record.version === null || record.version === undefined)) {
    errors._form = 'The current version is unknown. Reload before saving.'
  }

  const patch = {
    ...patchFromDraft(specs, creating ? {} : recordSource(record), draft, { sendAll: creating }),
    ...extraBody,
  }

  const changed = Object.keys(patch).some((k) => k !== 'reason')

  let body = null
  if (Object.keys(errors).length === 0 && changed) {
    body = creating ? { key, ...createDefaults, ...patch } : withVersion(record, patch)
  }

  return { errors, changed, body }
}
