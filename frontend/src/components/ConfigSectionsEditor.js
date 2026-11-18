'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Banner, Button, Skeleton } from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { dateTime } from '@/lib/format'
import { CONFIG_SECTIONS, SECTION_LABELS, sectionPath } from '@/lib/configuration/paths'
import { canEditConfiguration } from '@/lib/configuration/writes'
import { normalizeRecord, actorLabel } from '@/lib/configuration/normalize'
import { SECTION_RESOURCES } from '@/lib/configuration/sections'
import ConfigRecordForm from './ConfigRecordForm'

export default function ConfigSectionsEditor({ businessId, role, timezone }) {
  const router = useRouter()
  const canEdit = canEditConfiguration(role)
  const [section, setSection] = useState('profile')
  const [record, setRecord] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [dirty, setDirty] = useState(false)
  const [notice, setNotice] = useState(null)

  const fetchSection = useCallback(
    async (sec) => {
      setLoading(true)
      setLoadError(null)
      try {
        const path = sectionPath(businessId, sec)
        const res = await clientApi(path)
        setRecord(normalizeRecord(res))
      } catch (err) {
        setLoadError(err?.detail || err?.message || 'Could not load settings')
      } finally {
        setLoading(false)
      }
    },
    [businessId],
  )

  useEffect(() => {
    fetchSection(section)
  }, [section, fetchSection])

  const handleSaved = (next) => {
    setRecord(next)
    setNotice(`${SECTION_LABELS[section]} saved. Version ${next.version}.`)
    router.refresh()
  }

  const resourceDef = SECTION_RESOURCES[section]

  return (
    <div className="stack" style={{ gap: 'var(--space-4, 16px)' }}>
      <div aria-live="polite" className="sr-only">
        {loading ? `Loading ${SECTION_LABELS[section]}…` : loadError ? loadError : notice ? notice : ''}
      </div>

      {!canEdit && (
        <Banner variant="info">You can view these settings. Only owners and managers can change them.</Banner>
      )}

      {notice && (
        <Banner variant="success" title="Saved" onClose={() => setNotice(null)}>
          {notice}
        </Banner>
      )}

      <div className="admin-subnav" role="group" aria-label="Settings sections">
        {CONFIG_SECTIONS.map((name) => (
          <button
            key={name}
            type="button"
            aria-pressed={section === name}
            disabled={dirty && section !== name}
            className={`admin-subnav-btn ${section === name ? 'is-active' : ''}`}
            onClick={() => setSection(name)}
          >
            {SECTION_LABELS[name]}
          </button>
        ))}
      </div>

      {dirty && (
        <p className="text-caption text-secondary">Save or discard your changes before switching sections.</p>
      )}

      {loading && <Skeleton variant="text" count={4} />}

      {loadError && (
        <Banner
          variant="danger"
          title="Could not load settings"
          action={
            <Button size="sm" variant="secondary" onClick={() => fetchSection(section)}>
              Retry
            </Button>
          }
        >
          {loadError}
        </Banner>
      )}

      {!loading && !loadError && record && (
        <div className="journey-card stack">
          {record.version === 0 && !record.updated_at ? (
            <p className="text-caption text-secondary">Not saved yet. Showing defaults.</p>
          ) : (
            <p className="text-caption text-secondary">
              Version {record.version} · Last changed {dateTime(record.updated_at, timezone)} by{' '}
              {actorLabel(record.updated_by_id)}
            </p>
          )}

          {resourceDef?.notes?.map((note, idx) => (
            <p key={idx} className="text-caption text-secondary">
              {note}
            </p>
          ))}

          <ConfigRecordForm
            key={`${section}-${record.version}`}
            resource={resourceDef}
            record={record}
            canEdit={canEdit}
            onSaved={handleSaved}
            onCancel={() => fetchSection(section)}
            cancelLabel="Discard changes"
            onDirtyChange={setDirty}
          />
        </div>
      )}
    </div>
  )
}
