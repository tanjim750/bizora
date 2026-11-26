import { ApiError } from './errors';
import type { ApiRequest, ApiResponse, Transport } from './types';

export function createHttpTransport(
  baseUrl: string,
  options: { revalidate?: number } = {},
): Transport {
  const cleanBaseUrl = baseUrl.replace(/\/+$/, '');

  return async function httpTransport(req: ApiRequest): Promise<ApiResponse> {
    const cleanPath = req.path.startsWith('/') ? req.path : '/' + req.path;
    let url = `${cleanBaseUrl}${cleanPath}`;

    if (req.query) {
      const params = new URLSearchParams();
      for (const [key, val] of Object.entries(req.query)) {
        if (val === undefined) continue;
        if (Array.isArray(val)) {
          for (const item of val) {
            params.append(key, String(item));
          }
        } else if (typeof val === 'boolean') {
          params.append(key, val ? 'true' : 'false');
        } else {
          params.append(key, String(val));
        }
      }
      const qs = params.toString();
      if (qs) {
        url += (url.includes('?') ? '&' : '?') + qs;
      }
    }

    const headers: Record<string, string> = {
      accept: 'application/json',
      ...req.headers,
    };
    if (req.body !== undefined) {
      headers['content-type'] = 'application/json';
    }

    const init: RequestInit & { next?: { revalidate?: number } } = {
      method: req.method,
      headers,
      credentials: 'include',
    };

    if (req.body !== undefined) {
      init.body = JSON.stringify(req.body);
    }

    if (req.method !== 'GET') {
      init.cache = 'no-store';
    } else if (options.revalidate !== undefined) {
      init.next = { revalidate: options.revalidate };
    }

    let res: Response;
    try {
      res = await fetch(url, init);
    } catch {
      throw new ApiError(0, 'NETWORK_ERROR', 'Network request failed');
    }

    let body: unknown = null;
    if (res.status === 204) {
      body = null;
    } else {
      const text = await res.text();
      if (text) {
        try {
          body = JSON.parse(text);
        } catch {
          body = null;
        }
      }
    }

    const resHeaders: Record<string, string> = {};
    res.headers.forEach((val, key) => {
      resHeaders[key.toLowerCase()] = val;
    });

    return {
      status: res.status,
      body,
      headers: resHeaders,
    };
  };
}
