export const EXECUTE_ROLES = new Set(['OWNER', 'ADMIN', 'OPERATOR'])

export function executePath(actionId) {
  if (typeof actionId === 'boolean' || actionId === null || actionId === undefined) {
    throw new Error('Invalid action ID')
  }
  const str = String(actionId)
  if (!/^[1-9]\d*$/.test(str)) {
    throw new Error('Invalid action ID')
  }
  return `actions/${str}/execute`
}

export const EXECUTE_WARNING = [
  "Executing runs Bizora's simulated execution only.",
  'It stores a simulated success on this proposal, sets its status to EXECUTED and writes an audit entry.',
  'Nothing is sent to any customer, ad platform, courier or other external system.',
  'There is no undo.',
]

export function executionState(action, role) {
  if (!action || typeof action !== 'object') {
    return { kind: 'hidden', canExecute: false, message: '' }
  }

  const status = String(action.status || '').toUpperCase()

  if (status === 'APPROVED') {
    if (!action.approved_at) {
      return {
        kind: 'blocked',
        canExecute: false,
        message: 'This action has no approval time recorded, so the server will refuse to execute it.',
      }
    }
    if (action.is_simulated !== true) {
      return {
        kind: 'unavailable',
        canExecute: false,
        message:
          'Real execution is not available: no provider executor is connected, so the server refuses to run this action.',
      }
    }
    if (!EXECUTE_ROLES.has(role)) {
      return {
        kind: 'role',
        canExecute: false,
        message: 'Only owners, admins and operators can execute approved actions.',
      }
    }
    return {
      kind: 'ready',
      canExecute: true,
      message: '',
    }
  }

  if (status === 'EXECUTING') {
    return {
      kind: 'executing',
      canExecute: false,
      message:
        'Execution started but has not finished. It cannot be retried from here and needs manual reconciliation.',
    }
  }

  if (status === 'EXECUTED') {
    return {
      kind: 'executed',
      canExecute: false,
      message: '',
    }
  }

  if (status === 'FAILED') {
    return {
      kind: 'failed',
      canExecute: false,
      message: '',
    }
  }

  return {
    kind: 'hidden',
    canExecute: false,
    message: '',
  }
}

export function executionSummary(action) {
  if (!action || typeof action !== 'object') {
    return { executedAt: null, message: '', error: '', simulated: false }
  }

  const executedAt = action.executed_at || null
  const res = action.execution_result
  const message = res && typeof res.message === 'string' ? res.message : ''
  let error = ''
  if (res) {
    if (typeof res.error === 'string') {
      error = res.error
    } else if (res.errors) {
      error = 'The execution reported errors.'
    }
  }
  const simulated = action.is_simulated === true

  return { executedAt, message, error, simulated }
}

export function cleanExecuteError(text) {
  if (typeof text !== 'string') return ''
  const trimmed = text.trim()
  const m = trimmed.match(/^\[(['"])([\s\S]*)\1\]$/)
  if (m) {
    return m[2]
  }
  return trimmed
}

export function describeExecuteError(err) {
  if (!err) {
    return { kind: 'other', message: 'Executing the action failed.' }
  }
  if (err.status === 403) {
    return {
      kind: 'forbidden',
      message: 'Only owners, admins and operators can execute actions.',
    }
  }
  if (err.status === 404) {
    return {
      kind: 'not-found',
      message: 'This action no longer exists.',
    }
  }
  if (err.status === 409) {
    const cleaned = cleanExecuteError(err.detail)
    return {
      kind: 'conflict',
      message: cleaned || 'The action is not in a state that can be executed.',
    }
  }
  return {
    kind: 'other',
    message: err.detail || 'Executing the action failed.',
  }
}

export function normalizeExecutedAction(data) {
  if (!data || typeof data !== 'object') return null
  const idNum = Number(data.id)
  if (!Number.isInteger(idNum) || idNum <= 0) return null
  if (typeof data.status !== 'string' || !data.status.trim()) return null

  return {
    id: idNum,
    status: data.status,
    isSimulated: data.is_simulated === true,
    executedAt: data.executed_at ?? null,
    executionResult:
      data.execution_result && typeof data.execution_result === 'object' ? data.execution_result : null,
  }
}
