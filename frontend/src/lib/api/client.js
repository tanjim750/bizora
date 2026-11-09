import { ApiError, normalizeError } from './errors.js'

function csrfToken() {
  if (typeof document === 'undefined') return ''
  const pair = document.cookie.split('; ').find((item) => item.startsWith('csrftoken='))
  return pair ? decodeURIComponent(pair.slice('csrftoken='.length)) : ''
}

/**
 * Validates that a path is a safe, same-site relative path starting with a single '/'
 * to prevent open redirects.
 */
export function isSafeRelativePath(path) {
  if (typeof path !== 'string') return false
  return path.startsWith('/') && !path.startsWith('//') && !path.includes('://')
}

/**
 * Client-side fetch wrapper communicating via the same-origin /api/backend/ proxy.
 */
export async function clientApi(
  path,
  { method = 'GET', body, headers = {}, timeoutMs = 15000, _retried = false } = {},
) {
  const cleanPath = path.startsWith('/') ? path.slice(1) : path
  const url = `/api/backend/${cleanPath}`

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(url, {
      method,
      credentials: 'same-origin',
      signal: controller.signal,
      headers: {
        accept: 'application/json',
        ...(body === undefined ? {} : { 'content-type': 'application/json' }),
        ...(method === 'GET' ? {} : { 'X-CSRFToken': csrfToken() }),
        ...headers,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: 'no-store',
    })

    const data = await response.json().catch(() => null)

    if (!response.ok) {
      const normalized = normalizeError(data, response.status)

      // Handle CSRF expiration with a single automatic retry
      if (response.status === 403 && normalized.detail.toLowerCase().includes('csrf') && !_retried) {
        await fetch('/api/backend/frontend/session', { cache: 'no-store' }).catch(() => null)
        return clientApi(path, {
          method,
          body,
          headers,
          timeoutMs,
          _retried: true,
        })
      }

      // Handle session expiry (403 Authentication credentials were not provided)
      if (
        response.status === 403 &&
        (normalized.detail.includes('credentials were not provided') ||
          normalized.code === 'UNAUTHENTICATED' ||
          normalized.code === 'SESSION_EXPIRED')
      ) {
        if (typeof window !== 'undefined') {
          const currentPath = window.location.pathname + window.location.search
          const next = isSafeRelativePath(currentPath) ? encodeURIComponent(currentPath) : ''
          window.location.href = next ? `/login?next=${next}` : '/login'
        }
      }

      throw new ApiError(normalized)
    }

    return data
  } catch (err) {
    if (err instanceof ApiError) throw err
    if (err.name === 'AbortError') {
      throw new ApiError({
        status: 408,
        code: 'TIMEOUT',
        detail: 'Request timed out. Please try again.',
        raw: err,
      })
    }
    throw new ApiError({
      status: 0,
      code: 'NETWORK_ERROR',
      detail: err?.message || 'Network connection failed.',
      raw: err,
    })
  } finally {
    clearTimeout(timer)
  }
}
