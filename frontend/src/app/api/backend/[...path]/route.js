const BACKEND_ORIGIN = process.env.DJANGO_API_ORIGIN || 'http://127.0.0.1:8000'
const ALLOWED_ROOTS = new Set(['frontend', 'businesses', 'actions'])

async function proxy(request, context) {
  const { path } = await context.params
  if (
    !path?.length ||
    !ALLOWED_ROOTS.has(path[0]) ||
    path.some((segment) => !/^[a-zA-Z0-9_-]+$/.test(segment))
  ) {
    return Response.json({ detail: 'Unknown API route.' }, { status: 404 })
  }
  if (request.method !== 'GET') {
    const origin = request.headers.get('origin')
    const requestUrl = new URL(request.url)
    let sameOrigin = !origin
    if (origin) {
      try {
        const submitted = new URL(origin)
        sameOrigin =
          submitted.host === (request.headers.get('host') || requestUrl.host) &&
          submitted.protocol === requestUrl.protocol
      } catch {
        sameOrigin = false
      }
    }
    if (!sameOrigin) {
      return Response.json({ detail: 'Cross-origin request denied.' }, { status: 403 })
    }
  }
  const destination = new URL(`/api/${path.join('/')}/`, BACKEND_ORIGIN)
  destination.search = new URL(request.url).search
  const headers = { accept: 'application/json' }
  for (const name of ['cookie', 'content-type', 'x-csrftoken', 'idempotency-key']) {
    const value = request.headers.get(name)
    if (value) headers[name] = value
  }
  if (request.method !== 'GET') headers.origin = destination.origin
  try {
    const upstream = await fetch(destination, {
      method: request.method,
      headers,
      body: ['GET', 'HEAD'].includes(request.method) ? undefined : await request.text(),
      cache: 'no-store',
      redirect: 'manual',
    })
    const contentType = upstream.headers.get('content-type') || 'application/json'
    let body = await upstream.text()
    if (upstream.ok && contentType.includes('application/json') && body.includes('"results"')) {
      try {
        const data = JSON.parse(body)
        if (Array.isArray(data.results)) {
          let changed = false
          for (const key of ['next', 'previous']) {
            if (typeof data[key] !== 'string') continue
            const link = new URL(data[key])
            if (link.origin !== destination.origin || !link.pathname.startsWith('/api/')) continue
            data[key] = `/api/backend${link.pathname.slice(4)}${link.search}`
            changed = true
          }
          if (changed) body = JSON.stringify(data)
        }
      } catch {
        // Keep the upstream response if a nonstandard JSON payload cannot be inspected.
      }
    }
    const response = new Response(body, {
      status: upstream.status,
      headers: {
        'content-type': contentType,
        'cache-control': 'no-store',
      },
    })
    for (const cookie of upstream.headers.getSetCookie()) response.headers.append('set-cookie', cookie)
    return response
  } catch {
    return Response.json({ detail: 'Backend unavailable. Check the Django service.' }, { status: 503 })
  }
}

export const GET = proxy
export const POST = proxy
export const PUT = proxy
export const PATCH = proxy
export const DELETE = proxy
