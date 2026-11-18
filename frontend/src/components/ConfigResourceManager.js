'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { Banner, Button, DataTable, Dialog, StatusChip } from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { dateTime } from '@/lib/format'
import { canEditConfiguration } from '@/lib/configuration/writes'
import { normalizePage, normalizeRecord, actorLabel } from '@/lib/configuration/normalize'
import ConfigRecordForm from './ConfigRecordForm'

export default function ConfigResourceManager({
  businessId,
  role,
  timezone,
  resource,
  context,
  rowActions,
  below,
  onChanged,
}) {
  const router = useRouter()
  const canEdit = canEditConfiguration(role)
  const [page, setPage] = useState(1)
  const [list, setList] = useState({ results: [], count: 0 })
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [editor, setEditor] = useState(null)
  const [notice, setNotice] = useState(null)
  const [openingError, setOpeningError] = useState(null)

  const loadList = useCallback(async () => {
    setIsLoading(true)
    setLoadError(null)
    try {
      const data = await clientApi(resource.listPath(businessId, { page, pageSize: 25 }))
      const norm = normalizePage(data, normalizeRecord)
      setList(norm)
    } catch (err) {
      setLoadError(err)
    } finally {
      setIsLoading(false)
    }
  }, [businessId, page, resource])

  useEffect(() => {
    loadList()
  }, [loadList])

  const handleOpenRow = async (row) => {
    setOpeningError(null)
    try {
      const res = await clientApi(resource.itemPath(businessId, row))
      const rec = normalizeRecord(res)
      setEditor({ record: rec })
    } catch (err) {
      setOpeningError(err?.detail || err?.message || 'Could not open the record')
    }
  }

  const columns = useMemo(() => {
    const baseCols = (resource.columns || []).map((col) => ({
      key: col.key,
      label: col.label,
      align: col.align,
      render: (row) => {
        if (col.chip) {
          const chipLabel = col.text ? col.text(row, context) : row.status
          return <StatusChip status={row.status} label={chipLabel} size="sm" />
        }
        if (col.mono) {
          return <span className="font-mono">{col.text ? col.text(row, context) : row[col.key]}</span>
        }
        return col.text ? col.text(row, context) : (row[col.key] ?? '—')
      },
    }))

    baseCols.push({
      key: 'version',
      label: 'Version',
      align: 'right',
      render: (row) => <span className="font-mono">v{row.version ?? 0}</span>,
    })

    baseCols.push({
      key: 'updated',
      label: 'Updated',
      render: (row) =>
        row.updated_at ? `${dateTime(row.updated_at, timezone)} · ${actorLabel(row.updated_by_id)}` : '—',
    })

    baseCols.push({
      key: 'actions',
      label: '',
      align: 'right',
      render: (row) => (
        <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end' }}>
          <Button size="sm" variant="secondary" onClick={() => handleOpenRow(row)}>
            {canEdit ? 'Edit' : 'View'}
          </Button>
          {rowActions?.(row)}
        </div>
      ),
    })

    return baseCols
  }, [resource, context, canEdit, timezone, rowActions])

  const handleSaved = (savedRec) => {
    const actionWord = !editor?.record ? 'Created' : 'Saved'
    setNotice(`${actionWord} ${resource.singular} ${resource.nameOf(savedRec)}. Version ${savedRec.version}.`)
    setEditor(null)
    loadList()
    router.refresh()
    onChanged?.()
  }

  const dialogTitle = !editor?.record
    ? `New ${resource.singular}`
    : `${canEdit ? 'Edit' : 'View'} ${resource.singular}: ${resource.nameOf(editor.record)}`

  return (
    <div className="stack" style={{ gap: 'var(--space-4, 16px)' }}>
      <div aria-live="polite" className="sr-only">
        {isLoading
          ? `Loading ${resource.title}…`
          : loadError
            ? loadError.detail || 'Could not load records'
            : notice || ''}
      </div>

      {!canEdit && (
        <Banner variant="info">
          You can view this configuration. Only owners and managers can change it.
        </Banner>
      )}

      {openingError && (
        <Banner variant="danger" title="Could not open the record" onClose={() => setOpeningError(null)}>
          {openingError}
        </Banner>
      )}

      {notice && (
        <Banner variant="success" title="Saved" onClose={() => setNotice(null)}>
          {notice}
        </Banner>
      )}

      {resource.notes?.map((n, i) => (
        <p key={i} className="text-caption text-secondary">
          {n}
        </p>
      ))}

      {canEdit && resource.createPath && (
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Button size="sm" variant="primary" onClick={() => setEditor({ record: null })}>
            New {resource.singular}
          </Button>
        </div>
      )}

      <DataTable
        ariaLabel={resource.title}
        showDensityToggle={false}
        openInDrawer={false}
        isLoading={isLoading}
        error={loadError}
        onRetry={loadList}
        emptyTitle={`No ${resource.title.toLowerCase()} yet`}
        emptyDescription="Nothing has been saved here yet."
        columns={columns}
        rows={list.results}
        pagination={{
          page,
          pageSize: 25,
          total: list.count,
          onPageChange: setPage,
        }}
      />

      {below}

      {editor && (
        <Dialog isOpen onClose={() => setEditor(null)} maxWidth="48rem" title={dialogTitle}>
          <ConfigRecordForm
            key={editor.record?.version ?? 'new'}
            businessId={businessId}
            resource={resource}
            record={editor.record}
            creating={!editor.record}
            canEdit={canEdit}
            context={context}
            onSaved={handleSaved}
            onCancel={() => setEditor(null)}
            cancelLabel="Cancel"
          />
        </Dialog>
      )}
    </div>
  )
}
