'use client'

import { Field, Input, Select, Textarea, Checkbox } from '@/components/ui'
import { fieldError } from '@/lib/configuration/fieldKit'

export default function ConfigFields({
  specs = [],
  draft = {},
  errors = {},
  onChange,
  disabled = false,
  lockedPaths = [],
  idPrefix = 'cfg',
}) {
  return (
    <div className="grid-kpi">
      {specs.map((spec) => {
        const controlId = `${idPrefix}-${spec.path.replace(/\./g, '-')}`
        const err = fieldError(errors, spec.path)
        const isLocked = disabled || lockedPaths.includes(spec.path)
        const val = draft[spec.path]

        if (spec.type === 'bool') {
          return (
            <div key={spec.path} className="form-field">
              <Checkbox
                id={controlId}
                label={spec.label}
                hint={spec.hint}
                checked={Boolean(val)}
                disabled={isLocked}
                onChange={(e) => onChange?.(spec.path, e.target.checked)}
              />
              {err && (
                <p className="form-error" role="alert">
                  {err}
                </p>
              )}
            </div>
          )
        }

        if (spec.type === 'multi') {
          const selected = Array.isArray(val) ? val.map(String) : []
          const opts = spec.options || []

          const handleToggle = (optValue, checked) => {
            let next
            if (checked) {
              const set = new Set([...selected, String(optValue)])
              next = opts.filter((o) => set.has(String(o.value))).map((o) => String(o.value))
            } else {
              next = selected.filter((v) => v !== String(optValue))
            }
            onChange?.(spec.path, next)
          }

          return (
            <fieldset key={spec.path} className="form-field">
              <legend className="form-label">{spec.label}</legend>
              <div className="stack" style={{ gap: 'var(--space-2, 8px)' }}>
                {opts.map((opt) => (
                  <Checkbox
                    key={String(opt.value)}
                    id={`${controlId}-${String(opt.value).replace(/\s+/g, '-')}`}
                    label={opt.label}
                    checked={selected.includes(String(opt.value))}
                    disabled={isLocked}
                    onChange={(e) => handleToggle(opt.value, e.target.checked)}
                  />
                ))}
              </div>
              {spec.hint && !err && <p className="form-hint">{spec.hint}</p>}
              {err && (
                <p className="form-error" role="alert">
                  {err}
                </p>
              )}
            </fieldset>
          )
        }

        if (spec.type === 'textarea' || spec.type === 'list') {
          const hint = spec.hint || (spec.type === 'list' ? 'One per line.' : undefined)
          return (
            <Field
              key={spec.path}
              id={controlId}
              label={spec.label}
              hint={hint}
              error={err}
              required={spec.required}
            >
              <Textarea
                id={controlId}
                rows={3}
                value={val ?? ''}
                placeholder={spec.placeholder}
                disabled={isLocked}
                onChange={(e) => onChange?.(spec.path, e.target.value)}
              />
            </Field>
          )
        }

        if (spec.type === 'select') {
          let opts = spec.options || []
          if (!spec.required && !spec.allowEmpty) {
            opts = [{ value: '', label: 'Not set' }, ...opts]
          }
          return (
            <Field
              key={spec.path}
              id={controlId}
              label={spec.label}
              hint={spec.hint}
              error={err}
              required={spec.required}
            >
              <Select
                id={controlId}
                options={opts}
                value={val ?? ''}
                disabled={isLocked}
                onChange={(e) => onChange?.(spec.path, e.target.value)}
              />
            </Field>
          )
        }

        // text, int, decimal
        const inputMode = spec.type === 'int' ? 'numeric' : spec.type === 'decimal' ? 'decimal' : undefined

        return (
          <Field
            key={spec.path}
            id={controlId}
            label={spec.label}
            hint={spec.hint}
            error={err}
            required={spec.required}
          >
            <Input
              id={controlId}
              value={val ?? ''}
              placeholder={spec.placeholder}
              disabled={isLocked}
              inputMode={inputMode}
              onChange={(e) => onChange?.(spec.path, e.target.value)}
            />
          </Field>
        )
      })}
    </div>
  )
}
