'use client'

import { useState, useMemo, useEffect } from 'react'
import { Banner, Button, Field, Input } from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { STALE_MESSAGE, classifyWriteError } from '@/lib/configuration/writes'
import { normalizeRecord, recordSource } from '@/lib/configuration/normalize'
import { rebaseDraft } from '@/lib/configuration/fieldKit'
import ConfigFields from './ConfigFields'

export default function ConfigRecordForm({
  businessId,
  resource,
  record,
  creating = false,
  canEdit,
  context,
  onSaved,
  onCancel,
  cancelLabel = 'Cancel',
  onDirtyChange,
}) {
  const [current, setCurrent] = useState(record)
  const [draft, setDraft] = useState(() => resource.draftFor(record, context))
  const [key, setKey] = useState('')
  const [busy, setBusy] = useState(false)
  const [stale, setStale] = useState(false)
  const [message, setMessage] = useState('')
  const [errors, setErrors] = useState({})

  const specs = useMemo(
    () => resource.specsFor({ record: current, draft, creating, context }),
    [resource, current, draft, creating, context],
  )

  const result = useMemo(
    () => resource.build({ record: current, draft, key, creating, context }),
    [resource, current, draft, key, creating, context],
  )

  useEffect(() => {
    onDirtyChange?.(result.changed)
  }, [result.changed, onDirtyChange])

  const handleFieldChange = (path, value) => {
    setDraft((prev) => ({ ...prev, [path]: value }))
    if (errors[path]) {
      setErrors((prev) => {
        const next = { ...prev }
        delete next[path]
        return next
      })
    }
  }

  const handleReloadKeepEdits = async () => {
    try {
      setBusy(true)
      const path = resource.itemPath(businessId, current)
      const res = await clientApi(path)
      const latest = normalizeRecord(res)
      const latestSpecs = resource.specsFor({ record: latest, draft, creating: false, context })
      const rebased = rebaseDraft(latestSpecs, recordSource(current), recordSource(latest), draft)
      setCurrent(latest)
      setDraft(rebased)
      setStale(false)
      setMessage('')
      setErrors({})
    } catch (err) {
      setMessage(err?.detail || err?.message || 'Could not reload record.')
    } finally {
      setBusy(false)
    }
  }

  const handleSave = async () => {
    if (result.errors && Object.keys(result.errors).length > 0) {
      setErrors(result.errors)
      setMessage(result.errors._form || 'Fix the highlighted fields.')
      return
    }

    try {
      setBusy(true)
      setMessage('')
      setErrors({})

      const path = creating ? resource.createPath(businessId) : resource.itemPath(businessId, current)
      const method = creating ? 'POST' : resource.updateMethod
      const res = await clientApi(path, { method, body: result.body })
      const savedRecord = normalizeRecord(res)
      setCurrent(savedRecord)
      onSaved?.(savedRecord)
    } catch (err) {
      const failure = classifyWriteError(err, creating ? 'create' : 'update')
      setStale(Boolean(failure.stale))
      setErrors(failure.fieldErrors || {})
      setMessage(failure.stale ? '' : failure.fieldErrors?._form || failure.message || 'Could not save')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="stack" style={{ gap: 'var(--space-4, 16px)' }}>
      {stale && (
        <Banner
          variant="warning"
          title={STALE_MESSAGE}
          action={
            <Button size="sm" variant="secondary" onClick={handleReloadKeepEdits}>
              Reload and keep my edits
            </Button>
          }
        />
      )}

      {message && (
        <Banner variant="danger" title="Could not save">
          {message}
        </Banner>
      )}

      {creating && resource.keyField && (
        <Field
          label="Key"
          required
          hint="Lowercase letters, digits, _ or -. It cannot be changed later."
          error={errors.key}
        >
          <Input value={key} onChange={(e) => setKey(e.target.value)} />
        </Field>
      )}

      <ConfigFields
        specs={specs}
        draft={draft}
        errors={errors}
        onChange={handleFieldChange}
        idPrefix={`cfg-${resource.id}`}
        lockedPaths={resource.lockedPaths ? resource.lockedPaths({ creating }) : []}
        disabled={!canEdit || busy}
      />

      {canEdit && (
        <div className="button-row">
          <Button variant="primary" isLoading={busy} disabled={!result.changed || busy} onClick={handleSave}>
            {creating ? `Create ${resource.singular}` : 'Save changes'}
          </Button>
          {onCancel && (
            <Button variant="secondary" disabled={busy} onClick={onCancel}>
              {cancelLabel}
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
