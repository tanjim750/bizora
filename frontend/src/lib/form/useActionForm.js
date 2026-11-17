'use client'

import { useRef, useState, useCallback } from 'react'
import { newIdempotencyKey } from '../api/idempotency.js'
import { ApiError } from '../api/errors.js'

/**
 * Hook for managing action forms with safe writes:
 * - Busy / loading indicator
 * - ApiError integration with field-level errors
 * - Single idempotency key per intent, reused on retry and rotated on success or payload change
 * - 409 STALE_STATE detection and reload flow (keeping user inputs)
 */
export function useActionForm({ onReload, onSuccess } = {}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [stale, setStale] = useState(false)

  const keyRef = useRef(newIdempotencyKey())
  const [idempotencyKey, setIdempotencyKey] = useState(() => keyRef.current)
  const lastPayloadRef = useRef(null)

  const reset = useCallback(() => {
    setBusy(false)
    setError('')
    setSuccess('')
    setFieldErrors({})
    setStale(false)
    const nextKey = newIdempotencyKey()
    keyRef.current = nextKey
    setIdempotencyKey(nextKey)
    lastPayloadRef.current = null
  }, [])

  const execute = useCallback(
    async (actionFn, payload = {}) => {
      setBusy(true)
      setError('')
      setSuccess('')
      setFieldErrors({})
      setStale(false)

      // Compare current payload to last payload.
      // If payload changed, rotate to a new idempotency key.
      // If retrying the exact same payload, reuse the existing key!
      const serialized = JSON.stringify(payload)
      if (lastPayloadRef.current !== null && lastPayloadRef.current !== serialized) {
        const nextKey = newIdempotencyKey()
        keyRef.current = nextKey
        setIdempotencyKey(nextKey)
      }
      lastPayloadRef.current = serialized

      try {
        const result = await actionFn(payload, keyRef.current)
        setBusy(false)
        setSuccess('Action completed successfully.')

        // Rotate key on success for the next user intent
        const nextKey = newIdempotencyKey()
        keyRef.current = nextKey
        setIdempotencyKey(nextKey)
        lastPayloadRef.current = null

        if (onSuccess) onSuccess(result)
        return result
      } catch (err) {
        setBusy(false)

        if (err?.status === 409 || err?.code === 'STALE_STATE') {
          setStale(true)
          setError('This record changed. Reloaded with latest data.')
          if (onReload) {
            try {
              await onReload()
            } catch {
              // Ignore reload failure
            }
          }
          return null
        }

        if (err instanceof ApiError) {
          setError(err.detail)
          setFieldErrors(err.fieldErrors || {})
        } else {
          setError(err?.message || 'An unexpected error occurred.')
        }

        return null
      }
    },
    [onReload, onSuccess],
  )

  return {
    busy,
    error,
    success,
    fieldErrors,
    stale,
    idempotencyKey,
    execute,
    reset,
    setError,
    setSuccess,
  }
}

export default useActionForm
