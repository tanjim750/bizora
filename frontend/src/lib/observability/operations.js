/**
 * Observability operations library (pure functions).
 * Contract: app/observability/serializers.py and app/observability/operations.py
 */

/**
 * Builds the operation request body with an idempotency key.
 * @param {string} key
 * @returns {{ idempotency_key: string }}
 */
export function operationBody(key) {
  if (typeof key !== 'string' || key.length === 0 || key.length > 200) {
    throw new Error('A valid idempotency key (1-200 characters) is required.')
  }
  return { idempotency_key: key }
}

/**
 * Describes the result of an operation attempt.
 * @param {'connection_test' | 'sync_retry'} kind
 * @param {object | null | undefined} attempt
 * @returns {{ tone: 'success' | 'warning' | 'danger', text: string }}
 */
export function describeAttempt(kind, attempt) {
  const fallback = {
    tone: 'warning',
    text: 'The server answered without a clear result.',
  }

  if (!attempt || typeof attempt !== 'object') {
    return fallback
  }

  if (kind !== 'connection_test' && kind !== 'sync_retry') {
    return fallback
  }

  const status = attempt.status

  if (status === 'SUCCEEDED') {
    return {
      tone: 'success',
      text: kind === 'connection_test' ? 'Connection test succeeded.' : 'Sync retry succeeded.',
    }
  }

  if (status === 'FAILED') {
    return {
      tone: 'danger',
      text: kind === 'connection_test' ? 'Connection test failed.' : 'Sync retry failed.',
    }
  }

  if (status === 'UNSUPPORTED') {
    return {
      tone: 'warning',
      text: 'This action is not supported for this connection.',
    }
  }

  if (status === 'RUNNING') {
    return {
      tone: 'warning',
      text: 'The action is still running.',
    }
  }

  return fallback
}

/**
 * Derives a human-readable error description for an operation error.
 * @param {object | null | undefined} err
 * @returns {string}
 */
export function operationErrorText(err) {
  if (!err) {
    return 'The action could not be started.'
  }

  if (err.status === 409) {
    return 'This action is not supported for this connection.'
  }

  if (err.status === 403) {
    return 'Only owners and managers can run this action.'
  }

  if (err.status === 0 || err.status === 408) {
    return 'The server could not be reached. Try again in a moment.'
  }

  if (typeof err.detail === 'string' && err.detail.trim().length > 0) {
    return err.detail
  }

  return 'The action could not be started.'
}
