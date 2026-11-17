// @purpose Development-only "Continue as demo owner" sign-in helpers. Never active in a production build.

const LOOPBACK_HOSTNAMES = new Set(['localhost', '127.0.0.1', '[::1]'])

function hostnameOf(hostHeader) {
  try {
    return new URL(`http://${hostHeader}`).hostname
  } catch {
    return ''
  }
}

function backendIsLoopback(env) {
  try {
    return LOOPBACK_HOSTNAMES.has(new URL(env.DJANGO_API_ORIGIN || 'http://127.0.0.1:8000').hostname)
  } catch {
    return false
  }
}

/**
 * Returns the demo credentials only when ALL of these hold (fail closed):
 *  - NODE_ENV is exactly "development" (so unset, "test", "production" or anything else is OFF),
 *  - BIZORA_DEMO_LOGIN is exactly "1",
 *  - BIZORA_DEMO_USERNAME and BIZORA_DEMO_PASSWORD are both set (server-side environment only),
 *  - the Django backend origin is on this machine (localhost, 127.0.0.1 or [::1]).
 * Otherwise returns null and the feature does not exist (the route answers 404, the button is hidden).
 */
export function demoLoginConfig(env = process.env) {
  if (env.NODE_ENV !== 'development') return null
  if (env.BIZORA_DEMO_LOGIN !== '1') return null
  const username = env.BIZORA_DEMO_USERNAME
  const password = env.BIZORA_DEMO_PASSWORD
  if (!username || !password) return null
  if (!backendIsLoopback(env)) return null
  return { username, password }
}

/**
 * True only when the request was addressed to this machine (Host is localhost, 127.0.0.1 or [::1]).
 * This blocks other devices on the network and DNS-rebinding pages, whose Host is a name or LAN address.
 */
export function isLocalRequest(request) {
  const host = request.headers.get('host') || new URL(request.url).host
  return LOOPBACK_HOSTNAMES.has(hostnameOf(host))
}

/** Same-origin check for unsafe requests. A missing Origin header is allowed (non-browser clients); "null" is not. */
export function isSameOrigin(request) {
  const origin = request.headers.get('origin')
  if (!origin) return true
  try {
    const submitted = new URL(origin)
    const requestUrl = new URL(request.url)
    return (
      submitted.host === (request.headers.get('host') || requestUrl.host) &&
      submitted.protocol === requestUrl.protocol
    )
  } catch {
    return false
  }
}

/** Browsers label cross-site requests with Sec-Fetch-Site; refuse those. Non-browser clients send nothing. */
export function fetchSiteAllowed(request) {
  const site = request.headers.get('sec-fetch-site')
  return !site || site === 'same-origin' || site === 'none'
}

/** Reads one cookie's value out of a list of Set-Cookie header strings. */
export function cookieFromSetCookie(setCookies, name) {
  for (const line of setCookies) {
    const first = line.split(';', 1)[0]
    if (first.startsWith(`${name}=`)) return first.slice(name.length + 1)
  }
  return ''
}
