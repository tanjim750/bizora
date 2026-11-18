export const REASON_SPEC = {
  path: 'reason',
  label: 'Reason for change (optional)',
  type: 'text',
  maxLength: 500,
  omitWhenBlank: true,
  hint: 'Saved in the change history. Never enter passwords or keys.',
}

export function getPath(obj, path) {
  if (!obj || typeof obj !== 'object' || typeof path !== 'string') return undefined
  const parts = path.split('.')
  let curr = obj
  for (const part of parts) {
    if (curr === null || curr === undefined || typeof curr !== 'object') {
      return undefined
    }
    curr = curr[part]
  }
  return curr
}

export function setPath(obj, path, value) {
  const parts = path.split('.')
  function cloneAndSet(current, index) {
    const part = parts[index]
    const next = current && typeof current === 'object' && !Array.isArray(current) ? { ...current } : {}
    if (index === parts.length - 1) {
      next[part] = value
      return next
    }
    next[part] = cloneAndSet(current ? current[part] : undefined, index + 1)
    return next
  }
  return cloneAndSet(obj, 0)
}

export function parseListText(text) {
  if (typeof text !== 'string') return []
  return text
    .split(/[\n,]/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
}

export function draftFromSettings(specs, source) {
  const draft = {}
  for (const spec of specs) {
    const val = getPath(source, spec.path)
    if (spec.type === 'bool') {
      draft[spec.path] = Boolean(val)
    } else if (spec.type === 'multi') {
      draft[spec.path] = Array.isArray(val) ? val.map(String) : []
    } else if (spec.type === 'list') {
      draft[spec.path] = Array.isArray(val) ? val.join('\n') : ''
    } else {
      if (val === null || val === undefined) {
        draft[spec.path] = ''
      } else {
        draft[spec.path] = String(val)
      }
    }
  }
  return draft
}

function checkRange(num, min, max, label) {
  if (min !== undefined && max !== undefined) {
    if (num < min || num > max) return `${label} must be between ${min} and ${max}.`
  } else if (min !== undefined) {
    if (num < min) return `${label} must be at least ${min}.`
  } else if (max !== undefined) {
    if (num > max) return `${label} must be at most ${max}.`
  }
  return null
}

export function validateDraft(specs, draft) {
  const errors = {}

  for (const spec of specs) {
    const val = draft[spec.path]
    const label = spec.label
    const isBlank = val === undefined || val === null || (typeof val === 'string' && val.trim().length === 0)

    if (spec.type === 'bool') {
      continue
    }

    if (spec.type === 'text' || spec.type === 'textarea') {
      if (isBlank) {
        if (spec.required) {
          errors[spec.path] = `${label} is required.`
        }
        continue
      }
      const trimmed = String(val).trim()
      if (spec.maxLength !== undefined && trimmed.length > spec.maxLength) {
        errors[spec.path] = `${label} must be at most ${spec.maxLength} characters.`
        continue
      }
      if (spec.regex && !spec.regex.test(trimmed)) {
        errors[spec.path] = spec.regexMessage || `${label} is not in the expected format.`
        continue
      }
      continue
    }

    if (spec.type === 'int') {
      if (isBlank) {
        if (spec.required) {
          errors[spec.path] = `${label} is required.`
        }
        continue
      }
      const trimmed = String(val).trim()
      if (!/^-?\d+$/.test(trimmed)) {
        errors[spec.path] = `${label} must be a whole number.`
        continue
      }
      const num = Number(trimmed)
      const rangeErr = checkRange(num, spec.min, spec.max, label)
      if (rangeErr) {
        errors[spec.path] = rangeErr
        continue
      }
      continue
    }

    if (spec.type === 'decimal') {
      if (isBlank) {
        if (spec.required) {
          errors[spec.path] = `${label} is required.`
        }
        continue
      }
      const trimmed = String(val).trim()
      if (!/^-?\d+(\.\d+)?$/.test(trimmed)) {
        errors[spec.path] = `${label} must be a number.`
        continue
      }
      if (spec.places !== undefined) {
        const dotIdx = trimmed.indexOf('.')
        if (dotIdx !== -1) {
          const fracDigits = trimmed.length - dotIdx - 1
          if (fracDigits > spec.places) {
            errors[spec.path] = `${label} allows at most ${spec.places} decimal places.`
            continue
          }
        }
      }
      const num = Number(trimmed)
      const rangeErr = checkRange(num, spec.min, spec.max, label)
      if (rangeErr) {
        errors[spec.path] = rangeErr
        continue
      }
      continue
    }

    if (spec.type === 'select') {
      if (isBlank) {
        if (spec.allowEmpty && val === '') {
          // allowed empty string
          continue
        }
        if (spec.required) {
          errors[spec.path] = `${label} is required.`
        }
        continue
      }
      const strVal = String(val)
      const hasOpt = (spec.options || []).some((o) => {
        if (typeof o === 'object' && o !== null) {
          return String(o.value) === strVal
        }
        return String(o) === strVal
      })
      if (!hasOpt) {
        errors[spec.path] = `${label} has an unsupported value.`
      }
      continue
    }

    if (spec.type === 'multi') {
      const items = Array.isArray(val) ? val : []
      const optValues = new Set(
        (spec.options || []).map((o) => (typeof o === 'object' && o !== null ? String(o.value) : String(o))),
      )
      const hasBad = items.some((item) => !optValues.has(String(item)))
      if (hasBad) {
        errors[spec.path] = `${label} has an unsupported choice.`
        continue
      }
      if (spec.maxItems !== undefined && items.length > spec.maxItems) {
        errors[spec.path] = `${label} allows at most ${spec.maxItems} choices.`
        continue
      }
      if (spec.minItems !== undefined && items.length < spec.minItems) {
        errors[spec.path] = `${label} needs at least ${spec.minItems} choice(s).`
        continue
      }
      continue
    }

    if (spec.type === 'list') {
      const items = typeof val === 'string' ? parseListText(val) : Array.isArray(val) ? val : []
      if (spec.minItems !== undefined && items.length < spec.minItems) {
        errors[spec.path] = `${label} needs at least ${spec.minItems} item(s).`
        continue
      }
      if (spec.maxItems !== undefined && items.length > spec.maxItems) {
        errors[spec.path] = `${label} allows at most ${spec.maxItems} items.`
        continue
      }
      if (spec.itemMaxLength !== undefined) {
        const hasTooLong = items.some((item) => String(item).length > spec.itemMaxLength)
        if (hasTooLong) {
          errors[spec.path] = `${label}: each item must be at most ${spec.itemMaxLength} characters.`
          continue
        }
      }
      continue
    }
  }

  return errors
}

export function patchFromDraft(specs, source, draft, { sendAll = false } = {}) {
  let patch = {}

  for (const spec of specs) {
    const draftVal = draft[spec.path]
    const origVal = getPath(source, spec.path)

    if (spec.type === 'bool') {
      const bDraft = Boolean(draftVal)
      if (sendAll) {
        patch = setPath(patch, spec.path, bDraft)
      } else {
        const bOrig = Boolean(origVal)
        if (bDraft !== bOrig) {
          patch = setPath(patch, spec.path, bDraft)
        }
      }
      continue
    }

    if (spec.type === 'multi') {
      const draftArr = Array.isArray(draftVal) ? draftVal : []
      if (sendAll) {
        if (draftArr.length > 0) {
          patch = setPath(patch, spec.path, draftArr)
        }
      } else {
        const origArr = Array.isArray(origVal) ? origVal : []
        const draftSet = new Set(draftArr)
        const origSet = new Set(origArr)
        const areSetsEqual = draftSet.size === origSet.size && [...draftSet].every((x) => origSet.has(x))
        if (!areSetsEqual) {
          patch = setPath(patch, spec.path, draftArr)
        }
      }
      continue
    }

    if (spec.type === 'list') {
      const parsed =
        typeof draftVal === 'string' ? parseListText(draftVal) : Array.isArray(draftVal) ? draftVal : []
      if (sendAll) {
        if (parsed.length > 0) {
          patch = setPath(patch, spec.path, parsed)
        }
      } else {
        const origArr = Array.isArray(origVal) ? origVal : []
        const isSame = parsed.length === origArr.length && parsed.every((item, i) => item === origArr[i])
        if (!isSame) {
          patch = setPath(patch, spec.path, parsed)
        }
      }
      continue
    }

    if (spec.type === 'text' || spec.type === 'textarea') {
      const trimmed = draftVal !== undefined && draftVal !== null ? String(draftVal).trim() : ''
      const origStr = origVal !== undefined && origVal !== null ? String(origVal) : ''

      if (sendAll) {
        if (trimmed !== '') {
          patch = setPath(patch, spec.path, trimmed)
        }
      } else {
        if (trimmed !== '') {
          if (trimmed !== origStr) {
            patch = setPath(patch, spec.path, trimmed)
          }
        } else {
          if (origStr !== '' && !spec.omitWhenBlank) {
            patch = setPath(patch, spec.path, '')
          }
        }
      }
      continue
    }

    if (spec.type === 'int') {
      const trimmed = draftVal !== undefined && draftVal !== null ? String(draftVal).trim() : ''
      if (sendAll) {
        if (trimmed !== '') {
          patch = setPath(patch, spec.path, Number(trimmed))
        }
      } else {
        if (trimmed !== '') {
          const num = Number(trimmed)
          if (origVal === null || origVal === undefined || String(num) !== String(origVal)) {
            patch = setPath(patch, spec.path, num)
          }
        }
      }
      continue
    }

    if (spec.type === 'decimal') {
      const trimmed = draftVal !== undefined && draftVal !== null ? String(draftVal).trim() : ''
      if (sendAll) {
        if (trimmed !== '') {
          patch = setPath(patch, spec.path, trimmed)
        }
      } else {
        if (trimmed !== '') {
          if (
            origVal === null ||
            origVal === undefined ||
            origVal === '' ||
            Number(trimmed) !== Number(origVal)
          ) {
            patch = setPath(patch, spec.path, trimmed)
          }
        }
      }
      continue
    }

    if (spec.type === 'select') {
      const trimmed = draftVal !== undefined && draftVal !== null ? String(draftVal).trim() : ''
      const opt = (spec.options || []).find((o) => {
        if (typeof o === 'object' && o !== null) {
          return String(o.value) === trimmed
        }
        return String(o) === trimmed
      })
      const optVal = opt !== undefined ? (typeof opt === 'object' && opt !== null ? opt.value : opt) : trimmed

      if (sendAll) {
        if (trimmed !== '') {
          patch = setPath(patch, spec.path, optVal)
        }
      } else {
        if (trimmed === '') {
          if (spec.allowEmpty && origVal !== null && origVal !== undefined && origVal !== '') {
            patch = setPath(patch, spec.path, '')
          }
        } else {
          if (origVal === null || origVal === undefined || trimmed !== String(origVal)) {
            patch = setPath(patch, spec.path, optVal)
          }
        }
      }
      continue
    }
  }

  return patch
}

export function fieldError(errors, path) {
  if (!errors || typeof errors !== 'object') return undefined

  if (errors[path] !== undefined) {
    return errors[path]
  }

  if (path.startsWith('parameters.')) {
    const stripped = path.slice('parameters.'.length)
    if (errors[stripped] !== undefined) {
      return errors[stripped]
    }
  }

  const prefix = `${path}.`
  const matching = []
  for (const [k, v] of Object.entries(errors)) {
    if (k.startsWith(prefix) && v) {
      matching.push(v)
    }
  }

  if (matching.length > 0) {
    return matching.join(' ')
  }

  return undefined
}

export function rebaseDraft(specs, oldSource, newSource, draft) {
  const oldDraft = draftFromSettings(specs, oldSource)
  const newDraft = draftFromSettings(specs, newSource)
  const result = { ...newDraft }

  for (const spec of specs) {
    if (draft[spec.path] !== oldDraft[spec.path]) {
      result[spec.path] = draft[spec.path]
    }
  }

  return result
}
