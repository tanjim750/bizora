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

  const mockRes = await handleMockRequest({
    method: req.method,
    path: req.path,
    query: req.query,
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
