function csrfToken() {
  const pair = document.cookie.split('; ').find((item) => item.startsWith('csrftoken='))
  return pair ? decodeURIComponent(pair.slice('csrftoken='.length)) : ''
}

export function errorMessage(data, status) {
  if (!data || typeof data !== 'object') return `Request failed (${status})`
  for (const key of ['detail', 'error', 'message']) {
    if (typeof data[key] === 'string') return data[key]
  }
  const first = Object.entries(data)[0]
  if (first) return `${first[0]}: ${Array.isArray(first[1]) ? first[1].join(' ') : String(first[1])}`
  return `Request failed (${status})`
}

export async function clientApi(path, { method = 'GET', body, headers = {} } = {}) {
  const response = await fetch(`/api/backend/${path}`, {
    method,
    credentials: 'same-origin',
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
  if (!response.ok) throw new Error(errorMessage(data, response.status))
  return data
}
