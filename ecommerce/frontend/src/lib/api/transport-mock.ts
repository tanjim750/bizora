import 'server-only';
import { handleMockRequest } from '@/mocks/server/router';
import type { ApiRequest, ApiResponse, Transport } from './types';

export const mockTransport: Transport = async function mockTransport(
  req: ApiRequest,
): Promise<ApiResponse> {
  const headers: Record<string, string> = {};
  if (req.headers) {
    for (const [k, v] of Object.entries(req.headers)) {
      headers[k.toLowerCase()] = v;
    }
  }

  if (req.body !== undefined && !headers['content-type']) {
    headers['content-type'] = 'application/json';
  }

  const query: Record<string, string | string[]> = {};
  if (req.query) {
    for (const [k, v] of Object.entries(req.query)) {
      if (v === undefined) continue;
      if (Array.isArray(v)) {
        query[k] = v.map((item) => String(item));
      } else {
        query[k] = String(v);
      }
    }
  }

  const mockRes = await handleMockRequest({
    method: req.method,
    path: req.path,
    query,
    body: req.body,
    headers,
    cookies: {},
  });

  return {
    status: mockRes.status,
    body: mockRes.body,
    headers: mockRes.headers,
  };
};
