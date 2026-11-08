import { cookies } from 'next/headers'

const BACKEND_ORIGIN = process.env.DJANGO_API_ORIGIN || 'http://127.0.0.1:8000'

export async function serverApi(path, options = {}) {
  const cookieHeader = (await cookies()).toString()
  try {
    const response = await fetch(new URL(`/api/${path}`, BACKEND_ORIGIN), {
      ...options,
      headers: { accept: 'application/json', cookie: cookieHeader, ...options.headers },
      cache: 'no-store',
    })
    const data = await response.json().catch(() => null)
    return { ok: response.ok, status: response.status, data }
  } catch {
    return { ok: false, status: 503, data: { detail: 'Backend unavailable. Check the Django service.' } }
  }
}

export async function getSession() {
  return (await serverApi('frontend/session/')).data || { authenticated: false, businesses: [] }
}
