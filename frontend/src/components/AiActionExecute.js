'use client'

import { useState } from 'react'
import { Play } from 'lucide-react'
import { Banner, Button, ConfirmDialog } from '@/components/ui'
import { clientApi } from '@/lib/clientApi'
import { dateTime } from '@/lib/format'
import {
  EXECUTE_WARNING,
  executePath,
  executionState,
  executionSummary,
  describeExecuteError,
  normalizeExecutedAction,
} from '@/lib/ai/actions'

export default function AiActionExecute({ action, role, timezone, onDone }) {
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState(null)
  const [override, setOverride] = useState(null)

  const current = override ? { ...action, ...override } : action
  const state = executionState(current, role)
  const summary = executionSummary(current)

  const handleConfirmExecute = async () => {
    if (busy) return
    setBusy(true)
    try {
      const data = await clientApi(executePath(action.id), { method: 'POST' })
      const norm = normalizeExecutedAction(data)
      if (!norm) {
        setNotice({
          variant: 'danger',
          title: 'Execution answered, but the answer could not be read.',
          message: '',
        })
        return
      }

      setOverride({
        status: norm.status,
        executed_at: norm.executedAt,
        execution_result: norm.executionResult,
        is_simulated: norm.isSimulated,
      })

      if (norm.status === 'EXECUTED') {
        const title = norm.isSimulated ? 'Execution recorded (simulated)' : 'Execution recorded'
        setNotice({
          variant: 'success',
          title,
          message: norm.executionResult?.message || '',
        })
      } else if (norm.status === 'FAILED') {
        setNotice({
          variant: 'danger',
          title: 'Execution failed',
          message: norm.executionResult?.error || '',
        })
      }

      onDone?.(norm)
    } catch (err) {
      const desc = describeExecuteError(err)
      setNotice({
        variant: 'danger',
        title: '',
        message: desc.message,
      })
      if (desc.kind === 'conflict') {
        onDone?.(null)
      }
    } finally {
      setBusy(false)
      setConfirmOpen(false)
    }
  }

  if (state.kind === 'hidden' && !notice) {
    return null
  }

  return (
    <div className="stack-sm">
      <div aria-live="polite">
        {notice && (
          <Banner variant={notice.variant} title={notice.title || undefined} onClose={() => setNotice(null)}>
            {notice.message}
          </Banner>
        )}
      </div>

      {['role', 'unavailable', 'blocked', 'executing'].includes(state.kind) && (
        <p className="muted text-caption">{state.message}</p>
      )}

      {state.kind === 'executed' && (
        <div className="stack-sm">
          <p className="text-body font-semibold">
            Executed{summary.simulated ? ' (simulated)' : ''}
            {summary.executedAt ? ` at ${dateTime(summary.executedAt, timezone || 'Asia/Dhaka')}` : ''}
          </p>
          {summary.message && <p className="text-caption text-secondary">{summary.message}</p>}
          {summary.simulated && (
            <p className="text-caption text-secondary">Nothing was sent to any external system.</p>
          )}
        </div>
      )}

      {state.kind === 'failed' && (
        <div className="stack-sm">
          <p className="text-body font-semibold">Execution failed.</p>
          {summary.error && <p className="text-caption text-secondary">{summary.error}</p>}
        </div>
      )}

      {state.kind === 'ready' && (
        <div className="stack-sm">
          <h4 className="font-semibold text-body">Execute this action</h4>
          <Banner variant="warning" title="Execution is simulated">
            {EXECUTE_WARNING.map((line, idx) => (
              <p key={idx}>{line}</p>
            ))}
          </Banner>
          <div>
            <Button variant="primary" size="sm" icon={Play} onClick={() => setConfirmOpen(true)}>
              Execute (simulated)
            </Button>
          </div>
        </div>
      )}

      {confirmOpen && (
        <ConfirmDialog
          isOpen={confirmOpen}
          onClose={() => setConfirmOpen(false)}
          onConfirm={handleConfirmExecute}
          title="Execute this action?"
          message={EXECUTE_WARNING.join(' ')}
          confirmLabel="Execute (simulated)"
          variant="primary"
          isLoading={busy}
        />
      )}
    </div>
  )
}
