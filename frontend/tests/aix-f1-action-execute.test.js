import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  EXECUTE_ROLES,
  executePath,
  EXECUTE_WARNING,
  executionState,
  executionSummary,
  cleanExecuteError,
  describeExecuteError,
  normalizeExecutedAction,
} from '../src/lib/ai/actions.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const ROOT = path.resolve(__dirname, '..')

test('ai actions lib: roles, paths, warnings, executionState (AIX-F1)', () => {
  assert.ok(EXECUTE_ROLES.has('OWNER'))
  assert.ok(EXECUTE_ROLES.has('ADMIN'))
  assert.ok(EXECUTE_ROLES.has('OPERATOR'))
  assert.ok(!EXECUTE_ROLES.has('MANAGER'))
  assert.ok(!EXECUTE_ROLES.has('VIEWER'))
  assert.ok(!EXECUTE_ROLES.has('MEMBER'))

  assert.equal(executePath(5), 'actions/5/execute')
  assert.equal(executePath('42'), 'actions/42/execute')
  for (const bad of [0, -1, '1.5', true, '', null, undefined]) {
    assert.throws(() => executePath(bad), /Invalid action ID/)
  }

  assert.deepEqual(EXECUTE_WARNING, [
    "Executing runs Bizora's simulated execution only.",
    'It stores a simulated success on this proposal, sets its status to EXECUTED and writes an audit entry.',
    'Nothing is sent to any customer, ad platform, courier or other external system.',
    'There is no undo.',
  ])

  // executionState checks
  assert.deepEqual(executionState({ status: 'SUGGESTED' }, 'OWNER'), {
    kind: 'hidden',
    canExecute: false,
    message: '',
  })
  assert.deepEqual(executionState({ status: 'REJECTED' }, 'OWNER'), {
    kind: 'hidden',
    canExecute: false,
    message: '',
  })

  // APPROVED without approved_at
  assert.deepEqual(executionState({ status: 'APPROVED', is_simulated: true }, 'OPERATOR'), {
    kind: 'blocked',
    canExecute: false,
    message: 'This action has no approval time recorded, so the server will refuse to execute it.',
  })

  // APPROVED is_simulated false
  assert.deepEqual(
    executionState(
      {
        status: 'APPROVED',
        approved_at: '2026-11-10T12:00:00Z',
        is_simulated: false,
      },
      'OPERATOR',
    ),
    {
      kind: 'unavailable',
      canExecute: false,
      message:
        'Real execution is not available: no provider executor is connected, so the server refuses to run this action.',
    },
  )

  // APPROVED is_simulated missing
  assert.deepEqual(executionState({ status: 'APPROVED', approved_at: '2026-11-10T12:00:00Z' }, 'OPERATOR'), {
    kind: 'unavailable',
    canExecute: false,
    message:
      'Real execution is not available: no provider executor is connected, so the server refuses to run this action.',
  })

  // APPROVED role not in EXECUTE_ROLES
  assert.deepEqual(
    executionState(
      {
        status: 'APPROVED',
        approved_at: '2026-11-10T12:00:00Z',
        is_simulated: true,
      },
      'MANAGER',
    ),
    {
      kind: 'role',
      canExecute: false,
      message: 'Only owners, admins and operators can execute approved actions.',
    },
  )

  // APPROVED ready
  assert.deepEqual(
    executionState(
      {
        status: 'APPROVED',
        approved_at: '2026-11-10T12:00:00Z',
        is_simulated: true,
      },
      'OPERATOR',
    ),
    {
      kind: 'ready',
      canExecute: true,
      message: '',
    },
  )

  // EXECUTING
  assert.deepEqual(executionState({ status: 'EXECUTING' }, 'OWNER'), {
    kind: 'executing',
    canExecute: false,
    message:
      'Execution started but has not finished. It cannot be retried from here and needs manual reconciliation.',
  })

  // EXECUTED & FAILED
  assert.deepEqual(executionState({ status: 'EXECUTED' }, 'OWNER'), {
    kind: 'executed',
    canExecute: false,
    message: '',
  })
  assert.deepEqual(executionState({ status: 'FAILED' }, 'OWNER'), {
    kind: 'failed',
    canExecute: false,
    message: '',
  })

  // Junk
  assert.deepEqual(executionState(null, 'OWNER'), {
    kind: 'hidden',
    canExecute: false,
    message: '',
  })
})

test('ai actions lib: executionSummary, errors, normalizeExecutedAction (AIX-F1)', () => {
  // executionSummary
  const contractAction = {
    executed_at: '2026-11-10T13:00:00Z',
    is_simulated: true,
    execution_result: {
      status: 'success',
      message: 'Simulated execution completed successfully',
    },
  }
  assert.deepEqual(executionSummary(contractAction), {
    executedAt: '2026-11-10T13:00:00Z',
    message: 'Simulated execution completed successfully',
    error: '',
    simulated: true,
  })

  assert.deepEqual(
    executionSummary({
      is_simulated: false,
      execution_result: { error: 'Network timeout' },
    }),
    {
      executedAt: null,
      message: '',
      error: 'Network timeout',
      simulated: false,
    },
  )

  assert.deepEqual(
    executionSummary({
      execution_result: { errors: ['item 1'] },
    }),
    {
      executedAt: null,
      message: '',
      error: 'The execution reported errors.',
      simulated: false,
    },
  )

  assert.deepEqual(executionSummary({ execution_result: null }), {
    executedAt: null,
    message: '',
    error: '',
    simulated: false,
  })

  // cleanExecuteError
  assert.equal(
    cleanExecuteError("['AiAction cannot execute without approval (approved_at must be set).']"),
    'AiAction cannot execute without approval (approved_at must be set).',
  )
  assert.equal(
    cleanExecuteError('["Action cannot be approved from state \'EXECUTED\'."]'),
    "Action cannot be approved from state 'EXECUTED'.",
  )
  assert.equal(cleanExecuteError('Plain error message'), 'Plain error message')
  assert.equal(cleanExecuteError(null), '')

  // describeExecuteError
  assert.deepEqual(describeExecuteError({ status: 403 }), {
    kind: 'forbidden',
    message: 'Only owners, admins and operators can execute actions.',
  })
  assert.deepEqual(describeExecuteError({ status: 404 }), {
    kind: 'not-found',
    message: 'This action no longer exists.',
  })
  assert.deepEqual(
    describeExecuteError({
      status: 409,
      detail: "['Action cannot execute.']",
    }),
    {
      kind: 'conflict',
      message: 'Action cannot execute.',
    },
  )
  assert.deepEqual(
    describeExecuteError({
      status: 409,
      detail: '',
    }),
    {
      kind: 'conflict',
      message: 'The action is not in a state that can be executed.',
    },
  )
  assert.deepEqual(
    describeExecuteError({
      status: 500,
      detail: 'Internal server failure',
    }),
    {
      kind: 'other',
      message: 'Internal server failure',
    },
  )
  assert.deepEqual(describeExecuteError(null), {
    kind: 'other',
    message: 'Executing the action failed.',
  })

  // normalizeExecutedAction
  const norm = normalizeExecutedAction({
    id: 10,
    status: 'EXECUTED',
    is_simulated: true,
    executed_at: '2026-11-10T12:00:00Z',
    execution_result: { status: 'success' },
  })
  assert.deepEqual(norm, {
    id: 10,
    status: 'EXECUTED',
    isSimulated: true,
    executedAt: '2026-11-10T12:00:00Z',
    executionResult: { status: 'success' },
  })

  assert.deepEqual(
    normalizeExecutedAction({
      id: 10,
      status: 'FAILED',
    }),
    {
      id: 10,
      status: 'FAILED',
      isSimulated: false,
      executedAt: null,
      executionResult: null,
    },
  )

  assert.equal(normalizeExecutedAction(null), null)
  assert.equal(normalizeExecutedAction({}), null)
  assert.equal(normalizeExecutedAction({ id: 0, status: 'EXECUTED' }), null)
  assert.equal(normalizeExecutedAction({ id: 10, status: '' }), null)
})

test('source text: actions lib, AiActionExecute.js, AiStudio.js (AIX-F1)', () => {
  const libPath = path.join(ROOT, 'src/lib/ai/actions.js')
  assert.ok(fs.existsSync(libPath), 'actions.js must exist')
  const libContent = fs.readFileSync(libPath, 'utf8')
  assert.doesNotMatch(libContent, /@\//)
  assert.doesNotMatch(libContent, /\bwindow\b/)
  assert.doesNotMatch(libContent, /\bfetch\b/)
  assert.doesNotMatch(libContent, /\bimport\s+/)

  const compPath = path.join(ROOT, 'src/components/AiActionExecute.js')
  assert.ok(fs.existsSync(compPath), 'AiActionExecute.js must exist')
  const compContent = fs.readFileSync(compPath, 'utf8')
  assert.match(compContent, /^'use client'/)
  assert.match(compContent, /from\s+['"]@\/lib\/ai\/actions['"]/)
  assert.match(compContent, /from\s+['"]@\/lib\/clientApi['"]/)
  assert.match(compContent, /from\s+['"]@\/components\/ui['"]/)

  // Verify all imported ui components exist in ui/index.js
  const uiIndexContent = fs.readFileSync(path.join(ROOT, 'src/components/ui/index.js'), 'utf8')
  const uiImportsMatch = compContent.match(/import\s+\{([^}]+)\}\s+from\s+['"]@\/components\/ui['"]/)
  assert.ok(uiImportsMatch)
  const importedUiNames = uiImportsMatch[1].split(',').map((s) => s.trim())
  for (const name of importedUiNames) {
    assert.ok(uiIndexContent.includes(name), `UI kit index must export ${name}`)
  }

  // Required strings in AiActionExecute.js
  const reqStrings = [
    'executePath',
    'executionState',
    'executionSummary',
    'describeExecuteError',
    'normalizeExecutedAction',
    'EXECUTE_WARNING',
    'ConfirmDialog',
    "method: 'POST'",
    'Execute (simulated)',
    'Execute this action?',
    'Execution is simulated',
    'Nothing was sent to any external system.',
    'aria-live="polite"',
  ]
  for (const s of reqStrings) {
    assert.ok(compContent.includes(s), `AiActionExecute.js must include "${s}"`)
  }

  // Banned patterns in AiActionExecute.js
  assert.doesNotMatch(compContent, /\bwindow\.confirm\b/)
  assert.doesNotMatch(compContent, /\bIdempotency-Key\b/i)
  assert.doesNotMatch(compContent, /<Banner\b[^>]*\btone=/)
  const hex = compContent.match(/#(?:[0-9a-fA-F]{3}){1,2}\b/g) || []
  assert.equal(hex.length, 0, 'No raw hex')
  const px = compContent.match(/\b\d+px\b/g) || []
  assert.equal(px.length, 0, 'No px units')

  // AiStudio.js checks
  const studioPath = path.join(ROOT, 'src/components/AiStudio.js')
  const studioContent = fs.readFileSync(studioPath, 'utf8')
  assert.match(studioContent, /import\s+AiActionExecute\s+from\s+['"]\.\/AiActionExecute['"]/)
  assert.match(studioContent, /<AiActionExecute/)
  assert.ok(studioContent.includes('approval_note: reviewNote.trim()'))
  assert.ok(studioContent.includes("'EXECUTED', 'FAILED'"))
  assert.doesNotMatch(studioContent, /\{\s*note:\s*reviewNote/)
  assert.ok(studioContent.includes('Execution is simulated.'))
  assert.ok(studioContent.includes('reviewNote.length < 3'))
  assert.ok(studioContent.includes('reviewNote.length > 1000'))
  assert.ok(studioContent.includes('actions/${actionId}/approve'))
  assert.ok(studioContent.includes('actions/${actionId}/reject'))
})
