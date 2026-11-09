import { cookies } from 'next/headers'
import { cache } from 'react'

const BACKEND_ORIGIN = process.env.DJANGO_API_ORIGIN || 'http://127.0.0.1:8000'

/**
 * Server-side API client for fetching data directly from the Django backend in Server Components.
 */
export async function serverApi(path, options = {}) {
  let cookieHeader = ''
  try {
    cookieHeader = (await cookies()).toString()
  } catch {
    // cookies() unavailable outside request context
  }

  const cleanPath = path.startsWith('/') ? path.slice(1) : path
  const url = new URL(`/api/${cleanPath}`, BACKEND_ORIGIN)

  try {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), options.timeoutMs || 15000)

    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        accept: 'application/json',
        cookie: cookieHeader,
        ...options.headers,
      },
      cache: 'no-store',
    }).finally(() => clearTimeout(timer))

    const data = await response.json().catch(() => null)
    return { ok: response.ok, status: response.status, data }
  } catch {
    return {
      ok: false,
      status: 503,
      data: { detail: 'Backend unavailable. Check the Django service.' },
    }
  }
}

/**
 * React.cached helper to fetch the current user session once per request waterfall.
 */
export const getSession = cache(async () => {
  const result = await serverApi('frontend/session/')
  return result.ok && result.data?.authenticated ? result.data : { authenticated: false, businesses: [] }
})
