import {
  cookieFromSetCookie,
  demoLoginConfig,
  fetchSiteAllowed,
  isLocalRequest,
  isSameOrigin,
} from '../../../lib/demoLogin.js'

// Development-only demo sign-in. The username and password come from server-side environment variables and are
// never sent to the browser or written to code. The route does not exist (404) unless ALL of these hold: a
// development server, BIZORA_DEMO_LOGIN=1, credentials set, a backend on this machine, and a request addressed to
// localhost / 127.0.0.1 / [::1]. In a production build it is always off.

const noStore = { 'cache-control': 'no-store' }

export async function GET(request) {
  const enabled = demoLoginConfig() !== null && isLocalRequest(request)
  return Response.json({ enabled }, { headers: noStore })
}

export async function POST(request) {
  const demo = demoLoginConfig()
  if (!demo || !isLocalRequest(request)) {
    return Response.json({ detail: 'Not found.' }, { status: 404, headers: noStore })
  }
  if (!isSameOrigin(request) || !fetchSiteAllowed(request)) {
    return Response.json({ detail: 'Cross-origin request denied.' }, { status: 403, headers: noStore })
  }
  const backend = new URL(process.env.DJANGO_API_ORIGIN || 'http://127.0.0.1:8000')
  try {
    const session = await fetch(new URL('/api/frontend/session/', backend), {
      headers: { accept: 'application/json' },
      cache: 'no-store',
      redirect: 'manual',
    })
    const csrf = cookieFromSetCookie(session.headers.getSetCookie(), 'csrftoken')
    if (!csrf) {
      return Response.json(
        { detail: 'Demo sign-in failed: no CSRF token from the backend.' },
        { status: 502, headers: noStore },
      )
    }
    const upstream = await fetch(new URL('/api/frontend/login/', backend), {
      method: 'POST',
      headers: {
        accept: 'application/json',
        'content-type': 'application/json',
        cookie: `csrftoken=${csrf}`,
        'x-csrftoken': csrf,
        origin: backend.origin,
      },
      body: JSON.stringify({ username: demo.username, password: demo.password }),
      cache: 'no-store',
      redirect: 'manual',
    })
    if (!upstream.ok) {
      console.error(`[demo-login] backend refused the demo sign-in (HTTP ${upstream.status})`)
      return Response.json(
        { detail: 'Demo sign-in failed. Check that the demo user exists in the local database.' },
        { status: 502, headers: noStore },
      )
    }
    const response = Response.json({ authenticated: true }, { headers: noStore })
    for (const cookie of upstream.headers.getSetCookie()) response.headers.append('set-cookie', cookie)
    return response
  } catch (error) {
    console.error(`[demo-login] backend request failed (${error?.name ?? 'error'})`)
    return Response.json(
      { detail: 'Backend unavailable. Check the Django service.' },
      { status: 503, headers: noStore },
    )
  }
}
